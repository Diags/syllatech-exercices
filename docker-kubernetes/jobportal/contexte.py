"""Le contexte de construction : ce que `docker build .` envoie vraiment.

Le point ne designe pas « le dossier ou se trouve le Dockerfile ». Il
designe le **contexte** : l'arborescence entiere que le client archive et
transmet au demon AVANT que la premiere instruction ne s'execute. Un
`target/` de 300 Mo ou un `.git/` volumineux y passent, meme si aucun
`COPY` ne les nomme.

C'est pour cela que `.dockerignore` existe, et c'est pour cela qu'il agit
sur DEUX choses a la fois :

1. la taille de ce qui est transmis ;
2. **l'empreinte des `COPY`**, donc le cache. Un fichier ignore ne fait pas
   invalider la couche qui le contiendrait — c'est la moitie invisible du
   probleme, et le chapitre 2 la mesure.

⚠️ LES MOTIFS NE SONT PAS CEUX DE `.gitignore`. Ils sont relatifs a la
racine du contexte, `*` ne traverse pas un `/`, `**` le traverse, et c'est
le DERNIER motif qui correspond qui l'emporte — d'ou les exceptions en `!`.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class FichierDuContexte:
    chemin: str          # relatif a la racine, en « / »
    taille: int
    empreinte: str
    # Le contenu n'est retenu que pour les petits fichiers : il sert au
    # chapitre 2, qui EXTRAIT le secret d'une couche pour le montrer.
    contenu: bytes | None = None


@dataclass
class Contexte:
    """Une arborescence, et la regle qui dit ce qui en sort."""

    racine: Path
    fichiers: dict[str, FichierDuContexte] = field(default_factory=dict)
    ignores: list[str] = field(default_factory=list)
    exclus: dict[str, FichierDuContexte] = field(default_factory=dict)

    @property
    def taille(self) -> int:
        return sum(f.taille for f in self.fichiers.values())

    @property
    def taille_exclue(self) -> int:
        return sum(f.taille for f in self.exclus.values())

    def correspondants(self, motifs: list[str]) -> list[FichierDuContexte]:
        """Les fichiers qu'un `COPY source...` emporterait."""
        retenus: dict[str, FichierDuContexte] = {}
        for motif in motifs:
            for chemin, fichier in self.fichiers.items():
                if _sous_le_chemin(chemin, motif):
                    retenus[chemin] = fichier
        return [retenus[cle] for cle in sorted(retenus)]

    def empreinte_de(self, motifs: list[str]) -> str:
        """L'empreinte de ce qu'un `COPY` emporte — la cle de cache reelle.

        ⚠️ Docker calcule cette empreinte sur le CONTENU et sur les
        metadonnees des fichiers copies. Deux consequences que le chapitre 2
        mesure : changer un caractere invalide la couche, et un `COPY . .`
        rend donc TOUTE modification, meme d'un README, destructrice pour le
        cache de tout ce qui suit.
        """
        # >>> depart: condenser le chemin ET le contenu de chaque fichier copie
        #     return ""
        empreinte = hashlib.sha256()
        for fichier in self.correspondants(motifs):
            empreinte.update(fichier.chemin.encode("utf-8"))
            empreinte.update(b"\0")
            empreinte.update(fichier.empreinte.encode("ascii"))
            empreinte.update(b"\0")
        return empreinte.hexdigest()[:16]
        # <<<


def _sous_le_chemin(chemin: str, motif: str) -> bool:
    """`src` emporte `src/main/Fichier.java` ; `.` emporte tout."""
    motif = motif.strip("./") or "."
    if motif == ".":
        return True
    if chemin == motif:
        return True
    if chemin.startswith(motif + "/"):
        return True
    return _correspond(chemin, motif)


def _en_expression(motif: str) -> re.Pattern[str]:
    """Traduit un motif `.dockerignore` en expression reguliere.

    ⚠️ `*` ne traverse pas un `/`, `**` le traverse. C'est la regle de Go
    (`filepath.Match`), pas celle du shell, et c'est ce qui fait que
    `*/target` n'attrape pas `a/b/target`.
    """
    morceaux: list[str] = []
    i = 0
    while i < len(motif):
        caractere = motif[i]
        if motif.startswith("**", i):
            morceaux.append(".*")
            i += 2
            if motif.startswith("/", i):
                i += 1
                morceaux.append("")
            continue
        if caractere == "*":
            morceaux.append("[^/]*")
        elif caractere == "?":
            morceaux.append("[^/]")
        else:
            morceaux.append(re.escape(caractere))
        i += 1
    return re.compile("^" + "".join(morceaux) + "(/.*)?$")


def _correspond(chemin: str, motif: str) -> bool:
    return _en_expression(motif.strip("/")).match(chemin) is not None


