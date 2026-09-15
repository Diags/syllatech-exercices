"""Chapitre 6 — Integration avec Spring Java.

    uv run python chapitres/chapitre_6_spring.py

Deux sens de circulation, deux mecanismes. Ce chapitre fait passer les deux,
mesure le contrat de chacun, et provoque l'echec le plus frequent : un 200
qui rend du HTML.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                                   # noqa: E402
from jobportal import cluster as grappe                         # noqa: E402
from jobportal import (controleur, integration, moteur, outils,  # noqa: E402
                       traces, yaml_minimal)

RACINE = Path(__file__).resolve().parent.parent
MANIFESTES = RACINE / "manifestes"

AGENT_METIER = {
    "apiVersion": "kagent.dev/v1alpha2",
    "kind": "Agent",
    "metadata": {"name": "assistant-metier", "namespace": "kagent"},
    "spec": {
        "type": "Declarative",
        "declarative": {
            "systemMessage": "Tu reponds aux questions sur les offres du "
                             "portail, en utilisant tes outils.",
            "modelConfig": "claude-config",
            "tools": [{
                "type": "McpServer",
                "mcpServer": {"name": "outils-jobportal",
                              "kind": "RemoteMCPServer",
                              "toolNames": ["rechercher_offres"]},
            }],
        },
    },
}


def plateforme():
    api = controleur.Api()
    for fichier in sorted(MANIFESTES.glob("*.yaml")):
        for document in yaml_minimal.charger_fichier_tous(fichier):
            api.appliquer(document)
    api.appliquer(AGENT_METIER)
    controleur.Controleur(api).reconcilier()
    spring = integration.ApiSpring()
    m = moteur.Moteur(api, grappe.avec_incident(),
                      outils_en_plus=integration.outils_de_spring(spring))
    return api, m, spring


def main() -> None:
    console.utf8()
    _sens_un()
    _le_contrat()
    _le_200_qui_ment()
    _sens_deux()
    _colocaliser()


def _sens_un() -> None:
    print("1. SENS 1 — SPRING APPELLE L'AGENT\n")
    api, m, _ = plateforme()
    point = integration.PointDEntreeA2A(m)
    charge = {"task": "Diagnostique l'incident : des pods redemarrent.",
              "sessionId": "incident-4412",
              "metadata": {"traceparent": "00-4bf92f-00f067-01"}}

    print("   Ce que le `RestClient` Spring envoie :\n")
    print(f"      POST /api/a2a/kagent/assistant-sre")
    print(f"      {json.dumps(charge, ensure_ascii=False)}\n")

    echange = point.poster("assistant-sre", charge)
    print("   Ce que kagent rend :\n")
    print(f"      {echange.corps_brut[:130]}…\n")
    reponse, erreur = integration.lire_la_reponse(echange.corps_brut)
    print(f"      status  : {reponse['status']}")
    print(f"      usage   : {reponse['usage']}")
    print(f"      lecture : {'OK' if not erreur else erreur}")

    print("\n   Cote Spring, cela tient en un `RestClient` et un `record`.")
    print("   L'agent est un service HTTP comme un autre — et c'est")
    print("   precisement ce que « Kubernetes-native » veut dire : pas de")
    print("   SDK proprietaire, pas de plateforme a part.")


def _le_contrat() -> None:
    print("\n\n2. LE CONTRAT, ET CE QU'IL ELAGUE AUSSI\n")
    api, m, _ = plateforme()
    point = integration.PointDEntreeA2A(m)

    essais = [
        ("complet", {"task": "Diagnostique.", "sessionId": "s-1",
                     "metadata": {"traceparent": "00-abc-def-01"}}),
        ("minimal", {"task": "Diagnostique."}),
        ("champ en trop", {"task": "Diagnostique.", "userId": "marie",
                           "priorite": "haute"}),
        ("sans tache", {"sessionId": "s-2"}),
    ]
    print(f"   {'REQUETE':<16} {'ACCEPTEE':>10}  DETAIL")
    for libelle, charge in essais:
        echange = point.poster("assistant-sre", dict(charge))
        detail = (echange.erreur if echange.erreur
                  else (f"elague : {echange.elagues}" if echange.elagues
                        else "—"))
        print(f"   {libelle:<16} {'non' if echange.erreur else 'oui':>10}  "
              f"{detail}")

    print("\n   ⚠️ La troisieme ligne est la meme lecon qu'au chapitre 2,")
    print("   mais de l'autre cote du fil : les champs que le contrat ne")
    print("   connait pas sont retires, en silence. Un `userId` ajoute")
    print("   cote Spring « pour tracer qui demande » n'arrive jamais a")
    print("   l'agent — et rien ne le dit.")
    print("\n   La quatrieme, en revanche, echoue proprement : `task` est")
    print("   obligatoire. Un contrat qui a des champs obligatoires se")
    print("   defend ; un contrat tout optionnel ne defend rien.")


def _le_200_qui_ment() -> None:
    print("\n\n3. LA MESURE QUI TRANCHE : UN 200 QUI REND DU HTML\n")
    corps_html = ("<!doctype html>\n<html><head><title>502 Bad Gateway</title>"
                  "</head>\n<body><h1>502 Bad Gateway</h1></body></html>")
    corps_json_tronque = '{"status": "completed", "result": "Diag'
    corps_valide = json.dumps({"status": "completed", "result": "ok"})

    cas = [
        ("JSON valide", corps_valide, "application/json"),
        ("HTML, code 200", corps_html, "text/html; charset=utf-8"),
        ("JSON tronque", corps_json_tronque, "application/json"),
        ("JSON hors contrat", '{"resultat": "ok"}', "application/json"),
    ]
    print(f"   {'CORPS RECU':<20} {'LU':>5}  DIAGNOSTIC")
    for libelle, corps, type_ in cas:
        reponse, erreur = integration.lire_la_reponse(corps, type_)
        print(f"   {libelle:<20} {'oui' if reponse else 'NON':>5}  "
              f"{erreur or '—'}")

    print("\n   ⚠️ La deuxieme ligne est celle qui coute une matinee. Le")
    print("   code HTTP est 200. Le client ne leve pas d'erreur reseau. La")
    print("   desserialisation echoue, et l'exception qui remonte parle de")
    print("   JSON — pas d'agent, pas de passerelle, pas")
    print("   d'authentification.")
    print("\n   Les causes habituelles : une passerelle qui rend sa propre")
    print("   page d'erreur, une redirection vers une mire")
    print("   d'authentification suivie par le client, un `Ingress` qui")
    print("   route vers le mauvais service. Toutes rendent du HTML avec")
    print("   un 200.")
    print("\n   La parade tient en une ligne de code : verifier le")
    print("   `Content-Type` AVANT de desserialiser, et journaliser les")
    print("   soixante premiers caracteres du corps quand il ne convient")
    print("   pas. Le message devient alors immediat — c'est la troisieme")
    print("   colonne du tableau ci-dessus.")


def _sens_deux() -> None:
    print("\n\n4. SENS 2 — L'AGENT APPELLE VOTRE API SPRING\n")
    api, m, spring = plateforme()
    serveur = api.lire("RemoteMCPServer", "outils-jobportal")
    print("   Le `RemoteMCPServer` qui pointe vers Spring :\n")
    for cle, valeur in serveur.spec.items():
        print(f"      {cle:<14} {valeur}")

    agent = api.lire("Agent", "assistant-metier")
    trousseau = m.trousseau(agent)
    print(f"\n   L'agent metier, et ce qu'il a le droit d'appeler :")
    print(f"      accordes    : {trousseau.accordes}")
    print(f"      exposes     : {sorted(integration.outils_de_spring(spring))}")
    print(f"      dangereux   : {trousseau.dangereux or 'aucun'}\n")

    session = m.invoquer("assistant-metier",
                         "Quelles offres proposez-vous a Lyon ?")
    print(f"   Question    : « Quelles offres proposez-vous a Lyon ? »")
    print(f"   Outils      : {session.outils_appeles}")
    print(f"   Cote Spring : {len(spring.appels)} appel(s) recu(s) - {spring.appels}")
    resultats = [m_.contenu for m_ in session.messages if m_.role == "tool"]
    if resultats:
        print(f"   Rendu       : {resultats[0][:110]}")

    print("\n   Votre API metier devient un outil de l'agent, sans que")
    print("   l'agent ne sache rien de Spring. Le `RemoteMCPServer` est le")
    print("   seul point de contact, et il se declare en YAML comme le")
    print("   reste.")
    print("\n   ⚠️ Et la question du chapitre 3 se repose ici, sur VOTRE")
    print("   API : exposer `creer_ticket` en outil, c'est donner a un")
    print("   modele le droit d'ecrire dans votre systeme.")
    outils_spring = integration.outils_de_spring(spring)
    for nom, outil in sorted(outils_spring.items()):
        print(f"      {nom:<22} {outil.genre:<8} {outil.description}")
    print("\n   Le decoupage naturel est celui-la : un serveur MCP en")
    print("   LECTURE, expose largement ; un second en ECRITURE, declare")
    print("   dans un `RemoteMCPServer` separe, accorde a un seul agent, et")
    print("   sous un compte de service distinct.")


def _colocaliser() -> None:
    print("\n\n5. POURQUOI CO-LOCALISER DANS LE MEME CLUSTER\n")
    api, m, spring = plateforme()
    collecteur = m.collecteur
    racine = collecteur.ouvrir(
        "POST /api/diagnostics", **{"service.name": "jobportal-api"})
    point = integration.PointDEntreeA2A(m)
    point.poster("assistant-sre",
                 {"task": "Diagnostique l'incident.",
                  "metadata": {"traceparent": "00-4bf92f-00f067-01"}},
                 parent=racine)
    racine.millisecondes = sum(s.millisecondes
                               for s in collecteur.enfants(racine))

    print("   Une requete utilisateur, de bout en bout — le span de votre")
    print("   application Spring, puis celui de l'agent, dans UNE trace :\n")
    for ligne in traces.rendre(collecteur, collecteur.traces[0]):
        print(f"      {ligne}")

    print(f"\n   {len(collecteur.traces)} trace, "
          f"{len(collecteur.spans)} spans : l'incident se suit de la")
    print("   requete HTTP jusqu'a l'appel d'outil, sans changer d'ecran.")
    print("\n   Ce que la co-localisation apporte, concretement :")
    print("      • le reseau interne du cluster : l'agent n'est jamais")
    print("        expose publiquement, et l'appel ne sort pas ;")
    print("      • les memes `Secret` Kubernetes pour les deux cotes ;")
    print("      • la meme chaine GitOps — manifestes de l'application et")
    print("        de l'agent dans le meme depot, la meme revue ;")
    print("      • le meme collecteur OTEL, donc la trace ci-dessus.")
    print("\n   ⚠️ Et la contrepartie, qu'il faut assumer : l'agent devient")
    print("   une dependance de votre application. Sa panne est votre")
    print("   panne, son cout est sur votre facture, et la latence de son")
    print("   modele est dans votre temps de reponse. Le traiter comme une")
    print("   dependance ordinaire — delai d'attente, repli, disjoncteur —")
    print("   n'est pas une precaution excessive : c'est le minimum, et")
    print("   c'est exactement ce qu'on ferait pour n'importe quel service")
    print("   tiers.")
    print()


if __name__ == "__main__":
    main()
