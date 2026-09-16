"""Le moteur : la boucle d'un agent, ses outils, et la delegation A2A.

CE QUE LE MOTEUR FAIT
---------------------
Il execute la conversation : il envoie les messages au modele, exécute les
outils que le modele demande, reinjecte les resultats, et recommence — dans
la limite de `maxIterations`. Un agent delegue (`type: Agent`) est un outil
comme les autres, simplement plus cher.

⚠️ LE MODELE EST FACTICE, ET C'EST VOULU
Il n'y a ni cle d'API ni reseau. `ModeleFactice` decide selon des regles
DECLAREES, lisibles en bas de ce fichier. Ce que le projet mesure n'est donc
pas la qualite d'un LLM — c'est ce que le MOTEUR fait de ses decisions :
quels outils sont autorises, combien d'appels une delegation coute, quels
spans sont emis, et ce qui arrive quand le modele demande un outil qu'il n'a
pas.

Le modele factice a une propriete que les vrais n'ont pas : il repond de
DEUX facons selon qu'on lui donne des outils ou non. Sans outils, il
affirme de memoire, et il se trompe. Avec, il observe. C'est le *grounding*,
et le chapitre 3 imprime les deux reponses cote a cote.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from . import outils as outillage
from . import traces


class ErreurMoteur(Exception):
    """Une boucle trop longue, un cycle de delegation, un agent introuvable."""


# ⚠️ ENTREES DECLAREES : le cout d'un appel, en jetons et en millisecondes.
JETONS_PAR_CARACTERE = 0.25
MS_PAR_APPEL_MODELE = 620.0
MS_PAR_APPEL_OUTIL = 45.0
PROFONDEUR_MAXIMALE = 3


def jetons(texte: str) -> int:
    return max(1, int(len(texte) * JETONS_PAR_CARACTERE))


@dataclass
class AppelOutil:
    nom: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class Message:
    role: str                     # system | user | assistant | tool
    contenu: str
    outil: str = ""


@dataclass
class Session:
    """Ce que le tableau de bord montre d'une invocation."""

    agent: str
    question: str
    messages: list[Message] = field(default_factory=list)
    appels_d_outils: list[AppelOutil] = field(default_factory=list)
    appels_de_modele: int = 0
    delegations: list[str] = field(default_factory=list)
    jetons_entree: int = 0
    jetons_sortie: int = 0
    tronquee: bool = False

    @property
    def reponse(self) -> str:
        for message in reversed(self.messages):
            if message.role == "assistant" and message.contenu:
                return message.contenu
        return ""

    @property
    def jetons(self) -> int:
        return self.jetons_entree + self.jetons_sortie

    @property
    def outils_appeles(self) -> list[str]:
        return [appel.nom for appel in self.appels_d_outils]


# ── le modele factice ────────────────────────────────────────────────────

class ModeleFactice:
    """Des regles declarees, pas un LLM. Lisez-les : c'est le but.

    ⚠️ LE POINT IMPORTANT : la premiere regle est « si j'ai un outil de
    lecture que je n'ai pas encore appele et que la question porte sur
    l'etat du cluster, je l'appelle ». La derniere est « sinon, je reponds
    de memoire ». Un agent sans outils tombe donc directement sur la
    derniere — et c'est exactement ce qui se passe avec un vrai modele.
    """

    ENCHAINEMENT = ["k8s_get_resources", "k8s_get_pod_logs",
                    "k8s_get_events", "prometheus_query"]

    # Les outils METIER, exposes par une API Spring en MCP (chapitre 6).
    METIER = ["rechercher_offres"]

    # La reponse « de memoire » : plausible, precise, et fausse.
    DE_MEMOIRE = ("D'apres mon experience, un pod qui redemarre en boucle "
                  "vient presque toujours d'une sonde de liveness trop "
                  "stricte. Augmentez son « initialDelaySeconds » a 60 s "
                  "et le probleme disparaitra.")

    def __init__(self, nom: str = "claude-fictif") -> None:
        self.nom = nom
        self.appels = 0

    def repondre(self, session: Session, disponibles: list[str],
                 observations: dict[str, Any]) -> AppelOutil | str:
        self.appels += 1
        question = session.question.lower()

        if _parle_du_cluster(question):
            for nom in self.ENCHAINEMENT:
                if nom in disponibles and nom not in session.outils_appeles:
                    return AppelOutil(nom, _arguments(nom, observations))

        if _parle_du_metier(question):
            for nom in self.METIER:
                if nom in disponibles and nom not in session.outils_appeles:
                    return AppelOutil(nom, _arguments(nom, observations,
                                                      question))

        for nom in disponibles:
            if nom.startswith("a2a:") and nom not in session.outils_appeles:
                return AppelOutil(nom)

        if not observations:
            return self.DE_MEMOIRE
        return _conclure(observations)


