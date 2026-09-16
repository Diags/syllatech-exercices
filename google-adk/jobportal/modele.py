"""Le modèle factice — un `BaseLlm` ADK, écrit à la main.

ADK est conçu pour Gemini : `Agent(model="gemini-flash-latest")` résout un nom
de modèle vers un client Google, qui demande une clé. `BaseLlm` est la porte
prévue pour un fournisseur maison, et elle n'a **qu'une seule** méthode
abstraite : `generate_content_async`, un générateur asynchrone de
`LlmResponse`.

CE QUE CE MODÈLE FAIT

Il appelle réellement les outils — une `FunctionCall` dans une `Part` — lit
leur retour au tour suivant, et construit sa réponse à partir de là. Il
respecte aussi `output_key` : ce que l'agent écrit dans l'état de session est
ce que le suivant relit, et c'est tout le mécanisme du chapitre 4.
"""

from __future__ import annotations

import json
import re
from typing import AsyncGenerator

from google.adk.models import BaseLlm, LlmRequest, LlmResponse
from google.genai import types


class ModeleFactice(BaseLlm):
    """Déterministe, sans réseau, et qui se sert vraiment de ses outils.

    `BaseLlm` est un modèle Pydantic : les compteurs passent par `__dict__`,
    sans quoi Pydantic refuse l'affectation.
    """

    model: str = "factice"

    def __init__(self, nom: str = "factice", **donnees) -> None:
        super().__init__(model=nom, **donnees)
        self.__dict__["appels"] = []
        self.__dict__["tours"] = 0
        self.__dict__["prompts"] = []

    @property
    def appels(self) -> list[str]:
        return self.__dict__["appels"]

    @property
    def tours(self) -> int:
        return self.__dict__["tours"]

    @property
    def prompts(self) -> list[str]:
        return self.__dict__["prompts"]

    # ------------------------------------------------------------------

    async def generate_content_async(self, llm_request: LlmRequest,
                                     stream: bool = False
                                     ) -> AsyncGenerator[LlmResponse, None]:
        self.__dict__["tours"] += 1
        texte = _texte(llm_request)
        self.prompts.append(texte)

        # >>> depart: si des outils sont disponibles et qu'aucun retour n'est encore arrive, rendre une LlmResponse dont le content porte une types.Part(function_call=types.FunctionCall(...)). Sinon, repondre en texte. Cinq tests le verifient.
        #     yield LlmResponse(content=types.Content(role="model", parts=[types.Part(text="")])); return
        outils = _outils(llm_request)
        if outils and not _retours(llm_request):
            nom, arguments = _choisir(outils, texte, _instruction(llm_request))
            self.appels.append(nom)
            yield LlmResponse(content=types.Content(
                role="model",
                parts=[types.Part(function_call=types.FunctionCall(
                    name=nom, args=arguments))]))
            return

        yield LlmResponse(content=types.Content(
            role="model", parts=[types.Part(text=self._repondre(llm_request, texte))]))
        # <<<

    # ------------------------------------------------------------------

    def _repondre(self, llm_request: LlmRequest, texte: str) -> str:
        donnees = _retours(llm_request)
        nom = self.model
        if donnees:
            return (f"[{nom}] d'apres les outils : " + " ; ".join(donnees[:3])
                    + (f" (+{len(donnees) - 3})" if len(donnees) > 3 else ""))

        # L'instruction de l'agent porte déjà l'état substitué : un `{analyse}`
        # dans l'instruction du rédacteur est remplacé par ADK AVANT l'appel.
        # C'est tout le mécanisme d'`output_key`, et c'est ici qu'on le voit.
        instruction = _instruction(llm_request)
        amont = _amont(instruction)
        if amont:
            return f"[{nom}] a partir de « {amont[:70]} » : synthese."
        return f"[{nom}] reponse sur « {_mot_cle(texte)} »."


# ------------------------------------------------------------------ aides

def _texte(llm_request: LlmRequest) -> str:
    morceaux = []
    for contenu in (llm_request.contents or []):
        for part in (contenu.parts or []):
            if part.text:
                morceaux.append(part.text)
    return "\n".join(morceaux)


def _instruction(llm_request: LlmRequest) -> str:
    config = getattr(llm_request, "config", None)
    return str(getattr(config, "system_instruction", "") or "")


def _outils(llm_request: LlmRequest) -> list[dict]:
    """Les déclarations de fonctions, telles qu'ADK les envoie au modèle.

    Elles vivent dans `config.tools[].function_declarations` — pas dans un
    paramètre `tools` comme chez d'autres frameworks. Les chercher ailleurs
    donne un agent qui n'appelle jamais rien, sans erreur.
    """
    declarations = []
    config = getattr(llm_request, "config", None)
    for outil in (getattr(config, "tools", None) or []):
        for declaration in (getattr(outil, "function_declarations", None) or []):
            declarations.append({
                "name": declaration.name,
                "parametres": list(
                    (getattr(declaration.parameters, "properties", None) or {})),
            })
    return declarations


