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
    # TODO : rendre un objet JSON serialisable. (1) refuser un prompt absent avec un message metier, car le runtime envoie des payloads vides ; (2) attraper les exceptions, sinon LEUR MESSAGE part vers l'appelant — nom d'hote interne, chemin, requete SQL ; (3) rendre context.session_id, sans quoi deux utilisateurs sont indiscernables dans les journaux. Le chapitre 1 mesure les trois, outils/verifier_agent.py les verifie.
    return {"resultat": "a ecrire", "session": context.session_id}


if __name__ == "__main__":
    app.run()
