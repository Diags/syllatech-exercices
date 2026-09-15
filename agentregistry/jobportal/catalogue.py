"""Couche C — le catalogue, et la resolution des references.

Les deux couches precedentes regardent un manifeste SEUL. Celle-ci le regarde
au milieu des autres, et c'est la seule qui peut repondre a la question qui
compte a la mise en production : « ce que cet agent reference existe-t-il ? »

Le decoupage vient de l'amont, pas d'un choix de conception ici :

    agent_validate.go :  func (a *Agent) Validate() error         ← couche B
    agent_validate.go :  func (a *Agent) ResolveRefs(ctx, resolver) ← couche C

« No network I/O; ref existence is covered by ResolveRefs. » Un manifeste
structurellement parfait dont toutes les references pendouillent passe la
premiere et echoue la seconde — et seule la seconde a besoin d'un registre.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Iterable

from jobportal.manifeste import (
    ESPACE_PAR_DEFAUT,
    ETIQUETTE_PAR_DEFAUT,
    Document,
    etiquetable,
)
from jobportal.regles import ErreurDeChamp, verifier

# agent_validate.go, resolveResourceRefs : le type par defaut vient du CHAMP
# dans lequel la reference est posee, pas de la reference elle-meme.
TYPE_PAR_CHAMP = {
    "mcpServers": "MCPServer",
    "plugins": "Plugin",
    "skills": "Skill",
    "instructions": "Prompt",
}


@dataclass(frozen=True)
class Identite:
    """L'identite de stockage : (type, espace, nom, etiquette)."""

    type: str
    espace: str
    nom: str
    etiquette: str = ""

    def __str__(self) -> str:
        base = f"{self.type}/{self.espace}/{self.nom}"
        return f"{base}@{self.etiquette}" if self.etiquette else base


@dataclass
class Resultat:
    """Ce que `arctl apply` rend pour UN document."""

    document: Document
    identite: Identite | None
    structure: list[ErreurDeChamp] = field(default_factory=list)
    references: list[ErreurDeChamp] = field(default_factory=list)
    remplace: Identite | None = None

    @property
    def accepte(self) -> bool:
        return not self.structure and not self.references

    @property
    def erreurs(self) -> list[ErreurDeChamp]:
        return self.structure + self.references


