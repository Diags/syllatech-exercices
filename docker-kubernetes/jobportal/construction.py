"""`docker build` : l'algorithme du cache, ecrit en clair.

LA REGLE, EN UNE PHRASE
-----------------------
Chaque instruction produit une couche dont la **cle de cache** est calculee
a partir de *la cle de la couche parente* et du *texte de l'instruction* —
plus, pour un `COPY` ou un `ADD`, **l'empreinte des fichiers copies**.

Deux consequences, et ce sont les deux seules choses a retenir :

1. si une couche manque le cache, **toutes celles qui la suivent le
   manquent aussi**, puisqu'elles ont une parente differente ;
2. un `COPY . .` place tot fait donc dependre tout le reste du fichier le
   plus volatil du projet — souvent un README.

Le chapitre 2 mesure l'ecart entre deux Dockerfile qui produisent la MEME
image : l'un reconstruit six couches sur une modification d'un caractere,
l'autre zero.

⚠️ CE QUI EST MODELISE, ET CE QUI NE L'EST PAS
Ce module implante le constructeur **classique** : les etapes s'executent
dans l'ordre, toutes, meme celles dont l'image finale ne depend pas.
BuildKit — le constructeur par defaut depuis Docker 23 — fait deux choses
de plus : il construit les etapes **en parallele** et **saute** celles qui
ne contribuent pas a la cible. L'algorithme du cache, lui, est le meme, et
c'est lui que le cours enseigne.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from . import effets
from .contexte import Contexte
from .dockerfile import (Dockerfile, Etape, Instruction, arguments_exec,
                         forme_exec, sources_et_destination)
from .image import Couche, FichierImage, Image


class ErreurConstruction(Exception):
    """Une etape introuvable, un COPY sans source."""


@dataclass
class Etat:
    """Ce que le constructeur sait a un instant donne d'une etape."""

    cle: str
    couches: list[Couche] = field(default_factory=list)
    repertoire: str = "/"
    utilisateur: str = "root"
    variables: dict[str, str] = field(default_factory=dict)
    ports: list[int] = field(default_factory=list)
    point_d_entree: list[str] = field(default_factory=list)
    exec_: bool = True

    def fichiers(self) -> dict[str, FichierImage]:
        vue: dict[str, FichierImage] = {}
        for couche in self.couches:
            for chemin in couche.supprimes:
                for existant in [c for c in vue
                                 if c == chemin or c.startswith(chemin.rstrip("/") + "/")]:
                    del vue[existant]
            vue.update(couche.ajoutes)
        return vue


@dataclass
class Pas:
    """Une instruction executee, et ce qu'elle a coute."""

    instruction: Instruction
    etape: str
    couche: Couche | None
    en_cache: bool
    secondes: float


@dataclass
class Construction:
    """Le resultat d'un `docker build`."""

    image: Image
    pas: list[Pas] = field(default_factory=list)
    inconnues: list[str] = field(default_factory=list)

    @property
    def secondes(self) -> float:
        return sum(pas.secondes for pas in self.pas)

    @property
    def couches_reconstruites(self) -> int:
        return sum(1 for pas in self.pas
                   if pas.couche is not None and not pas.en_cache)

    @property
    def couches_reutilisees(self) -> int:
        return sum(1 for pas in self.pas
                   if pas.couche is not None and pas.en_cache)

    @property
    def resume(self) -> str:
        return (f"{self.couches_reconstruites} couche(s) reconstruite(s), "
                f"{self.couches_reutilisees} reutilisee(s) — "
                f"{self.secondes:.1f} s")


class Cache:
    """Le cache de construction : des cles vers des couches deja faites."""

    def __init__(self) -> None:
        self.couches: dict[str, Couche] = {}
        self.demandes = 0
        self.succes = 0

    def chercher(self, cle: str) -> Couche | None:
        self.demandes += 1
        trouvee = self.couches.get(cle)
        if trouvee is not None:
            self.succes += 1
        return trouvee

    def poser(self, cle: str, couche: Couche) -> None:
        self.couches[cle] = couche

    def vider(self) -> None:
        """Ce que fait `docker build --no-cache`."""
        self.couches.clear()

    def __len__(self) -> int:
        return len(self.couches)


def _cle(parente: str, morceaux: list[str]) -> str:
    # >>> depart: composer la cle a partir de la cle PARENTE et des morceaux
    #     return "sha256:constante"
    empreinte = hashlib.sha256(parente.encode("utf-8"))
    for morceau in morceaux:
        empreinte.update(b"\0")
        empreinte.update(morceau.encode("utf-8"))
    return "sha256:" + empreinte.hexdigest()[:10]
    # <<<


