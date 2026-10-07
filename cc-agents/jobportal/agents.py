"""Le runtime de sous-agents — la sémantique de Claude Code, en 150 lignes.

Pourquoi le réécrire plutôt que de lancer de vrais sous-agents ? Parce qu'un
vrai sous-agent coûte une clé d'API, un réseau, et surtout **ne se mesure
pas** : on ne peut pas ouvrir sa fenêtre de contexte pour vérifier ce qu'elle
contient. Ici, si.

Ce runtime reproduit fidèlement les trois règles qui comptent :

1. **Un agent est un fichier** `.claude/agents/<nom>.md` — front-matter YAML
   (`name`, `description`, `tools`, `model`) puis le prompt système en prose.
   Les fichiers de ce projet sont de VRAIS agents : copiez-les dans votre
   projet, ils fonctionnent.
2. **`tools` est une liste blanche.** Un outil absent de la liste n'est pas
   « déconseillé » : il est **refusé**. C'est ce qui garantit qu'un réviseur
   en lecture seule ne réécrira jamais le code qu'il juge.
3. **Le contexte est isolé, et seule la conclusion remonte.** L'agent peut
   lire cinquante fichiers ; la session principale ne reçoit que son rapport.

Ce qui est substitué : le modèle. `modele.py` fournit un analyseur factice et
déterministe. La structure — isolation, filtrage d'outils, orchestration — est
ce que le cours enseigne, et elle est ici entièrement authentique.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import depot

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_AGENTS = RACINE / ".claude" / "agents"

SIGNES_PAR_TOKEN = 3.6      # approximation assumée : on cherche l'ordre de grandeur

# Le coût relatif des modèles, normalisé sur Haiku. Les rapports comptent, pas
# les montants : ils bougent, l'arbitrage non.
COUT = {"haiku": 1.0, "sonnet": 3.0, "opus": 15.0, "inherit": 3.0}

# La latence d'un aller-retour modele, par modele. Elle est ATTENDUE pour de
# vrai (time.sleep) et non ajoutee apres coup : sans cela, le fan-out ne
# gagnerait rien — le travail local est trop rapide, et l'ouverture des fils
# couterait plus que le calcul. Or dans une vraie session, c'est exactement
# l'inverse : la latence domine tout. Ces valeurs sont reduites d'un facteur
# dix par rapport au reel pour qu'un chapitre s'execute en une seconde.
LATENCE = {"haiku": 0.25, "sonnet": 0.60, "opus": 1.20, "inherit": 0.60}


class OutilRefuse(RuntimeError):
    """Levée quand un agent appelle un outil absent de son « tools ».

    C'est le moindre privilège, appliqué. Un réviseur en lecture seule qui
    tente d'écrire ne produit pas un mauvais patch : il ne produit rien.
    """


def tokens(texte: str) -> int:
    return round(len(texte) / SIGNES_PAR_TOKEN)


# --------------------------------------------------------------- le contexte

@dataclass
class Contexte:
    """Une fenêtre de contexte, et ce qui s'y accumule.

    Le chapitre 1 dit que « chaque fichier lu s'y accumule ». Ici on le compte.
    """

    nom: str
    entrees: list[tuple[str, str]] = field(default_factory=list)

    def ajouter(self, source: str, texte: str) -> None:
        self.entrees.append((source, texte))

    @property
    def taille(self) -> int:
        return sum(tokens(t) for _, t in self.entrees)

    def __repr__(self) -> str:
        return f"<contexte {self.nom} : {len(self.entrees)} entrees, {self.taille} tokens>"


# ------------------------------------------------------------- la définition

@dataclass
class Agent:
    nom: str
    description: str
    outils: list[str]
    modele: str
    prompt: str

    @classmethod
    def depuis(cls, fichier: Path) -> "Agent":
        texte = fichier.read_text(encoding="utf-8")
        champs, prompt = _frontmatter(texte)
        manquants = [c for c in ("name", "description") if c not in champs]
        if manquants:
            raise ValueError(f"{fichier.name} : champ(s) obligatoire(s) absent(s) : "
                             f"{', '.join(manquants)}")
        # « tools » absent = hérite de tout. C'est le défaut de Claude Code, et
        # c'est précisément ce qu'on ne veut PAS pour un agent de lecture.
        outils = ([o.strip() for o in champs["tools"].split(",")]
                  if "tools" in champs else ["*"])
        return cls(champs["name"], champs["description"], outils,
                   champs.get("model", "inherit"), prompt.strip())


def _frontmatter(texte: str) -> tuple[dict, str]:
    if not texte.startswith("---"):
        return {}, texte
    fin = texte.find("\n---", 3)
    if fin == -1:
        return {}, texte
    champs: dict[str, str] = {}
    cle = None
    for ligne in texte[3:fin].splitlines():
        if not ligne.strip():
            continue
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", ligne)
        if m:
            cle = m.group(1)
            champs[cle] = m.group(2).strip()
        elif cle and ligne.startswith((" ", "\t")):
            champs[cle] = (champs[cle] + " " + ligne.strip()).strip()
    return champs, texte[fin + 4:]


def charger(dossier: Path = DOSSIER_AGENTS) -> dict[str, Agent]:
    return {a.nom: a for a in (Agent.depuis(f) for f in sorted(dossier.glob("*.md")))}


# ------------------------------------------------------------- l'exécution

@dataclass
class Rapport:
    """Ce que la session principale reçoit. RIEN D'AUTRE ne remonte."""

    agent: str
    texte: str
    constats: list[dict] = field(default_factory=list)
    tokens_internes: int = 0     # ce que l'agent a lu — resté chez lui
    cout: float = 0.0
    secondes: float = 0.0

    @property
    def tokens_rendus(self) -> int:
        return tokens(self.texte)


