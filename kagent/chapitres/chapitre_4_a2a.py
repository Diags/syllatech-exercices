"""Chapitre 4 — A2A : des agents qui s'invoquent.

    uv run python chapitres/chapitre_4_a2a.py

`type: Agent` transforme un agent en outil d'un autre. Ce chapitre compte ce
que cette ligne de YAML coute — en appels de modele, en jetons, en
millisecondes — et ce qu'elle achete.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                                   # noqa: E402
from jobportal import cluster as grappe                         # noqa: E402
from jobportal import controleur, moteur, traces, yaml_minimal  # noqa: E402

RACINE = Path(__file__).resolve().parent.parent
MANIFESTES = RACINE / "manifestes"
QUESTION = "Diagnostique l'incident : des pods redemarrent."


def plateforme() -> tuple[controleur.Api, moteur.Moteur]:
    api = controleur.Api()
    for fichier in sorted(MANIFESTES.glob("*.yaml")):
        for document in yaml_minimal.charger_fichier_tous(fichier):
            api.appliquer(document)
    controleur.Controleur(api).reconcilier()
    return api, moteur.Moteur(api, grappe.avec_incident())


def main() -> None:
    console.utf8()
    _un_agent_comme_outil()
    _le_cout_de_la_delegation()
    _larbre_des_invocations()
    _le_cycle()
    _quand_deleguer()


def _un_agent_comme_outil() -> None:
    print("1. UN AGENT DECLARE COMME OUTIL D'UN AUTRE\n")
    api, m = plateforme()
    orchestrateur = api.lire("Agent", "orchestrateur")
    outils_declares = orchestrateur.spec["declarative"]["tools"]

    print("   Les `tools` de l'orchestrateur, tels que le manifeste les")
    print("   declare :\n")
    for outil in outils_declares:
        cible = (outil.get("agent") or outil.get("mcpServer") or {}).get("name")
        print(f"      type: {outil['type']:<12} → {cible}")

    print("\n   Et ce que le moteur en fait :\n")
    trousseau = m.trousseau(orchestrateur)
    print(f"      accordes : {trousseau.accordes}")
    print("\n   Un agent delegue apparait dans le trousseau comme n'importe")
    print("   quel autre outil, avec un prefixe `a2a:`. Pour le modele, la")
    print("   difference n'existe pas : il appelle un nom, il recoit un")
    print("   texte.")
    print("\n   ⚠️ Pour l'exploitation, en revanche, la difference est")
    print("   entiere. Un outil coute un appel HTTP ; un agent delegue")
    print("   coute une CONVERSATION complete — son propre modele, ses")
    print("   propres outils, ses propres jetons. C'est la section")
    print("   suivante.")


def _le_cout_de_la_delegation() -> None:
    print("\n\n2. LA MESURE QUI TRANCHE : CE QUE LA DELEGATION COUTE\n")
    mesures = []
    for nom in ("assistant-sre", "orchestrateur"):
        api, m = plateforme()
        session = m.invoquer(nom, QUESTION)
        mesures.append((nom, session, m))

    print(f"   {'AGENT':<18} {'APPELS MODELE':>14} {'OUTILS':>8} "
          f"{'DELEGATIONS':>12} {'JETONS':>8} {'SPANS':>7}")
    for nom, session, m in mesures:
        print(f"   {nom:<18} {session.appels_de_modele:>14} "
              f"{len(session.outils_appeles) - len(session.delegations):>8} "
              f"{len(session.delegations):>12} {session.jetons:>8} "
              f"{len(m.collecteur.spans):>7}")

    seul, groupe = mesures[0][1], mesures[1][1]
    print(f"\n   {groupe.appels_de_modele} appels au modele contre "
          f"{seul.appels_de_modele} : deleguer a deux")
    print("   specialistes ne divise pas le travail, il l'AJOUTE. Chaque")
    print("   specialiste refait sa propre boucle — son prompt systeme, ses")
    print("   outils, sa conclusion — et l'orchestrateur en fait une de")
    print("   plus pour synthetiser.")
    print("\n   Ce qu'on achete en echange, et qui ne se mesure pas ici :")
    print("      • des prompts COURTS, donc des agents qu'on peut relire ;")
    print("      • des specialistes testables un par un ;")
    print("      • et surtout des PERMISSIONS separees — l'agent qui lit")
    print("        Prometheus n'a aucun outil Kubernetes, et vice versa.")
    print("\n   ⚠️ Ce dernier point est le vrai argument. Un agent unique")
    print("   avec dix outils cumule dix surfaces d'attaque ; trois agents")
    print("   de trois outils n'en cumulent aucune. Le decoupage A2A est")
    print("   d'abord une frontiere de privileges, ensuite une question de")
    print("   qualite de reponse.")


def _larbre_des_invocations() -> None:
    print("\n\n3. L'ARBRE DES INVOCATIONS\n")
    api, m = plateforme()
    session = m.invoquer("orchestrateur", QUESTION)
    for ligne in traces.rendre(m.collecteur):
        print(f"   {ligne}")
    print(f"\n   {len(m.collecteur.spans)} spans, une seule trace : le")
    print("   contexte a ete propage du parent vers chaque delegue. Le")
    print("   chapitre 5 montre ce qui arrive quand il ne l'est pas.")
    print("\n   Lisez l'arbre de haut en bas : l'orchestrateur appelle son")
    print("   modele, qui demande `a2a:agent-etat` ; l'agent d'etat ouvre")
    print("   sa propre boucle sous le span parent, appelle deux outils,")
    print("   conclut ; l'orchestrateur reprend la main et delegue aux")
    print("   metriques ; puis il synthetise.")
    print(f"\n   Jetons totaux, tous spans confondus : "
          f"{m.collecteur.total('gen_ai.usage.input_tokens'):.0f} en entree, "
          f"{m.collecteur.total('gen_ai.usage.output_tokens'):.0f} en sortie")


def _le_cycle() -> None:
    print("\n\n4. LE CYCLE QUE LES MANIFESTES NE MONTRENT PAS\n")
    api, m = plateforme()
    ping = api.lire("Agent", "agent-ping")
    pong = api.lire("Agent", "agent-pong")
    print("   Deux agents, chacun valide, chacun `Ready` :\n")
    for ligne in controleur.rendre_statut([ping, pong]):
        print(f"      {ligne}")
    print(f"\n      agent-ping delegue a : "
          f"{[o['agent']['name'] for o in ping.spec['declarative']['tools']]}")
    print(f"      agent-pong delegue a : "
          f"{[o['agent']['name'] for o in pong.spec['declarative']['tools']]}")

    print("\n   Aucun des deux manifestes ne contient de cycle : il faut")
    print("   les lire ENSEMBLE pour le voir, et le controleur ne le")
    print("   cherche pas — il verifie que la reference existe, pas qu'elle")
    print("   ne revient pas.\n")
    try:
        m.invoquer("agent-ping", QUESTION)
        print("      l'invocation a abouti (!)")
    except moteur.ErreurMoteur as erreur:
        print(f"      invocation → {erreur}")

    print("\n   ⚠️ La detection se fait A L'EXECUTION, en gardant la pile")
    print("   des agents traverses. C'est la seule facon : un graphe")
    print("   d'agents se recompose a chaque `apply`, et un cycle peut")
    print("   apparaitre entre deux manifestes appliques par deux equipes")
    print("   differentes.")
    print("\n   Le second garde-fou est une PROFONDEUR MAXIMALE :")
    print(f"      moteur.PROFONDEUR_MAXIMALE = {moteur.PROFONDEUR_MAXIMALE}")
    print("   Sans lui, une chaine sans cycle mais tres longue produirait")
    print("   la meme facture qu'une boucle infinie — simplement plus")
    print("   lentement.")


def _quand_deleguer() -> None:
    print("\n\n5. QUAND DELEGUER, ET QUAND NE PAS\n")
    print("   A2A est un protocole ouvert : un specialiste peut vivre dans")
    print("   un autre langage, un autre framework, un autre cluster. Cela")
    print("   en fait un bon outil d'INTEGRATION — et un mauvais reflexe")
    print("   d'architecture.\n")
    print("   Deleguer quand :")
    print("      • les permissions doivent etre separees (l'argument le")
    print("        plus solide) ;")
    print("      • le specialiste existe deja, ecrit par une autre equipe ;")
    print("      • le prompt d'un agent unique devient illisible.\n")
    print("   Ne pas deleguer quand :")
    print("      • il s'agit seulement de « decouper pour faire propre » :")
    print("        chaque delegation coute une conversation entiere ;")
    print("      • la reponse du specialiste doit revenir STRUCTUREE — un")
    print("        appel d'outil ordinaire rend du JSON, une delegation")
    print("        rend du texte qu'il faudra relire ;")
    print("      • la latence compte : les delegations s'additionnent, et")
    print("        rien ne les parallelise dans ce modele.")
    print("\n   ⚠️ Et un point d'exploitation qu'on decouvre tard : un")
    print("   specialiste qui repond mal fait echouer l'orchestrateur SANS")
    print("   erreur. Le texte remonte comme un resultat d'outil ordinaire,")
    print("   et le modele appelant en fait ce qu'il peut. C'est la raison")
    print("   pour laquelle les traces du chapitre 5 ne sont pas un")
    print("   confort mais un prerequis.")
    print()


if __name__ == "__main__":
    main()
