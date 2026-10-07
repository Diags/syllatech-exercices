"""Decouper un VPC — et compter les adresses qu'on n'a pas.

TROIS CHOSES QUE LE CALCUL MENTAL RATE
--------------------------------------
1. **un /24 ne donne pas 254 adresses utilisables, mais 251.** Le cloud
   reserve cinq adresses par sous-reseau : l'adresse de reseau, la
   passerelle, le DNS, une adresse gardee pour un usage futur, et le
   broadcast. Sur un /28, cela fait **11 adresses sur 16** — de quoi ne pas
   demarrer un cluster ;
2. **deux plages « manifestement differentes » se chevauchent souvent.**
   `10.0.0.0/16` contient `10.0.128.0/17` en entier ;
3. **deux VPC aux plages qui se chevauchent ne peuvent pas etre appaires.**
   Ce n'est pas une limite d'outil : le routage serait ambigu. C'est la
   raison pour laquelle on planifie son adressage AVANT le premier `apply`,
   et pas quand la fusion d'entreprise arrive.

⚠️ LES CINQ ADRESSES RESERVEES SONT CELLES D'AWS. Azure en reserve cinq
aussi, GCP quatre. Le nombre est declare dans `RESERVEES_PAR_SOUS_RESEAU`
et se change en un endroit.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from typing import Iterable

# ⚠️ ENTREE DECLAREE — voir l'en-tete.
RESERVEES_PAR_SOUS_RESEAU = 5


class ErreurReseau(Exception):
    """Un decoupage impossible, un chevauchement, un prefixe absurde."""


@dataclass(frozen=True)
class SousReseau:
    nom: str
    plage: ipaddress.IPv4Network
    public: bool = False
    zone: str = ""

    @property
    def total(self) -> int:
        return self.plage.num_addresses

    @property
    def utilisables(self) -> int:
        """⚠️ Le chiffre qui compte, et ce n'est pas `total - 2`."""
        # TODO : retirer les adresses que le fournisseur se reserve
        return self.total

    def __str__(self) -> str:
        return f"{self.nom} {self.plage}"


@dataclass
class Vpc:
    nom: str
    plage: ipaddress.IPv4Network
    sous_reseaux: list[SousReseau] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.plage.num_addresses

    @property
    def utilisables(self) -> int:
        return sum(s.utilisables for s in self.sous_reseaux)

    @property
    def alloues(self) -> int:
        return sum(s.total for s in self.sous_reseaux)

    @property
    def libres(self) -> int:
        return self.total - self.alloues

    def ajouter(self, sous_reseau: SousReseau) -> None:
        # TODO : refuser un sous-reseau hors du VPC, ou qui en chevauche un autre
        self.sous_reseaux.append(sous_reseau)


def reseau(texte: str) -> ipaddress.IPv4Network:
    try:
        return ipaddress.IPv4Network(texte, strict=False)
    except ValueError as erreur:
        raise ErreurReseau(f"plage illisible : « {texte} » — {erreur}") from erreur


def decouper(plage: str | ipaddress.IPv4Network,
             prefixe: int) -> list[ipaddress.IPv4Network]:
    """Tous les sous-reseaux d'un prefixe donne. « /16 en /24 » → 256."""
    base = reseau(plage) if isinstance(plage, str) else plage
    if prefixe < base.prefixlen:
        raise ErreurReseau(
            f"/{prefixe} est PLUS GRAND que {base} — un sous-reseau ne peut "
            f"pas deborder de son VPC")
    if prefixe > 32:
        raise ErreurReseau(f"/{prefixe} n'existe pas")
    return list(base.subnets(new_prefix=prefixe))


def chevauchent(a: str | ipaddress.IPv4Network,
                b: str | ipaddress.IPv4Network) -> bool:
    premier = reseau(a) if isinstance(a, str) else a
    second = reseau(b) if isinstance(b, str) else b
    return premier.overlaps(second)


def appairable(a: Vpc, b: Vpc) -> tuple[bool, str]:
    """⚠️ Deux VPC aux plages qui se chevauchent ne s'appairent PAS."""
    if a.plage.overlaps(b.plage):
        return False, (f"{a.plage} et {b.plage} se chevauchent : le routage "
                       f"serait ambigu, l'appairage est refuse")
    return True, "appairage possible"


@dataclass
class Plan:
    """Un decoupage complet, pret a etre relu."""

    vpc: Vpc
    laisses: list[ipaddress.IPv4Network] = field(default_factory=list)


def planifier(nom: str, plage: str, zones: Iterable[str],
              prefixe_public: int = 24,
              prefixe_prive: int = 20) -> Plan:
    """Un sous-reseau public et un prive par zone, sans chevauchement.

    ⚠️ Les prives sont plus GRANDS que les publics, et ce n'est pas un
    caprice : le public n'accueille qu'une passerelle et un repartiteur de
    charge, le prive accueille toutes les charges de travail — et, avec un
    reseau de pods qui pioche dans le VPC, une adresse par pod.
    """
    vpc = Vpc(nom, reseau(plage))
    disponibles = list(vpc.plage.subnets(new_prefix=min(prefixe_public,
                                                        prefixe_prive)))
    curseur = 0
    for zone in zones:
        gros = disponibles[curseur]
        curseur += 1
        vpc.ajouter(SousReseau(f"prive-{zone}", gros, public=False, zone=zone))
    for zone in zones:
        gros = disponibles[curseur]
        curseur += 1
        petit = next(gros.subnets(new_prefix=prefixe_public))
        vpc.ajouter(SousReseau(f"public-{zone}", petit, public=True, zone=zone))
    laisses = disponibles[curseur:]
    return Plan(vpc, laisses)


def rendre(vpc: Vpc) -> list[str]:
    lignes = [f"{'SOUS-RESEAU':<18} {'PLAGE':<20} {'ZONE':<6} {'EXPOSE':<8} "
              f"{'TOTAL':>7} {'UTILISABLES':>12}"]
    for sous_reseau in vpc.sous_reseaux:
        lignes.append(
            f"{sous_reseau.nom:<18} {str(sous_reseau.plage):<20} "
            f"{sous_reseau.zone:<6} {'public' if sous_reseau.public else 'prive':<8} "
            f"{sous_reseau.total:>7} {sous_reseau.utilisables:>12}")
    lignes.append("")
    lignes.append(f"{'VPC ' + str(vpc.plage):<18} {'':<20} {'':<6} {'':<8} "
                  f"{vpc.total:>7} {vpc.utilisables:>12}")
    lignes.append(f"{'dont libres':<18} {'':<20} {'':<6} {'':<8} "
                  f"{vpc.libres:>7}")
    return lignes


def tiendrait(sous_reseau: SousReseau, pods_par_noeud: int,
              noeuds: int) -> tuple[bool, int, int]:
    """Un cluster dont chaque pod prend une adresse du VPC tient-il ?

    ⚠️ C'est le calcul qu'on ne fait jamais avant, et toujours apres : avec
    un reseau de pods qui pioche dans le VPC (le CNI d'AWS, par exemple),
    un noeud consomme une adresse pour lui-meme PLUS une par pod.
    """
    besoin = noeuds * (1 + pods_par_noeud)
    return besoin <= sous_reseau.utilisables, besoin, sous_reseau.utilisables