class Session:
    """La session principale : elle orchestre, et garde la main."""

    def __init__(self, agents: dict[str, Agent] | None = None,
                 acceleration: float = 1.0) -> None:
        self.agents = agents if agents is not None else charger()
        self.contexte = Contexte("session principale")
        self.facture = 0.0
        # Les tests n'ont pas a attendre : ils verifient le rapport entre deux
        # durees, pas leur valeur absolue.
        self.acceleration = acceleration

    # -- outils, filtrés par la liste blanche de l'agent ------------------

    def _outils(self, agent: Agent, contexte: Contexte) -> dict:
        def garde(nom, fonction):
            def appel(*a, **k):
                # TODO : refuser l'appel si l'outil est absent du « tools » de l'agent (« * » veut dire : herite de tout). Lever OutilRefuse en nommant l'outil ET la liste. C'est LA garantie du chapitre 2 : trois tests la verifient.
                pass
                sortie = fonction(*a, **k)
                contexte.ajouter(nom, str(sortie))
                return sortie
            return appel

        return {
            "Read": garde("Read", depot.lire),
            "Grep": garde("Grep", depot.chercher),
            "Glob": garde("Glob", depot.lister),
            "Write": garde("Write", lambda chemin, contenu: f"ecrit {chemin}"),
            "Edit": garde("Edit", lambda chemin, avant, apres: f"modifie {chemin}"),
        }

    # -- déléguer ---------------------------------------------------------

    def deleguer(self, nom: str, tache: str, travail=None) -> Rapport:
        """Lance un sous-agent. Son contexte est NEUF et meurt avec lui."""
        if nom not in self.agents:
            raise KeyError(f"pas d'agent « {nom} » dans {DOSSIER_AGENTS} "
                           f"(connus : {', '.join(sorted(self.agents))})")
        agent = self.agents[nom]

        # Contexte neuf : l'agent ne sait RIEN de la conversation en cours.
        # C'est le prix de l'isolation, et la cause de l'erreur la plus
        # fréquente — lui confier une tâche qui suppose ce qu'on vient de dire.
        contexte = Contexte(f"agent {nom}")
        contexte.ajouter("prompt systeme", agent.prompt)
        contexte.ajouter("tache", tache)

        debut = time.perf_counter()
        outils = self._outils(agent, contexte)
        rapport = (travail or _travail_par_defaut)(agent, tache, outils)
        time.sleep(LATENCE[agent.modele] * self.acceleration)
        secondes = time.perf_counter() - debut

        rapport.agent = nom
        rapport.tokens_internes = contexte.taille
        rapport.cout = contexte.taille * COUT[agent.modele] / 1000
        rapport.secondes = secondes
        self.facture += rapport.cout

        # SEUL le rapport entre dans la session principale.
        self.contexte.ajouter(f"rapport de {nom}", rapport.texte)
        return rapport


def _travail_par_defaut(agent: Agent, tache: str, outils: dict) -> Rapport:
    return Rapport(agent.nom, f"(aucun travail fourni pour « {tache} »)")


def fan_out(session: "Session", taches: list[tuple[str, str, object]]) -> list[Rapport]:
    """Lance plusieurs sous-agents EN MEME TEMPS.

    Le gain de temps n'est pas le principal : c'est l'isolation. Chaque agent
    a son contexte, donc aucun ne pollue celui des autres ni celui de la
    session — et l'orchestrateur ne reçoit que N conclusions courtes.

    ⚠️ Le fan-out ne vaut que pour des tâches VRAIMENT independantes. Deux
    agents qui ecrivent le meme fichier se marchent dessus ; un agent qui
    attend le resultat d'un autre n'est pas un fan-out mais un pipeline.
    `conflit()` ci-dessous montre le premier cas, et il n'est pas theorique.
    """
    from concurrent.futures import ThreadPoolExecutor

    # TODO : lancer les taches EN MEME TEMPS avec un ThreadPoolExecutor et rendre les rapports dans l'ordre des taches. Deux tests le verifient : le gain de temps, et la separation des contextes.
    return [session.deleguer(n, t, w) for n, t, w in taches]


def conflit(taches: list[tuple[str, str, object]], cibles: list[str]) -> list[str]:
    """Rend les cibles que plusieurs taches se disputent.

    Le test qui compte avant de paralleliser. Deux agents sur le meme fichier,
    ce n'est pas « un peu plus lent » : c'est le travail du premier ecrase par
    le second, sans erreur et sans trace.
    """
    vus: dict[str, int] = {}
    for cible in cibles:
        vus[cible] = vus.get(cible, 0) + 1
    return sorted(c for c, n in vus.items() if n > 1)
