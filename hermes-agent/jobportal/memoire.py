"""La mémoire — autour du VRAI `tools.memory_tool.MemoryStore` de Hermes.

Rien n'est réimplémenté : `MemoryStore` est la classe de Hermes, avec ses deux
cibles, ses deux plafonds, son refus de dépassement, son instantané figé et
son filtre d'injection au chargement. Ce module ne fait que trois choses :

  · rendre ses réponses lisibles (`Ecriture`) ;
  · mesurer ce qu'il fait (`saturer`, `taille_du_bloc`) ;
  · préparer un dossier de mémoire jetable (`maison_jetable`), pour que les
    chapitres et les tests n'écrivent jamais dans votre vrai `~/.hermes`.

LES DEUX PROPRIÉTÉS QUI SURPRENNENT

**1. L'instantané est figé.** `format_for_system_prompt` rend l'état capturé
au `load_from_disk()`, pas l'état vivant : *« Mid-session writes do not affect
this. »* Une écriture en cours de session répond `success: True` et ne change
pas le prompt système — le souvenir n'arrive qu'à la session suivante.

Ce n'est pas un oubli, c'est un arbitrage : un prompt système qui change à
chaque tour invalide le cache de préfixe du fournisseur, et chaque tour est
alors refacturé plein tarif. Hermes choisit la stabilité du cache contre la
fraîcheur du souvenir, et le dit dans sa docstring.

**2. Le fichier de mémoire est une surface d'attaque.** Au chargement, chaque
entrée est passée au détecteur de menaces ; une entrée qui déclenche est
remplacée dans l'instantané par `[BLOCKED: …]`. Le texte d'origine reste dans
la liste vivante — pour que l'utilisateur le VOIE et puisse l'effacer, plutôt
que de le faire disparaître en silence.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from tools.memory_tool import ENTRY_DELIMITER, MemoryStore, get_memory_dir

CIBLES = ("memory", "user")


def maison_jetable() -> Path:
    """Un `HERMES_HOME` temporaire, pour ne jamais toucher le vrai.

    ⚠️ `get_memory_dir()` lit la variable d'environnement au moment de
    l'appel. Sans cette précaution, un chapitre écrirait dans le
    `~/.hermes/memories` de la personne qui le lance — et y laisserait les
    entrées de démonstration, y compris la piégée.
    """
    dossier = Path(tempfile.mkdtemp(prefix="hermes-cours-"))
    os.environ["HERMES_HOME"] = str(dossier)
    memoires = get_memory_dir()
    memoires.mkdir(parents=True, exist_ok=True)
    return memoires




@dataclass
class Ecriture:
    """Une réponse de `MemoryStore.add`, lue."""

    reussie: bool
    message: str
    usage: str
    entrees: int
    entrees_actuelles: tuple[str, ...] = ()

    @classmethod
    def depuis(cls, reponse: dict) -> "Ecriture":
        return cls(
            reussie=bool(reponse.get("success")),
            message=str(reponse.get("message") or reponse.get("error") or ""),
            usage=str(reponse.get("usage") or ""),
            entrees=int(reponse.get("entry_count") or 0),
            entrees_actuelles=tuple(reponse.get("current_entries") or ()),
        )

    def __str__(self) -> str:
        return (f"{'ok    ' if self.reussie else 'REFUSE'}  "
                f"{self.usage:<22}{self.message[:58]}")


def neuf() -> MemoryStore:
    """Un magasin vide, aux plafonds par défaut — DANS UN DOSSIER JETABLE.

    ⚠️ `MemoryStore()` construit bien des listes vides, mais `add()` relit le
    fichier sous verrou avant d'écrire, puis sauvegarde. Un magasin « neuf »
    n'est donc neuf que si le DOSSIER l'est : sans précaution, la première
    écriture d'un chapitre atterrit dans `%LOCALAPPDATA%\\hermes\\memories`
    — la vraie mémoire de la machine — et les écritures suivantes la relisent.

    Constaté en écrivant ce projet : les sondes ont laissé « Fait 000 : xxx »
    dans un vrai MEMORY.md, et un test a ensuite vu 31 entrées là où il en
    attendait une. C'est pourquoi `neuf()` bascule d'abord `HERMES_HOME`.

    Corollaire à retenir : importer Hermes suffit à créer son dossier de
    travail — `SOUL.md`, `state.db`, `sessions/` — avant même d'avoir lancé
    la commande `hermes`.
    """
    maison_jetable()
    return MemoryStore()


def ecrire(store: MemoryStore, cible: str, contenu: str) -> Ecriture:
    return Ecriture.depuis(store.add(cible, contenu))


def plafonds(store: MemoryStore) -> dict[str, int]:
    return {"memory": store.memory_char_limit, "user": store.user_char_limit}


def entrees(store: MemoryStore, cible: str) -> list[str]:
    """La liste VIVANTE — celle qui contient tout, y compris le douteux."""
    return list(getattr(store, f"{cible}_entries"))


def taille_du_bloc(store: MemoryStore, cible: str) -> int:
    """La taille du bloc RÉELLEMENT injecté dans le prompt système."""
    return len(store.format_for_system_prompt(cible) or "")


def saturer(cible: str = "memory", taille: int = 60,
            maximum: int = 500) -> tuple[MemoryStore, int, Ecriture]:
    """Écrit jusqu'au refus. Rend le magasin, le nombre accepté, le refus.

    C'est la seule façon honnête de connaître la capacité : elle ne se déduit
    pas du plafond, parce qu'une entrée coûte un peu plus que son texte.
    """
    # TODO : ecrire dans le magasin jusqu'a ce que Hermes REFUSE, et rendre (magasin, nombre accepte, refus). La capacite ne se deduit pas du plafond : une entree coute un peu plus que son texte. Trois tests le verifient, dont un sur le contenu du refus — qui est une consigne de consolidation, pas un message d'erreur.
    return neuf(), 0, Ecriture(False, "a ecrire", "", 0)


# ------------------------------------------------- le disque, sans risque

def ecrire_fichier(memoires: Path, cible: str, entrees_: list[str]) -> Path:
    """Écrit un MEMORY.md / USER.md avec le VRAI séparateur de Hermes.

    ⚠️ `ENTRY_DELIMITER` vaut « \\n§\\n ». Un fichier édité à la main avec des
    tirets de liste n'a donc qu'UNE entrée — et si une seule ligne y déclenche
    le détecteur, c'est tout le fichier qui est remplacé par `[BLOCKED: …]`.
    Le chapitre 2 le mesure.
    """
    chemin = memoires / ("MEMORY.md" if cible == "memory" else "USER.md")
    chemin.write_text(ENTRY_DELIMITER.join(entrees_), encoding="utf-8")
    return chemin


def charger(memoires: Path) -> MemoryStore:
    store = MemoryStore()
    store.load_from_disk()
    return store


def bloquees(store: MemoryStore, cible: str = "memory") -> int:
    """Combien d'entrées ont été remplacées par un marqueur dans l'instantané."""
    bloc = store.format_for_system_prompt(cible) or ""
    return bloc.count("[BLOCKED:")
