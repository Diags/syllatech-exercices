"""Les mesures du cours, rejouables sur votre machine.

    uv run python mesures/mesurer.py             mesure, écrit mesures/resultats.json
    uv run python mesures/mesurer.py --comparer  mesure, compare au fichier sans l'écraser

Il faut Ollama installé et les modèles téléchargés :
    ollama pull qwen2.5:1.5b-instruct-q4_K_M
    ollama pull qwen2.5:1.5b-instruct-q8_0
    ollama pull qwen2.5:1.5b-instruct-fp16
    ollama pull bge-m3

LE SCRIPT LANCE SES PROPRES SERVEURS. Votre Ollama n'est ni utilisé ni
modifié : chaque mesure tourne sur un `ollama serve` temporaire (port 11435),
lancé avec une configuration connue, enregistrée dans les résultats, et arrêté
à la fin. Mesuré sur ce poste, à une minute d'intervalle, le même modèle
donnait 15 jetons/s sur le serveur de l'application Ollama et 33 sur un serveur
lancé à la main : des chiffres pris sur des serveurs différents ne se comparent pas.

LES VITESSES DÉPENDENT DE LA MACHINE, ET DE CE QU'ELLE FAIT D'AUTRE. Sur un
portable en usage, la même requête a varié de 13 à 36 jetons/s. Les trois
quantizations sont donc mesurées EN ALTERNANCE (q4, q8, fp16, q4, q8, fp16…),
chargées ensemble : une charge passagère les touche toutes, et la comparaison
reste juste même quand les chiffres absolus baissent. La charge du processeur
est relevée à chaque tour.

Les durées viennent d'Ollama lui-même (champs *_duration, en nanosecondes),
pas d'un chronomètre autour de l'appel. Sauf le débit en parallèle, qui est par
nature un temps mesuré de l'extérieur.

⚠️ Ollama garde en cache le début du dernier prompt de chaque modèle : un
prompt identique n'est pas relu, mais `prompt_eval_count` compte quand même
tous ses jetons. Chaque mesure de vitesse commence donc par un préfixe
différent (« Essai n »), et l'effet du cache est mesuré à part.
"""

import concurrent.futures
import contextlib
import ctypes
import datetime
import json
import os
import pathlib
import platform
import re
import statistics
import subprocess
import sys
import tempfile
import time

import httpx
import ollama

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from jobportal.donnees import ANNONCES, CHAMPS, OFFRES  # noqa: E402
from jobportal.fiche import champs_justes, extraire_fiche  # noqa: E402

MODELES = ["qwen2.5:1.5b-instruct-q4_K_M", "qwen2.5:1.5b-instruct-q8_0", "qwen2.5:1.5b-instruct-fp16"]
EMBEDDINGS = "bge-m3"
RESULTATS = pathlib.Path(__file__).with_name("resultats.json")
PORT = 11435

PROMPT_VITESSE = "Rédige une annonce d'environ 150 mots pour un poste de développeur Java à Lyon."
# Un prompt long pour mesurer la lecture : les douze annonces à la suite.
PROMPT_LONG = "Résume ces annonces en une ligne chacune.\n\n" + "\n\n".join(a["texte"] for a in ANNONCES)
TOURS = 7
JETONS_GENERES = 96  # court : la charge de la machine change moins au cours d'un tour
CONTEXTES = [2048, 8192, 32768]
REGLAGES = ["OLLAMA_NUM_PARALLEL", "OLLAMA_MAX_LOADED_MODELS", "OLLAMA_CONTEXT_LENGTH",
            "OLLAMA_KEEP_ALIVE", "OLLAMA_FLASH_ATTENTION", "OLLAMA_KV_CACHE_TYPE"]

sys.stdout.reconfigure(encoding="utf-8")


# ---------------------------------------------------------------- la machine

def machine() -> dict:
    info = {"systeme": platform.platform(), "threads": os.cpu_count(), "processeur": platform.processor()}
    if sys.platform == "win32":
        import winreg
        cle = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
        info["processeur"] = winreg.QueryValueEx(cle, "ProcessorNameString")[0].strip()

        class Memoire(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong)] + [
                (n, ctypes.c_ulonglong) for n in ("total", "dispo", "tp", "dp", "tv", "dv", "dev")]
        m = Memoire()
        m.dwLength = ctypes.sizeof(Memoire)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        info["ram_go"] = round(m.total / 1024**3, 1)
    return info