def _parle_du_cluster(question: str) -> bool:
    return bool(re.search(
        r"pod|cluster|redemarr|crash|memoire|incident|diagnostiq|502",
        question))


def _parle_du_metier(question: str) -> bool:
    return bool(re.search(r"offre|poste|emploi|candidat|recrut", question))


def _arguments(nom: str, observations: dict[str, Any],
               question: str = "") -> dict[str, Any]:
    """Les arguments que le modele choisit — a partir de ce qu'il a DEJA lu."""
    if nom == "k8s_get_pod_logs":
        coupable = _coupable(observations)
        return {"pod": coupable, "lignes": 5} if coupable else {"pod": ""}
    if nom == "prometheus_query":
        coupable = _coupable(observations)
        return {"requete": f'container_memory_working_set_bytes{{pod="{coupable}"}}'}
    if nom == "rechercher_offres":
        trouve = re.search(r"\b(lyon|nantes|paris)\b", question.lower())
        return {"ville": trouve.group(1) if trouve else ""}
    return {}


def _coupable(observations: dict[str, Any]) -> str:
    for ressource in observations.get("k8s_get_resources") or []:
        if ressource.get("etat") != "Running":
            return ressource["nom"]
    return ""


def _conclure(observations: dict[str, Any]) -> str:
    """La conclusion ANCREE : elle cite ce qui a ete lu, et rien d'autre."""
    morceaux: list[str] = []
    coupable = _coupable(observations)
    ressources = observations.get("k8s_get_resources") or []
    for ressource in ressources:
        if ressource["nom"] == coupable:
            morceaux.append(
                f"{coupable} est en {ressource['etat']} apres "
                f"{ressource['redemarrages']} redemarrages")

    journal = observations.get("k8s_get_pod_logs") or []
    for ligne in journal:
        if "OutOfMemoryError" in ligne:
            morceaux.append("son journal finit sur une OutOfMemoryError")

    metrique = observations.get("prometheus_query") or {}
    if metrique and not metrique.get("vide"):
        valeur = metrique["resultat"][0]["valeur"]
        morceaux.append(f"sa memoire atteint {valeur / 1024 ** 2:.0f} Mio")

    if not morceaux:
        return ("Je n'ai rien pu observer : aucun outil n'a rendu de "
                "resultat exploitable.")
    return ("Diagnostic ancre sur trois observations — "
            + " ; ".join(morceaux)
            + ". La limite de memoire du conteneur est trop basse pour la "
              "charge : c'est elle qu'il faut relever, pas la sonde.")


# ── le moteur ────────────────────────────────────────────────────────────

