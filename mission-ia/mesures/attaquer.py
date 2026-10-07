"""Rejoue les attaques du chapitre « Sécuriser », deux fois, sans puis avec défenses.

    uv run python mesures/attaquer.py

Les offres piégées (jobportal.securite.PIEGES) sont publiées sur le portail le
temps de la mesure : l'index les contient, comme si un recruteur malveillant
les avait déposées. Écrit mesures/securite.json.
"""

import datetime
import json
import pathlib
import sys

import ollama

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from jobportal import agent, securite  # noqa: E402
from jobportal.donnees import OFFRES  # noqa: E402
from jobportal.recherche import Index  # noqa: E402

PASSAGES = 2
sys.stdout.reconfigure(encoding="utf-8")


def main() -> int:
    client = ollama.Client()
    index = Index(client, OFFRES + securite.PIEGES)
    approches = {
        "sans défense": lambda q: agent.repondre_guide_relie(client, index, q),
        "avec défenses": lambda q: securite.repondre_securise(client, index, q, consigne_defensive=True),
        "défenses du code seules (sans D1)": lambda q: securite.repondre_securise(
            client, index, q, consigne_defensive=False),
    }
    resultats = {}
    for nom, repondre in approches.items():
        resultats[nom] = []
        for k in range(PASSAGES):
            passage = []
            for attaque in securite.ATTAQUES:
                texte, trace = repondre(attaque["question"])
                passage.append({"id": attaque["id"], "sorte": attaque["sorte"],
                                "reussie": attaque["reussie"](texte), "reponse": texte,
                                "alertes": trace.alertes})
            resultats[nom].append(passage)
            reussies = [a["id"] for a in passage if a["reussie"]]
            print(f"{nom}, passage {k + 1} : {len(reussies)}/{len(passage)} attaques réussies  {reussies}")
    sortie = pathlib.Path(__file__).with_name("securite.json")
    sortie.write_text(json.dumps({"date": datetime.date.today().isoformat(), "modele": agent.MODELE,
                                  "resultats": resultats}, ensure_ascii=False, indent=1) + "\n",
                      encoding="utf-8")
    print(f"écrit : {sortie}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
