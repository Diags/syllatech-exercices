"""Composer des SLA — l'arithmetique qui surprend tout le monde.

TROIS REGLES, ET ELLES SUFFISENT
--------------------------------
1. **en serie**, les disponibilites se MULTIPLIENT. Une chaine de trois
   services a 99,9 % ne vaut pas 99,9 % : elle vaut 99,70 %, et la
   difference se compte en heures de panne par an ;
2. **en parallele**, ce sont les INDISPONIBILITES qui se multiplient. Deux
   repliques a 99,5 % donnent 99,9975 % — c'est tout l'interet d'une
   seconde zone ;
3. une chaine n'est **jamais meilleure que son maillon le plus faible**, et
   elle est toujours strictement pire.

⚠️ CE QUE CES FORMULES SUPPOSENT, ET QUI EST FAUX
Elles supposent des pannes **independantes**. Elles ne le sont pas : deux
repliques partagent un plan de controle, une configuration, une mise a jour
et souvent une equipe. La redondance calculee ici est donc un PLAFOND
theorique, jamais une promesse. C'est aussi pourquoi un incident majeur
touche rarement une seule zone.

⚠️ ET CE QU'UN SLA N'EST PAS
Un SLA n'est pas une garantie de service : c'est un bareme de REMISE. Quand
le fournisseur descend sous son engagement, il rend un pourcentage de votre
facture — pas votre chiffre d'affaires. Le chapitre 1 met les deux chiffres
cote a cote.
"""

from __future__ import annotations

from dataclasses import dataclass, field

SECONDES_PAR_AN = 365.25 * 24 * 3600
SECONDES_PAR_MOIS = SECONDES_PAR_AN / 12


class ErreurDisponibilite(Exception):
    """Une disponibilite hors de [0, 1], une chaine vide."""


@dataclass(frozen=True)
class Composant:
    nom: str
    disponibilite: float             # 0.999 pour 99,9 %
    repliques: int = 1               # en parallele, dans une meme etape

    def __post_init__(self) -> None:
        if not 0.0 <= self.disponibilite <= 1.0:
            raise ErreurDisponibilite(
                f"« {self.nom} » : disponibilite hors de [0, 1] "
                f"({self.disponibilite})")
        if self.repliques < 1:
            raise ErreurDisponibilite(f"« {self.nom} » : 0 replique")

    @property
    def effective(self) -> float:
        """⚠️ N repliques : ce sont les PANNES qui se multiplient."""
        # TODO : rendre la disponibilite de N repliques en parallele
        return self.disponibilite


@dataclass
class Chaine:
    """Des composants traverses l'un apres l'autre par une requete."""

    nom: str
    composants: list[Composant] = field(default_factory=list)

    @property
    def disponibilite(self) -> float:
        # TODO : composer les disponibilites d'une chaine traversee de bout en bout
        return min(c.effective for c in self.composants)

    @property
    def maillon_faible(self) -> Composant:
        return min(self.composants, key=lambda c: c.effective)


def panne_par_an(disponibilite: float) -> float:
    """Secondes d'indisponibilite sur une annee."""
    return (1.0 - disponibilite) * SECONDES_PAR_AN


def panne_par_mois(disponibilite: float) -> float:
    return (1.0 - disponibilite) * SECONDES_PAR_MOIS


def duree(secondes: float) -> str:
    """« 26 h 17 min » — la seule forme qui parle a quelqu'un d'astreinte."""
    secondes = int(round(secondes))
    jours, reste = divmod(secondes, 86400)
    heures, reste = divmod(reste, 3600)
    minutes, secondes = divmod(reste, 60)
    morceaux = []
    if jours:
        morceaux.append(f"{jours} j")
    if heures or jours:
        morceaux.append(f"{heures} h")
    if minutes or heures or jours:
        morceaux.append(f"{minutes} min")
    morceaux.append(f"{secondes} s")
    return " ".join(morceaux[:3] if len(morceaux) > 2 else morceaux)


def pourcent(disponibilite: float, decimales: int = 4) -> str:
    return f"{disponibilite * 100:.{decimales}f} %"


def neuf(nombre: int) -> float:
    """« trois neuf » → 0.999."""
    if nombre < 1:
        raise ErreurDisponibilite("au moins un neuf")
    return 1.0 - 10.0 ** (-nombre)


# ── le bareme de remise ──────────────────────────────────────────────────
#
# ⚠️ ENTREE DECLAREE. Ce bareme est celui d'un SLA de calcul courant (AWS
# EC2, Azure Virtual Machines) au moment de l'ecriture du cours. Les
# fournisseurs le revisent ; le principe, lui, ne bouge pas.

PALIERS = [
    (0.9999, 0.00, "engagement tenu"),
    (0.9900, 0.10, "sous 99,99 %"),
    (0.9500, 0.25, "sous 99,00 %"),
    (0.0000, 1.00, "sous 95,00 %"),
]


def remise(disponibilite_constatee: float) -> tuple[float, str]:
    """La part de la facture MENSUELLE rendue, et le palier atteint."""
    for seuil, part, libelle in PALIERS:
        if disponibilite_constatee >= seuil:
            return part, libelle
    return 1.0, "sous 95,00 %"


@dataclass
class Incident:
    """Une panne, et ce qu'elle coute vraiment."""

    minutes: float
    facture_mensuelle: float
    chiffre_daffaires_par_heure: float

    @property
    def disponibilite_du_mois(self) -> float:
        return 1.0 - (self.minutes * 60) / SECONDES_PAR_MOIS

    @property
    def remise(self) -> float:
        part, _ = remise(self.disponibilite_du_mois)
        return self.facture_mensuelle * part

    @property
    def perte(self) -> float:
        return self.chiffre_daffaires_par_heure * self.minutes / 60

    @property
    def reste_a_charge(self) -> float:
        return self.perte - self.remise


def rendre(chaine: Chaine) -> list[str]:
    """La chaine, composant par composant, et son total."""
    lignes = [f"{'COMPOSANT':<22} {'SLA':>10} {'REPL.':>6} "
              f"{'EFFECTIF':>11} {'PANNE / AN':>14}"]
    for composant in chaine.composants:
        lignes.append(
            f"{composant.nom:<22} {pourcent(composant.disponibilite, 3):>10} "
            f"{composant.repliques:>6} {pourcent(composant.effective):>11} "
            f"{duree(panne_par_an(composant.effective)):>14}")
    total = chaine.disponibilite
    lignes.append(f"{'EN SERIE':<22} {'':<10} {'':>6} "
                  f"{pourcent(total):>11} {duree(panne_par_an(total)):>14}")
    return lignes