def charge_processeur(secondes: float = 1.0) -> float:
    """La charge du processeur, en %, sur `secondes` (Windows : GetSystemTimes)."""
    if sys.platform != "win32":
        return round(100 * os.getloadavg()[0] / os.cpu_count(), 1)

    def temps():
        idle, noyau, user = (ctypes.c_ulonglong() for _ in range(3))
        ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(noyau), ctypes.byref(user))
        return idle.value, noyau.value + user.value  # le temps noyau inclut l'inactivité

    i1, t1 = temps()
    time.sleep(secondes)
    i2, t2 = temps()
    return round(100 * (1 - (i2 - i1) / (t2 - t1)), 1)


# ---------------------------------------------------------------- les serveurs

@contextlib.contextmanager
def serveur(**reglages: str):
    """Un `ollama serve` temporaire sur le port 11435, avec ces réglages. Rend le
    client et la configuration que le serveur annonce lui-même au démarrage."""
    hote = f"http://127.0.0.1:{PORT}"
    with contextlib.suppress(httpx.HTTPError):
        httpx.get(f"{hote}/api/version", timeout=1)
        raise RuntimeError(f"le port {PORT} est déjà pris : un serveur précédent tourne encore")
    journal = tempfile.NamedTemporaryFile(prefix="ollama-mesure-", suffix=".log", delete=False)
    env = {**os.environ, "OLLAMA_HOST": f"127.0.0.1:{PORT}", **reglages}
    processus = subprocess.Popen(["ollama", "serve"], env=env, stdout=subprocess.DEVNULL, stderr=journal)
    try:
        for _ in range(150):
            with contextlib.suppress(httpx.HTTPError):
                httpx.get(f"{hote}/api/version", timeout=1)
                break
            time.sleep(0.2)
        else:
            raise RuntimeError(f"le serveur temporaire ne répond pas sur {hote}")
        texte = pathlib.Path(journal.name).read_text(encoding="utf-8", errors="replace")
        config = dict(re.findall(r"(OLLAMA_[A-Z_]+):(\S*?)(?=\s|\])", texte))
        yield ollama.Client(host=hote), {k: config.get(k, "?") for k in REGLAGES}
    finally:
        # Tout l'arbre : `ollama serve` lance un `llama-server` par modèle chargé, et
        # sous Windows terminate() n'arrête que le parent. Constaté le 07/10/2026 :
        # deux llama-server orphelins gardaient 2,8 Go de mémoire depuis la veille.
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(processus.pid)], capture_output=True)
        else:
            processus.terminate()
        processus.wait(timeout=30)
        journal.close()
        with contextlib.suppress(OSError):
            os.remove(journal.name)


def decharger_tout(client: ollama.Client) -> None:
    for m in client.ps().models:
        client.generate(model=m.model, prompt="", keep_alive=0)
    for _ in range(50):
        if not client.ps().models:
            return
        time.sleep(0.2)


def charge_du_modele(client: ollama.Client, modele: str):
    return next(m for m in client.ps().models if m.model == modele)


def par_seconde(compte: int, duree_ns: int) -> float:
    return round(compte / (duree_ns / 1e9), 1)


def chat(client: ollama.Client, modele: str, texte: str, **options):
    return client.chat(model=modele, messages=[{"role": "user", "content": texte}],
                       options={"temperature": 0, "seed": 42, **options}, keep_alive="30m")


# ---------------------------------------------------------------- les mesures

