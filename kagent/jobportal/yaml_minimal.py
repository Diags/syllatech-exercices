"""Un lecteur YAML — le sous-ensemble que Compose et Kubernetes utilisent.

POURQUOI NE PAS PRENDRE PyYAML
------------------------------
Parce que ce projet ne doit rien installer, et surtout parce que le cours a
besoin de MONTRER deux pieges qu'une bibliotheque escamote :

- **l'indentation est la syntaxe.** Deux espaces de trop deplacent une cle
  d'un niveau, et le fichier reste valide. Kubernetes accepte alors un
  manifeste qui ne veut pas dire ce qu'on croit ;
- **certains mots nus ne sont pas des chaines.** `yes`, `no`, `on`, `off`
  valaient des booleens en YAML 1.1 — c'est la « norvegienne » (`NO`, le
  code du pays, lu comme `false`). YAML 1.2 y a mis fin, mais les lecteurs
  ne se sont pas tous alignes. Ce lecteur-ci **les garde en chaines** et le
  dit ; `true`/`false` restent des booleens.

CE QUI EST SUPPORTE
-------------------
Les documents separes par `---`, les tables d'association par indentation,
les sequences `- `, les formes en ligne `{a: b}` et `[a, b]`, les chaines
simples et doubles, les blocs `|`, `|-`, `>` et `>-`, les commentaires, et
les scalaires `null` / `true` / `false` / entiers / flottants.

CE QUI NE L'EST PAS
-------------------
Les ancres (`&x`) et references (`*x`), les cles complexes (`? `), les
etiquettes (`!!str`). Chacune leve une `ErreurYaml` nommant la ligne :
un manifeste a moitie compris vaudrait moins que pas de lecteur du tout.
"""

from __future__ import annotations

import re
from typing import Any


class ErreurYaml(Exception):
    """Une syntaxe non geree, avec le numero de ligne."""


_ENTIER = re.compile(r"^[+-]?\d+$")
_FLOTTANT = re.compile(r"^[+-]?(\d+\.\d*|\.\d+)([eE][+-]?\d+)?$")


def _scalaire(brut: str, ligne: int) -> Any:
    texte = brut.strip()
    if not texte:
        return None
    if texte[0] in "&*":
        raise ErreurYaml(
            f"ligne {ligne} : les ancres et references ne sont pas gerees")
    if texte.startswith("!!"):
        raise ErreurYaml(f"ligne {ligne} : les etiquettes ne sont pas gerees")
    if texte[0] == '"' and texte[-1] == '"' and len(texte) >= 2:
        return texte[1:-1].replace('\\"', '"').replace("\\n", "\n")
    if texte[0] == "'" and texte[-1] == "'" and len(texte) >= 2:
        return texte[1:-1].replace("''", "'")
    if texte in ("null", "~", "Null", "NULL"):
        return None
    if texte in ("true", "True", "TRUE"):
        return True
    if texte in ("false", "False", "FALSE"):
        return False
    if _ENTIER.match(texte):
        return int(texte)
    if _FLOTTANT.match(texte):
        return float(texte)
    return texte


class _Lecteur:

    def __init__(self, source: str) -> None:
        self.lignes: list[tuple[int, int, str]] = []   # numero, retrait, texte
        for numero, brute in enumerate(source.splitlines(), 1):
            sans_commentaire = _sans_commentaire(brute)
            if not sans_commentaire.strip():
                continue
            retrait = len(sans_commentaire) - len(sans_commentaire.lstrip(" "))
            if "\t" in sans_commentaire[:retrait + 1]:
                raise ErreurYaml(
                    f"ligne {numero} : tabulation dans l'indentation — "
                    f"YAML l'interdit, et l'erreur est invisible a l'œil")
            self.lignes.append((numero, retrait, sans_commentaire.strip()))
        self.brutes = source.splitlines()
        self.position = 0

    def fini(self) -> bool:
        return self.position >= len(self.lignes)

    def courante(self) -> tuple[int, int, str]:
        return self.lignes[self.position]

    # -- les blocs -------------------------------------------------------

    def valeur(self, retrait_minimal: int) -> Any:
        if self.fini():
            return None
        _, retrait, texte = self.courante()
        if retrait < retrait_minimal:
            return None
        if texte.startswith("- "):
            return self.sequence(retrait)
        if texte == "-":
            return self.sequence(retrait)
        return self.table(retrait)

    def sequence(self, retrait: int) -> list[Any]:
        elements: list[Any] = []
        while not self.fini():
            numero, courant, texte = self.courante()
            if courant < retrait or not (texte == "-" or texte.startswith("- ")):
                break
            self.position += 1
            contenu = texte[2:].strip() if texte.startswith("- ") else ""
            if not contenu:
                elements.append(self.valeur(courant + 1))
                continue
            cle, reste, est_une_cle = _couper(contenu)
            if est_une_cle:
                # `- nom: x` ouvre une table dont la premiere cle est sur la
                # meme ligne que le tiret. Son retrait est celui du contenu.
                interne = retrait + 2
                table: dict[str, Any] = {}
                table[cle] = (_valeur_en_ligne(reste, numero) if reste
                              else self.valeur(interne + 1))
                suite = self.table(interne) if not self.fini() and \
                    self.courante()[1] >= interne else {}
                table.update(suite)
                elements.append(table)
            else:
                elements.append(_valeur_en_ligne(contenu, numero))
        return elements

    def table(self, retrait: int) -> dict[str, Any]:
        table: dict[str, Any] = {}
        while not self.fini():
            numero, courant, texte = self.courante()
            if courant < retrait:
                break
            if courant > retrait:
                raise ErreurYaml(
                    f"ligne {numero} : indentation inattendue "
                    f"({courant} espaces la ou {retrait} sont attendus)")
            if texte.startswith("- "):
                break
            cle, reste, est_une_cle = _couper(texte)
            if not est_une_cle:
                raise ErreurYaml(
                    f"ligne {numero} : « {texte} » n'est ni une cle ni un "
                    f"element de liste")
            self.position += 1
            if reste in ("|", "|-", ">", ">-"):
                table[cle] = self._bloc(numero, reste)
            elif reste:
                table[cle] = _valeur_en_ligne(reste, numero)
            else:
                table[cle] = self.valeur(retrait + 1)
        return table

    def _bloc(self, numero: int, marque: str) -> str:
        """Un bloc `|` ou `>`, lu sur les lignes BRUTES."""
        depart = numero          # la ligne de la marque, en base 1
        brutes = self.brutes
        retrait_bloc = None
        morceaux: list[str] = []
        indice = depart          # la ligne suivante, en base 0
        while indice < len(brutes):
            brute = brutes[indice]
            if not brute.strip():
                morceaux.append("")
                indice += 1
                continue
            retrait = len(brute) - len(brute.lstrip(" "))
            if retrait_bloc is None:
                retrait_bloc = retrait
            if retrait < retrait_bloc:
                break
            morceaux.append(brute[retrait_bloc:])
            indice += 1
        # On avance le lecteur de lignes utiles au-dela du bloc.
        while not self.fini() and self.courante()[0] <= indice:
            self.position += 1
        jointure = "\n" if marque.startswith("|") else " "
        texte = jointure.join(morceaux).rstrip("\n ")
        return texte if marque.endswith("-") else texte + "\n"


