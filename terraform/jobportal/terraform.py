"""Les commandes : init, plan, apply, destroy, et la chirurgie d'etat.

Ce module assemble les pieces precedentes en un mini-Terraform utilisable.
Il tient en une classe parce que les quatre commandes partagent exactement
trois choses : un dossier de code, un fichier d'etat, et une realite.

⚠️ **L'ordre des operations n'est pas celui du fichier.** Les destructions
passent avant les creations pour qu'un remplacement libere son nom avant de
le reprendre. Terraform fait plus fin — il construit un graphe de
dependances et le parcourt en parallele — mais le principe est le meme :
c'est le moteur qui decide de l'ordre, jamais la position dans le fichier.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .configuration import Configuration, charger
from .etat import Etat, Verrou
from .fournisseur import Realite
from .plan import Action, DestructionEmpechee, Plan, calculer


class Terraform:
    """Un dossier de code, un etat, une realite."""

    def __init__(self, dossier: Path | str,
                 etat: Path | str | None = None,
                 realite: Path | str | None = None) -> None:
        self.dossier = Path(dossier)
        self.chemin_etat = Path(etat) if etat else self.dossier / "terraform.tfstate"
        self.chemin_realite = (Path(realite) if realite
                               else self.dossier / "realite.json")

    # -- lecture --------------------------------------------------------

    def configuration(self, valeurs: dict[str, Any] | None = None
                      ) -> Configuration:
        return charger(self.dossier, valeurs)

    def etat(self) -> Etat:
        return Etat(self.chemin_etat)

    def realite(self) -> Realite:
        return Realite(self.chemin_realite)

    # -- les commandes --------------------------------------------------

    def plan(self, valeurs: dict[str, Any] | None = None) -> Plan:
        """`terraform plan` : ce qui changerait, sans rien changer."""
        return calculer(self.configuration(valeurs), self.etat())

    def apply(self, valeurs: dict[str, Any] | None = None,
              plan: Plan | None = None) -> Plan:
        """`terraform apply` : execute le plan, puis reecrit l'etat."""
        etat = self.etat()
        realite = self.realite()
        a_faire = plan if plan is not None else self.plan(valeurs)

        for changement in a_faire.changements:
            if (changement.action in (Action.DETRUIRE, Action.REMPLACER)
                    and changement.empeche_la_destruction):
                raise DestructionEmpechee(
                    f"{changement.adresse} porte `prevent_destroy = true` : "
                    f"Terraform refuse de la detruire")

        with Verrou(self.chemin_etat):
            # TODO : executer en trois temps — destructions, puis creations, puis modifications
            etat.ecrire()
        return a_faire

    def destroy(self, valeurs: dict[str, Any] | None = None) -> Plan:
        """`terraform destroy` : tout retirer, dans l'ordre inverse."""
        etat = self.etat()
        realite = self.realite()
        plan = Plan()
        for ressource in etat.ressources.values():
            for instance in ressource.instances:
                identifiant = instance.attributs.get("id")
                if identifiant:
                    realite.detruire(identifiant)
                plan.changements.append(
                    _destruction(ressource.adresse, instance))
        with Verrou(self.chemin_etat):
            etat.ressources.clear()
            etat.ecrire()
        return plan

    # -- la chirurgie d'etat --------------------------------------------

    def state_list(self) -> list[str]:
        return self.etat().adresses()

    def state_rm(self, adresse: str, cle: str | None = None) -> bool:
        """On cesse de suivre la ressource — elle continue d'exister."""
        etat = self.etat()
        retire = etat.retirer(adresse, cle)
        if retire:
            etat.ecrire()
        return retire

    def state_mv(self, source: str, cible: str) -> bool:
        """On renomme l'entree d'etat — la ressource ne bouge pas."""
        etat = self.etat()
        deplace = etat.deplacer(source, cible)
        if deplace:
            etat.ecrire()
        return deplace

    def importer(self, adresse: str, identifiant: str,
                 cle: str | None = None) -> bool:
        """`terraform import` : faire adopter par l'etat un objet existant."""
        objet = self.realite().lire(identifiant)
        if objet is None:
            return False
        etat = self.etat()
        etat.poser(adresse, cle, objet)
        etat.ecrire()
        return True


def _destruction(adresse: str, instance) -> Any:
    from .plan import Changement

    cle = instance.cle
    complete = adresse + (f'["{cle}"]' if cle is not None else "")
    return Changement(Action.DETRUIRE, complete,
                      avant=instance.attributs, cle=cle)