def mesurer_modeles(client: ollama.Client) -> dict:
    tailles = {m.model: m.size for m in client.list().models}
    resultats = {}

    print("\nchargement et mémoire, un modèle à la fois")
    for modele in MODELES:
        decharger_tout(client)
        froid = chat(client, modele, "Bonjour", num_predict=1)
        charge = charge_du_modele(client, modele)
        resultats[modele] = {
            "disque_mo": round(tailles[modele] / 1e6),
            "memoire_chargee_mo": round(charge.size / 1e6),
            "vram_mo": round(charge.size_vram / 1e6),
            "contexte_par_defaut": charge.context_length,
            "chargement_a_froid_s": round(froid.load_duration / 1e9, 2),
            "generation_mesures": [], "lecture_mesures": [],
        }
        print(f"   {modele:<30} {resultats[modele]['disque_mo']} Mo sur disque, "
              f"{resultats[modele]['memoire_chargee_mo']} Mo chargé, "
              f"froid {resultats[modele]['chargement_a_froid_s']} s")

    print(f"\nvitesse — {TOURS} tours, les trois modèles en alternance")
    for modele in MODELES:  # les trois chargés ensemble (OLLAMA_MAX_LOADED_MODELS=3)
        chat(client, modele, "Bonjour", num_predict=1)
    charges = []
    for k in range(TOURS):
        charges.append(charge_processeur())
        for modele in MODELES:
            r = chat(client, modele, f"Essai {k}. {PROMPT_VITESSE}", num_predict=JETONS_GENERES)
            resultats[modele]["generation_mesures"].append(par_seconde(r.eval_count, r.eval_duration))
            r = chat(client, modele, f"Essai {k}. {PROMPT_LONG}", num_predict=1)
            resultats[modele]["lecture_mesures"].append(par_seconde(r.prompt_eval_count, r.prompt_eval_duration))
            resultats[modele]["prompt_long_jetons"] = r.prompt_eval_count
            resultats[modele]["prompt_long_ms"] = round(r.prompt_eval_duration / 1e6)
        print(f"   tour {k + 1}, processeur à {charges[-1]} % : " + ", ".join(
            f"{m.split('-')[-1]} {resultats[m]['generation_mesures'][-1]}" for m in MODELES) + " jetons/s")

    for modele in MODELES:
        # Le dernier prompt long de ce modèle, à l'identique : le cache sert-il ?
        r = chat(client, modele, f"Essai {TOURS - 1}. {PROMPT_LONG}", num_predict=1)
        res = resultats[modele]
        res["prompt_long_relu_jetons"] = r.prompt_eval_count
        res["prompt_long_relu_ms"] = round(r.prompt_eval_duration / 1e6)
        res["generation_jetons_par_s"] = statistics.median(res["generation_mesures"])
        res["lecture_prompt_jetons_par_s"] = statistics.median(res["lecture_mesures"])
        res["charge_processeur_pourcent"] = charges

    # Chaque tour comparé à lui-même : la charge commune à un tour s'annule.
    for rapide, lent in zip(MODELES, MODELES[1:]):
        rapports = [a / b for a, b in zip(resultats[rapide]["generation_mesures"],
                                          resultats[lent]["generation_mesures"])]
        resultats[rapide][f"rapport_de_vitesse_sur_{lent.split('-')[-1]}"] = round(statistics.median(rapports), 2)
        print(f"   {rapide.split('-')[-1]} / {lent.split('-')[-1]}, médiane des rapports par tour : "
              f"{statistics.median(rapports):.2f}")

    print("\nqualité — extraction des 12 annonces")
    for modele in MODELES:
        justes, details, secondes = 0, [], 0.0
        for annonce in ANNONCES:
            fiche, r = extraire_fiche(client, modele, annonce["texte"])
            n = champs_justes(fiche, annonce["attendu"])
            justes += n
            secondes += r.total_duration / 1e9
            details.append({"obtenu": fiche, "justes": n})
        resultats[modele].update(extraction_champs_justes=justes,
                                 extraction_champs_total=len(ANNONCES) * len(CHAMPS),
                                 extraction_secondes_par_annonce=round(secondes / len(ANNONCES), 2),
                                 extraction_detail=details)
        print(f"   {modele:<30} {justes}/{len(ANNONCES) * len(CHAMPS)} champs justes")
    return resultats


def mesurer_contextes(client: ollama.Client, modele: str) -> dict:
    """La mémoire occupée par le modèle chargé, selon la fenêtre de contexte demandée."""
    print(f"\ncontexte — {modele}")
    resultat = {}
    for n in CONTEXTES:
        decharger_tout(client)
        chat(client, modele, "Bonjour", num_ctx=n, num_predict=1)
        charge = charge_du_modele(client, modele)
        resultat[str(n)] = {"memoire_mo": round(charge.size / 1e6), "context_length": charge.context_length}
        print(f"   num_ctx {n:<26} {resultat[str(n)]['memoire_mo']} Mo")
    return resultat