def _sans_commentaire(ligne: str) -> str:
    """Retire un `#` de commentaire sans casser un `#` dans une chaine."""
    resultat = []
    guillemet: str | None = None
    for indice, caractere in enumerate(ligne):
        if guillemet:
            resultat.append(caractere)
            if caractere == guillemet:
                guillemet = None
            continue
        if caractere in "\"'":
            guillemet = caractere
            resultat.append(caractere)
            continue
        if caractere == "#" and (indice == 0 or ligne[indice - 1] in " \t"):
            break
        resultat.append(caractere)
    return "".join(resultat).rstrip()


_CLE = re.compile(r'^("(?:[^"\\]|\\.)*"|\'(?:[^\']|\'\')*\'|[^:]+?):(\s|$)')


def _couper(texte: str) -> tuple[str, str, bool]:
    if texte.startswith(("{", "[")):
        return "", texte, False
    trouve = _CLE.match(texte)
    if trouve is None:
        return "", texte, False
    brute = trouve.group(1).strip()
    cle = brute[1:-1] if brute[:1] in "\"'" else brute
    return cle, texte[trouve.end():].strip(), True


def _valeur_en_ligne(texte: str, ligne: int) -> Any:
    texte = texte.strip()
    if texte.startswith("{"):
        return _forme_table(texte, ligne)
    if texte.startswith("["):
        return _forme_liste(texte, ligne)
    return _scalaire(texte, ligne)


def _morceaux(texte: str, ouvrant: str, fermant: str, ligne: int) -> list[str]:
    if not texte.endswith(fermant):
        raise ErreurYaml(f"ligne {ligne} : « {fermant} » manquant")
    interieur = texte[1:-1]
    parts: list[str] = []
    profondeur = 0
    guillemet: str | None = None
    courant: list[str] = []
    for caractere in interieur:
        if guillemet:
            courant.append(caractere)
            if caractere == guillemet:
                guillemet = None
            continue
        if caractere in "\"'":
            guillemet = caractere
            courant.append(caractere)
            continue
        if caractere in "{[":
            profondeur += 1
        elif caractere in "}]":
            profondeur -= 1
        if caractere == "," and profondeur == 0:
            parts.append("".join(courant))
            courant = []
            continue
        courant.append(caractere)
    if "".join(courant).strip():
        parts.append("".join(courant))
    return [p.strip() for p in parts if p.strip()]


def _forme_table(texte: str, ligne: int) -> dict[str, Any]:
    table: dict[str, Any] = {}
    for morceau in _morceaux(texte, "{", "}", ligne):
        cle, reste, est_une_cle = _couper(morceau)
        if not est_une_cle:
            raise ErreurYaml(f"ligne {ligne} : « {morceau} » sans « : »")
        table[cle] = _valeur_en_ligne(reste, ligne)
    return table


def _forme_liste(texte: str, ligne: int) -> list[Any]:
    return [_valeur_en_ligne(morceau, ligne)
            for morceau in _morceaux(texte, "[", "]", ligne)]


def charger(source: str) -> Any:
    """Le premier document du flux."""
    documents = charger_tous(source)
    return documents[0] if documents else None


def charger_tous(source: str) -> list[Any]:
    """Tous les documents — un manifeste Kubernetes en contient souvent trois."""
    documents: list[Any] = []
    for brut in _separer(source):
        lecteur = _Lecteur(brut)
        if lecteur.fini():
            continue
        documents.append(lecteur.valeur(0))
    return documents


def _separer(source: str) -> list[str]:
    morceaux: list[list[str]] = [[]]
    for ligne in source.splitlines():
        if ligne.rstrip() == "---":
            morceaux.append([])
            continue
        morceaux[-1].append(ligne)
    return ["\n".join(m) for m in morceaux if any(l.strip() for l in m)]


def charger_fichier(chemin) -> Any:
    from pathlib import Path
    return charger(Path(chemin).read_text(encoding="utf-8"))


def charger_fichier_tous(chemin) -> list[Any]:
    from pathlib import Path
    return charger_tous(Path(chemin).read_text(encoding="utf-8"))