def construire(fichier: Dockerfile, contexte: Contexte,
               cache: Cache | None = None, nom: str = "jobportal:1.0",
               arguments: dict[str, str] | None = None) -> Construction:
    """Execute le Dockerfile et rend l'image finale, cache compris."""
    cache = cache if cache is not None else Cache()
    construction = Construction(Image(nom))
    variables_de_tete = dict(arguments or {})
    for instruction in fichier.arguments_de_tete:
        nom_arg, _, defaut = instruction.arguments.partition("=")
        variables_de_tete.setdefault(nom_arg.strip(), defaut.strip())

    etats: dict[str, Etat] = {}
    dernier: Etat | None = None

    for etape in fichier.etapes:
        etat = _construire_une_etape(etape, fichier, contexte, cache,
                                     etats, construction, variables_de_tete)
        etats[etape.designation] = etat
        etats[str(etape.rang)] = etat
        dernier = etat

    assert dernier is not None
    finale = fichier.finale
    construction.image = Image(
        nom, list(dernier.couches), finale.base, dernier.utilisateur,
        dernier.point_d_entree, dernier.exec_, dict(dernier.variables),
        list(dernier.ports))
    return construction


def _construire_une_etape(etape: Etape, fichier: Dockerfile,
                          contexte: Contexte, cache: Cache,
                          etats: dict[str, Etat],
                          construction: Construction,
                          variables_de_tete: dict[str, str]) -> Etat:
    etat = Etat(cle="", variables=dict(variables_de_tete))

    for instruction in etape.instructions:
        if instruction.mot == "FROM":
            effet = effets.pour_la_base(etape.base)
            cle = _cle("racine", [f"FROM {etape.base}"])
            couche, en_cache, secondes = _obtenir(
                cache, cle, instruction, etape.designation, effet,
                effet.produit)
            etat.cle = cle
            etat.couches.append(couche)
            construction.pas.append(
                Pas(instruction, etape.designation, couche, en_cache, secondes))
            continue

        if instruction.mot in ("COPY", "ADD"):
            couche, en_cache, secondes = _copier(
                instruction, etape, fichier, contexte, cache, etats, etat)
            etat.cle = couche.identifiant
            etat.couches.append(couche)
            construction.pas.append(
                Pas(instruction, etape.designation, couche, en_cache, secondes))
            continue

        if instruction.mot == "RUN":
            commande = instruction.arguments.strip()
            if not effets.connue(commande) and commande not in construction.inconnues:
                construction.inconnues.append(commande)
            effet = effets.pour_la_commande(commande)
            cle = _cle(etat.cle, [instruction.texte])
            couche, en_cache, secondes = _obtenir(
                cache, cle, instruction, etape.designation, effet,
                _prefixer(effet.produit, etat.repertoire))
            etat.cle = cle
            etat.couches.append(couche)
            construction.pas.append(
                Pas(instruction, etape.designation, couche, en_cache, secondes))
            continue

        # Les instructions de metadonnees : elles changent la cle — donc
        # elles invalident la suite — mais ne posent aucune couche.
        _appliquer_les_metadonnees(instruction, etat)
        etat.cle = _cle(etat.cle, [instruction.texte])
        construction.pas.append(
            Pas(instruction, etape.designation, None, True, 0.0))

    return etat


def _obtenir(cache: Cache, cle: str, instruction: Instruction, etape: str,
             effet: effets.Effet,
             produit: dict[str, int]) -> tuple[Couche, bool, float]:
    trouvee = cache.chercher(cle)
    if trouvee is not None:
        reutilisee = Couche(trouvee.identifiant, trouvee.instruction,
                            dict(trouvee.ajoutes), set(trouvee.supprimes),
                            venue_du_cache=True, etape=etape)
        return reutilisee, True, 0.0

    ajoutes = {chemin: FichierImage(chemin, taille)
               for chemin, taille in produit.items()}
    couche = Couche(cle, instruction.texte, ajoutes, set(effet.efface),
                    venue_du_cache=False, etape=etape)
    cache.poser(cle, couche)
    return couche, False, effet.secondes