def _retours(llm_request: LlmRequest) -> list[str]:
    donnees: list[str] = []
    for contenu in (llm_request.contents or []):
        for part in (contenu.parts or []):
            reponse = getattr(part, "function_response", None)
            if reponse is None:
                continue
            # La reponse d'un transfert n'est pas une donnee : c'est un
            # accuse de reception. La compter ferait dire a l'agent « d'apres
            # les outils : None », ce qui a tout l'air d'un resultat vide.
            if reponse.name == "transfer_to_agent":
                continue
            charge = reponse.response or {}
            if charge.get("status") == "error":
                donnees.append(str(charge.get("message", "erreur")))
                continue
            valeurs = charge.get("offres")
            if valeurs is None and "median" in charge:
                valeurs = [f"salaire median : {charge['median'] // 1000}k EUR"]
            if valeurs is None:
                valeurs = [str(charge)]
            donnees += [str(x) for x in valeurs]
    return donnees


def _choisir(outils: list[dict], texte: str,
             instruction: str = "") -> tuple[str, dict]:
    """Choisit l'outil, puis construit ses arguments.

    ⚠️ `transfer_to_agent` est un outil comme les autres, ajoute par ADK des
    qu'un agent a des `sub_agents`. Son argument `agent_name` doit etre un nom
    EXACT de sous-agent — ADK leve « Agent X not found in the agent tree » et
    l'execution s'arrete. C'est la premiere chose qui casse quand on ecrit un
    modele soi-meme, et c'est aussi ce qu'un vrai modele rate parfois.
    """
    demande = texte.lower()
    metier = [o for o in outils if o["name"] != "transfer_to_agent"]

    # ⚠️ ADK donne AUSSI « transfer_to_agent » aux sous-agents, pour qu'ils
    # puissent rendre la main. Le choisir systematiquement fait rebondir la
    # question entre le coordinateur et l'expert jusqu'a epuisement de la pile
    # — et l'erreur qui sort alors est un « RecursionError » dans un deepcopy
    # de Pydantic, qui ne parle ni d'agents ni de delegation.
    #
    # La regle qui evite cela est celle d'un vrai modele : on delegue quand on
    # n'a PAS l'outil qu'il faut. Si on l'a, on s'en sert.
    # >>> depart: ne deleguer QUE si aucun outil metier n'est disponible. Choisir « transfer_to_agent » systematiquement fait rebondir la question entre coordinateur et expert jusqu'au RecursionError. Deux tests le verifient.
    #     pass
    if not metier:
        return "transfer_to_agent", {
            "agent_name": _destinataire(instruction, demande)}
    # <<<

    outils = metier
    choisi = outils[0]
    for outil in outils:
        if "salaire" in outil["name"].lower() and "salaire" in demande:
            choisi = outil
            break
    arguments = {}
    for parametre in choisi["parametres"]:
        arguments[parametre] = (_ville(texte) if "ville" in parametre
                                else _mot_cle(texte))
    return choisi["name"], arguments


def _destinataire(instruction: str, demande: str) -> str:
    """Le sous-agent a qui deleguer, choisi sur sa DESCRIPTION.

    ADK liste les sous-agents dans l'instruction, avec leur description. C'est
    elle — pas leur instruction — que le coordinateur lit pour choisir : une
    description vague produit une delegation au hasard, sans aucune erreur.
    """
    candidats = re.findall(r"Agent name: (\S+)\s+Agent description: (.+)",
                           instruction)
    if not candidats:
        return ""
    # >>> depart: choisir le sous-agent dont la DESCRIPTION partage le plus de mots avec la demande. C'est la description — jamais l'instruction — qu'ADK donne au coordinateur pour decider. Trois tests le verifient.
    #     return candidats[0][0]
    mots = re.findall(r"[a-z]{4,}", demande)
    meilleur, note_max = candidats[0][0], -1
    for nom, description in candidats:
        note = sum(1 for mot in mots if mot in description.lower())
        if note > note_max:
            meilleur, note_max = nom, note
    return meilleur
    # <<<


def _amont(instruction: str) -> str:
    """Ce que l'agent précédent a écrit, déjà substitué dans l'instruction."""
    m = re.search(r"\[(\w+)\][^\n]*", instruction)
    return m.group(0) if m else ""


def _mot_cle(texte: str) -> str:
    m = re.search(r"\b(DevOps|Python|Java|cloud|data|MLOps|Kubernetes)\b",
                  texte, re.IGNORECASE)
    return m.group(1) if m else "emploi"


def _ville(texte: str) -> str:
    m = re.search(r"\b(Lyon|Paris|Nantes|Bordeaux|Lille|Toulouse)\b",
                  texte, re.IGNORECASE)
    return m.group(1) if m else "Lyon"
