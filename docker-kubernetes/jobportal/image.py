"""Une image : des couches empilees, et ce qu'on ne peut plus en retirer.

UNE IMAGE N'EST PAS UN DOSSIER, C'EST UN EMPILEMENT
---------------------------------------------------
Chaque instruction qui pose une couche ajoute un calque en lecture seule
au-dessus des precedents. Ce qu'on *voit* dans le conteneur est la vue
fusionnee de tous les calques ; ce qu'on *transporte* est leur somme.

Les deux ne coincident pas, et c'est toute la lecon de ce module :

- **supprimer un fichier n'enleve rien de l'image.** Le calque suivant pose
  une marque de suppression (`whiteout`) ; le fichier disparait de la vue et
  reste dans le calque d'en dessous, transfere a chaque `pull`.
- **donc un secret copie puis efface reste extractible.** `docker save`
  suivi d'un `tar -x` le rend. Le chapitre 1 le fait, et imprime le mot de
  passe.

La seule facon de ne pas embarquer quelque chose est de ne jamais le poser
dans un calque de l'image finale — c'est-a-dire le multi-stage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator


@dataclass(frozen=True)
class FichierImage:
    chemin: str
    taille: int
    contenu: bytes | None = None


@dataclass
class Couche:
    """Un calque : ce qu'il ajoute, ce qu'il efface, ce qu'il pese."""

    identifiant: str
    instruction: str
    ajoutes: dict[str, FichierImage] = field(default_factory=dict)
    supprimes: set[str] = field(default_factory=set)
    venue_du_cache: bool = False
    etape: str = "0"

    @property
    def taille(self) -> int:
        """⚠️ Une couche qui EFFACE pese zero — elle n'enleve rien."""
        return sum(fichier.taille for fichier in self.ajoutes.values())

    @property
    def vide(self) -> bool:
        return not self.ajoutes and not self.supprimes


@dataclass
class Image:
    """Un empilement de calques, et son historique."""

    nom: str
    couches: list[Couche] = field(default_factory=list)
    base: str = "scratch"
    utilisateur: str = "root"
    point_d_entree: list[str] = field(default_factory=list)
    forme_exec: bool = True
    variables: dict[str, str] = field(default_factory=dict)
    ports: list[int] = field(default_factory=list)

    # -- ce qui est transporte ------------------------------------------

    @property
    def taille(self) -> int:
        """La taille reelle de l'image : la somme de TOUS les calques."""
        return sum(couche.taille for couche in self.couches)

    @property
    def taille_visible(self) -> int:
        """La taille de ce qu'on voit dans le conteneur, apres fusion.

        ⚠️ L'ecart entre les deux est exactement ce qu'un `RUN rm` a cru
        supprimer. Il est transfere a chaque `docker pull`, sur chaque
        noeud du cluster, a chaque deploiement.
        """
        return sum(fichier.taille for fichier in self.fichiers().values())

    @property
    def poids_mort(self) -> int:
        return self.taille - self.taille_visible

    # -- ce qui est visible ---------------------------------------------

    def fichiers(self) -> dict[str, FichierImage]:
        """La vue fusionnee : ce que `ls` montre dans le conteneur."""
        # TODO : empiler les calques, et appliquer leurs marques de suppression
        return {}

    def lire(self, chemin: str) -> FichierImage | None:
        return self.fichiers().get(chemin)

    # -- ce qui reste extractible ---------------------------------------

    def fouiller(self, chemin: str) -> list[tuple[Couche, FichierImage]]:
        """Ce qu'un `docker save` puis un `tar -x` rendraient.

        ⚠️ Cette methode ignore volontairement les suppressions : elle
        parcourt les calques un par un, comme le ferait quelqu'un qui a
        recupere votre image. C'est la difference entre « effacer » et
        « ne pas mettre ».
        """
        trouves = []
        for couche in self.couches:
            fichier = couche.ajoutes.get(chemin)
            if fichier is not None:
                trouves.append((couche, fichier))
        return trouves

    def historique(self) -> Iterator[tuple[int, Couche]]:
        for rang, couche in enumerate(self.couches):
            yield rang, couche


def _sous(chemin: str, prefixe: str) -> bool:
    return chemin == prefixe or chemin.startswith(prefixe.rstrip("/") + "/")


def rendre(image: Image) -> list[str]:
    """L'image, telle que la montrerait `docker history`."""
    lignes = [f"{'COUCHE':<12} {'TAILLE':>9}  INSTRUCTION"]
    for couche in image.couches:
        marque = "  (cache)" if couche.venue_du_cache else ""
        instruction = couche.instruction
        if len(instruction) > 52:
            instruction = instruction[:49] + "..."
        lignes.append(f"{court(couche.identifiant):<12} "
                      f"{_octets(couche.taille):>9}  {instruction}{marque}")
    lignes.append(f"{'TOTAL':<12} {_octets(image.taille):>9}")
    return lignes


def court(identifiant: str) -> str:
    """Les 12 premiers caracteres, comme `docker images` les montre."""
    return identifiant.split(":", 1)[-1][:12]


def _octets(nombre: int) -> str:
    if nombre == 0:
        return "0"
    for unite in ("o", "ko", "Mo", "Go"):
        if nombre < 1000 or unite == "Go":
            return f"{nombre:.0f} {unite}" if unite == "o" \
                else f"{nombre:.1f} {unite}"
        nombre /= 1000.0
    return f"{nombre:.1f} Go"


octets = _octets