def mesurer_parallele(client: ollama.Client, modele: str, etiquette: str, n: int = 4) -> dict:
    """n requêtes l'une après l'autre, puis n en même temps : le débit total, et
    l'heure d'arrivée de chaque réponse. Des réponses qui arrivent en escalier
    ont fait la queue ; des réponses qui arrivent ensemble ont été traitées
    ensemble."""
    print(f"\nparallèle — {etiquette} — {n} requêtes sur {modele}")
    decharger_tout(client)
    chat(client, modele, "Bonjour", num_predict=1)

    def une(k, debut):
        r = chat(client, modele, f"Requête {k}. {PROMPT_VITESSE}", num_predict=64)
        return r.eval_count, round(time.perf_counter() - debut, 2)

    charge = charge_processeur()
    debut = time.perf_counter()
    jetons = sum(une(k, debut)[0] for k in range(n))
    sequentiel = time.perf_counter() - debut
    debut = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(n) as pool:
        reponses = list(pool.map(lambda k: une(n + k, debut), range(n)))
    simultane = time.perf_counter() - debut
    resultat = {
        "charge_processeur_pourcent": charge,
        "requetes": n,
        "sequentiel_s": round(sequentiel, 2),
        "sequentiel_jetons_par_s": round(jetons / sequentiel, 1),
        "simultane_s": round(simultane, 2),
        "simultane_jetons_par_s": round(sum(j for j, _ in reponses) / simultane, 1),
        "simultane_arrivees_s": sorted(t for _, t in reponses),
    }
    for cle, valeur in resultat.items():
        print(f"   {cle:<34} {valeur}")
    return resultat


def mesurer_embeddings(client: ollama.Client) -> dict:
    """Chaque offre, puis une question par offre : la bonne offre arrive-t-elle en tête ?"""
    print(f"\nembeddings — {EMBEDDINGS}")
    decharger_tout(client)
    textes = [f"{o['titre']} chez {o['entreprise']}, {o['contrat']} à {o['ville']}, {o['mode']}"
              for o in OFFRES]
    questions = [
        "Je cherche un poste de développeur Java expérimenté dans la région lyonnaise",
        "Un emploi DevOps que je peux faire depuis chez moi",
        "Travailler sur l'intelligence artificielle et le machine learning",
        "Mission de design d'interfaces en indépendant",
        "Développeur front et back, contrat court, Alpes",
        "Finance d'entreprise et analyse de comptes",
    ]
    r_offres = client.embed(model=EMBEDDINGS, input=textes)
    r_questions = client.embed(model=EMBEDDINGS, input=questions)

    def cosinus(a, b):
        return sum(x * y for x, y in zip(a, b)) / (sum(x * x for x in a) ** 0.5 * sum(y * y for y in b) ** 0.5)

    rangs = []
    for i, q in enumerate(r_questions.embeddings):
        scores = [cosinus(q, o) for o in r_offres.embeddings]
        rangs.append(sorted(scores, reverse=True).index(scores[i]) + 1)
    resultat = {
        "rang_de_la_bonne_offre": dict(zip(questions, rangs)),
        "dimension": len(r_offres.embeddings[0]),
        "chargement_a_froid_s": round(r_offres.load_duration / 1e9, 2),
        "ms_par_texte": round((r_questions.total_duration - r_questions.load_duration) / 1e6 / len(questions), 1),
        "bonne_offre_en_tete": rangs.count(1),
        "questions": len(questions),
    }
    for cle, valeur in resultat.items():
        print(f"   {cle:<34} {valeur}")
    return resultat


# ---------------------------------------------------------------- ce que le cours affirme

def constats(r: dict) -> dict:
    """Ce que le cours affirme, tiré d'un passage. Une vitesse brute dépend de la
    charge de la machine ; ces constats-là ne doivent pas en dépendre."""
    m = [r["modeles"][x] for x in MODELES]
    p1, p4 = r["parallele"]["OLLAMA_NUM_PARALLEL=1"], r["parallele"]["OLLAMA_NUM_PARALLEL=4"]
    return {
        "q4 génère plus vite que q8 (médiane des rapports par tour > 1)":
            m[0]["rapport_de_vitesse_sur_q8_0"] > 1,
        "q8 génère plus vite que fp16 (médiane des rapports par tour > 1)":
            m[1]["rapport_de_vitesse_sur_fp16"] > 1,
        "OLLAMA_NUM_PARALLEL=1 : les réponses simultanées arrivent en escalier":
            all(b - a > 1.0 for a, b in zip(p1["simultane_arrivees_s"], p1["simultane_arrivees_s"][1:])),
        # Deux serveurs mesurés l'un après l'autre ne voient pas la même charge :
        # on compare chaque serveur à lui-même, en série puis en simultané.
        "OLLAMA_NUM_PARALLEL=4 : les réponses simultanées arrivent ensemble (à moins de 0,5 s)":
            p4["simultane_arrivees_s"][-1] - p4["simultane_arrivees_s"][0] < 0.5,
        "OLLAMA_NUM_PARALLEL=4 : plus de jetons/s en simultané qu'en série (rapport > 1,2)":
            p4["simultane_jetons_par_s"] > 1.2 * p4["sequentiel_jetons_par_s"],
        "le cache évite plus de 90 % de la relecture du prompt long":
            all(x["prompt_long_relu_ms"] < 0.1 * x["prompt_long_ms"] for x in m),
    }


