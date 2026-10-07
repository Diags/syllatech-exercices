"""Chapitre 3 — Quantization : le même modèle en q4, q8 et fp16.

Lancez : uv run python chapitres/chapitre_3_quantization.py
Ce script AFFICHE les mesures de mesures/resultats.json. Pour les refaire sur
votre machine (une quinzaine de minutes) : uv run python mesures/mesurer.py
"""

import json
import pathlib

from jobportal.console import ligne, titre

resultats = json.loads((pathlib.Path(__file__).parents[1] / "mesures" / "resultats.json")
                       .read_text(encoding="utf-8"))
machine = resultats["machine"]
print(f"\nMesuré le {resultats['date']} sur {machine['processeur']}, {machine['ram_go']} Go, "
      f"sans GPU, Ollama {resultats['ollama']}")

titre(1, "Taille, mémoire et vitesse")
for nom, m in resultats["modeles"].items():
    print(f"\n   {nom}")
    ligne("sur disque", f"{m['disque_mo']} Mo")
    ligne("en mémoire, chargé", f"{m['memoire_chargee_mo']} Mo")
    ligne("génération, médiane", f"{m['generation_jetons_par_s']} jetons/s "
          f"(de {min(m['generation_mesures'])} à {max(m['generation_mesures'])})")

titre(2, "Ce que coûte la vitesse : la qualité")
for nom, m in resultats["modeles"].items():
    ligne(nom, f"{m['extraction_champs_justes']}/{m['extraction_champs_total']} champs justes")

titre(3, "Les rapports, tour par tour")
q4, q8, _ = resultats["modeles"].values()
ligne("q4 / q8, médiane des rapports", q4["rapport_de_vitesse_sur_q8_0"])
ligne("q8 / fp16, médiane des rapports", q8["rapport_de_vitesse_sur_fp16"])
ligne("charge du processeur pendant la mesure", f"{min(q4['charge_processeur_pourcent'])} à "
      f"{max(q4['charge_processeur_pourcent'])} %")
