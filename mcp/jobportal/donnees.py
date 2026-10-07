"""Le « db » que les extraits du cours supposent.

Dans la vidéo, le code appelle `db.query(...)`, `db.postuler(...)`,
`db.get_offre(...)` sans jamais montrer ce qu'est `db` — c'est normal dans un
extrait pédagogique, mais c'est précisément ce qui empêche de l'exécuter.

Ce module fournit ce chaînon manquant : un jeu d'offres d'emploi en mémoire,
volontairement minuscule et sans dépendance. Vous pouvez le remplacer par une
vraie base sans toucher au reste du projet — c'est tout l'intérêt d'avoir
isolé les données derrière quelques fonctions.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class Offre:
    id: str
    titre: str
    entreprise: str
    lieu: str
    contrat: str
    competences: tuple[str, ...]
    description: str

    def en_dict(self) -> dict:
        return {
            "id": self.id,
            "titre": self.titre,
            "entreprise": self.entreprise,
            "lieu": self.lieu,
            "contrat": self.contrat,
            "competences": list(self.competences),
        }


@dataclass
class Candidature:
    offre_id: str
    cv: str
    depose_le: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))


OFFRES: dict[str, Offre] = {
    o.id: o
    for o in [
        Offre("JP-001", "Développeur Java / Spring Boot", "Clauger", "Lyon", "CDI",
              ("java", "spring", "postgresql"),
              "Concevoir et maintenir les services métier d'une plateforme industrielle."),
        Offre("JP-002", "Ingénieur IA — agents LLM", "syllatech", "Télétravail", "CDI",
              ("python", "llm", "mcp", "rag"),
              "Construire des agents outillés : serveurs MCP, RAG, évaluation."),
        Offre("JP-003", "Data engineer", "Soteck", "Nantes", "CDD",
              ("python", "sql", "airflow"),
              "Industrialiser les pipelines de données de la production."),
        Offre("JP-004", "Développeur front React", "Europlast", "Bordeaux", "CDI",
              ("react", "typescript", "accessibilité"),
              "Reprendre l'interface du portail client, accessibilité comprise."),
        Offre("JP-005", "SRE / plateforme Kubernetes", "Clauger", "Lyon", "CDI",
              ("kubernetes", "terraform", "observabilité"),
              "Opérer la plateforme interne et son socle d'observabilité."),
    ]
}

CANDIDATURES: list[Candidature] = []


def _plat(texte: str) -> str:
    """Minuscules sans accents : « Développeur » et « developpeur » doivent
    répondre à la même recherche. Un détail, mais c'est le genre de détail qui
    fait qu'un outil paraît cassé à l'utilisateur."""
    sans_accent = unicodedata.normalize("NFD", texte)
    return "".join(c for c in sans_accent if unicodedata.category(c) != "Mn").lower()


def query(mot_cle: str) -> list[dict]:
    """Recherche dans le titre, l'entreprise, le lieu et les compétences."""
    aiguille = _plat(mot_cle.strip())
    if not aiguille:
        return [o.en_dict() for o in OFFRES.values()]
    trouvees = [
        o for o in OFFRES.values()
        if aiguille in _plat(" ".join((o.titre, o.entreprise, o.lieu, *o.competences)))
    ]
    return [o.en_dict() for o in trouvees]


def get_offre(offre_id: str) -> str:
    """Rend une offre lisible par un humain — c'est ce qu'une *resource* MCP
    expose : de la donnée, pas une action."""
    offre = OFFRES.get(offre_id.strip().upper())
    if offre is None:
        return f"Aucune offre ne porte l'identifiant {offre_id}."
    return (
        f"{offre.titre} — {offre.entreprise} ({offre.lieu}, {offre.contrat})\n"
        f"Compétences : {', '.join(offre.competences)}\n\n{offre.description}"
    )


def postuler(offre_id: str, cv: str) -> str:
    """Enregistre une candidature — une *action*, donc un outil, pas une
    resource. La distinction n'est pas cosmétique : un client MCP peut lire
    une resource sans rien changer, et doit demander avant d'appeler un outil."""
    cle = offre_id.strip().upper()
    if cle not in OFFRES:
        raise ValueError(f"Offre inconnue : {offre_id}")
    if not cv.strip():
        raise ValueError("Le CV est vide.")
    CANDIDATURES.append(Candidature(offre_id=cle, cv=cv.strip()))
    return f"Candidature enregistrée pour {cle} ({OFFRES[cle].titre})."


def candidatures() -> list[dict]:
    return [{"offre_id": c.offre_id, "depose_le": c.depose_le} for c in CANDIDATURES]