class Moteur:
    """Il execute des agents. Il ne sait rien de Kubernetes."""

    def __init__(self, api, cluster, modele: ModeleFactice | None = None,
                 collecteur: traces.Collecteur | None = None,
                 outils_en_plus: dict | None = None) -> None:
        self.api = api
        self.cluster = cluster
        self.modele = modele or ModeleFactice()
        self.collecteur = collecteur or traces.Collecteur()
        # Les outils du `kagent-tool-server`, plus ceux qu'un
        # `RemoteMCPServer` metier ajouterait — l'API Spring du chapitre 6,
        # par exemple. Le moteur ne fait pas la difference, et c'est le but.
        self.catalogue = {**outillage.catalogue(cluster),
                          **(outils_en_plus or {})}

    # -- ce qu'un agent a le droit d'appeler -----------------------------

    def trousseau(self, agent) -> outillage.Trousseau:
        # >>> depart: rassembler les outils MCP et les agents delegues (prefixe « a2a: »)
        #     return outillage.Trousseau(self.catalogue, [])
        corps = agent.spec.get("declarative") or {}
        accordes: list[str] = []
        for outil in corps.get("tools") or []:
            if outil.get("type") == "McpServer":
                accordes.extend((outil.get("mcpServer") or {}).get(
                    "toolNames") or [])
            elif outil.get("type") == "Agent":
                accordes.append(f"a2a:{(outil.get('agent') or {}).get('name')}")
        return outillage.Trousseau(self.catalogue, accordes)
        # <<<

    # -- l'invocation ----------------------------------------------------

    def invoquer(self, nom: str, question: str, espace: str = "kagent",
                 parent: traces.Span | None = None,
                 propager: bool = True,
                 pile: tuple[str, ...] = ()) -> Session:
        agent = self.api.lire("Agent", nom, espace)
        if agent is None:
            raise ErreurMoteur(f"agent introuvable : « {nom} »")
        # >>> depart: refuser un cycle de delegation, et plafonner la profondeur
        #     pass
        if nom in pile:
            # ⚠️ Un cycle de delegation ne se voit pas dans les manifestes :
            # chacun est valide isolement. Il faut le detecter A L'EXECUTION.
            raise ErreurMoteur(
                f"cycle de delegation : {' → '.join((*pile, nom))}")
        if len(pile) >= PROFONDEUR_MAXIMALE:
            raise ErreurMoteur(
                f"profondeur de delegation depassee ({PROFONDEUR_MAXIMALE}) : "
                f"{' → '.join((*pile, nom))}")
        # <<<

        # ⚠️ `propager=False` : le span s'ouvre SANS parent, donc dans une
        # trace neuve. C'est le bogue d'observabilite du chapitre 5.
        span = self.collecteur.ouvrir(
            f"invoke_agent {nom}", parent if propager else None,
            **{"agent.nom": nom, "gen_ai.operation.name": "invoke_agent"})

        corps = agent.spec.get("declarative") or {}
        trousseau = self.trousseau(agent)
        session = Session(nom, question)
        session.messages.append(
            Message("system", corps.get("systemMessage", "")))
        session.messages.append(Message("user", question))

        observations: dict[str, Any] = {}
        plafond = int(corps.get("maxIterations", 10))

        for _ in range(plafond):
            disponibles = trousseau.utilisables + [
                a for a in trousseau.accordes if a.startswith("a2a:")]
            appel_span = self.collecteur.ouvrir(
                "chat", span, **{
                    "gen_ai.operation.name": "chat",
                    "gen_ai.request.model": self.modele.nom,
                    "gen_ai.usage.input_tokens": _entree(session),
                })
            appel_span.millisecondes = MS_PAR_APPEL_MODELE
            session.appels_de_modele += 1
            session.jetons_entree += _entree(session)

            decision = self.modele.repondre(session, disponibles, observations)

            if isinstance(decision, str):
                appel_span.attributs["gen_ai.usage.output_tokens"] = \
                    jetons(decision)
                session.jetons_sortie += jetons(decision)
                session.messages.append(Message("assistant", decision))
                span.millisecondes = sum(
                    s.millisecondes for s in self.collecteur.enfants(span))
                return session

            appel_span.attributs["gen_ai.usage.output_tokens"] = jetons(
                decision.nom)
            session.jetons_sortie += jetons(decision.nom)
            session.appels_d_outils.append(decision)

            if decision.nom.startswith("a2a:"):
                delegue = decision.nom[len("a2a:"):]
                fille = self.invoquer(delegue, question, espace, span,
                                      propager, (*pile, nom))
                session.delegations.append(delegue)
                session.jetons_entree += fille.jetons_entree
                session.jetons_sortie += fille.jetons_sortie
                session.appels_de_modele += fille.appels_de_modele
                observations[decision.nom] = fille.reponse
                session.messages.append(
                    Message("tool", fille.reponse, decision.nom))
                continue

            outil_span = self.collecteur.ouvrir(
                f"execute_tool {decision.nom}", span,
                **{"outil.nom": decision.nom,
                   "gen_ai.operation.name": "execute_tool"})
            outil_span.millisecondes = MS_PAR_APPEL_OUTIL
            try:
                resultat = trousseau.appeler(decision.nom, **decision.arguments)
            except (outillage.ErreurOutil, Exception) as erreur:   # noqa: BLE001
                outil_span.attributs["erreur"] = type(erreur).__name__
                resultat = f"erreur : {erreur}"
            observations[decision.nom] = resultat
            session.messages.append(
                Message("tool", str(resultat), decision.nom))

        session.tronquee = True
        span.millisecondes = sum(s.millisecondes
                                 for s in self.collecteur.enfants(span))
        return session


def _entree(session: Session) -> int:
    return jetons("".join(m.contenu for m in session.messages))
