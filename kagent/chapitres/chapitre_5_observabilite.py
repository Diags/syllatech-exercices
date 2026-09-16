"""Chapitre 5 — Observabilite et tests.

    uv run python chapitres/chapitre_5_observabilite.py

Un agent est une machine a decisions. Ce chapitre regarde ces decisions une
par une, puis casse la propagation du contexte pour montrer ce qu'on perd —
sans qu'aucune erreur ne soit levee.
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
    _la_session()
    _les_spans()
    _la_trace_cassee()
    _le_cockpit()
    _tester_un_agent()


def _la_session() -> None:
    print("1. CE QU'UNE SESSION CONTIENT\n")
    api, m = plateforme()
    session = m.invoquer("assistant-sre", QUESTION)

    print(f"   {'ROLE':<12} {'OUTIL':<20} CONTENU")
    for message in session.messages:
        contenu = str(message.contenu).replace("\n", " ")
        if len(contenu) > 56:
            contenu = contenu[:53] + "..."
        print(f"   {message.role:<12} {message.outil:<20} {contenu}")

    print(f"\n   {len(session.messages)} messages, "
          f"{session.appels_de_modele} appels au modele, "
          f"{len(session.outils_appeles)} appels d'outils,")
    print(f"   {session.jetons_entree} jetons en entree et "
          f"{session.jetons_sortie} en sortie.")
    print("\n   ⚠️ Regardez la colonne des jetons d'entree dans la section")
    print("   suivante : elle CROIT a chaque tour. C'est la propriete la")
    print("   plus couteuse d'une boucle d'agent — chaque resultat d'outil")
    print("   est reinjecte dans le message suivant, et l'on repaie le")
    print("   contexte entier a chaque appel.")


def _les_spans() -> None:
    print("\n\n2. CHAQUE DECISION DEVIENT UN SPAN\n")
    api, m = plateforme()
    m.invoquer("assistant-sre", QUESTION)
    for ligne in traces.rendre(m.collecteur):
        print(f"   {ligne}")

    entree = m.collecteur.total("gen_ai.usage.input_tokens")
    sortie = m.collecteur.total("gen_ai.usage.output_tokens")
    appels = len(m.collecteur.par_nom("chat"))
    print(f"\n   {len(m.collecteur.spans)} spans, {appels} appels au modele, "
          f"{entree:.0f} jetons en entree.")
    print("\n   Les attributs suivent les conventions `gen_ai.*`")
    print("   d'OpenTelemetry : `gen_ai.operation.name`,")
    print("   `gen_ai.request.model`, `gen_ai.usage.input_tokens`. Ce n'est")
    print("   pas une coquetterie — c'est ce qui permet a un tableau de")
    print("   bord generique d'agreger le cout de VOS agents a cote de")
    print("   ceux des autres equipes, sans configuration.")
    print("\n   ⚠️ Et la progression des jetons d'entree, span par span,")
    print("   est la seule facon de voir venir une boucle qui s'emballe.")
    print("   Une alerte sur `gen_ai.usage.input_tokens` par session vaut")
    print("   mieux qu'un plafond de facture mensuel.")


def _la_trace_cassee() -> None:
    print("\n\n3. LA MESURE QUI TRANCHE : LA TRACE QUI SE COUPE EN DEUX\n")
    resultats = []
    for propage in (True, False):
        api, m = plateforme()
        session = m.invoquer("orchestrateur", QUESTION, propager=propage)
        resultats.append((propage, m, session))

    print(f"   {'CONTEXTE PROPAGE':<20} {'SPANS':>7} {'TRACES':>8} "
          f"{'REPONSE IDENTIQUE':>19}")
    reference = resultats[0][2].reponse
    for propage, m, session in resultats:
        print(f"   {'oui' if propage else 'NON':<20} "
              f"{len(m.collecteur.spans):>7} {len(m.collecteur.traces):>8} "
              f"{'oui' if session.reponse == reference else 'non':>19}")

    print("\n   Memes spans, meme reponse, meme cout — et trois traces au")
    print("   lieu d'une. Voici ce que l'explorateur de traces montre dans")
    print("   le second cas :\n")
    _, casse, _ = resultats[1]
    for ligne in traces.rendre(casse.collecteur):
        print(f"      {ligne}")

    print("\n   ⚠️ RIEN N'A ECHOUE. L'agent a repondu, les spans sont")
    print("   corrects, l'exportateur a tout recu. Simplement, la trace de")
    print("   l'orchestrateur ne contient plus ses delegues : il faut")
    print("   savoir que `agent-etat` a ete appele pour aller chercher sa")
    print("   trace, et il n'y a aucun lien pour le faire.")
    print("\n   La cause tient a une en-tete : `traceparent`. Le contexte")
    print("   d'une trace ne voyage pas tout seul — il se propage")
    print("   explicitement a chaque frontiere de processus. Un client HTTP")
    print("   sans instrumentation, une file de messages, un `Thread` lance")
    print("   a la main : chacun coupe la trace en silence.")
    print("\n   C'est la panne d'observabilite la plus courante, et la plus")
    print("   longue a diagnostiquer, parce qu'elle ne se manifeste que")
    print("   lorsqu'on cherche — c'est-a-dire pendant un incident.")


def _le_cockpit() -> None:
    print("\n\n4. LE TABLEAU DE BORD : SESSIONS, OUTILS, JETONS, DUREE\n")
    api, m = plateforme()
    sessions = []
    for nom, question in (("assistant-sre", QUESTION),
                          ("assistant-sans-outils", QUESTION),
                          ("orchestrateur", QUESTION),
                          ("assistant-outil-fantome", QUESTION)):
        sessions.append((nom, m.invoquer(nom, question)))

    print(f"   {'AGENT':<26} {'MODELE':>7} {'OUTILS':>7} {'DELEG.':>7} "
          f"{'JETONS':>8} {'MS':>7}")
    for nom, session in sessions:
        spans = [s for s in m.collecteur.spans
                 if s.attributs.get("agent.nom") == nom and s.racine]
        millisecondes = sum(s.millisecondes for s in spans)
        print(f"   {nom:<26} {session.appels_de_modele:>7} "
              f"{len(session.outils_appeles) - len(session.delegations):>7} "
              f"{len(session.delegations):>7} {session.jetons:>8} "
              f"{millisecondes:>7.0f}")

    print("\n   Ce tableau se lit comme celui d'un service HTTP : la")
    print("   colonne qui derape se voit, et l'on sait ou aller regarder.")
    print("   Un agent qui passe de 5 a 40 appels au modele du jour au")
    print("   lendemain a change de comportement — sans qu'une ligne de")
    print("   son manifeste n'ait bouge, parce que le MODELE, lui, a")
    print("   change.")
    print("\n   ⚠️ C'est l'argument decisif pour tracer un agent plutot")
    print("   qu'un service ordinaire : le code est fige, le comportement")
    print("   ne l'est pas. Un deploiement n'est plus le seul evenement")
    print("   capable de changer la production.")


def _tester_un_agent() -> None:
    print("\n\n5. TESTER UN AGENT : CE QUI EST POSSIBLE, ET CE QUI NE L'EST PAS\n")
    api, m = plateforme()
    jeu = [
        (QUESTION, ["k8s_get_resources", "k8s_get_pod_logs"]),
        ("Pourquoi des 502 ?", ["k8s_get_resources"]),
        ("Le cluster va-t-il bien ?", ["k8s_get_resources"]),
    ]
    print(f"   {'QUESTION':<44} {'OUTILS ATTENDUS OBSERVES':>26}")
    reussites = 0
    for question, attendus in jeu:
        session = m.invoquer("assistant-sre", question)
        vus = set(session.outils_appeles)
        ok = set(attendus) <= vus
        reussites += ok
        court = question if len(question) <= 42 else question[:39] + "..."
        print(f"   {court:<44} {'oui' if ok else 'NON':>26}")
    print(f"\n   {reussites}/{len(jeu)} — et c'est bien ce qu'on peut")
    print("   tester : le COMPORTEMENT observable, pas le texte produit.")
    print("\n   Ce qui se teste sur un agent :")
    print("      • les outils qu'il appelle, et dans quel ordre ;")
    print("      • ceux qu'il n'appelle JAMAIS — un test d'absence vaut")
    print("        souvent mieux qu'un test de presence ;")
    print("      • le nombre d'appels au modele, comme garde-fou de cout ;")
    print("      • la forme de la sortie quand elle est structuree.\n")
    print("   Ce qui ne se teste pas :")
    print("      • la formulation exacte de la reponse. La comparer a une")
    print("        chaine attendue produit un test qui echoue au premier")
    print("        changement de modele, pour rien.")
    print("\n   ⚠️ Le declaratif aide, et il ne rend pas deterministe. Ce")
    print("   qu'il garantit est que l'ENTREE est reproductible : meme")
    print("   prompt, memes outils, meme modele — donc un ecart de")
    print("   comportement s'explique par le modele, et pas par une")
    print("   configuration que personne ne retrouve.")
    print()


if __name__ == "__main__":
    main()
