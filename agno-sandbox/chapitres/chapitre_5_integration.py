"""Chapitre 5 — Intégrer l'évaluateur au job portal.

    uv run python chapitres/chapitre_5_integration.py

Le cours montre une route FastAPI. Ce chapitre exerce les mêmes étapes sans
serveur : ce qui compte n'est pas le framework, c'est ce qui traverse la
frontière — et dans quel ORDRE.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal.commun import ligne, titre, utf8               # noqa: E402
from jobportal.evaluateur import Evaluateur                   # noqa: E402
from jobportal.executeurs import DELAI, Bride                 # noqa: E402
from jobportal.gardes import Resumee                          # noqa: E402
from jobportal.service import Service, TAILLE_MAX             # noqa: E402
from jobportal.soumissions import CORPUS, Soumission          # noqa: E402


def main() -> None:
    utf8()
    service = Service(evaluateur=Evaluateur(executeur=Bride(),
                                            garde=Resumee()))

    titre(1, "LE MONTAGE COMPLET")
    for couche, choix, pourquoi in (
            ("execution", "Bride",
             "sous-processus, environnement vide, dossier jetable"),
            ("garde de prompt", "Resumee",
             "le texte du candidat n'entre pas dans le contexte"),
            ("sortie", "Verdict (output_schema)",
             "un objet borne, pas une phrase"),
            ("frontiere", "Service",
             "plafond de taille, file de revue, lot resistant")):
        print(f"   {couche:<18}{choix:<26}{pourquoi}")
    print()
    print("   Les quatre se changent independamment. C'est le seul vrai")
    print("   critere d'une architecture : pouvoir remplacer `Bride` par un")
    print("   conteneur sans toucher au reste.")

    titre(2, "L'ORDRE DES CONTROLES")
    enorme = Soumission("code-enorme", "honnete", "x = 1\n" * 5000,
                        "faire travailler le serveur pour rien")
    debut = time.perf_counter()
    resultat = service.recevoir(enorme)
    duree = (time.perf_counter() - debut) * 1000
    ligne("soumission de "
          f"{len(enorme.code)} signes", f"refusee en {duree:.1f} ms", 30)
    ligne("plafond", f"{TAILLE_MAX} signes", 30)
    ligne("sous-processus demarre", "aucun", 30)
    print()
    print("   Le controle de taille passe AVANT tout le reste. Refuser apres")
    print("   avoir demarre un sous-processus coute un sous-processus : sur")
    print("   une campagne de 400 candidatures, c'est la difference entre un")
    print("   refus gratuit et 80 secondes de machine.")

    titre(3, "UNE CAMPAGNE COMPLETE")
    debut = time.perf_counter()
    evaluations = service.lot([s for s in CORPUS if s.famille != "ressource"])
    duree = time.perf_counter() - debut
    for cle, valeur in service.depot.resume().items():
        ligne(cle, str(valeur), 18)
    ligne("duree", f"{duree:.1f} s pour {len(evaluations)} evaluations", 18)
    ligne("par soumission", f"{duree / max(1, len(evaluations)) * 1000:.0f} ms",
          18)
    print()
    print("   Le temps est domine par le demarrage des sous-processus, pas")
    print("   par le modele. Sur une vraie installation, l'ordre s'inverse —")
    print("   et c'est le chapitre 6.")

    titre(4, "LA FILE DE REVUE HUMAINE")
    if service.depot.a_relire:
        for nom in service.depot.a_relire:
            ligne(nom, service.depot.verdicts[nom].resume[:44], 28)
    else:
        print("   Aucune soumission marquee « comportement_suspect ».")
        print()
        print("   ⚠️ Et c'est un resultat, pas un succes. Avec la garde")
        print("   « resumee », le modele ne voit plus le texte du candidat :")
        print("   il ne peut donc plus signaler qu'il etait suspect.")
        print()
        print("   La detection revient alors au HARNAIS, qui compte les")
        print("   marques de consigne avant de resumer. Ce n'est pas une")
        print("   perte — c'est un deplacement, d'un modele vers du code")
        print("   deterministe. Mais il faut le faire exprès, et le service")
        print("   de ce chapitre ne le fait pas encore.")

    titre(5, "CE QUE LE LOT GARANTIT")
    print("   Un enregistrement mal forme sorti de la file : le champ « code »")
    print("   est nul. Cela n'a rien d'exotique — une file rend ce qu'on y a")
    print("   mis, et un formulaire vide y met un nul.\n")
    fautive = Soumission("enregistrement-nul", "honnete", None,   # type: ignore[arg-type]
                         "faire lever le harnais lui-meme")
    service2 = Service(evaluateur=Evaluateur(executeur=Bride(),
                                             garde=Resumee()))
    faites = service2.lot([
        next(s for s in CORPUS if s.nom == "tri-correct"),
        fautive,
        next(s for s in CORPUS if s.nom == "tri-inverse")])
    ligne("soumissions envoyees", "3", 26)
    ligne("evaluations rendues", str(len(faites)), 26)
    ligne("refusees et journalisees", str(len(service2.depot.refuses)), 26)
    for nom, pourquoi in service2.depot.refuses.items():
        ligne(f"  {nom}", pourquoi[:44], 26)
    print()
    print("   Sans le `try` de `Service.lot`, cette seule ligne emporte la")
    print("   campagne : c'est le dossier fautif qui decide lesquels de ses")
    print("   concurrents seront notes — et personne ne s'en apercoit avant")
    print("   de compter les verdicts manquants.")

    titre(6, "CE QU'IL MANQUE POUR EN FAIRE UN SERVICE")
    for manque, pourquoi in (
            ("une file (Redis, SQS…)",
             "sinon une requete HTTP attend l'evaluation entiere"),
            ("une limite de debit par candidat",
             f"le delai de {DELAI:.0f} s se multiplie par le nombre d'envois"),
            ("un stockage durable",
             "`Depot` est un dictionnaire en memoire"),
            ("l'identite du candidat",
             "un verdict sans auteur ne se conteste pas"),
            ("un journal des refus",
             "les refus sont la moitie de ce qu'on veut relire")):
        print(f"   {manque:<34}{pourquoi}")
    print()
    print("   Aucun de ces cinq points n'est propre a l'IA. C'est du service")
    print("   ordinaire — et c'est precisement pour cela qu'on l'oublie dans")
    print("   un projet d'agent.")

    print("\n   Au chapitre suivant : ce que cela coute, et ce qui casse.\n")


if __name__ == "__main__":
    main()
