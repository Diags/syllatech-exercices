"""Un analyseur HCL — le sous-ensemble qui suffit a ce cours.

POURQUOI ECRIRE UN ANALYSEUR PLUTOT QUE LANCER `terraform`
---------------------------------------------------------
Ce projet doit tourner apres un clone, sans binaire a installer et sans
compte cloud. Mais surtout : ce que le cours enseigne n'est pas la syntaxe
du HCL, c'est ce que Terraform *fait* avec — le plan, l'etat, l'ordre des
operations. Or ces trois choses sont des algorithmes, et un algorithme
s'ecrit et se lit.

Les chapitres impriment donc le plan produit par CE code, sur de VRAIS
fichiers `.tf` places dans `infra/`. Si vous savez lire ce plan, vous savez
lire celui de Terraform.

CE QUI EST SUPPORTE
-------------------
- les blocs : `terraform`, `provider`, `variable`, `locals`, `resource`,
  `module`, `output` ;
- les valeurs : chaines (avec interpolation `${...}`), nombres, booleens,
  listes, objets, et l'identifiant nu d'un type (`string`, `set(string)`) ;
- les references : `var.x`, `local.x`, `each.key`, `each.value`,
  `module.x.y`, et `<type>.<nom>.<attribut>` ;
- les fonctions : `contains`, `length`, `upper`, `lower`, `join`, `keys`,
  `values`, `merge`, `toset`, `format` ;
- l'indexation : `var.liste[0]`, `local.carte["prod"]` ;
- les expressions `for` sous leurs deux formes, celles du cours :
  `[for v in X : expr]` et `{for k, v in X : cle => valeur}` ;
- `for_each`, `count`, `count.index`, et les blocs imbriques
  (`validation`, `lifecycle`, `ports`...).

CE QUI NE L'EST PAS
-------------------
Les `dynamic` blocks, les `provisioner`, les expressions conditionnelles
ternaires, les heredocs, les `splat` (`a.*.b`) et l'arithmetique. Chacun
leve une erreur explicite plutot que de produire un resultat faux — c'est
la seule facon honnete de livrer un sous-ensemble.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


class ErreurHcl(Exception):
    """Une erreur de syntaxe, avec la ligne — comme Terraform en rend une."""


# ── les lexemes ──────────────────────────────────────────────────────────

_MOTIFS = [
    ("espace", r"[ \t\r]+"),
    ("commentaire", r"(#|//)[^\n]*"),
    ("bloc_commentaire", r"/\*.*?\*/"),
    ("saut", r"\n"),
    ("nombre", r"-?\d+(?:\.\d+)?"),
    ("chaine", r'"(?:[^"\\]|\\.)*"'),
    ("identifiant", r"[A-Za-z_][A-Za-z0-9_-]*"),
    ("fleche", r"=>"),
    ("symbole", r"[{}\[\]()=,:.]"),
]
_LEXEUR = re.compile(
    "|".join(f"(?P<{nom}>{motif})" for nom, motif in _MOTIFS),
    re.DOTALL,
)


@dataclass
class Lexeme:
    genre: str
    texte: str
    ligne: int


def lexer(source: str) -> list[Lexeme]:
    lexemes: list[Lexeme] = []
    ligne = 1
    position = 0
    while position < len(source):
        trouve = _LEXEUR.match(source, position)
        if trouve is None:
            raise ErreurHcl(f"caractere inattendu ligne {ligne} : "
                            f"{source[position]!r}")
        genre = trouve.lastgroup
        texte = trouve.group()
        position = trouve.end()
        if genre == "saut":
            ligne += 1
            lexemes.append(Lexeme("saut", texte, ligne))
            continue
        ligne += texte.count("\n")
        if genre in ("espace", "commentaire", "bloc_commentaire"):
            continue
        lexemes.append(Lexeme(genre, texte, ligne))
    lexemes.append(Lexeme("fin", "", ligne))
    return lexemes


# ── l'arbre ──────────────────────────────────────────────────────────────

@dataclass
class Bloc:
    """Un bloc HCL : son type, ses etiquettes, son contenu."""

    type: str
    etiquettes: list[str]
    attributs: dict[str, Any] = field(default_factory=dict)
    blocs: list["Bloc"] = field(default_factory=list)
    ligne: int = 0

    def enfants(self, type_voulu: str) -> list["Bloc"]:
        return [bloc for bloc in self.blocs if bloc.type == type_voulu]

    def enfant(self, type_voulu: str) -> "Bloc | None":
        trouves = self.enfants(type_voulu)
        return trouves[0] if trouves else None


# ── les expressions, non evaluees ────────────────────────────────────────

@dataclass
class Reference:
    """`var.taille`, `each.key`, `conteneur.app.nom` — resolu plus tard."""

    chemin: tuple[str, ...]

    def __str__(self) -> str:
        return ".".join(self.chemin)


@dataclass
class Index:
    """`var.liste[0]`, `local.carte["prod"]` — un acces par cle ou rang."""

    source: Any
    cle: Any


@dataclass
class Appel:
    """`contains(["a"], var.x)` — resolu plus tard."""

    nom: str
    arguments: list[Any]


@dataclass
class Interpolation:
    """Une chaine `"a-${var.x}-b"`, decoupee en morceaux."""

    morceaux: list[Any]   # str litteraux, ou expressions


@dataclass
class BoucleListe:
    """`[for v in X : expr]`."""

    variable: str
    source: Any
    valeur: Any


@dataclass
class BoucleObjet:
    """`{for k, v in X : cle => valeur}`."""

    cle_variable: str
    valeur_variable: str
    source: Any
    cle: Any
    valeur: Any


# ── l'analyseur ──────────────────────────────────────────────────────────

class Analyseur:

    def __init__(self, source: str, fichier: str = "<memoire>") -> None:
        self.lexemes = lexer(source)
        self.position = 0
        self.fichier = fichier

    # -- outillage ------------------------------------------------------

    @property
    def courant(self) -> Lexeme:
        return self.lexemes[self.position]

    def avancer(self) -> Lexeme:
        lexeme = self.lexemes[self.position]
        self.position += 1
        return lexeme

    def sauter_les_sauts(self) -> None:
        while self.courant.genre == "saut":
            self.position += 1

    def attendre(self, texte: str) -> Lexeme:
        if self.courant.texte != texte:
            raise ErreurHcl(
                f"{self.fichier} ligne {self.courant.ligne} : "
                f"« {texte} » attendu, « {self.courant.texte} » trouve")
        return self.avancer()

    # -- le corps -------------------------------------------------------

    def analyser(self) -> list[Bloc]:
        """Le fichier entier : une suite de blocs de premier niveau."""
        blocs: list[Bloc] = []
        self.sauter_les_sauts()
        while self.courant.genre != "fin":
            blocs.append(self.bloc())
            self.sauter_les_sauts()
        return blocs

    def bloc(self) -> Bloc:
        depart = self.courant
        if depart.genre != "identifiant":
            raise ErreurHcl(f"{self.fichier} ligne {depart.ligne} : "
                            f"un bloc doit commencer par un identifiant, "
                            f"« {depart.texte} » trouve")
        type_bloc = self.avancer().texte
        etiquettes: list[str] = []
        while self.courant.genre == "chaine":
            etiquettes.append(self._chaine_simple(self.avancer().texte))
        self.attendre("{")
        bloc = Bloc(type_bloc, etiquettes, ligne=depart.ligne)
        self._corps(bloc)
        return bloc

    def _corps(self, bloc: Bloc) -> None:
        self.sauter_les_sauts()
        while self.courant.texte != "}":
            if self.courant.genre == "fin":
                raise ErreurHcl(f"{self.fichier} : « }} » manquant "
                                f"pour le bloc « {bloc.type} » "
                                f"ouvert ligne {bloc.ligne}")
            nom = self.avancer()
            if nom.genre not in ("identifiant", "chaine"):
                raise ErreurHcl(f"{self.fichier} ligne {nom.ligne} : "
                                f"attribut ou bloc attendu, "
                                f"« {nom.texte} » trouve")
            cle = (self._chaine_simple(nom.texte)
                   if nom.genre == "chaine" else nom.texte)
            if self.courant.texte == "=":
                self.avancer()
                bloc.attributs[cle] = self.expression()
            elif self.courant.texte == "{" or self.courant.genre == "chaine":
                # Un bloc imbrique, avec ou sans etiquette.
                etiquettes: list[str] = []
                while self.courant.genre == "chaine":
                    etiquettes.append(
                        self._chaine_simple(self.avancer().texte))
                self.attendre("{")
                interne = Bloc(cle, etiquettes, ligne=nom.ligne)
                self._corps(interne)
                bloc.blocs.append(interne)
            else:
                raise ErreurHcl(f"{self.fichier} ligne {nom.ligne} : "
                                f"« = » ou « {{ » attendu apres « {cle} »")
            self.sauter_les_sauts()
        self.attendre("}")

    # -- les expressions ------------------------------------------------

    def expression(self) -> Any:
        self.sauter_les_sauts()
        lexeme = self.courant
        if lexeme.genre == "chaine":
            self.avancer()
            return self._chaine(lexeme.texte)
        if lexeme.genre == "nombre":
            self.avancer()
            texte = lexeme.texte
            return float(texte) if "." in texte else int(texte)
        if lexeme.texte == "[":
            return self._liste()
        if lexeme.texte == "{":
            return self._objet()
        if lexeme.genre == "identifiant":
            return self._identifiant()
        raise ErreurHcl(f"{self.fichier} ligne {lexeme.ligne} : "
                        f"expression attendue, « {lexeme.texte} » trouve")

    def _identifiant(self) -> Any:
        premier = self.avancer().texte
        if premier == "true":
            return True
        if premier == "false":
            return False
        if premier == "null":
            return None
        if self.courant.texte == "(":
            return self._indexations(self._appel(premier))
        chemin = [premier]
        while self.courant.texte == ".":
            self.avancer()
            suivant = self.avancer()
            chemin.append(suivant.texte)
        return self._indexations(Reference(tuple(chemin)))

    def _indexations(self, source: Any) -> Any:
        """`a[0]`, `a["x"]`, et les chaines : `a[0][1]`."""
        # >>> depart: enrouler la source dans un `Index` tant qu'un « [ » suit
        #     return source
        while self.courant.texte == "[":
            self.avancer()
            cle = self.expression()
            self.attendre("]")
            source = Index(source, cle)
        return source
        # <<<

    def _appel(self, nom: str) -> Appel:
        self.attendre("(")
        arguments: list[Any] = []
        self.sauter_les_sauts()
        while self.courant.texte != ")":
            arguments.append(self.expression())
            self.sauter_les_sauts()
            if self.courant.texte == ",":
                self.avancer()
                self.sauter_les_sauts()
        self.attendre(")")
        return Appel(nom, arguments)

    def _liste(self) -> Any:
        self.attendre("[")
        self.sauter_les_sauts()
        if self.courant.texte == "for":
            return self._boucle_liste()
        elements: list[Any] = []
        while self.courant.texte != "]":
            elements.append(self.expression())
            self.sauter_les_sauts()
            if self.courant.texte == ",":
                self.avancer()
                self.sauter_les_sauts()
        self.attendre("]")
        return elements

    def _boucle_liste(self) -> BoucleListe:
        self.attendre("for")
        variable = self.avancer().texte
        self.attendre("in")
        source = self.expression()
        self.attendre(":")
        valeur = self.expression()
        self.sauter_les_sauts()
        self.attendre("]")
        return BoucleListe(variable, source, valeur)

    def _objet(self) -> Any:
        self.attendre("{")
        self.sauter_les_sauts()
        if self.courant.texte == "for":
            return self._boucle_objet()
        objet: dict[str, Any] = {}
        while self.courant.texte != "}":
            cle_lexeme = self.avancer()
            cle = (self._chaine_simple(cle_lexeme.texte)
                   if cle_lexeme.genre == "chaine" else cle_lexeme.texte)
            if self.courant.texte in ("=", ":"):
                self.avancer()
            objet[cle] = self.expression()
            self.sauter_les_sauts()
            if self.courant.texte == ",":
                self.avancer()
                self.sauter_les_sauts()
        self.attendre("}")
        return objet

    def _boucle_objet(self) -> BoucleObjet:
        self.attendre("for")
        cle_variable = self.avancer().texte
        self.attendre(",")
        valeur_variable = self.avancer().texte
        self.attendre("in")
        source = self.expression()
        self.attendre(":")
        cle = self.expression()
        self.attendre("=>")
        valeur = self.expression()
        self.sauter_les_sauts()
        self.attendre("}")
        return BoucleObjet(cle_variable, valeur_variable, source, cle, valeur)

    # -- les chaines ----------------------------------------------------

    @staticmethod
    def _chaine_simple(brute: str) -> str:
        return brute[1:-1].replace('\\"', '"').replace("\\n", "\n")

    def _chaine(self, brute: str) -> Any:
        """Une chaine, decoupee si elle contient des `${...}`."""
        contenu = self._chaine_simple(brute)
        # >>> depart: decouper la chaine en morceaux litteraux et en expressions `${...}`
        #     return contenu
        if "${" not in contenu:
            return contenu
        morceaux: list[Any] = []
        reste = contenu
        while "${" in reste:
            avant, _, apres = reste.partition("${")
            if avant:
                morceaux.append(avant)
            expression, _, reste = apres.partition("}")
            sous = Analyseur(expression.strip(), self.fichier)
            morceaux.append(sous.expression())
        if reste:
            morceaux.append(reste)
        return Interpolation(morceaux)
        # <<<


def analyser_fichier(chemin) -> list[Bloc]:
    """Analyse un fichier `.tf` et rend ses blocs de premier niveau."""
    from pathlib import Path

    fichier = Path(chemin)
    return Analyseur(fichier.read_text(encoding="utf-8"),
                     fichier.name).analyser()


def analyser_dossier(dossier) -> list[Bloc]:
    """Tous les `.tf` d'un dossier, dans l'ordre alphabetique.

    C'est ce que fait Terraform : il ne lit pas les sous-dossiers, et
    l'ordre des fichiers n'a aucune importance — seul le graphe de
    dependances compte.
    """
    from pathlib import Path

    blocs: list[Bloc] = []
    for fichier in sorted(Path(dossier).glob("*.tf")):
        blocs.extend(analyser_fichier(fichier))
    return blocs
