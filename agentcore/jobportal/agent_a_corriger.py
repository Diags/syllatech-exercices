"""Le même agent, avec cinq défauts — et il se déploie très bien.

    uv run python outils/verifier_agent.py jobportal.agent_a_corriger

Aucun n'est une erreur de syntaxe. `agentcore configure && agentcore launch`
réussit, l'endpoint répond 200, et les tests d'intégration passent. Les cinq
se découvrent en production, dans cet ordre de coût croissant.
"""

from __future__ import annotations

import datetime

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from .metier import chercher

app = BedrockAgentCoreApp()


# 1. Deux entrypoints. Le SDK n'en garde qu'un — le dernier decore — et ne
#    dit rien. Celui-ci ne sera jamais appele.
@app.entrypoint
def rechercher(payload):
    return {"resultat": [str(o) for o in chercher(payload["prompt"])]}


# 2. Pas de parametre `context` : plus de session_id, donc aucun moyen de
#    rattacher un appel a une conversation ni de separer deux utilisateurs
#    dans les journaux.
@app.entrypoint
def invoke(payload):
    # 3. `payload["prompt"]` sans garde : un payload vide leve une KeyError.
    #    Le runtime en envoie lors de ses verifications.
    question = payload["prompt"]

    # 4. Aucun `try`. Si `chercher` leve, le message de l'exception part
    #    tel quel vers l'appelant.
    offres = chercher(question)

    # 5. `datetime` n'est pas serialisable en JSON. Le runtime ne leve pas :
    #    il str()-ifie tout le dictionnaire, et le client recoit un repr
    #    Python dans une chaine.
    return {"resultat": [str(o) for o in offres],
            "genere_le": datetime.datetime.now()}


if __name__ == "__main__":
    app.run()
