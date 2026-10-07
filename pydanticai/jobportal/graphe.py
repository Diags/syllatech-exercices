"""Le graphe du chapitre 5 — un workflow d'agents, avec un état partagé.

⚠️ L'API A CHANGÉ. La vidéo montre :

    from pydantic_graph import BaseNode, End, Graph, GraphRunContext
    graphe = Graph(nodes=[Analyser, Decider, Rediger])

`Graph(nodes=[...])` lève aujourd'hui `TypeError` : `Graph` n'est plus
construit directement, il est **produit** par un `GraphBuilder`. Les étapes
s'écrivent comme des fonctions décorées, les arêtes se déclarent, et
`build()` rend le graphe. Un test de ce projet vérifie que l'ancienne forme
échoue bien — pour que personne ne perde une heure à se demander pourquoi.

POURQUOI UN GRAPHE PLUTÔT QU'UN AGENT

Un `Agent` boucle : le modèle appelle des outils jusqu'à produire sa sortie.
C'est parfait pour une tâche, et insuffisant pour un **processus** — une suite
d'étapes dont certaines branchent, et dont on veut inspecter l'état à
mi-parcours. Ici, `Etat.etapes` enregistre le chemin réellement pris, et
`render()` dessine le graphe sans l'exécuter.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic_graph import GraphBuilder, StepContext

from .agents import Deps, Recommandation, agent_offres
from .donnees import DatabaseConn

SEUIL = 3      # en dessous, conseiller n'a pas de sens — autant le dire


@dataclass
class Etat:
    """L'état qui traverse le graphe. Inspectable à chaque étape."""

    candidat_id: int
    db: DatabaseConn
    offres: list[str] = field(default_factory=list)
    recommandation: Recommandation | None = None
    etapes: list[str] = field(default_factory=list)
    modele: object = None


# Les deux issues de la décision. Ce sont des TYPES, et c'est ce qui permet au
# graphe de brancher : `b.match(Assez)` ne teste pas une condition, il
# reconnaît un type. La branche est donc vérifiable statiquement.

@dataclass
class Assez:
    offres: list[str]


@dataclass
class TropPeu:
    combien: int


constructeur = GraphBuilder(state_type=Etat, output_type=str, name="conseil")


@constructeur.step
async def collecter(ctx: StepContext[Etat, None, None]) -> Assez | TropPeu:
    """Étape 1 : lire la base. Aucun modèle ici — inutile d'en payer un."""
    ctx.state.etapes.append("collecter")
    offres = await ctx.state.db.offres(ctx.state.candidat_id)
    ctx.state.offres = offres
    return Assez(offres) if len(offres) >= SEUIL else TropPeu(len(offres))


@constructeur.step
async def analyser(ctx: StepContext[Etat, None, Assez]) -> str:
    """Étape 2a : l'agent du chapitre 2, réutilisé tel quel."""
    ctx.state.etapes.append("analyser")
    resultat = await agent_offres(ctx.state.modele).run(
        "Resume les offres suivies et donne une recommandation.",
        deps=Deps(ctx.state.candidat_id, ctx.state.db))
    ctx.state.recommandation = resultat.output
    return resultat.output.resume


@constructeur.step
async def renoncer(ctx: StepContext[Etat, None, TropPeu]) -> str:
    """Étape 2b : ne pas appeler de modèle quand il n'a rien à dire.

    C'est le nœud qui justifie le graphe. Dans un agent unique, cette décision
    serait prise PAR le modèle — donc payée, et parfois mal prise. Ici elle
    est prise par du code, gratuitement, et elle est testable.
    """
    ctx.state.etapes.append("renoncer")
    return (f"seulement {ctx.inputs.combien} offre(s) suivie(s) : "
            f"trop peu pour conseiller quoi que ce soit")


# TODO : cabler le graphe : start -> collecter, puis une decision() qui branche sur le TYPE rendu — .branch(match(Assez).to(analyser)) et .branch(match(TropPeu).to(renoncer)) — et les deux issues vers end_node. Retirez ensuite validate_graph_structure=False du build. Quatre tests le verifient, dont un qui exige que les DEUX branches soient reellement empruntees.
graphe = constructeur.build(validate_graph_structure=False)


async def conseiller(candidat_id: int, db: DatabaseConn, modele=None) -> tuple[str, Etat]:
    etat = Etat(candidat_id=candidat_id, db=db, modele=modele)
    sortie = await graphe.run(state=etat)
    return sortie, etat
