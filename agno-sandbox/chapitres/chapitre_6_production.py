"""Chapitre 6 — Production : coûts, observabilité, robustesse.

    uv run python chapitres/chapitre_6_production.py

Ce que les cinq chapitres précédents ont construit, vu du côté de la
facture et de l'astreinte. Les mesures de temps sont réelles ; celles de
coût en jetons sont des ordres de grandeur, et le chapitre le dit.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal.commun import ligne, titre, utf8               # noqa: E402
from jobportal.evaluateur import Evaluateur                   # noqa: E402
from jobportal.executeurs import NIVEAUX, Bride, EnLocal      # noqa: E402
from jobportal.gardes import GARDES, Resumee                  # noqa: E402
from jobportal.service import Service                         # noqa: E402
from jobportal.soumissions import CORPUS                      # noqa: E402
from jobportal.verdict import LONGUEUR_RESUME                 # noqa: E402

CANDIDATURES_PAR_MOIS = 400


def main() -> None:
    utf8()
    honnete = next(s for s in CORPUS if s.nom == "tri-correct")

    titre(1, "LE COUT EN TEMPS, PAR NIVEAU D'ISOLATION")
    for niveau in NIVEAUX:
        debut = time.perf_counter()
        for _ in range(3):
            niveau.executer(honnete.code)
        moyenne = (time.perf_counter() - debut) / 3 * 1000
        par_mois = moyenne * CANDIDATURES_PAR_MOIS / 1000
        ligne(niveau.nom, f"{moyenne:>7.0f} ms/soumission   "
                          f"{par_mois:>6.0f} s pour {CANDIDATURES_PAR_MOIS} "
                          f"candidatures", 18)
    print()
    print("   L'isolation coute quelques minutes de machine par mois. C'est")
    print("   le meilleur rapport de tout ce cours : le chapitre 3 a montre")
    print("   ce qu'elle arrete, et voila ce qu'elle coute.")

    titre(2, "LE COUT EN JETONS, PAR GARDE")
    print("   Ordre de grandeur assume : quatre signes par jeton.\n")
    execution = Bride().executer(honnete.code)
    for garde in GARDES:
        signes = len(garde.envelopper(execution.sortie, execution.erreur))
        jetons = signes // 4
        ligne(garde.nom, f"{jetons:>5} jetons par evaluation   "
                         f"{jetons * CANDIDATURES_PAR_MOIS:>8} par mois", 16)
    print()
    print("   Sur une sortie honnete et courte, les trois se valent. La")
    print("   difference apparait sur une sortie longue — et c'est le")
    print("   candidat qui decide de sa longueur, sauf avec « resumee ».")
    print()
    long = "\n".join(f"ligne {n}" for n in range(5000))
    couts = {}
    for garde in GARDES:
        couts[garde.nom] = len(garde.envelopper(long, "")) // 4
        ligne(f"  {garde.nom} sur 5 000 lignes",
              f"{couts[garde.nom]:>7} jetons", 30)
    print()
    facteur = max(couts.values()) / max(1, min(couts.values()))
    print("   Un seul candidat malveillant multiplie donc la facture d'un")
    print(f"   facteur {facteur:.0f} — ou ne la change pas du tout. C'est un")
    print("   choix d'architecture, pas un reglage de quota.")

    titre(3, "CE QU'IL FAUT JOURNALISER")
    service = Service(evaluateur=Evaluateur(executeur=Bride(),
                                            garde=Resumee()))
    service.lot([s for s in CORPUS if s.famille != "ressource"])
    for quoi, pourquoi in (
            ("le verdict complet", "il se conteste, donc il se relit"),
            ("le niveau d'isolation",
             "un verdict rendu « en local » ne vaut pas le meme"),
            ("la garde utilisee",
             "elle change ce que le modele a lu, donc son verdict"),
            ("les refus et leur raison",
             f"{len(service.depot.refuses)} ici — invisibles sinon"),
            ("la duree d'execution",
             "une soumission interrompue n'est pas une soumission ratee")):
        print(f"   {quoi:<26}{pourquoi}")
    print()
    print("   La deuxieme ligne est celle qu'on oublie. Un verdict sans son")
    print("   contexte d'execution n'est pas reproductible — et six mois plus")
    print("   tard, personne ne saura si le 80 de ce candidat a ete rendu")
    print("   avec ou sans bac a sable.")

    titre(4, "LES TROIS PANNES DE CE MONTAGE")
    for panne, signe, parade in (
            ("le sous-processus ne demarre plus",
             "toutes les evaluations en erreur",
             "un repli explicite, jamais vers « en local »"),
            ("le modele est indisponible",
             "aucun verdict, l'execution a pourtant eu lieu",
             "garder le rapport d'execution, rejouer plus tard"),
            ("une soumission sature le disque",
             "le dossier temporaire ne se vide plus",
             "un plafond de taille de sortie, deja pose")):
        print(f"   {panne}")
        print(f"      se voit a   {signe}")
        print(f"      parade      {parade}")
    print()
    print("   La premiere parade est la seule qui compte vraiment : le repli")
    print("   d'un bac a sable en panne ne doit JAMAIS etre l'execution")
    print("   locale. Un repli qui degrade la securite au moment ou")
    print("   l'infrastructure va mal est exactement le moment ou l'on")
    print("   n'avait pas besoin de cela.")

    titre(5, "CE QUE LE PROJET A MESURE, EN UNE PAGE")
    for constat, mesure in (
            ("un exec() local n'arrete rien", "0/8 attaques arretees"),
            ("le Python portable arrete moins de la moitie",
             "4/10 attaques arretees"),
            ("aucun niveau ne touche aux attaques de verdict",
             "3 soumissions, 3 niveaux, 9 REUSSIE"),
            ("delimiter ne reduit pas la surface",
             "324 signes hostiles, avant comme apres"),
            ("resumer la ramene a zero", "0 signe, et un prompt constant"),
            ("la sortie typee borne le degat",
             f"{LONGUEUR_RESUME} signes au maximum dans le verdict")):
        print(f"   {constat:<48}{mesure}")
    print()
    print("   Les deux dernieres lignes sont la seule vraie defense en")
    print("   profondeur de ce projet : l'une empeche le texte d'entrer,")
    print("   l'autre borne ce qui peut sortir. Elles ne se remplacent pas.")

    titre(6, "CE QUE CE PROJET NE PROUVE PAS")
    for limite in (
            "aucun vrai modele n'est appele : le modele de ce projet est un",
            "  substitut deterministe, et les scores qu'il rend n'ont de sens",
            "  que les uns par rapport aux autres ;",
            "la question « un vrai LLM obeirait-il a la consigne cachee ? »",
            "  n'est donc PAS tranchee ici. Ce qui est mesure est ce qui",
            "  entre dans son contexte, ce qui ne depend d'aucun modele ;",
            "`Bride` n'est pas un bac a sable : c'est ce qu'on peut ecrire en",
            "  Python portable, et le chapitre 3 mesure son insuffisance ;",
            "les couts en jetons sont des ordres de grandeur, pas des",
            "  factures."):
        print(f"   · {limite}" if not limite.startswith("  ") else f"   {limite}")

    print("\n   uv run python outils/mesurer.py           (la matrice)")
    print("   uv run python outils/mesurer.py --gardes  (les gardes)\n")


if __name__ == "__main__":
    main()