def _copier(instruction: Instruction, etape: Etape, fichier: Dockerfile,
            contexte: Contexte, cache: Cache, etats: dict[str, Etat],
            etat: Etat) -> tuple[Couche, bool, float]:
    sources, destination = sources_et_destination(instruction)
    origine = instruction.drapeaux.get("from")

    if origine is not None:
        # `COPY --from=build` : la source n'est pas le contexte, c'est le
        # systeme de fichiers d'une autre etape. La cle inclut donc la cle
        # finale de cette etape — si l'etape a rejoue, la copie rejoue.
        source_etat = etats.get(origine)
        if source_etat is None:
            raise ErreurConstruction(
                f"ligne {instruction.ligne} : « --from={origine} » — "
                f"aucune etape de ce nom n'a ete construite avant")
        empreinte = source_etat.cle
        pris = _prendre(source_etat.fichiers(), sources,
                        _absolu(destination, etat.repertoire))
    else:
        empreinte = contexte.empreinte_de(sources)
        pris = _depuis_le_contexte(contexte, sources, destination,
                                   etat.repertoire)

    cle = _cle(etat.cle, [instruction.texte, empreinte])
    trouvee = cache.chercher(cle)
    if trouvee is not None:
        return (Couche(trouvee.identifiant, trouvee.instruction,
                       dict(trouvee.ajoutes), set(trouvee.supprimes),
                       venue_du_cache=True, etape=etape.designation),
                True, 0.0)

    couche = Couche(cle, instruction.texte, pris, set(),
                    venue_du_cache=False, etape=etape.designation)
    cache.poser(cle, couche)
    # Le temps d'une copie : proportionnel a ce qu'elle transporte.
    secondes = round(0.2 + couche.taille / 200_000_000, 2)
    return couche, False, secondes


def _depuis_le_contexte(contexte: Contexte, sources: list[str],
                        destination: str,
                        repertoire: str) -> dict[str, FichierImage]:
    cible = _absolu(destination, repertoire)
    fichiers: dict[str, FichierImage] = {}
    for fichier in contexte.correspondants(sources):
        chemin = f"{cible.rstrip('/')}/{fichier.chemin}"
        fichiers[chemin] = FichierImage(chemin, fichier.taille,
                                        fichier.contenu)
    return fichiers


def _prendre(source: dict[str, FichierImage], sources: list[str],
             destination: str) -> dict[str, FichierImage]:
    """`COPY --from=build /app/target/x.jar app.jar`."""
    pris: dict[str, FichierImage] = {}
    for motif in sources:
        for chemin, fichier in source.items():
            if chemin == motif or chemin.startswith(motif.rstrip("/") + "/"):
                cible = (destination if chemin == motif
                         else f"{destination.rstrip('/')}"
                               f"/{chemin[len(motif):].lstrip('/')}")
                pris[cible] = FichierImage(cible, fichier.taille)
    return pris


def _absolu(chemin: str, repertoire: str) -> str:
    if chemin.startswith("/"):
        return chemin
    return f"{repertoire.rstrip('/')}/{chemin.lstrip('./')}" or "/"


def _prefixer(produit: dict[str, int], repertoire: str) -> dict[str, int]:
    return {(chemin if chemin.startswith("/")
             else _absolu(chemin, repertoire)): taille
            for chemin, taille in produit.items()}


def _appliquer_les_metadonnees(instruction: Instruction, etat: Etat) -> None:
    if instruction.mot == "WORKDIR":
        etat.repertoire = _absolu(instruction.arguments.strip(),
                                  etat.repertoire)
    elif instruction.mot == "USER":
        etat.utilisateur = instruction.arguments.strip()
    elif instruction.mot == "ENV":
        cle, _, valeur = instruction.arguments.partition("=")
        if not valeur:
            cle, _, valeur = instruction.arguments.partition(" ")
        etat.variables[cle.strip()] = valeur.strip().strip('"')
    elif instruction.mot == "ARG":
        cle, _, valeur = instruction.arguments.partition("=")
        etat.variables.setdefault(cle.strip(), valeur.strip())
    elif instruction.mot == "EXPOSE":
        for morceau in instruction.arguments.split():
            etat.ports.append(int(morceau.split("/")[0]))
    elif instruction.mot == "ENTRYPOINT":
        etat.point_d_entree = arguments_exec(instruction)
        etat.exec_ = forme_exec(instruction)
    elif instruction.mot == "CMD" and not etat.point_d_entree:
        etat.point_d_entree = arguments_exec(instruction)
        etat.exec_ = forme_exec(instruction)


def rendre(construction: Construction) -> list[str]:
    """La construction, telle qu'elle defile dans un terminal."""
    lignes: list[str] = []
    total = len(construction.pas)
    for rang, pas in enumerate(construction.pas, 1):
        etat = "CACHED" if pas.couche is not None and pas.en_cache else ""
        if pas.couche is None:
            etat = "meta"
        instruction = pas.instruction.texte
        if len(instruction) > 46:
            instruction = instruction[:43] + "..."
        duree = f"{pas.secondes:5.1f}s" if pas.secondes else "      "
        lignes.append(f"  [{rang:>2}/{total}] {instruction:<46} "
                      f"{duree} {etat}")
    lignes.append("")
    lignes.append(f"  => {construction.resume}")
    return lignes
