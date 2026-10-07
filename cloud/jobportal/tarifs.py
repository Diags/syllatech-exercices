"""Les prix — des ENTREES declarees, pas des mesures.

⚠️ LISEZ CECI AVANT DE CITER UN EURO DE CE PROJET.

Aucun appel n'est fait a aucune API de tarification : il n'y a ni reseau ni
compte. Les prix ci-dessous sont des ordres de grandeur relevés une fois sur
les grilles publiques d'un hyperscaleur en region europeenne, arrondis, et
figes ici. Ils changent tous les trimestres et varient d'une region a
l'autre.

Ce que le projet MESURE n'est aucun de ces prix. Il mesure ce qu'il en
deduit : le RAPPORT entre deux facons de faire la meme chose. Un
environnement allume en permanence coute 4,2 fois celui qu'on eteint le
soir — et ce rapport ne depend pas du prix horaire, seulement du nombre
d'heures. C'est ce rapport qui enseigne quelque chose ; le montant, lui,
n'est la que pour le rendre concret.

Les vrais prix se lisent dans le calculateur du fournisseur, et se
verifient sur la facture du mois suivant. Rien d'autre ne fait foi.
"""

from __future__ import annotations

from dataclasses import dataclass

HEURES_PAR_MOIS = 730.0          # 365,25 x 24 / 12, l'unite de facturation


@dataclass(frozen=True)
class Machine:
    """Un gabarit de machine virtuelle."""

    nom: str
    vcpu: int
    memoire_gio: float
    euros_par_heure: float
    commentaire: str = ""

    @property
    def euros_par_mois(self) -> float:
        return self.euros_par_heure * HEURES_PAR_MOIS


MACHINES: dict[str, Machine] = {
    "petite":       Machine("petite", 2, 8, 0.0456,
                            "2 vCPU / 8 Gio — un service applicatif"),
    "moyenne":      Machine("moyenne", 4, 16, 0.0912,
                            "le double, au double du prix : lineaire"),
    "grande":       Machine("grande", 8, 32, 0.1824, "le double encore"),
    "tres-grande":  Machine("tres-grande", 16, 64, 0.3648,
                            "⚠️ celle qu'on prend « pour etre tranquille »"),
    "memoire":      Machine("memoire", 4, 32, 0.1330,
                            "optimisee memoire : plus chere a vCPU egal"),
}

# Les engagements de duree, en part du tarif a la demande.
#
# ⚠️ Un engagement de trois ans divise la facture par deux — et vous lie
# pour trois ans. C'est un arbitrage financier, pas technique : on ne
# reserve que ce dont on est SUR qu'il tournera encore dans trois ans.
ENGAGEMENTS: dict[str, float] = {
    "a la demande": 1.00,
    "reserve 1 an": 0.62,
    "reserve 3 ans": 0.44,
    "spot": 0.28,          # ⚠️ interruptible a deux minutes de preavis
}

# Le stockage objet, en euros par Gio et par mois, par palier.
#
# ⚠️ Les paliers froids facturent AUSSI la restitution, et imposent une
# duree minimale de conservation. Descendre une donnee qu'on relira demain
# coute donc plus cher que de l'avoir laissee au chaud.
PALIERS_STOCKAGE: dict[str, dict[str, float]] = {
    "standard":     {"stockage": 0.0230, "restitution": 0.0000, "jours_minimum": 0},
    "acces-rare":   {"stockage": 0.0125, "restitution": 0.0100, "jours_minimum": 30},
    "archive":      {"stockage": 0.0040, "restitution": 0.0200, "jours_minimum": 90},
    "archive-profonde": {"stockage": 0.0018, "restitution": 0.0200,
                         "jours_minimum": 180},
}

# Le reseau, en euros par Gio.
#
# ⚠️ L'ENTREE EST GRATUITE, LA SORTIE NE L'EST PAS. Et le trafic entre deux
# zones de disponibilite est facture DES DEUX COTES — ce qui fait qu'une
# base repliquee sur trois zones paie son trafic de replication six fois.
RESEAU: dict[str, float] = {
    "entree": 0.000,
    "sortie internet": 0.085,
    "entre zones (emission)": 0.010,
    "entre zones (reception)": 0.010,
    "entre regions": 0.020,
    "meme zone": 0.000,
}

# Une base managee : le supplement par rapport a la meme machine nue.
#
# ⚠️ Ce supplement paie les sauvegardes, les correctifs, la bascule
# automatique et les restaurations. Le comparer au salaire horaire de qui
# les ferait a la main est le seul calcul honnete.
SUPPLEMENT_MANAGE = 1.85

# Une fonction serverless.
SERVERLESS = {
    "euros_par_million_d_appels": 0.20,
    "euros_par_gio_seconde": 0.0000166667,
}
