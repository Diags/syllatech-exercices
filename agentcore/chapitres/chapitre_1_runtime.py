"""Chapitre 1 — Démarrer avec AgentCore.

    uv run python chapitres/chapitre_1_runtime.py

Tout ce chapitre passe par le **vrai** `BedrockAgentCoreApp`. Aucun compte
AWS, aucun `agentcore launch` : l'application est une Starlette, on l'appelle
en direct, et les réponses sont celles que le runtime renverrait.

Sept comportements du contrat, dont quatre qu'aucune documentation n'annonce.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bedrock_agentcore.runtime import BedrockAgentCoreApp        # noqa: E402
from bedrock_agentcore.runtime.models import PingStatus          # noqa: E402

from jobportal.agent import app                                  # noqa: E402
from jobportal.commun import ligne, silence, titre, utf8         # noqa: E402
from jobportal.contrat import appeler, morceaux, sante           # noqa: E402


def main() -> None:
    utf8()

    titre(1, "LE CONTRAT : UN dict ENTRE, UN dict SORT")
    print("   @app.entrypoint decore une fonction. AgentCore emballe le")
    print("   reste : routes, serveur, format, sante.\n")
    for etiquette, charge, session in (
            ("payload normal", {"prompt": "DevOps a Lyon"}, None),
            ("avec une session", {"prompt": "DevOps a Lyon"}, "s-123"),
            ("prompt manquant", {}, None),
            ("aucun corps", None, None)):
        reponse = appeler(app, charge, session=session)
        ligne(etiquette, str(reponse), 20)
    print()
    print("   « aucun corps » rend 400 « Invalid JSON », pas 200 avec un")
    print("   payload vide : le runtime exige un corps JSON, meme vide ({}).")

    titre(2, "LES ROUTES QUE LE RUNTIME SERT")
    for route in app.routes:
        methodes = sorted(getattr(route, "methods", None) or ["WEBSOCKET"])
        ligne(getattr(route, "path", "?"), ", ".join(methodes), 16)
    print()
    print("   /ping est ce que l'orchestrateur interroge pour savoir s'il")
    print("   peut vous envoyer du trafic. /invocations est votre agent.")
    ligne("sante actuelle", sante(app), 16)

    titre(3, "LA SESSION VIENT D'UN EN-TETE, PAS DU PAYLOAD")
    sans = appeler(app, {"prompt": "x"}).json
    avec = appeler(app, {"prompt": "x"}, session="s-abc").json
    ligne("sans en-tete", f"session = {sans.get('session')!r}", 20)
    ligne("avec l'en-tete", f"session = {avec.get('session')!r}", 20)
    print()
    print("   L'en-tete est X-Amzn-Bedrock-AgentCore-Runtime-Session-Id, et")
    print("   c'est le RUNTIME qui le pose. En local il est absent : on croit")
    print("   alors que l'isolation par session ne marche pas, alors qu'on ne")
    print("   l'a simplement pas simulee.")

    titre(4, "UN ENTRYPOINT QUI LEVE RENVOIE SON MESSAGE AU CLIENT")
    casse = BedrockAgentCoreApp()

    @casse.entrypoint
    def boum(payload):
        raise ValueError("connexion refusee vers postgres-prod.interne:5432")

    with silence():
        reponse = appeler(casse, {"prompt": "x"})
    ligne("code", str(reponse.code), 20)
    ligne("corps rendu au client", reponse.texte, 20)
    print()
    print("   Le message de l'exception traverse. Un nom d'hote interne, un")
    print("   chemin de fichier ou un fragment de requete SQL arrive donc")
    print("   chez l'appelant. Attrapez vos exceptions DANS l'entrypoint et")
    print("   rendez un message neutre — le detail va dans les journaux.")

    titre(5, "UN RETOUR NON SERIALISABLE EST str()-IFIE, SANS ERREUR")
    import datetime

    sale = BedrockAgentCoreApp()

    @sale.entrypoint
    def horodate(payload):
        return {"quand": datetime.datetime(2026, 9, 14, 4, 9)}

    with silence():
        reponse = appeler(sale, {"prompt": "x"})
    ligne("code", str(reponse.code), 20)
    ligne("ce que le client recoit", reponse.texte, 20)
    print()
    print("   200, et une CHAINE contenant un repr Python. Le consommateur")
    print("   qui lit reponse[\"quand\"] recoit un texte, pas une date — et")
    print("   rien, nulle part, ne signale la conversion. Rendez des types")
    print("   JSON, ou serialisez vous-meme.")

    titre(6, "DEUX @app.entrypoint : LE SECOND GAGNE, EN SILENCE")
    deux = BedrockAgentCoreApp()

    @deux.entrypoint
    def premier(payload):
        return {"qui": "premier"}

    @deux.entrypoint
    def second(payload):
        return {"qui": "second"}

    with silence():
        reponse = appeler(deux, {"prompt": "x"})
    ligne("handlers enregistres", str(list(deux.handlers)), 24)
    ligne("qui repond", reponse.texte, 24)
    print()
    print("   Le SDK ne garde qu'un handler, sous la cle « main ». Le premier")
    print("   decorateur n'a servi a rien, et rien ne le dit. Dans un fichier")
    print("   de 300 lignes, cela se voit le jour du deploiement.")

    titre(7, "UN GENERATEUR CHANGE LE TRANSPORT")
    flux = BedrockAgentCoreApp()

    @flux.entrypoint
    def par_morceaux(payload):
        for mot in ("Trois", "offres", "correspondent"):
            yield {"mot": mot}

    with silence():
        reponse = appeler(flux, {"prompt": "x"})
    ligne("flux ?", str(reponse.flux), 20)
    for evenement in morceaux(reponse):
        ligne("  evenement", evenement, 18)
    print()
    print("   Meme decorateur, meme route : c'est le TYPE DE RETOUR qui fait")
    print("   passer le runtime en text/event-stream. Un « yield » ajoute par")
    print("   megarde change donc le contrat de votre API, sans un mot.")

    titre(8, "LA SANTE SE FORCE — AVEC L'ENUM, PAS AVEC SA CHAINE")
    with silence():
        app.force_ping_status("HealthyBusy")             # la chaine
        par_chaine = sante(app)
        app.force_ping_status(PingStatus.HEALTHY_BUSY)   # l'enum
        par_enum = sante(app)
        app.clear_forced_ping_status()
    ligne('force_ping_status("HealthyBusy")', par_chaine, 34)
    ligne("force_ping_status(PingStatus.…)", par_enum, 34)
    ligne("apres clear_forced_ping_status()", sante(app), 34)
    print()
    print("   La chaine a la bonne valeur, et pourtant /ping continue de")
    print("   repondre « Healthy ». Le handler leve un AttributeError qu'il")
    print("   journalise et avale : l'orchestrateur n'apprend jamais que")
    print("   l'instance est saturee, et continue de lui envoyer du trafic.")
    print("   Une panne de charge, causee par une annotation de type.")

    print("\n   Au chapitre suivant : faire executer du code a l'agent.\n")


if __name__ == "__main__":
    main()
