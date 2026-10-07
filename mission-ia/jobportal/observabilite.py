"""Observer l'assistant : une ligne de journal par requête, et leur résumé.

Chaque requête laisse une ligne JSON (le format que lisent la plupart des
outils de journalisation) : quand, combien de temps, combien de jetons, quels
outils, quelles sources. Le résumé en tire ce qu'un client demande :
combien de requêtes, à quelle vitesse, pour quel volume.

Le coût d'une requête locale ne se mesure pas : il se CALCULE, à partir du
temps mesuré et d'un coût horaire de la machine que seul le client connaît
(hypothèse, comme dans le dossier de cadrage).
"""

import datetime
import json
import math
import pathlib
import statistics
import sys
from dataclasses import asdict


class Journal:
    def __init__(self, chemin: str | None = None, garder: int = 1000):
        self.chemin = pathlib.Path(chemin) if chemin else None
        self.garder = garder
        self.recentes: list[dict] = []

    def ecrire(self, trace, reponse: str) -> dict:
        ligne = {"quand": datetime.datetime.now().isoformat(timespec="seconds"),
                 **{k: v for k, v in asdict(trace).items() if not k.startswith("_")},
                 "longueur_reponse": len(reponse)}
        texte = json.dumps(ligne, ensure_ascii=False)
        if self.chemin:
            with self.chemin.open("a", encoding="utf-8") as f:
                f.write(texte + "\n")
        else:
            print(texte, file=sys.stdout, flush=True)
        self.recentes = (self.recentes + [ligne])[-self.garder:]
        return ligne


def centile(valeurs: list[float], p: float) -> float:
    """Le centile p (0 à 100), par la méthode « au plus proche rang » : le rang s'arrondit
    vers le haut (round, arrondi bancaire, donnait 2 pour la médiane de 1 à 5)."""
    # TODO : trier, puis prendre la valeur au rang p/100 × n, arrondi vers le HAUT, au moins 1.
    return sorted(valeurs)[len(valeurs) // 2]


def resumer(lignes: list[dict]) -> dict:
    if not lignes:
        return {"requetes": 0}
    durees = [l["duree_ms"] for l in lignes]
    entree = [l["jetons_entree"] for l in lignes]
    sortie = [l["jetons_sortie"] for l in lignes]
    outils: dict[str, int] = {}
    for l in lignes:
        for o in l["outils"]:
            outils[o["nom"]] = outils.get(o["nom"], 0) + 1
    return {"requetes": len(lignes), "duree_ms_mediane": statistics.median(durees),
            "duree_ms_p95": centile(durees, 95), "duree_ms_max": max(durees),
            "jetons_entree_moyens": round(statistics.mean(entree)),
            "jetons_sortie_moyens": round(statistics.mean(sortie)), "outils": outils}


def cout_local_eur(duree_ms_mediane: float, cout_horaire_machine_eur: float) -> float:
    """Le coût d'une requête sur une machine dédiée : son temps × le coût horaire (HYPOTHÈSE du client)."""
    return round(duree_ms_mediane / 3_600_000 * cout_horaire_machine_eur, 5)