def lire_dockerignore(texte: str) -> list[str]:
    motifs: list[str] = []
    for brute in texte.splitlines():
        ligne = brute.strip()
        if not ligne or ligne.startswith("#"):
            continue
        motifs.append(ligne)
    return motifs


def _ignore(chemin: str, motifs: list[str]) -> bool:
    """Le DERNIER motif qui correspond decide.

    C'est ce qui permet d'ecrire « tout sauf ceci » :

        *
        !pom.xml

    et c'est aussi ce qui fait qu'inverser les deux lignes ne garde rien.
    """
    # >>> depart: appliquer les motifs dans l'ordre — le DERNIER qui correspond decide
    #     return False
    verdict = False
    for motif in motifs:
        nie = motif.startswith("!")
        nu = motif[1:] if nie else motif
        if _correspond(chemin, nu):
            verdict = not nie
    return verdict
    # <<<


POIDS = "poids.json"


def charger(racine: Path | str,
            appliquer_dockerignore: bool = True) -> Contexte:
    """Lit une arborescence et applique son `.dockerignore`.

    ⚠️ LES POIDS DECLARES. Un depot Git ne peut pas transporter un jar de
    47 Mo, un depot Maven de 212 Mo ni un `.git` de 184 Mo. Ces fichiers
    existent donc en reduction — ou pas du tout — dans `contexte/`, et leur
    taille reelle est declaree dans `contexte/poids.json`. Le chargeur la
    prend a la place de la taille sur disque, et fabrique une entree pour
    les chemins declares qui n'existent pas.

    Comme `effets.py`, c'est une ENTREE du modele et non une mesure. Ce que
    le projet mesure, ce sont les couches reconstruites — jamais les octets.
    """
    base = Path(racine)
    fichier_ignore = base / ".dockerignore"
    motifs = (lire_dockerignore(fichier_ignore.read_text(encoding="utf-8"))
              if appliquer_dockerignore and fichier_ignore.exists() else [])
    contexte = Contexte(base, ignores=motifs)

    declares = _poids_declares(base)

    for chemin in sorted(base.rglob("*")):
        if chemin.is_dir() or chemin.name == POIDS:
            continue
        relatif = chemin.relative_to(base).as_posix()
        contenu = chemin.read_bytes()
        _poser(contexte, relatif, declares.get(relatif, len(contenu)),
               hashlib.sha256(contenu).hexdigest()[:16], motifs,
               contenu if len(contenu) <= 65_536 else None)

    for relatif, taille in declares.items():
        if relatif in contexte.fichiers or relatif in contexte.exclus:
            continue
        # Un chemin declare mais absent du disque : `.git/...` ne peut pas
        # exister ici, puisque ce dossier vit DANS un depot Git.
        empreinte = hashlib.sha256(
            f"{relatif}:{taille}".encode("utf-8")).hexdigest()[:16]
        _poser(contexte, relatif, taille, empreinte, motifs)

    return contexte


def _poser(contexte: Contexte, chemin: str, taille: int, empreinte: str,
           motifs: list[str], contenu: bytes | None = None) -> None:
    fichier = FichierDuContexte(chemin, taille, empreinte, contenu)
    if _ignore(chemin, motifs):
        contexte.exclus[chemin] = fichier
    else:
        contexte.fichiers[chemin] = fichier


def _poids_declares(base: Path) -> dict[str, int]:
    fichier = base / POIDS
    if not fichier.exists():
        return {}
    brut = json.loads(fichier.read_text(encoding="utf-8"))
    return {cle: int(valeur) for cle, valeur in brut.items()
            if not cle.startswith("_")}


def modifier(contexte: Contexte, chemin: str, contenu: bytes) -> Contexte:
    """Rend un contexte ou un fichier a change — sans toucher au disque.

    Les chapitres s'en servent pour montrer l'effet d'UNE modification sur
    le cache, sans ecrire dans le depot.
    """
    copie = Contexte(contexte.racine, dict(contexte.fichiers),
                     list(contexte.ignores), dict(contexte.exclus))
    fichier = FichierDuContexte(
        chemin, len(contenu), hashlib.sha256(contenu).hexdigest()[:16],
        contenu if len(contenu) <= 65_536 else None)
    if _ignore(chemin, copie.ignores):
        copie.exclus[chemin] = fichier
        copie.fichiers.pop(chemin, None)
    else:
        copie.fichiers[chemin] = fichier
        copie.exclus.pop(chemin, None)
    return copie


def octets(nombre: int) -> str:
    """Une taille lisible, en unites decimales — celles de `docker images`."""
    for unite in ("o", "ko", "Mo", "Go"):
        if nombre < 1000 or unite == "Go":
            return f"{nombre:.0f} {unite}" if unite == "o" else f"{nombre:.1f} {unite}"
        nombre /= 1000.0
    return f"{nombre:.1f} Go"
