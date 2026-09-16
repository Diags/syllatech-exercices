"""Chapitre 3 — Skills : l'agent qui s'améliore.

    uv run python chapitres/chapitre_3_skills.py

Les quatre SKILL.md de `jobportal/skills/` sont écrits au vrai format et
analysés par `agent.skill_utils` — le code que Hermes exécute. Ce qui est
affiché vient donc de lui.

Ce que ce chapitre ne montre pas : l'agent qui ÉCRIT une skill. Cela demande
un modèle. Il montre ce qu'une skill fait gagner une fois écrite, et les deux
façons qu'a une skill de n'exister pour personne.
"""

from __future__ import annotations

import platform
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal.commun import (ligne, titre, toutes_les_competences,  # noqa: E402
                              utf8)
from jobportal.competences import (Competence, avec_competence,      # noqa: E402
                                   cout_en_signes, lire_toutes,
                                   proposees, sans_competence)

REDECOUVERTE = [
    "chercher ou sont stockees les candidatures",
    "comprendre le champ de statut et ses valeurs",
    "calculer l'anciennete, et se tromper de fuseau",
    "rediger une relance, sans connaitre le ton habituel",
    "oublier de repasser le statut a « relancee »",
    "relancer deux fois le meme candidat au tour suivant",
]


def _plier(texte: str, largeur: int) -> list[str]:
    lignes, courante = [], ""
    for mot in texte.split():
        if len(courante) + len(mot) + 1 > largeur:
            lignes.append(courante)
            courante = mot
        else:
            courante = f"{courante} {mot}".strip()
    return lignes + ([courante] if courante else [])


