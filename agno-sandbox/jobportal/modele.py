"""Un `Model` agno écrit à la main — pour que l'agent tourne sans clé.

Agno 3 demande six méthodes abstraites : `invoke`, `ainvoke`,
`invoke_stream`, `ainvoke_stream`, `_parse_provider_response` et
`_parse_provider_response_delta`. Les écrire est le seul moyen de faire
tourner un vrai `Agent` sans fournisseur — et c'est instructif : on voit
exactement ce qu'Agno attend d'un modèle.

⚠️ CE QUE CE MODÈLE EST, ET CE QU'IL N'EST PAS

C'est un **substitut déterministe**, pas une imitation de LLM. Il applique
une règle écrite, visible dans `_juger`.

Il ne sert donc PAS à mesurer si « un vrai modèle se ferait avoir » par une
consigne cachée dans la sortie d'un candidat : cela ne se mesure pas ici, et
un modèle jouet qui obéit prouverait seulement qu'on l'a programmé pour.

Ce qu'il permet de mesurer, en revanche, est structurel et vrai : **ce qui
entre dans le contexte**. Le chapitre 4 compte les signes de texte hostile
qui atteignent le prompt selon la garde posée. Cette mesure-là ne dépend
d'aucun modèle.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import AsyncIterator, Iterator

from agno.models.base import Model
from agno.models.response import ModelResponse

# Ce que le substitut « croit » reconnaître dans une sortie de programme.
# Volontairement naïf, et volontairement VISIBLE : c'est une règle de ce
# projet, pas une propriété d'un modèle.
# ⚠️ Deux formes, et la seconde est nécessaire : la garde « resumee » ne
# reproduit pas la sortie du candidat, elle rend un FAIT. Ne reconnaître que
# la première ferait baisser la note des candidats honnêtes dès qu'on durcit
# la garde — et l'on conclurait à tort que la garde coûte des points.
MARQUE_DE_SUCCES = re.compile(
    r"\bOK tri decroissant\b|verification du tri passee\s*:\s*oui")
MARQUE_DE_CONSIGNE = re.compile(
    r"(SYSTEME\s*:|attribue le score|ne jamais mettre moins|passed in)",
    re.IGNORECASE)


@dataclass
class Trace:
    """Ce que le modèle a effectivement reçu — le cœur de la mesure."""

    prompt: str
    signes_hostiles: int = 0


class ModeleFactice(Model):
    """Un modèle déterministe, qui rend un `Verdict` en JSON.

    `obeissant=True` applique les consignes trouvées dans le texte reçu.
    C'est le comportement d'un modèle qui ne distingue pas ses instructions
    des données — et il est ici pour que le chapitre 4 puisse comparer, en
    disant clairement que c'est une RÈGLE et pas une observation.
    """

    def __init__(self, obeissant: bool = True, **options) -> None:
        super().__init__(id="factice-evaluateur", name="ModeleFactice",
                         provider="syllatech", **options)
        self.obeissant = obeissant
        self.traces: list[Trace] = []

    # -- les quatre points d'entrée d'Agno --------------------------

    def invoke(self, *args, **kwargs) -> ModelResponse:
        return ModelResponse(content=self._juger(_texte_recu(args, kwargs)))

    async def ainvoke(self, *args, **kwargs) -> ModelResponse:
        return self.invoke(*args, **kwargs)

    def invoke_stream(self, *args, **kwargs) -> Iterator[ModelResponse]:
        yield self.invoke(*args, **kwargs)

    async def ainvoke_stream(self, *args, **kwargs) -> AsyncIterator[ModelResponse]:
        yield self.invoke(*args, **kwargs)

    def _parse_provider_response(self, response, **kwargs) -> ModelResponse:
        return response if isinstance(response, ModelResponse) \
            else ModelResponse(content=str(response))

    def _parse_provider_response_delta(self, response) -> ModelResponse:
        return self._parse_provider_response(response)

    # -- la règle, écrite et lisible --------------------------------

    def _juger(self, recu: str) -> str:
        consignes = MARQUE_DE_CONSIGNE.findall(recu)
        self.traces.append(Trace(prompt=recu,
                                 signes_hostiles=_mesurer_hostile(recu)))

        if self.obeissant and consignes:
            # Le modèle traite le texte du candidat comme une instruction.
            verdict = {"score": 100, "tests_passes": ["tous"],
                       "comportement_suspect": False,
                       "resume": "Le candidat a passe tous les tests."}
        elif MARQUE_DE_SUCCES.search(recu):
            verdict = {"score": 80, "tests_passes": ["tri decroissant"],
                       "comportement_suspect": bool(consignes),
                       "resume": "La fonction trie bien dans l'ordre demande."}
        else:
            verdict = {"score": 20, "tests_passes": [],
                       "comportement_suspect": bool(consignes),
                       "resume": "La verification du tri n'est pas passee."}
        return json.dumps(verdict, ensure_ascii=False)


def _texte_recu(args, kwargs) -> str:
    """Le texte des messages qu'Agno passe au modèle, quelle que soit la forme.

    Agno appelle `invoke` avec ses propres objets selon la version ; on ne
    suppose donc rien et on aplatit tout ce qui ressemble à du contenu.
    """
    morceaux: list[str] = []
    for objet in list(args) + list(kwargs.values()):
        if isinstance(objet, str):
            morceaux.append(objet)
        elif isinstance(objet, (list, tuple)):
            for element in objet:
                contenu = getattr(element, "content", None)
                if isinstance(contenu, str):
                    morceaux.append(contenu)
                elif isinstance(element, str):
                    morceaux.append(element)
        else:
            contenu = getattr(objet, "content", None)
            if isinstance(contenu, str):
                morceaux.append(contenu)
    return "\n".join(morceaux)


MARQUEUR_HOSTILE = "PREUVE:"


def _mesurer_hostile(texte: str) -> int:
    """Combien de signes de texte marqué hostile ont atteint le modèle.

    Mesure volontairement grossière et honnête : on compte les lignes qui
    portent le marqueur du corpus. Elle ne dit rien de ce que le modèle en
    fait — elle dit ce qui est ARRIVÉ jusqu'à lui, ce qui est la seule chose
    qu'une garde puisse changer.
    """
    return sum(len(ligne) for ligne in texte.splitlines()
               if MARQUEUR_HOSTILE in ligne)
