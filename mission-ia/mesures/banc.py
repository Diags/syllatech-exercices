"""Passe le banc de la mission sur une approche, deux fois, et écrit le résultat.

    uv run python mesures/banc.py modele-seul|rag|agent|guide [modèle Ollama]

Chaque approche passe le banc (14 cas) ET le jeu de validation (8 cas jamais
regardés pour régler l'assistant).

Deux passages, parce que température 0 et graine fixe ne garantissent pas une
réponse identique (mesuré au cours « LLM en local ») : un écart entre les deux
se voit dans le fichier, au lieu d'être caché par une seule mesure.
Il faut Ollama, et : ollama pull qwen2.5:1.5b-instruct-q4_K_M
"""

import datetime
import json
import pathlib
import sys
import time

import ollama

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from jobportal import agent, securite  # noqa: E402
from jobportal.banc import CAS, CAS_VALIDATION, noter  # noqa: E402
from jobportal.donnees import OFFRES  # noqa: E402
from jobportal.recherche import Index  # noqa: E402

MODELE = "qwen2.5:1.5b-instruct-q4_K_M"
SYSTEME = ("Tu es l'assistant du portail d'emploi. Tu réponds aux candidats et aux recruteurs sur les "
           "offres du portail, en français, en citant la référence de chaque offre (OFF-xxx).")
PASSAGES = 2
# Sans borne, le modèle seul a écrit jusqu'à 3 278 jetons pour UNE question — une
# liste d'offres inventées, des minutes de calcul (journal d'Ollama : « truncated = 1 »,
# il a fait glisser son contexte pour continuer). En production, on borne toujours.
OPTIONS = {"temperature": 0, "seed": 42, "num_predict": 400}

sys.stdout.reconfigure(encoding="utf-8")


def modele_seul(client: ollama.Client, modele: str):
    """Le modèle, avec des consignes, mais sans aucune donnée du portail."""
    def repondre(question: str) -> str:
        r = client.chat(model=modele, messages=[{"role": "system", "content": SYSTEME},
                                                {"role": "user", "content": question}],
                        options=OPTIONS)
        return r.message.content
    return repondre


def rag(client: ollama.Client, modele: str):
    index = Index(client, OFFRES)
    return lambda question: agent.repondre_rag(client, index, question, modele)[0]


def agent_outille(client: ollama.Client, modele: str):
    index = Index(client, OFFRES)
    return lambda question: agent.repondre_agent(client, index, question, modele)[0]


def guide(client: ollama.Client, modele: str):
    index = Index(client, OFFRES)
    return lambda question: agent.repondre_guide(client, index, question, modele)[0]


def guide_relie(client: ollama.Client, modele: str):
    index = Index(client, OFFRES)
    return lambda question: agent.repondre_guide_relie(client, index, question, modele)[0]


def securise(client: ollama.Client, modele: str):
    index = Index(client, OFFRES)
    return lambda question: securite.repondre_securise(client, index, question, modele,
                                                       consigne_defensive=True)[0]


def securise_sans_d1(client: ollama.Client, modele: str):
    index = Index(client, OFFRES)
    return lambda question: securite.repondre_securise(client, index, question, modele,
                                                       consigne_defensive=False)[0]


APPROCHES = {"modele-seul": modele_seul, "rag": rag, "agent": agent_outille, "guide": guide,
             "guide-relie": guide_relie, "securise": securise, "securise-sans-d1": securise_sans_d1}
JEUX = {"banc": CAS, "validation": CAS_VALIDATION}


def passer(repondre, cas_du_jeu) -> dict:
    notes, debut = [], time.perf_counter()
    for cas in cas_du_jeu:
        reponse = repondre(cas["question"])
        notes.append({**noter(cas, reponse), "reponse": reponse})
    return {"justes": sum(n["juste"] for n in notes), "total": len(notes),
            "secondes": round(time.perf_counter() - debut, 1), "notes": notes}


def main() -> int:
    approche = sys.argv[1] if len(sys.argv) > 1 else "modele-seul"
    modele = sys.argv[2] if len(sys.argv) > 2 else MODELE
    repondre = APPROCHES[approche](ollama.Client(), modele)
    passages = []
    for k in range(PASSAGES):
        passage = {}
        for nom, cas_du_jeu in JEUX.items():
            p = passer(repondre, cas_du_jeu)
            passage[nom] = p
            print(f"passage {k + 1}, {nom} : {p['justes']}/{p['total']} cas justes, {p['secondes']} s")
            for n in p["notes"]:
                echecs = [c for c, ok in n["controles"].items() if not ok]
                print(f"   {'✓' if n['juste'] else '✗'} {n['id']:<22} {', '.join(echecs)}")
        passages.append(passage)
    suffixe = "" if modele == MODELE else "-" + modele.split(":")[1].split("-")[0]  # ex. « -3b »
    sortie = pathlib.Path(__file__).with_name(f"banc-{approche}{suffixe}.json")
    sortie.write_text(json.dumps({"approche": approche, "modele": modele,
                                  "date": datetime.date.today().isoformat(), "passages": passages},
                                 ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"écrit : {sortie}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
