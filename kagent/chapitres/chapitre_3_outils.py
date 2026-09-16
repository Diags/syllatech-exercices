"""Chapitre 3 — Les outils cloud-native.

    uv run python chapitres/chapitre_3_outils.py

La mesure du chapitre tient en deux reponses a la meme question : celle d'un
agent prive d'outils, et celle d'un agent qui observe. L'une est plausible
et fausse ; l'autre cite ce qu'elle a lu.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                                   # noqa: E402
from jobportal import cluster as grappe                         # noqa: E402
from jobportal import controleur, moteur, outils, yaml_minimal  # noqa: E402

RACINE = Path(__file__).resolve().parent.parent
MANIFESTES = RACINE / "manifestes"
QUESTION = "Pourquoi des pods redemarrent-ils dans le cluster ?"


def plateforme() -> tuple[controleur.Api, moteur.Moteur, grappe.Cluster]:
    api = controleur.Api()
    for fichier in sorted(MANIFESTES.glob("*.yaml")):
        for document in yaml_minimal.charger_fichier_tous(fichier):
            api.appliquer(document)
    controleur.Controleur(api).reconcilier()
    cluster = grappe.avec_incident()
    return api, moteur.Moteur(api, cluster), cluster


def main() -> None:
    console.utf8()
    api, m, cluster = plateforme()
    _le_catalogue(m)
    _le_grounding(m)
    _le_trousseau(api, m)
    _le_prompt_nest_pas_un_controle(api, m, cluster)
    _loutil_fantome(api, m)


def _le_catalogue(m: moteur.Moteur) -> None:
    print("1. DES OUTILS DE SRE, ET UNE LIGNE QUI SEPARE TOUT\n")
    lecture = outils.lecture_seule(m.catalogue)
    action = outils.actions(m.catalogue)
    print(f"   {'OUTIL':<24} {'GENRE':<10} CE QU'IL FAIT")
    for nom in lecture + action:
        outil = m.catalogue[nom]
        print(f"   {nom:<24} {outil.genre:<10} {outil.description}")
    print(f"\n   {len(lecture)} outils de lecture, {len(action)} d'action.\n")
    print("   Cette ligne n'est pas une convention de nommage : c'est la")
    print("   seule question a poser devant un outil. `k8s_get_resources`")
    print("   ne peut rien casser, quoi que le modele decide.")
    print("   `k8s_delete_resource` supprime, quelle que soit la facon")
    print("   dont le prompt le presente.")
    print("\n   ⚠️ Un agent de diagnostic n'a besoin QUE de la colonne de")
    print("   gauche. Commencer par la lecture seule n'est pas de la")
    print("   prudence excessive : c'est la configuration qui rend un")
    print("   incident d'agent impossible.")


def _le_grounding(m: moteur.Moteur) -> None:
    print("\n\n2. LA MESURE QUI TRANCHE : LE MEME AGENT, SANS SES YEUX\n")
    print(f"   La question, identique dans les deux cas :")
    print(f"      « {QUESTION} »\n")

    resultats = {}
    for nom in ("assistant-sans-outils", "assistant-sre"):
        session = m.invoquer(nom, QUESTION)
        resultats[nom] = session
        print(f"   ── {nom}\n")
        print(f"      outils accordes : "
              f"{len(m.trousseau(m.api.lire('Agent', nom)).accordes)}")
        print(f"      outils appeles  : {session.outils_appeles or 'aucun'}")
        print(f"      appels au modele: {session.appels_de_modele}")
        print(f"      jetons          : {session.jetons}")
        print(f"      reponse :")
        for ligne in _plier(session.reponse, 62):
            print(f"         {ligne}")
        print()

    sans = resultats["assistant-sans-outils"]
    avec = resultats["assistant-sre"]
    print(f"   La reponse sans outils est PLAUSIBLE : une sonde de liveness")
    print("   trop stricte est une cause reelle de redemarrages en boucle.")
    print("   Elle est aussi FAUSSE — le journal du pod dit")
    print("   « OutOfMemoryError », et Prometheus confirme la memoire a")
    print("   98 % de la limite.")
    print("\n   Rien, dans la premiere reponse, ne signale qu'elle n'a rien")
    print("   observe. C'est ce qui rend un agent sans outils dangereux :")
    print("   il ne dit pas « je ne sais pas », il repond.")
    print(f"\n   Le cout de la difference : {avec.jetons} jetons contre "
          f"{sans.jetons},")
    print(f"   et {avec.appels_de_modele} appels au modele contre "
          f"{sans.appels_de_modele} — un facteur "
          f"{avec.jetons / sans.jetons:.0f} sur les")
    print("   jetons, pour une reponse qu'on peut verifier. C'est le prix")
    print("   du grounding, et il est bas.")
    print("\n   ⚠️ Le prompt de l'agent SRE dit « Verifie TOUJOURS les faits")
    print("   avec tes outils ». Cette phrase ne sert a rien SANS outils :")
    print("   les deux agents ont un prompt comparable, et seul celui qui")
    print("   a des outils observe. Le grounding est une question")
    print("   d'outillage, pas de formulation.")


def _plier(texte: str, largeur: int) -> list[str]:
    mots, lignes, courante = texte.split(), [], ""
    for mot in mots:
        if len(courante) + len(mot) + 1 > largeur:
            lignes.append(courante)
            courante = mot
        else:
            courante = f"{courante} {mot}".strip()
    if courante:
        lignes.append(courante)
    return lignes


def _le_trousseau(api: controleur.Api, m: moteur.Moteur) -> None:
    print("\n\n3. CE QU'UN AGENT A LE DROIT D'APPELER\n")
    print(f"   {'AGENT':<26} {'ACCORDES':>9} {'LECTURE SEULE':>14}  DANGEREUX")
    for agent in api.lister("Agent"):
        trousseau = m.trousseau(agent)
        if not trousseau.accordes:
            continue
        print(f"   {agent.nom:<26} {len(trousseau.accordes):>9} "
              f"{'oui' if trousseau.en_lecture_seule else 'NON':>14}  "
              f"{', '.join(trousseau.dangereux) or '—'}")

    print("\n   La liste `toolNames` est NOMINATIVE : un agent ne recoit")
    print("   pas « le serveur d'outils », il recoit les outils qu'il a")
    print("   nommes. La surface d'attaque reste donc egale a ce qu'on a")
    print("   ecrit, et se relit dans le manifeste.")
    print("\n   ⚠️ Et elle se verifie a l'EXECUTION, pas dans le prompt :")
    sre = m.trousseau(api.lire("Agent", "assistant-sre"))
    try:
        sre.appeler("k8s_delete_resource", nom="jobportal-api-7d4f")
        print("      la suppression a reussi (!)")
    except outils.ErreurOutil as erreur:
        print(f"      appel direct de `k8s_delete_resource` → {erreur}")


def _le_prompt_nest_pas_un_controle(api: controleur.Api, m: moteur.Moteur,
                                    cluster: grappe.Cluster) -> None:
    print("\n\n4. UN PROMPT N'EST PAS UN CONTROLE D'ACCES\n")
    etendu = api.lire("Agent", "assistant-sre-etendu")
    corps = etendu.spec["declarative"]
    print("   Le prompt de `assistant-sre-etendu` dit, mot pour mot :\n")
    for ligne in corps["systemMessage"].strip().splitlines():
        print(f"      {ligne.strip()}")
    trousseau = m.trousseau(etendu)
    print(f"\n   Et ses outils accordes : {trousseau.accordes}\n")
    print(f"   Le trousseau autorise-t-il la suppression ? "
          f"{'OUI' if trousseau.dangereux else 'non'}")
    avant = len(cluster.pods)
    resultat = trousseau.appeler("k8s_delete_resource", genre="Pod",
                                 nom="jobportal-web-5b9c")
    print(f"   Appel direct                    → {resultat}")
    print(f"   Pods avant / apres              → {avant} / {len(cluster.pods)}")
    print(f"   Journal des actions du cluster  → {cluster.journal_des_actions}")

    print("\n   ⚠️ Le prompt interdit la suppression. Le trousseau")
    print("   l'autorise. C'est le trousseau qui gagne — toujours.")
    print("\n   Un prompt est du TEXTE envoye a un modele : il oriente une")
    print("   decision, il ne contraint rien. Ce qui contraint, c'est la")
    print("   liste `toolNames`, et en dessous le RBAC du compte de")
    print("   service sous lequel le serveur d'outils s'execute.")
    print("\n   La regle pratique : si vous ne voulez pas qu'un geste soit")
    print("   possible, ne l'accordez pas. Ecrire « ne fais jamais X »")
    print("   dans un prompt et accorder X est la configuration la plus")
    print("   rassurante et la moins sure qui soit.")


def _loutil_fantome(api: controleur.Api, m: moteur.Moteur) -> None:
    print("\n\n5. UN OUTIL NOMME QUI N'EXISTE PAS NE FAIT ECHOUER PERSONNE\n")
    agent = api.lire("Agent", "assistant-outil-fantome")
    trousseau = m.trousseau(agent)
    print(f"   Outils nommes dans le manifeste : {trousseau.accordes}")
    print(f"   Exposes par le serveur          : {trousseau.utilisables}")
    print(f"   ⚠️ Introuvables                  : {trousseau.introuvables}\n")

    for ligne in controleur.rendre_statut([agent]):
        print(f"      {ligne}")

    session = m.invoquer("assistant-outil-fantome", QUESTION)
    print(f"\n   Invocation → outils appeles : {session.outils_appeles}")
    print(f"                reponse         :")
    for ligne in _plier(session.reponse, 62):
        print(f"                   {ligne}")

    print("\n   Le manifeste est valide : `toolNames` est une liste de")
    print("   chaines, et l'API ne peut pas savoir ce qu'un serveur")
    print("   distant expose. L'agent est `Ready`, il tourne, et il lui")
    print("   manque un œil — sans que rien ne le signale.")
    print("\n   Ici, la conclusion reste juste : les deux outils restants")
    print("   suffisaient. C'est precisement ce qui rend la panne")
    print("   difficile a voir — elle degrade la reponse au lieu de la")
    print("   casser, et seulement sur certaines questions.")
    print("\n   ⚠️ Le controle existe, mais il est cote SERVEUR : c'est la")
    print("   liste `tools/list` que le serveur MCP publie. Un test de")
    print("   demarrage qui compare `toolNames` a cette liste coute dix")
    print("   lignes et attrape toute la classe d'erreurs — y compris le")
    print("   jour ou le serveur renomme un outil.")
    print()


if __name__ == "__main__":
    main()