def main() -> None:
    utf8()
    competences = lire_toutes(toutes_les_competences())

    titre(1, "CE QUE HERMES LIT D'UN SKILL.md")
    relance = next(c for c in competences if c.dossier == "relancer-candidat")
    for cle, valeur in relance.entete.items():
        ligne(f"  {cle}", str(valeur), 20)
    print()
    ligne("description (extraite)", relance.description[:52] + "…", 24)
    ligne("outils requis (lus)", ", ".join(relance.outils_requis) or "aucun", 24)
    ligne("ensembles requis (lus)",
          ", ".join(relance.ensembles_requis) or "aucun", 24)
    ligne("corps", f"{len(relance.corps)} signes de procedure", 24)
    print()
    print("   Tout cela sort de `agent.skill_utils.parse_frontmatter` et de")
    print("   ses voisines. Le format n'est pas devine : c'est celui que")
    print("   Hermes analyse.")
    print()
    print("   Remarquez l'imbrication : les conditions sont sous")
    print("   « metadata.hermes », pas a la racine. Ecrites a la racine,")
    print("   elles sont IGNOREES — la section 5 le montre sur une skill qui")
    print("   fait exactement cette faute.")

    titre(2, "OUTIL CONTRE SKILL, EN UNE LIGNE")
    ligne("un outil", "une CAPACITE — lire un fichier, appeler une API", 14)
    ligne("une skill", "une PROCEDURE — l'ordre, les pieges, les ecueils", 14)
    print()
    print("   L'agent avait deja tous les outils pour relancer un candidat.")
    print("   Ce qu'il n'avait pas, c'est l'ordre des etapes et la liste de")
    print("   ce qu'il ne faut pas faire. C'est cela qui ne se redecouvre")
    print("   pas — et c'est cela qu'une skill retient.")

    titre(3, "CE QUE LA SKILL FAIT GAGNER")
    naif = sans_competence(REDECOUVERTE)
    savant = avec_competence(relance)
    ligne("sans la skill", f"{len(REDECOUVERTE)} tours de redecouverte, "
                           f"{cout_en_signes(naif)} signes", 20)
    ligne("avec la skill", f"1 lecture, {cout_en_signes(savant)} signes", 20)
    print()
    print("   Les nombres ne disent pas grand-chose : la procedure est plus")
    print("   longue que la liste des tatonnements. Le gain n'est pas la.\n")
    for etape in REDECOUVERTE[-2:]:
        print(f"      {etape}")
    print()
    print("   Les deux dernieres lignes sont le vrai cout : ce ne sont pas")
    print("   des tours en plus, ce sont des ERREURS. La section « Ce qu'il")
    print("   ne faut pas faire » de la skill les nomme, et c'est la seule")
    print("   partie qu'aucun outil ne remplace.")
    print()
    print("   Une skill n'est donc pas une optimisation de contexte : c'est")
    print("   de la memoire PROCEDURALE. Le chapitre 2 retenait des faits ;")
    print("   celui-ci retient des façons de faire.")

    titre(4, "LA PREMIERE FACON DE N'EXISTER POUR PERSONNE : LA PLATEFORME")
    print(f"   Cette machine : {platform.system()} ({sys.platform})\n")
    print(f"   {'skill':<22}{'plateformes declarees':<30}proposee ici")
    for c in competences:
        ligne_plateformes = ", ".join(c.plateformes) or "(aucune)"
        print(f"   {c.nom[:21]:<22}{ligne_plateformes:<30}"
              f"{'oui' if c.proposee_ici else 'NON'}")
    absentes = [c.nom for c in competences if not c.proposee_ici]
    print()
    print(f"   {len(proposees(competences))} sur {len(competences)} skills sont "
          f"proposees ici.")
    if absentes:
        print(f"   Absente(s) : {', '.join(absentes)}")
    print()
    print("   Une skill hors plateforme n'est pas EN ERREUR : elle est")
    print("   simplement absente de la liste. Aucun message, aucun");
    print("   avertissement. On cherche alors pourquoi l'agent « ne sait pas")
    print("   faire » quelque chose qu'on a pourtant ecrit — et la reponse")
    print("   est dans une ligne de frontmatter.")

    titre(5, "LES AUTRES FACONS : CE QUI SE CHARGE ET NE SERT PAS")
    print("   La description est ce que l'agent lit pour CHOISIR. Et les")
    print("   conditions ne se declarent pas la ou l'on croit.\n")
    total = 0
    for c in competences:
        soucis = c.defauts()
        total += len(soucis)
        ligne(c.nom[:26], "rien a signaler" if not soucis
              else f"{len(soucis)} defaut(s)", 28)
        for souci in soucis:
            for morceau in _plier(souci, 62):
                print(f"      {morceau}")
    print()
    print(f"   {total} defauts sur {len(competences)} skills, et pas une seule")
    print("   erreur de syntaxe : les cinq fichiers se chargent.")
    print()
    print("   Le plus couteux est celui d'« exporter-rapport » : elle exige")
    print("   l'ensemble « code_execution », la condition est ecrite a la")
    print("   racine du frontmatter, et Hermes ne la lit que sous")
    print("   « metadata.hermes ». La skill sera donc proposee meme sans son")
    print("   ensemble d'outils — et elle echouera au milieu de son travail,")
    print("   apres avoir commence a modifier des donnees.")

    titre(6, "CE QUE CE CHAPITRE NE PROUVE PAS")
    for limite in (
            "l'agent n'ecrit pas ses skills ici : la boucle d'auto-",
            "  amelioration demande un modele. Les cinq SKILL.md sont",
            "  ecrits a la main, dans la forme qu'il aurait produite ;",
            "le chargement progressif (la skill n'entre en contexte que",
            "  lorsqu'elle est retenue) n'est pas mesure ici — le cours",
            "  « Claude Code : les Skills » le mesure, sur le meme principe ;",
            "la synchronisation entre machines (skills_sync, skills_hub)"):
        print(f"   · {limite}" if not limite.startswith("  ") else f"   {limite}")
    print()
    print("   Ce qui EST verifie : le format, son analyse par le code de")
    print("   Hermes, et les deux facons de rendre une skill invisible.")

    print("\n   Au chapitre suivant : les outils que ces procedures appellent.\n")


if __name__ == "__main__":
    main()
