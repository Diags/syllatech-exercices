"""Le modèle factice — un `BaseLLM` CrewAI, écrit à la main.

POURQUOI PAS `crewai.LLM`

`LLM.__new__` dispatche sur le NOM du modèle : il cherche un fournisseur natif
dans une liste fermée (openai, anthropic, google, bedrock, ollama…) et, s'il
n'en trouve pas, réclame `crewai[litellm]`. Un `LLM(model="factice")` lève donc
`ImportError` avant même qu'on puisse redéfinir quoi que ce soit.

`BaseLLM` est la porte prévue pour un fournisseur maison : une seule méthode
abstraite, `call`. C'est elle qu'on implémente ici — et l'écrire une fois
apprend ce que CrewAI attend vraiment d'un modèle.

⚠️ À RETENIR AU PASSAGE : **CrewAI 1.x n'embarque plus LiteLLM.** Le cœur ne
connaît qu'une liste fermée de fournisseurs ; tout le reste passe par l'extra
`crewai[litellm]`. Un projet qui suit le cours avec un modèle exotique échoue
sur un `ImportError` qui ne parle pas du chapitre en cours.

CE QUE CE MODÈLE FAIT, ET POURQUOI C'EST IMPORTANT

Il appelle réellement les outils qu'on lui donne, et **construit sa réponse à
partir de ce qu'ils rendent**. Un modèle factice qui répond toujours la même
chose vérifie la plomberie et rien d'autre : un agent qui ignore le retour de
ses outils passerait tous les tests et se tromperait en production.
"""

from __future__ import annotations

import json
import re
from typing import Any

from crewai.llms.base_llm import BaseLLM
from pydantic import BaseModel

# CrewAI attend un agent qui « pense » puis conclut. Ce format n'est pas
# décoratif : c'est le protocole ReAct que l'exécuteur analyse. Rendre autre
# chose fait boucler l'agent jusqu'à `max_iter`.
FINAL = "Thought: j'ai ce qu'il me faut.\nFinal Answer: {}"
OUTIL = "Thought: j'ai besoin de chercher.\nAction: {nom}\nAction Input: {args}"