class Catalogue:
    """Le registre, reduit a ce qu'il fait d'un manifeste.

    Ce qu'il n'est pas : une base Postgres, un serveur HTTP, un daemon Docker.
    Ce qu'il est : la table (type, espace, nom, etiquette) → objet, et les
    deux regles qui la peuplent — le defaut d'identite, et la resolution des
    references.
    """

    def __init__(self) -> None:
        self.objets: dict[Identite, dict[str, Any]] = {}
        self.journal: list[Resultat] = []

    # ── identite ────────────────────────────────────────────────────────

    @staticmethod
    def identite_de(doc: Document) -> Identite:
        """L'identite EFFECTIVE : les defauts du serveur sont poses ici.

        object.go : « Inbound defaulting from empty to "default" happens at
        the apply boundary » pour l'espace ; « When Tag is omitted, the store
        fills it with the literal "latest" tag » pour l'etiquette.
        """
        # TODO : poser les deux defauts du serveur — espace et etiquette
        return Identite(doc.type, doc.espace, doc.nom, doc.etiquette)

    # ── resolution ──────────────────────────────────────────────────────

    def references_de(self, doc: Document) -> list[tuple[str, Identite, dict]]:
        """Les references d'un document, NORMALISEES.

        Normaliser, c'est poser trois defauts que le manifeste n'ecrit pas :
        le type (depuis le champ), l'espace (celui de l'objet qui reference),
        et l'etiquette (« latest »). Les trois sont invisibles a la relecture.
        """
        if doc.type != "Agent":
            return []
        espace = doc.espace or ESPACE_PAR_DEFAUT
        sorties = []
        for champ, type_attendu in TYPE_PAR_CHAMP.items():
            valeur = doc.spec.get(champ)
            refs = ([valeur] if isinstance(valeur, dict)
                    else valeur if isinstance(valeur, list) else [])
            for i, ref in enumerate(refs):
                if not isinstance(ref, dict):
                    continue
                type_ = ref.get("kind") or type_attendu
                chemin = (f"spec.{champ}" if champ == "instructions"
                          else f"spec.{champ}[{i}]")
                sorties.append((
                    chemin,
                    Identite(
                        type_,
                        ref.get("namespace") or espace,
                        ref.get("name") or "",
                        (ref.get("tag") or ETIQUETTE_PAR_DEFAUT)
                        if etiquetable(type_) else "",
                    ),
                    ref,
                ))
        return sorties

    def resoudre(self, doc: Document) -> list[ErreurDeChamp]:
        """Agent.ResolveRefs : chaque reference designe-t-elle un objet ?

        ErrDanglingRef = « referenced resource not found ». C'est la seule
        erreur de ce projet qui depend de ce qui a ete applique AVANT.
        """
        erreurs = []
        # TODO : signaler chaque reference dont la cible n'est pas au catalogue
        return erreurs
        return erreurs

    # ── apply ───────────────────────────────────────────────────────────

    def appliquer(self, doc: Document, *, valider: bool = True) -> Resultat:
        """Les trois etapes d'`arctl apply`, dans l'ordre du serveur.

        1. structure  (Validate)      — le document, seul ;
        2. references (ResolveRefs)   — le document, dans le catalogue ;
        3. ecriture   (Store.Upsert)  — et seulement si 1 et 2 sont vides.
        """
        avec_defauts = doc.avec_defauts()
        structure = verifier(avec_defauts) if valider else []
        references = self.resoudre(avec_defauts)
        identite = self.identite_de(doc)
        resultat = Resultat(doc, identite, structure, references)

        if resultat.accepte:
            ancien = self.objets.get(identite)
            if ancien is not None:
                resultat.remplace = identite
            self.objets[identite] = self._normaliser(avec_defauts)
        self.journal.append(resultat)
        return resultat

    def appliquer_tous(self, documents: Iterable[Document]) -> list[Resultat]:
        """`arctl apply -f fichier.yaml` sur un fichier multi-documents.

        « Resources are applied in document order, so define dependencies
        first » (examples/full-stack.yaml). L'ordre n'est donc pas un detail
        de presentation : deplacer l'agent en tete casse le fichier.
        """
        return [self.appliquer(d) for d in documents]

    @staticmethod
    def _normaliser(doc: Document) -> dict[str, Any]:
        """Ce que le registre STOCKE — pas ce que l'auteur a ecrit.

        agent_validate.go, validateResourceRefs : « defaults an empty Kind to
        expectKind IN PLACE. The defaulting must persist into the stored spec:
        the deploy-time resolver looks up stores[ref.Kind] with no defaulting
        of its own, so a ref left with an empty Kind would resolve to no store
        and fail the deploy. »

        Autrement dit : le validateur ECRIT dans l'objet qu'il valide. Le
        fichier et la fiche du catalogue ne disent deja plus la meme chose.
        """
        stocke = copy.deepcopy(doc.brut)
        if doc.type != "Agent":
            return stocke
        spec = stocke.get("spec")
        if not isinstance(spec, dict):
            return stocke
        for champ, type_attendu in TYPE_PAR_CHAMP.items():
            valeur = spec.get(champ)
            refs = ([valeur] if isinstance(valeur, dict)
                    else valeur if isinstance(valeur, list) else [])
            for ref in refs:
                if isinstance(ref, dict):
                    ref.setdefault("kind", type_attendu)
        return stocke

    # ── lecture ─────────────────────────────────────────────────────────

    def obtenir(self, identite: Identite) -> dict[str, Any] | None:
        return self.objets.get(identite)

    def par_type(self, type_: str) -> list[Identite]:
        return sorted((i for i in self.objets if i.type == type_), key=str)

    def etiquettes(self, type_: str, nom: str,
                   espace: str = ESPACE_PAR_DEFAUT) -> list[str]:
        """`arctl get <type> <nom> --all-tags`."""
        return sorted(i.etiquette for i in self.objets
                      if i.type == type_ and i.nom == nom and i.espace == espace)

    def selectionner(self, type_: str, selecteur: str = "") -> list[Identite]:
        """La decouverte, telle que l'API la propose.

        `GET /v0/mcpservers?labels=cle=valeur,cle2=valeur2` — c'est le seul
        filtre de contenu des routes de liste. Il n'y a pas de route de
        recherche, et aucun champ « capability » dans le schema : une
        decouverte par capacite passe donc par une CONVENTION de libelles
        que le registre ne definit pas.
        """
        voulus = dict(
            paire.split("=", 1) for paire in selecteur.split(",") if "=" in paire
        ) if selecteur else {}
        trouves = []
        for identite in self.par_type(type_):
            libelles = (self.objets[identite].get("metadata") or {}) \
                .get("labels") or {}
            if all(libelles.get(c) == v for c, v in voulus.items()):
                trouves.append(identite)
        return trouves

    def __len__(self) -> int:
        return len(self.objets)
