"""Les skills — autour du VRAI analyseur de Hermes.

`agent.skill_utils` est le code que Hermes exécute pour lire une skill :

    parse_frontmatter(texte)      -> (dict, corps)
    extract_skill_description(fm) -> str
    extract_skill_conditions(fm)  -> {requires_tools, requires_toolsets, …}
    skill_matches_platform(fm)    -> bool   (contre LA plateforme courante)
    normalize_skill_lookup_name(s)-> str
    is_valid_namespace(s)         -> bool

Les SKILL.md de `jobportal/skills/` sont écrits au vrai format et passés à ces
fonctions. Ce qui est affiché par les chapitres vient donc de Hermes, pas
d'une relecture à l'œil.

CE QUI EST SUBSTITUÉ

Rien, pour l'analyse. En revanche, **l'agent n'écrit pas ses skills ici** :
la boucle d'auto-amélioration demande un modèle. Les cinq skills du projet
sont écrites à la main, dans la forme qu'aurait produite l'agent — et le
chapitre 3 mesure ce qu'une skill fait gagner, pas comment elle naît.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agent.skill_utils import (extract_skill_conditions,
                               extract_skill_description, is_valid_namespace,
                               normalize_skill_lookup_name, parse_frontmatter,
                               skill_matches_platform)


@dataclass
class Competence:
    """Une skill, lue par le code de Hermes."""

    dossier: str
    entete: dict
    corps: str
    conditions: dict = field(default_factory=dict)

    @classmethod
    def depuis(cls, dossier: str, texte: str) -> "Competence":
        entete, corps = parse_frontmatter(texte)
        return cls(dossier=dossier, entete=entete, corps=corps,
                   conditions=extract_skill_conditions(entete))

    @property
    def nom(self) -> str:
        return str(self.entete.get("name") or self.dossier)

    @property
    def description(self) -> str:
        return extract_skill_description(self.entete)

    @property
    def plateformes(self) -> list[str]:
        return list(self.entete.get("platforms") or [])

    @property
    def proposee_ici(self) -> bool:
        """Hermes proposera-t-il cette skill SUR CETTE MACHINE ?

        ⚠️ `skill_matches_platform` ne prend pas de plateforme en argument :
        il compare à celle qui exécute. Une skill hors plateforme n'est pas
        en erreur — elle est simplement absente de la liste, sans un mot.
        """
        return bool(skill_matches_platform(self.entete))

    @property
    def outils_requis(self) -> list[str]:
        return list(self.conditions.get("requires_tools") or [])

    @property
    def ensembles_requis(self) -> list[str]:
        return list(self.conditions.get("requires_toolsets") or [])

    # Les quatre conditions que Hermes lit — et où il les lit.
    CONDITIONS = ("requires_tools", "requires_toolsets",
                  "fallback_for_tools", "fallback_for_toolsets")

    def defauts(self) -> list[str]:
        """Ce qui empêchera cette skill d'être trouvée ou comprise."""
        soucis = []

        # >>> depart: lister ce qui empechera cette skill d'etre trouvee, choisie ou conditionnee. Le defaut le plus couteux est le premier : les conditions (requires_tools, requires_toolsets, fallback_for_*) ne se declarent QUE sous « metadata.hermes ». Ecrites a la racine, elles sont ignorees sans un mot, et la skill est proposee meme sans ses outils. Trois tests le verifient.
        #     return []

        # ⚠️ Le défaut le plus coûteux, et le plus facile à écrire : les
        # conditions ne se déclarent PAS à la racine du frontmatter. Hermes
        # les lit sous `metadata.hermes.*` et ignore tout le reste, sans un
        # mot. Une skill qui exige un outil absent est alors proposée quand
        # même — et elle échoue au milieu de son travail.
        mal_placees = [c for c in self.CONDITIONS if c in self.entete]
        if mal_placees:
            soucis.append(
                f"« {', '.join(mal_placees)} » a la racine du frontmatter : "
                "Hermes ne les lit que sous « metadata.hermes ». La condition "
                "est donc IGNOREE, et la skill proposee meme sans ses outils")
        if not self.entete.get("name"):
            soucis.append("aucun « name » : la skill ne se cherche pas par nom")
        if not self.description:
            soucis.append("aucune « description » : c'est elle qui decide si "
                          "l'agent la choisit — sans elle, il ne la choisit "
                          "jamais a propos")
        elif len(self.description) < 25:
            soucis.append(f"description de {len(self.description)} signes : "
                          "trop courte pour departager deux skills voisines")
        if not self.plateformes:
            soucis.append("aucune « platforms » : comportement implicite")
        if not self.corps.strip():
            soucis.append("corps vide : une skill sans procedure n'est rien")
        if self.entete.get("name") != normalize_skill_lookup_name(
                str(self.entete.get("name") or "")):
            soucis.append("le « name » contient des espaces de bord")
        namespace = str(self.entete.get("name") or "").split(":")[0] \
            if ":" in str(self.entete.get("name") or "") else None
        if namespace and not is_valid_namespace(namespace):
            soucis.append(f"namespace « {namespace} » invalide")
        return soucis
        # <<<


def lire_toutes(paires) -> list[Competence]:
    return [Competence.depuis(dossier, texte) for dossier, texte in paires]


def proposees(competences: list[Competence]) -> list[Competence]:
    return [c for c in competences if c.proposee_ici]


# ------------------------------------ ce qu'une skill fait gagner

def cout_en_signes(texte: str) -> int:
    return len(texte)


def sans_competence(etapes: list[str]) -> str:
    """Ce que l'agent doit redecouvrir a chaque fois.

    Les etapes ne sont pas le probleme : c'est de les retrouver DANS LE BON
    ORDRE, avec les pieges, qui coute — et qui rate une fois sur trois.
    """
    return "\n".join(f"(tour {n}) {e}" for n, e in enumerate(etapes, 1))


def avec_competence(competence: Competence) -> str:
    """Ce que l'agent relit : la procedure, une fois."""
    return competence.corps.strip()