class ModeleFactice(BaseLLM):
    """Un modèle déterministe qui se sert vraiment de ses outils."""

    def __init__(self, model: str = "factice", **donnees: Any) -> None:
        super().__init__(model=model, **donnees)
        # `BaseLLM` est un modèle Pydantic : un attribut non déclaré ne peut
        # pas être posé normalement. On passe par __dict__, le seul endroit
        # où un mouchard de test peut vivre sans polluer le schéma.
        self.__dict__["appels"] = []
        self.__dict__["outils_vus"] = []

    @property
    def appels(self) -> list[str]:
        return self.__dict__["appels"]

    @property
    def outils_vus(self) -> list[str]:
        return self.__dict__["outils_vus"]

    # ------------------------------------------------------------------

    def call(self, messages, tools=None, callbacks=None, available_functions=None,
             from_task=None, from_agent=None, response_model=None, **kwargs):
        texte = _texte(messages)
        # ⚠️ CrewAI ne passe PAS les outils par le parametre `tools` : il les
        # decrit DANS LE PROMPT, en ReAct pur. `tools` et `available_functions`
        # arrivent vides. Les chercher la — comme le ferait n'importe qui
        # habitue aux API de function calling — donne un agent qui n'appelle
        # jamais rien, sans la moindre erreur.
        # >>> depart: recuperer les noms d'outils. CrewAI ne les passe PAS par « tools » : il les decrit DANS LE PROMPT, sous « Tool Name: ... ». Chercher uniquement dans `tools` donne un agent qui n'appelle jamais rien, sans la moindre erreur. Trois tests le verifient.
        #     noms = []
        noms = _noms(tools) or _outils_du_prompt(texte)
        # <<<
        if noms:
            self.outils_vus.append(noms)

        if response_model is not None:
            return self._structurer(response_model, texte)

        if noms and not _deja_appele(texte):
            # La QUESTION, pas tout le prompt : celui-ci contient aussi les
            # descriptions des outils, et y chercher « salaire » ferait
            # toujours choisir l'outil de salaires.
            question = getattr(from_task, "description", "") or texte
            nom, arguments = self._choisir(noms, question, texte)
            self.appels.append(nom)
            return OUTIL.format(nom=nom, args=json.dumps(arguments, ensure_ascii=False))

        return FINAL.format(self._conclure(texte, from_agent))

    # ------------------------------------------------------------------

    def _choisir(self, noms: list[str], question: str,
                 prompt: str) -> tuple[str, dict]:
        """Choisit l'outil que la QUESTION designe, et respecte son schema.

        Deux pieges, et les deux sont silencieux :

        · prendre noms[0] marche tant qu'il n'y a qu'un outil, puis devient
          faux sans rien dire — l'agent appelle toujours le meme, et l'on
          croit que le modele « prefere » cet outil ;
        · inventer les noms d'arguments fait echouer l'action avec un message
          que CrewAI renvoie au modele comme une observation ordinaire. La
          reponse finale cite alors le message d'erreur, ce qui ressemble a
          un resultat.
        """
        demande = question.lower()
        choisi = noms[0]
        for nom in noms:
            if "delegate" in nom.lower() or "delegue" in nom.lower():
                choisi = nom
                break
            if "salaire" in nom.lower() and ("salaire" in demande
                                             or "remuneration" in demande):
                choisi = nom
                break
        return choisi, self._arguments(choisi, question, prompt)

    def _arguments(self, nom: str, question: str, prompt: str) -> dict:
        """Construit les arguments a partir du SCHEMA lu dans le prompt."""
        champs = _schema_du_prompt(nom, prompt)
        if not champs:
            return {"mot_cle": _mot_cle(question)}
        valeurs = {}
        for champ in champs:
            if champ == "coworker":
                valeurs[champ] = _premier_collegue(prompt)
            elif champ == "context":
                valeurs[champ] = f"Sujet : {_mot_cle(question)}."
            elif champ in ("task", "question"):
                valeurs[champ] = question[:160]
            else:
                valeurs[champ] = _mot_cle(question)
        return valeurs

    def _conclure(self, texte: str, agent) -> str:
        """La réponse dépend du RÔLE et de ce que les outils ont rendu.

        Le rôle compte : c'est la promesse de CrewAI — des spécialistes, pas
        des clones. Un modèle factice qui l'ignore rendrait la démonstration
        du chapitre 2 vide de sens.
        """
        role = getattr(agent, "role", "") or "Agent"
        donnees = _retours(texte)
        if donnees:
            return (f"[{role}] d'apres les outils : "
                    + " ; ".join(donnees[:3])
                    + (f" (+{len(donnees) - 3})" if len(donnees) > 3 else ""))
        amont = _contexte(texte)
        if amont:
            return f"[{role}] a partir de l'analyse recue : {amont[:120]}"
        return f"[{role}] rapport factice sur « {_mot_cle(texte)} »."

    def _structurer(self, modele: type[BaseModel], texte: str):
        donnees = _retours(texte)
        valeurs = {}
        for nom, champ in modele.model_fields.items():
            valeurs[nom] = _valeur(champ.annotation, nom, donnees, texte)
        return modele(**valeurs)


# ------------------------------------------------------------------ aides

def _texte(messages) -> str:
    if isinstance(messages, str):
        return messages
    return "\n".join(str(m.get("content", "")) if isinstance(m, dict) else str(m)
                     for m in (messages or []))


def _noms(tools) -> list[str]:
    noms = []
    for outil in tools or []:
        if isinstance(outil, dict):
            noms.append(outil.get("function", {}).get("name") or outil.get("name", "?"))
        else:
            noms.append(getattr(outil, "name", "?"))
    return noms


# Le gabarit ReAct que CrewAI insere dans le prompt contient LUI-MEME les mots
# « Observation: the result of the action ». Le prendre pour une vraie
# observation fait conclure l'agent avant d'avoir rien appele — et la reponse
# cite alors le gabarit, ce qui a tout l'air d'un resultat.
GABARIT = re.compile(r"Observation:\s*the result of the action", re.IGNORECASE)


