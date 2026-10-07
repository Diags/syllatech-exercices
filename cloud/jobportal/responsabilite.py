"""Le modele de responsabilite partagee, calcule couche par couche.

CE QUE CE MODELE DIT VRAIMENT
-----------------------------
Pas « le fournisseur securise, vous aussi ». Il dit, pour CHAQUE couche de
la pile, qui repond en cas d'incident. Et il dit surtout ceci, qui est la
seule phrase a retenir :

    **Vos donnees, vos identites et votre configuration restent a vous
    dans les quatre colonnes.** Il n'existe aucun service qui vous en
    decharge.

C'est pour cela que l'immense majorite des incidents cloud rendus publics
sont des fautes de configuration — un stockage laisse ouvert, une cle
d'acces dans un depot — et non des failles d'hyperviseur.

Le module compte les couches dont vous repondez dans chaque modele. Le
chapitre 1 imprime le tableau, et la ligne qui ne bouge jamais.

⚠️ CE TABLEAU EST UNE LECTURE, PAS UNE NORME. Les matrices publiees par
les fournisseurs different dans le detail (la « virtualisation » ou le
« reseau » sont parfois decoupes autrement) et evoluent avec les services.
Celle-ci decoupe la pile en onze couches, et elle est declaree
en un seul endroit, ci-dessous.
"""

from __future__ import annotations

from dataclasses import dataclass

FOURNISSEUR = "fournisseur"
CLIENT = "client"
PARTAGE = "partage"

MODELES = ("sur site", "IaaS", "PaaS", "SaaS")


@dataclass(frozen=True)
class Couche:
    nom: str
    responsables: dict[str, str]
    commentaire: str = ""


# ⚠️ ENTREE DECLAREE — voir l'en-tete du module.
COUCHES: tuple[Couche, ...] = (
    Couche("donnees", dict.fromkeys(MODELES, CLIENT),
           "⚠️ a vous dans les QUATRE colonnes, sans exception"),
    Couche("identites et acces", dict.fromkeys(MODELES, CLIENT),
           "⚠️ idem : personne ne configure vos droits a votre place"),
    Couche("configuration du service",
           {"sur site": CLIENT, "IaaS": CLIENT, "PaaS": CLIENT,
            "SaaS": CLIENT},
           "⚠️ idem : le partage public d'un stockage est votre geste"),
    Couche("application",
           {"sur site": CLIENT, "IaaS": CLIENT, "PaaS": CLIENT,
            "SaaS": FOURNISSEUR}),
    Couche("execution (runtime)",
           {"sur site": CLIENT, "IaaS": CLIENT, "PaaS": FOURNISSEUR,
            "SaaS": FOURNISSEUR}),
    Couche("intergiciel",
           {"sur site": CLIENT, "IaaS": CLIENT, "PaaS": FOURNISSEUR,
            "SaaS": FOURNISSEUR}),
    Couche("systeme d'exploitation",
           {"sur site": CLIENT, "IaaS": CLIENT, "PaaS": FOURNISSEUR,
            "SaaS": FOURNISSEUR},
           "la frontiere IaaS / PaaS : les correctifs de securite"),
    Couche("virtualisation",
           {"sur site": CLIENT, "IaaS": FOURNISSEUR, "PaaS": FOURNISSEUR,
            "SaaS": FOURNISSEUR}),
    Couche("serveurs et stockage",
           {"sur site": CLIENT, "IaaS": FOURNISSEUR, "PaaS": FOURNISSEUR,
            "SaaS": FOURNISSEUR}),
    Couche("reseau physique",
           {"sur site": CLIENT, "IaaS": FOURNISSEUR, "PaaS": FOURNISSEUR,
            "SaaS": FOURNISSEUR}),
    Couche("centre de donnees",
           {"sur site": CLIENT, "IaaS": FOURNISSEUR, "PaaS": FOURNISSEUR,
            "SaaS": FOURNISSEUR},
           "l'alimentation, le refroidissement, les portes"),
)


class ErreurResponsabilite(Exception):
    """Un modele inconnu."""


def a_vous(modele: str) -> list[Couche]:
    if modele not in MODELES:
        raise ErreurResponsabilite(
            f"modele inconnu : « {modele} » — connus : {list(MODELES)}")
    return [couche for couche in COUCHES
            if couche.responsables[modele] == CLIENT]


def toujours_a_vous() -> list[Couche]:
    """Les couches qui vous reviennent dans TOUS les modeles."""
    # >>> depart: rendre les couches dont le CLIENT repond dans TOUS les modeles
    #     return []
    return [couche for couche in COUCHES
            if all(couche.responsables[modele] == CLIENT
                   for modele in MODELES)]
    # <<<


def compter() -> dict[str, int]:
    return {modele: len(a_vous(modele)) for modele in MODELES}


def rendre() -> list[str]:
    largeur = max(len(couche.nom) for couche in COUCHES) + 2
    entete = f"{'COUCHE':<{largeur}}" + "".join(f"{m:>12}" for m in MODELES)
    lignes = [entete, "-" * len(entete)]
    for couche in COUCHES:
        ligne = f"{couche.nom:<{largeur}}"
        for modele in MODELES:
            qui = couche.responsables[modele]
            ligne += f"{'VOUS' if qui == CLIENT else 'fournis.':>12}"
        lignes.append(ligne)
    lignes.append("-" * len(entete))
    compte = compter()
    lignes.append(f"{'couches a votre charge':<{largeur}}"
                  + "".join(f"{compte[m]:>12}" for m in MODELES))
    return lignes
