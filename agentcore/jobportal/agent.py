"""L'agent du job portal — le VRAI `BedrockAgentCoreApp`.

    uv run python -m jobportal.agent        # sert sur http://localhost:8080

C'est l'objet du SDK, pas une imitation : `BedrockAgentCoreApp` est une
application **Starlette**, elle sert `/invocations`, `/ping` et `/ws`, et le
décorateur `@app.entrypoint` est celui d'AWS. Le contrat est donc exerçable
ici, sans compte AWS et sans `agentcore launch`.

CE QUI EST RÉEL, ET CE QUI NE L'EST PAS

Réel : l'application, ses routes, le format des réponses, le streaming, la
santé, la gestion des erreurs, et l'en-tête de session.

Substitué : le MODÈLE. Le cours écrit `agent = Agent(model="…")` de Strands ;
ici, `repondre()` est une fonction locale. Ce qu'AgentCore emballe et déploie
n'est pas le modèle : c'est **l'entrypoint**. Remplacer `repondre` par un
appel Bedrock ne change rien au reste.
"""

from __future__ import annotations

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from .metier import repondre

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload, context):
    """Le contrat : un dict JSON entre, un objet sérialisable sort.

    ⚠️ `context.session_id` vient de l'en-tête
    `X-Amzn-Bedrock-AgentCore-Runtime-Session-Id`, posé par le runtime. En
    local il vaut `None` tant qu'on ne l'envoie pas — et c'est exactement ce
    qui fait croire que l'isolation par session « ne marche pas » quand on
    teste à la main.
    """
    # >>> depart: rendre un objet JSON serialisable. (1) refuser un prompt absent avec un message metier, car le runtime envoie des payloads vides ; (2) attraper les exceptions, sinon LEUR MESSAGE part vers l'appelant — nom d'hote interne, chemin, requete SQL ; (3) rendre context.session_id, sans quoi deux utilisateurs sont indiscernables dans les journaux. Le chapitre 1 mesure les trois, outils/verifier_agent.py les verifie.
    #     return {"resultat": "a ecrire", "session": context.session_id}
    question = payload.get("prompt")
    if not question:
        # Un refus explicite vaut mieux qu'une réponse à une question vide :
        # le modèle inventerait, et l'appelant ne saurait pas pourquoi.
        return {"erreur": "le champ « prompt » est obligatoire"}

    try:
        return {"resultat": repondre(question), "session": context.session_id}
    except Exception as erreur:      # noqa: BLE001
        # ⚠️ SANS ce bloc, le message de l'exception part TEL QUEL vers
        # l'appelant — nom d'hote interne, chemin de fichier, fragment de
        # requete SQL. Le chapitre 1 le mesure. Le detail va dans les
        # journaux ; le client recoit une phrase neutre.
        app.logger.exception("echec de l'entrypoint", exc_info=erreur)
        return {"erreur": "traitement impossible", "session": context.session_id}
    # <<<


if __name__ == "__main__":
    app.run()