def _deja_appele(texte: str) -> bool:
    return bool(re.search(r"Observation:\s*(?!the result of the action)\S", texte))


def _outils_du_prompt(texte: str) -> list[str]:
    """Les noms d'outils, relus dans le prompt.

    CrewAI les ecrit sous la forme « Tool Name: recherche_doffres_internes ».
    Le nom est DERIVE du libelle passe a @tool — « Recherche d'offres
    internes » devient « recherche_doffres_internes ». Ce n'est ni le libelle
    ni le nom de la fonction Python : emettre l'un des deux fait echouer
    l'action.
    """
    return re.findall(r"Tool Name:\s*(\S+)", texte)


def _schema_du_prompt(nom: str, prompt: str) -> list[str]:
    """Les champs « required » du schema de l'outil `nom`, lus dans le prompt."""
    debut = prompt.find(f"Tool Name: {nom}")
    if debut == -1:
        return []
    bloc = prompt[debut:debut + 4000]
    # >>> depart: extraire les champs « required » du schema JSON de l'outil. Inventer les noms d'arguments fait echouer l'action, et l'erreur revient au modele comme une observation ordinaire : la reponse finale cite alors le message d'erreur, ce qui ressemble a un resultat.
    #     return []
    m = re.search(r'"required":\s*\[([^\]]*)\]', bloc)
    return re.findall(r'"([^"]+)"', m.group(1)) if m else []
    # <<<


def _premier_collegue(prompt: str) -> str:
    """Le nom EXACT d'un collegue, lu dans la description de l'outil.

    Une delegation a un role qui n'existe pas echoue — et l'erreur revient au
    modele sous forme d'observation, donc sans rien interrompre.
    """
    m = re.search(r"coworkers:\s*(.+)", prompt)
    if not m:
        return "Analyste"
    return m.group(1).splitlines()[0].split(",")[0].strip().rstrip(".")


def _contexte(texte: str) -> str:
    """Le resultat de la tache precedente, quand `context=[...]` l'a transmis.

    CrewAI l'insere sous « This is the context you're working with: ». Un agent
    qui ne le lit pas produit un rapport independant — et l'on croit avoir une
    chaine la ou l'on a deux taches sans rapport.
    """
    m = re.search(r"context you're working with:\s*(.+)", texte)
    return m.group(1).strip() if m else ""


def _mot_cle(texte: str) -> str:
    m = re.search(r"\b(DevOps|Python|Java|cloud|data|MLOps|Kubernetes)\b",
                  texte, re.IGNORECASE)
    return m.group(1) if m else "emploi"


def _retours(texte: str) -> list[str]:
    """Ce que les outils ont rendu, relu depuis la trace ReAct."""
    donnees = []
    for brut in re.findall(r"Observation:\s*(.+)", texte):
        if GABARIT.search("Observation: " + brut):
            continue
        try:
            charge = json.loads(brut.strip())
        except ValueError:
            donnees.append(brut.strip()[:90])
            continue
        donnees += ([str(x) for x in charge] if isinstance(charge, list)
                    else [str(charge)])
    return donnees


def _valeur(annotation, nom: str, donnees: list[str], texte: str):
    origine = getattr(annotation, "__origin__", None)
    if annotation is int:
        return min(5, max(1, len(donnees) or 3))
    if annotation is float:
        return 1.0
    if annotation is bool:
        return bool(donnees)
    if origine in (list, set, tuple):
        interieur = getattr(annotation, "__args__", (str,))[0]
        if isinstance(interieur, type) and issubclass(interieur, BaseModel):
            return [interieur(**{n: _valeur(c.annotation, n, donnees[i:i + 1], texte)
                                 for n, c in interieur.model_fields.items()})
                    for i in range(min(3, len(donnees) or 1))]
        return [str(x) for x in (donnees or [_mot_cle(texte)])][:5]
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation(**{n: _valeur(c.annotation, n, donnees, texte)
                             for n, c in annotation.model_fields.items()})
    if "source" in nom:
        return "base interne du job portal"
    return (f"{len(donnees)} resultat(s) : " + ", ".join(donnees[:2])
            if donnees else f"synthese sur « {_mot_cle(texte)} »")
