"""L'assistant du portail : un agent avec outils, et la trace de chaque requête.

Trois approches, comparées sur le banc :
- repondre_rag : on cherche les offres proches de la question, on les donne
  au modèle, un seul appel ;
- repondre_agent : le modèle choisit ses outils (recherche, filtres,
  candidatures), le code les exécute, et l'on boucle jusqu'à la réponse ;
- repondre_guide : le code fait lui-même ce qui est déterministe (compter les
  candidatures d'une référence citée, classer, chercher) et le modèle rédige.
  Mesuré : avec Qwen2.5 1,5B, l'agent annonce « je vais rechercher » sans
  appeler d'outil ; ici, rien ne dépend de cet appel.
Chaque réponse s'accompagne d'une Trace : durée, appels au modèle, jetons,
outils appelés. C'est elle que le chapitre « Observer » exploite.
"""

import json
import re
import time
import uuid
from dataclasses import dataclass, field

import ollama

from jobportal import outils
from jobportal.donnees import PAR_REFERENCE
from jobportal.recherche import Index

MODELE = "qwen2.5:1.5b-instruct-q4_K_M"
OPTIONS = {"temperature": 0, "seed": 42, "num_predict": 400}  # une réponse bornée, toujours

SYSTEME = """Tu es l'assistant du portail d'emploi. Tu réponds en français, uniquement sur les offres du portail et leurs candidatures.
Pour toute information sur une offre, appelle un outil : n'invente jamais une offre, une référence ou un chiffre.
Cite la référence (OFF-xxx) de chaque offre dont tu parles, et seulement celles que les outils ont rendues.
Si les outils ne trouvent rien, dis qu'aucune offre du portail ne correspond.
Si la question ne porte pas sur les offres ou les candidatures du portail, réponds que tu ne peux pas y répondre."""

SYSTEME_RAG = """Tu es l'assistant du portail d'emploi. Tu réponds en français, uniquement à partir des offres fournies.
Cite la référence (OFF-xxx) de chaque offre dont tu parles. N'invente jamais une offre, une référence ou un chiffre.
Si aucune offre fournie ne correspond, dis qu'aucune offre du portail ne correspond.
Si la question ne porte pas sur les offres du portail, réponds que tu ne peux pas y répondre."""


@dataclass
class Trace:
    identifiant: str
    question: str
    modele: str
    appels_modele: int = 0
    jetons_entree: int = 0
    jetons_sortie: int = 0
    outils: list = field(default_factory=list)
    sources: list = field(default_factory=list)  # les offres données au modèle
    alertes: list = field(default_factory=list)  # ce que les défenses ont arrêté ou retiré
    duree_ms: int = 0
    _debut: float = field(default_factory=time.perf_counter, repr=False)
    _contexte: str = field(default="", repr=False)  # les données données au modèle (non journalisées)

    def compter(self, reponse: ollama.ChatResponse) -> None:
        self.appels_modele += 1
        self.jetons_entree += reponse.prompt_eval_count or 0
        self.jetons_sortie += reponse.eval_count or 0

    def terminer(self, texte: str) -> tuple[str, "Trace"]:
        self.duree_ms = round((time.perf_counter() - self._debut) * 1000)
        return texte, self


def nouvelle_trace(question: str, modele: str) -> Trace:
    return Trace(identifiant=uuid.uuid4().hex[:12], question=question, modele=modele)


def repondre_rag(client: ollama.Client, index: Index, question: str,
                 modele: str = MODELE) -> tuple[str, Trace]:
    trace = nouvelle_trace(question, modele)
    offres = json.dumps([outils._fiche(o) for o in index.chercher(question)], ensure_ascii=False)
    r = client.chat(model=modele, options=OPTIONS, messages=[
        {"role": "system", "content": SYSTEME_RAG},
        {"role": "user", "content": f"Offres du portail :\n{offres}\n\nQuestion : {question}"}])
    trace.compter(r)
    return trace.terminer(r.message.content)


SYSTEME_GUIDE = """Tu es l'assistant du portail d'emploi. Tu réponds en français, uniquement à partir des données fournies.
Cite la référence (OFF-xxx) de chaque offre dont tu parles. Ne cite que des offres fournies ; n'invente jamais une offre, une référence ou un chiffre.
Si les données disent qu'une offre n'existe pas, ou si aucune offre fournie ne correspond, dis-le.
Si la question ne porte pas sur les offres ou les candidatures du portail, réponds que tu ne peux pas y répondre."""

REFERENCE = re.compile(r"OFF-\d{3}")
# Écrite d'après la SEULE formulation du banc : le jeu de validation dira si une
# règle écrite à la main tient face à une autre formulation.
CLASSEMENT = re.compile(r"le plus de candidatures", re.I)


