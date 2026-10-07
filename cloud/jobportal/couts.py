"""Calculer une facture — et surtout, calculer des RAPPORTS.

CE QUE CE MODULE CHERCHE A MONTRER
----------------------------------
Pas des montants : des rapports. Un montant depend d'une grille tarifaire
qui change tous les trimestres (voir `tarifs.py`, qui le dit). Un rapport,
lui, tient :

- un environnement de test allume en permanence coute **4,2 fois** celui
  qu'on eteint le soir et le week-end. Ce facteur est
  `730 / (8 x 5 x 52 / 12)`, et aucun prix n'y entre ;
- le cloud facture la **taille reservee**, jamais l'usage : une machine
  dont la pointe reelle atteint 11 % de son processeur se remplace par
  un gabarit plus petit, et le chapitre 5 imprime de combien ;
- une base repliquee sur trois zones paie son trafic de replication **six
  fois** : le transfert entre zones est facture a l'emission ET a la
  reception.

⚠️ CE QUI N'EST PAS MODELISE
Les remises par volume, les credits de depart, les engagements de depense
globale, les instances reservees convertibles, la facturation a la seconde
avec minimum d'une minute, et les frais des services managés annexes
(sauvegardes, journaux, metriques) — qui, cumules, pesent souvent plus que
la ligne « calcul ». Une facture reelle a toujours plus de lignes qu'un
modele.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import tarifs

HEURES_PAR_MOIS = tarifs.HEURES_PAR_MOIS
HEURES_OUVREES_PAR_MOIS = 8 * 5 * 52 / 12      # 173,33 h


class ErreurCout(Exception):
    """Un gabarit inconnu, un engagement inconnu, un palier inconnu."""


# ── le calcul ────────────────────────────────────────────────────────────

def machine(nom: str) -> tarifs.Machine:
    if nom not in tarifs.MACHINES:
        raise ErreurCout(f"gabarit inconnu : « {nom} » — "
                         f"connus : {sorted(tarifs.MACHINES)}")
    return tarifs.MACHINES[nom]


def cout_calcul(gabarit: str, heures: float = HEURES_PAR_MOIS,
                engagement: str = "a la demande", exemplaires: int = 1) -> float:
    if engagement not in tarifs.ENGAGEMENTS:
        raise ErreurCout(f"engagement inconnu : « {engagement} »")
    return (machine(gabarit).euros_par_heure * heures * exemplaires
            * tarifs.ENGAGEMENTS[engagement])


def cout_stockage(gio: float, palier: str = "standard",
                  mois: float = 1.0) -> float:
    if palier not in tarifs.PALIERS_STOCKAGE:
        raise ErreurCout(f"palier inconnu : « {palier} »")
    return gio * tarifs.PALIERS_STOCKAGE[palier]["stockage"] * mois


def cout_restitution(gio: float, palier: str) -> float:
    """⚠️ Ce que coute RELIRE une donnee descendue au froid."""
    if palier not in tarifs.PALIERS_STOCKAGE:
        raise ErreurCout(f"palier inconnu : « {palier} »")
    return gio * tarifs.PALIERS_STOCKAGE[palier]["restitution"]


def cout_reseau(gio: float, sens: str) -> float:
    if sens not in tarifs.RESEAU:
        raise ErreurCout(f"sens de trafic inconnu : « {sens} » — "
                         f"connus : {sorted(tarifs.RESEAU)}")
    return gio * tarifs.RESEAU[sens]


def cout_replication(gio: float, zones: int) -> float:
    """Un octet ecrit, replique vers `zones - 1` autres zones.

    ⚠️ Chaque traversee est facturee DEUX fois — a l'emission et a la
    reception. Trois zones font donc payer 2 x 2 = 4 fois le volume ecrit,
    et ce trafic n'apparait sur aucun tableau de bord applicatif.
    """
    traversees = max(0, zones - 1)
    return gio * traversees * (tarifs.RESEAU["entre zones (emission)"]
                               + tarifs.RESEAU["entre zones (reception)"])


# ── le dimensionnement ───────────────────────────────────────────────────

@dataclass(frozen=True)
class Observation:
    """Ce qu'un mois de metriques dit d'une machine."""

    gabarit: str
    cpu_moyen: float             # 0.08 pour 8 %
    cpu_pointe: float
    memoire_moyenne: float

    @property
    def cout_mensuel(self) -> float:
        return cout_calcul(self.gabarit)


def ajuster(observation: Observation, marge: float = 2.0) -> str:
    """Le plus petit gabarit qui tient la POINTE, avec une marge.

    ⚠️ On dimensionne sur la pointe, jamais sur la moyenne : une machine
    taillee pour sa moyenne tombe a chaque pic. Mais on dimensionne sur la
    pointe OBSERVEE, pas sur celle qu'on imagine — c'est toute la
    difference entre le right-sizing et le « au cas ou ».
    """
    # TODO : choisir le plus petit gabarit qui tient la POINTE, avec la marge
    return observation.gabarit


def economie(observation: Observation, marge: float = 2.0) -> tuple[str, float]:
    cible = ajuster(observation, marge)
    return cible, observation.cout_mensuel - cout_calcul(cible)


# ── la derive ────────────────────────────────────────────────────────────

@dataclass
class Ressource:
    """Une ligne de facture, avec ce qui la justifie — ou pas."""

    nom: str
    gabarit: str
    environnement: str
    heures_par_mois: float = HEURES_PAR_MOIS
    etiquettes: dict[str, str] = field(default_factory=dict)
    utilisee: bool = True

    @property
    def cout(self) -> float:
        return cout_calcul(self.gabarit, self.heures_par_mois)

    @property
    def etiquetee(self) -> bool:
        """⚠️ Sans etiquettes, une ligne de facture n'apprend rien."""
        return {"projet", "equipe", "environnement"} <= set(self.etiquettes)