def comparer(avant: dict, apres: dict) -> int:
    """Égalité stricte sur le déterministe (température 0, graine fixe, tailles) ;
    constats tenus dans les deux passages ; vitesses affichées, pas jugées."""
    ecarts = 0

    def verifier(ok: bool, texte: str) -> None:
        nonlocal ecarts
        ecarts += not ok
        print(f"   {'✓' if ok else '✗'} {texte}")

    print("\nCOMPARAISON avec mesures/resultats.json")
    for modele in MODELES:
        a, b = avant["modeles"][modele], apres["modeles"][modele]
        for cle in ("extraction_champs_justes", "disque_mo", "contexte_par_defaut"):
            verifier(a[cle] == b[cle], f"{modele} {cle} : {a[cle]} → {b[cle]}")
        verifier(abs(b["memoire_chargee_mo"] / a["memoire_chargee_mo"] - 1) <= 0.02,
                 f"{modele} memoire_chargee_mo : {a['memoire_chargee_mo']} → {b['memoire_chargee_mo']}")
    for n in avant["contextes"]:
        a, b = avant["contextes"][n]["memoire_mo"], apres["contextes"][n]["memoire_mo"]
        verifier(abs(b / a - 1) <= 0.02, f"num_ctx {n} : {a} → {b} Mo")
    verifier(avant["embeddings"]["rang_de_la_bonne_offre"] == apres["embeddings"]["rang_de_la_bonne_offre"],
             "embeddings : rangs identiques")
    for texte, ok in constats(apres).items():
        verifier(ok and constats(avant)[texte], f"constat tenu dans les deux passages : {texte}")
    print("\n   vitesses (dépendent de la charge, affichées pour information) :")
    for modele in MODELES:
        a, b = avant["modeles"][modele], apres["modeles"][modele]
        print(f"     {modele:<30} génération {a['generation_mesures']} → {b['generation_mesures']}")
    return ecarts


def main() -> int:
    resultats = {"date": datetime.date.today().isoformat(), "machine": machine()}
    with serveur(OLLAMA_MAX_LOADED_MODELS="3", OLLAMA_NUM_PARALLEL="1") as (client, config):
        presents = {m.model for m in client.list().models}
        manquants = [m for m in MODELES + [EMBEDDINGS] if m not in presents and f"{m}:latest" not in presents]
        if manquants:
            print("Modèles absents — lancez : " + " ; ".join(f"ollama pull {m}" for m in manquants))
            return 1
        resultats["ollama"] = client._client.get("/api/version").json()["version"]
        resultats["serveur_mesures"] = config
        print(f"serveur temporaire : {config}")
        resultats["modeles"] = mesurer_modeles(client)
        resultats["contextes"] = mesurer_contextes(client, MODELES[0])
        resultats["parallele"] = {"OLLAMA_NUM_PARALLEL=1": mesurer_parallele(client, MODELES[0], "réglé à 1")}
        resultats["embeddings"] = mesurer_embeddings(client)
        decharger_tout(client)
    with serveur(OLLAMA_NUM_PARALLEL="4") as (client, config):
        resultats["parallele"]["OLLAMA_NUM_PARALLEL=4"] = mesurer_parallele(client, MODELES[0], "réglé à 4")
        resultats["parallele"]["OLLAMA_NUM_PARALLEL=4"]["serveur"] = config
        decharger_tout(client)

    resultats["constats"] = constats(resultats)
    print("\nconstats")
    for texte, ok in resultats["constats"].items():
        print(f"   {'✓' if ok else '✗'} {texte}")

    if "--comparer" in sys.argv:
        trace = RESULTATS.with_name("resultats-comparaison.json")
        trace.write_text(json.dumps(resultats, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        return 1 if comparer(json.loads(RESULTATS.read_text(encoding="utf-8")), resultats) else 0
    RESULTATS.write_text(json.dumps(resultats, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"\nécrit : {RESULTATS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