def donnees_guidees(index: Index, question: str) -> dict:
    """Le code décide ce que le modèle reçoit : compter, classer, ou chercher."""
    donnees = {}
    for reference in REFERENCE.findall(question):
        resultat = json.loads(outils.compter_candidatures(reference))
        donnees.setdefault("candidatures", []).append(resultat)
    if CLASSEMENT.search(question):
        donnees["classement"] = json.loads(outils.classement_candidatures(3))
    if not donnees:
        # Avec la description : c'est elle qui a fait trouver l'offre (« Kubernetes »).
        donnees["offres"] = [{**outils._fiche(o), "description": o["description"]}
                             for o in index.chercher(question)]
    return donnees


def _outils_appeles(question: str, donnees: dict) -> list[dict]:
    """Pour la trace : ce que le code a exécuté à la place du modèle."""
    appels = [{"nom": "compter_candidatures", "arguments": {"reference": r}, "ms": 0}
              for r in REFERENCE.findall(question)]
    if "classement" in donnees:
        appels.append({"nom": "classement_candidatures", "arguments": {"n": 3}, "ms": 0})
    if "offres" in donnees:
        appels.append({"nom": "rechercher_offres", "arguments": {"requete": question}, "ms": 0})
    return appels


def repondre_guide(client: ollama.Client, index: Index, question: str, modele: str = MODELE,
                   systeme: str = SYSTEME_GUIDE, encadrer: bool = False) -> tuple[str, Trace]:
    """Le code fait le déterministe — compter, classer, chercher — et le modèle rédige.
    Aucun appel d'outil ne dépend du modèle : c'est là que le petit modèle échouait.
    Mesuré : sans la description des offres, il répondait « aucune offre » à des questions
    qu'elle seule éclairait (« Kubernetes », « tests d'intrusion »).
    `encadrer` place les données entre balises <donnees> (défense du chapitre sécurité)."""
    trace = nouvelle_trace(question, modele)
    donnees = donnees_guidees(index, question)
    trace.outils = _outils_appeles(question, donnees)
    trace.sources = [e["reference"] for liste in donnees.values() for e in liste
                     if e.get("reference") in PAR_REFERENCE]
    trace._contexte = json.dumps(donnees, ensure_ascii=False)
    contexte = f"<donnees>\n{trace._contexte}\n</donnees>" if encadrer else trace._contexte
    r = client.chat(model=modele, options=OPTIONS, messages=[
        {"role": "system", "content": systeme},
        {"role": "user", "content": f"Données du portail :\n{contexte}\n\nQuestion : {question}"}])
    trace.compter(r)
    return trace.terminer(r.message.content)


def relier_references(texte: str, offres: list[dict]) -> str:
    """Ajoute « (OFF-xxx) » après le titre d'une offre fournie que la réponse nomme sans la citer.

    Mesuré : le petit modèle donne souvent le bon fait sans la référence (« l'offre
    Ingénieur IA, 21 candidatures »). La citation doit être garantie par le code, pas
    espérée du modèle. Les titres longs passent d'abord, et une zone déjà reliée n'est
    plus disponible : « Développeur Java » ne s'accroche pas dans « Développeur Java senior »."""
    # TODO : pour chaque offre fournie que la réponse nomme sans sa référence, ajouter « (OFF-xxx) » après son titre. Les titres longs d'abord ; une zone déjà reliée n'est plus disponible.
    return texte


def repondre_guide_relie(client: ollama.Client, index: Index, question: str,
                         modele: str = MODELE, **reglages) -> tuple[str, Trace]:
    """L'approche guidée, puis les références reliées par le code, sur les seules
    offres données au modèle (trace.sources)."""
    texte, trace = repondre_guide(client, index, question, modele, **reglages)
    return relier_references(texte, [PAR_REFERENCE[r] for r in trace.sources]), trace


def repondre_agent(client: ollama.Client, index: Index, question: str,
                   modele: str = MODELE, tours_max: int = 4) -> tuple[str, Trace]:
    trace = nouvelle_trace(question, modele)
    messages = [{"role": "system", "content": SYSTEME}, {"role": "user", "content": question}]
    for _ in range(tours_max):
        r = client.chat(model=modele, messages=messages, tools=outils.SCHEMAS, options=OPTIONS)
        trace.compter(r)
        if not r.message.tool_calls:
            return trace.terminer(r.message.content)
        messages.append(r.message)
        for appel in r.message.tool_calls:
            nom, arguments = appel.function.name, dict(appel.function.arguments)
            debut = time.perf_counter()
            resultat = outils.executer(index, nom, arguments)
            trace.outils.append({"nom": nom, "arguments": arguments,
                                 "ms": round((time.perf_counter() - debut) * 1000)})
            messages.append({"role": "tool", "tool_name": nom, "content": resultat})
    return trace.terminer("Je n'ai pas pu terminer la recherche : reformulez la question, s'il vous plaît.")
