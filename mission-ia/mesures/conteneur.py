"""Construit l'image, la démarre, et mesure ce qu'un client demande d'un conteneur.

    uv run python mesures/conteneur.py

Il faut Docker, et Ollama sur l'hôte avec les modèles du cours. Mesure : la
durée de construction, la taille de l'image, le délai jusqu'à ce que /sante
réponde, la première question (index compris) puis une seconde, et la
mémoire du conteneur. Le conteneur est arrêté et supprimé à la fin, quoi qu'il
arrive. Écrit mesures/conteneur.json.
"""

import json
import pathlib
import subprocess
import sys
import time
import urllib.request

RACINE = pathlib.Path(__file__).resolve().parents[1]
IMAGE, NOM, PORT = "mission-ia", "mission-ia-mesure", 8765
sys.stdout.reconfigure(encoding="utf-8")


def docker(*args: str) -> str:
    return subprocess.run(["docker", *args], check=True, capture_output=True, text=True,
                          encoding="utf-8").stdout.strip()


def poser(question: str) -> tuple[float, dict]:
    corps = json.dumps({"question": question}).encode("utf-8")
    requete = urllib.request.Request(f"http://127.0.0.1:{PORT}/question", data=corps,
                                     headers={"Content-Type": "application/json"})
    debut = time.perf_counter()
    with urllib.request.urlopen(requete, timeout=300) as r:
        reponse = json.loads(r.read().decode("utf-8"))
    return round(time.perf_counter() - debut, 2), reponse


def main() -> int:
    debut = time.perf_counter()
    docker("build", "--no-cache", "-t", IMAGE, str(RACINE))
    # Deux tailles, à ne pas confondre (constaté avec le stockage containerd de Docker
    # Desktop) : `image inspect` donne la taille COMPRESSÉE, celle qui transite ; `docker
    # images` la taille sur le DISQUE. 84 Mo et 363 Mo pour la même image.
    resultat = {"construction_s": round(time.perf_counter() - debut, 1),
                "image_compressee_mo": round(int(docker("image", "inspect", IMAGE, "--format", "{{.Size}}")) / 1e6),
                "image_sur_disque": docker("images", IMAGE, "--format", "{{.Size}}")}
    try:
        debut = time.perf_counter()
        docker("run", "-d", "--name", NOM, "-p", f"{PORT}:8000", IMAGE)
        for _ in range(300):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/sante", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        resultat["demarrage_jusqu_a_sante_s"] = round(time.perf_counter() - debut, 2)
        resultat["premiere_question_s"], premiere = poser("Combien de candidatures a reçues l'offre OFF-103 ?")
        resultat["seconde_question_s"], seconde = poser("Quelles offres en alternance ?")
        resultat["reponses"] = [premiere["reponse"], seconde["reponse"]]
        resultat["memoire_conteneur"] = docker("stats", "--no-stream", "--format", "{{.MemUsage}}", NOM)
        resultat["utilisateur"] = docker("exec", NOM, "whoami")
    finally:
        subprocess.run(["docker", "rm", "-f", NOM], capture_output=True)
    (pathlib.Path(__file__).with_name("conteneur.json")).write_text(
        json.dumps(resultat, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(resultat, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
