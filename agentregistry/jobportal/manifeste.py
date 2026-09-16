"""L'enveloppe d'un manifeste AgentRegistry, et la liste des types.

Un manifeste est du YAML de forme Kubernetes :

    apiVersion: ar.dev/v1alpha1
    kind: MCPServer
    metadata: {name: …, tag: …}
    spec: {…}

Un fichier peut en contenir plusieurs, separes par `---`. L'ordre compte :
`arctl apply -f` applique dans l'ordre du document, donc les dependances
d'abord (docs/declarative-cli.md, section « Tips »).

Tout ce que ce module affirme vient de `pkg/api/v1alpha1/` du depot amont,
au commit 82bbd6c. Les citations sont dans le code, pas dans le README :
une regle qu'on ne peut pas remonter a sa source est une regle qu'on ne peut
pas contredire.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import yaml

# pkg/api/v1alpha1/doc.go : « GroupVersion is the apiVersion string used by
# every resource in this package. »
GROUPE_VERSION = "ar.dev/v1alpha1"

# pkg/api/v1alpha1/object.go : DefaultNamespace = "default".
ESPACE_PAR_DEFAUT = "default"

# pkg/api/v1alpha1/object.go : « When Tag is omitted, the store fills it with
# the literal "latest" tag. »
ETIQUETTE_PAR_DEFAUT = "latest"

# pkg/api/v1alpha1/kinds.go : deux semantiques de persistance.
#   TaggedArtifact : identite = (espace, nom, etiquette) — le catalogue.
#   MutableObject  : identite = (espace, nom)            — le plan de controle.
ARTEFACT_ETIQUETE = "TaggedArtifact"
OBJET_MUTABLE = "MutableObject"

# pkg/api/v1alpha1/doc.go, constantes Kind*, plus l'option de stockage lue
# dans le `MustRegisterKind` de chaque fichier de type.
TYPES: dict[str, str] = {
    "Agent": ARTEFACT_ETIQUETE,
    "MCPServer": ARTEFACT_ETIQUETE,
    "Skill": ARTEFACT_ETIQUETE,
    "Plugin": ARTEFACT_ETIQUETE,
    "Prompt": ARTEFACT_ETIQUETE,
    "Model": ARTEFACT_ETIQUETE,
    "Deployment": OBJET_MUTABLE,
    "Runtime": OBJET_MUTABLE,
    "Secret": OBJET_MUTABLE,
}

# Les quatre que le cours appelle « les artefacts du registre » : ce qu'une
# equipe produit et publie. Les cinq autres existent aussi, et le chapitre 2
# les compte.
ARTEFACTS_DU_COURS = ("MCPServer", "Skill", "Agent", "Prompt")


def etiquetable(type_: str) -> bool:
    """Un type qui accepte `metadata.tag`.

    pkg/api/v1alpha1/validation.go, validateRef : une etiquette posee sur un
    type non etiquetable est une erreur (`kind %q does not support tag
    pinning`), pas un champ ignore.
    """
    return TYPES.get(type_) == ARTEFACT_ETIQUETE


@dataclass
class Document:
    """Un manifeste, tel qu'il est ECRIT — avant tout defaut de serveur."""

    brut: dict[str, Any]
    fichier: str = "(memoire)"
    rang: int = 0

    @property
    def type(self) -> str:
        return self.brut.get("kind") or ""

    @property
    def api(self) -> str:
        return self.brut.get("apiVersion") or ""

    @property
    def metadonnees(self) -> dict[str, Any]:
        m = self.brut.get("metadata")
        return m if isinstance(m, dict) else {}

    @property
    def spec(self) -> dict[str, Any]:
        s = self.brut.get("spec")
        return s if isinstance(s, dict) else {}

    @property
    def nom(self) -> str:
        return self.metadonnees.get("name") or ""

    @property
    def espace(self) -> str:
        """L'espace de noms ECRIT — vide si le manifeste n'en pose pas."""
        return self.metadonnees.get("namespace") or ""

    @property
    def etiquette(self) -> str:
        """L'etiquette ECRITE — vide si le manifeste n'en pose pas."""
        return self.metadonnees.get("tag") or ""

    @property
    def origine(self) -> str:
        return f"{self.fichier}[{self.rang}]"

    def identite(self) -> str:
        """L'identite EFFECTIVE, defauts du serveur appliques.

        C'est ce que le registre stocke, et ce n'est pas ce que le fichier
        dit : deux champs sur trois peuvent etre absents du manifeste.
        """
        espace = self.espace or ESPACE_PAR_DEFAUT
        if etiquetable(self.type):
            return f"{self.type}/{espace}/{self.nom}@" \
                   f"{self.etiquette or ETIQUETTE_PAR_DEFAUT}"
        return f"{self.type}/{espace}/{self.nom}"

    def defauts_appliques(self) -> list[str]:
        """Les champs que le serveur a remplis a la place de l'auteur.

        Un manifeste relu en revue montre ce qui est ECRIT. Le registre valide
        et stocke ce qui est EFFECTIF. Cette liste est l'ecart entre les deux.
        """
        manquants = []
        if not self.espace:
            manquants.append(f"metadata.namespace → {ESPACE_PAR_DEFAUT}")
        if etiquetable(self.type) and not self.etiquette:
            manquants.append(f"metadata.tag → {ETIQUETTE_PAR_DEFAUT}")
        return manquants

    def avec_defauts(self) -> Document:
        """Le meme document, defauts du serveur poses dans metadata.

        pkg/api/v1alpha1/object.go : « Inbound defaulting from empty to
        "default" happens at the apply boundary (see resource.prepareApplyDoc),
        not on UnmarshalJSON. » — le defaut n'est donc PAS dans le decodage :
        c'est une etape a part, et un outil qui valide sans la faire ne valide
        pas ce que le registre valide.
        """
        copie = yaml.safe_load(yaml.safe_dump(self.brut))
        meta = copie.setdefault("metadata", {})
        meta.setdefault("namespace", ESPACE_PAR_DEFAUT)
        if etiquetable(self.type):
            meta.setdefault("tag", ETIQUETTE_PAR_DEFAUT)
        return Document(copie, self.fichier, self.rang)


@dataclass
class Fichier:
    """Un fichier de manifestes : un ou plusieurs documents, dans l'ordre."""

    chemin: Path
    documents: list[Document] = field(default_factory=list)

    def __iter__(self) -> Iterator[Document]:
        return iter(self.documents)

    def __len__(self) -> int:
        return len(self.documents)


def charger(chemin: Path | str) -> Fichier:
    """Lit un fichier de manifestes, `---` compris."""
    chemin = Path(chemin)
    texte = chemin.read_text(encoding="utf-8")
    documents = []
    for rang, brut in enumerate(yaml.safe_load_all(texte)):
        if brut is None:          # un `---` final, ou un fichier tout commente
            continue
        if not isinstance(brut, dict):
            raise ValueError(
                f"{chemin.name}[{rang}] : un manifeste doit etre une table")
        documents.append(Document(brut, chemin.name, rang))
    return Fichier(chemin, documents)


def charger_dossier(dossier: Path | str) -> list[Document]:
    """Tous les manifestes d'un dossier, tries par nom de fichier."""
    dossier = Path(dossier)
    documents: list[Document] = []
    for chemin in sorted(dossier.glob("*.yaml")):
        documents.extend(charger(chemin).documents)
    return documents