@dataclass
class Facture:
    ressources: list[Ressource] = field(default_factory=list)

    @property
    def total(self) -> float:
        return sum(r.cout for r in self.ressources)

    def par_etiquette(self, cle: str) -> dict[str, float]:
        """Ce qu'un tableau de bord FinOps peut repartir — et le reste."""
        repartition: dict[str, float] = {}
        for ressource in self.ressources:
            valeur = ressource.etiquettes.get(cle, "(non etiquete)")
            repartition[valeur] = repartition.get(valeur, 0.0) + ressource.cout
        return dict(sorted(repartition.items(),
                           key=lambda paire: -paire[1]))

    @property
    def part_non_etiquetee(self) -> float:
        aveugle = sum(r.cout for r in self.ressources if not r.etiquetee)
        return aveugle / self.total if self.total else 0.0

    @property
    def gaspillage(self) -> float:
        """Ce que coutent les ressources que personne n'utilise."""
        return sum(r.cout for r in self.ressources if not r.utilisee)


def eteindre_la_nuit(ressource: Ressource) -> float:
    """L'economie d'un simple arret hors heures ouvrees."""
    return ressource.cout - cout_calcul(ressource.gabarit,
                                        HEURES_OUVREES_PAR_MOIS)


FACTEUR_ALLUME_EN_PERMANENCE = HEURES_PAR_MOIS / HEURES_OUVREES_PAR_MOIS


# ── le cycle de vie du stockage ──────────────────────────────────────────

@dataclass(frozen=True)
class Regle:
    """« apres N jours, descendre au palier X »."""

    jours: int
    palier: str


def cout_sur_la_duree(gio: float, mois: int,
                      regles: list[Regle] | None = None) -> float:
    """Le cout total de conservation, avec ou sans cycle de vie."""
    # TODO : appliquer la regle en vigueur au mois considere, mois par mois
    return cout_stockage(gio, "standard", mois)


def euros(montant: float) -> str:
    return f"{montant:,.2f} €".replace(",", " ").replace(".", ",")
