"""Chapitre 2 — Calcul et stockage.

    uv run python chapitres/chapitre_2_calcul_stockage.py

Le curseur VM → conteneurs → serverless n'est pas une echelle de modernite :
c'est un arbitrage qui se chiffre. Et le stockage se choisit par famille,
puis se laisse refroidir.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                       # noqa: E402
from jobportal import couts, tarifs                 # noqa: E402


def main() -> None:
    console.utf8()
    _le_curseur()
    _le_point_de_bascule()
    _les_trois_familles()
    _le_cycle_de_vie()
    _le_piege_du_froid()


def _le_curseur() -> None:
    print("1. LE CURSEUR N'EST PAS UNE ECHELLE DE MODERNITE\n")
    print("   Le portail expose une API consultee par pics : deserte la nuit,")
    print("   tres sollicitee entre 8 h et 10 h. Trois facons de l'heberger,")
    print("   au meme service rendu :\n")

    appels_par_mois = 3_000_000
    gio_secondes = 3_000_000 * 0.4 * 0.512     # 400 ms a 512 Mio

    vm = couts.cout_calcul("moyenne", exemplaires=3)
    conteneurs = couts.cout_calcul("moyenne", exemplaires=1) + \
        couts.cout_calcul("petite", heures=couts.HEURES_PAR_MOIS * 0.3,
                          exemplaires=2)
    serverless = (appels_par_mois / 1e6
                  * tarifs.SERVERLESS["euros_par_million_d_appels"]
                  + gio_secondes * tarifs.SERVERLESS["euros_par_gio_seconde"])

    print(f"   {'SOLUTION':<40} {'PAR MOIS':>12}  CE QU'ON GERE")
    print(f"   {'3 machines, dimensionnees pour la pointe':<40} "
          f"{couts.euros(vm):>12}  systeme, correctifs, mise a l'echelle")
    print(f"   {'conteneurs manages + mise a l echelle':<40} "
          f"{couts.euros(conteneurs):>12}  l'image, et rien d'autre")
    print(f"   {'fonctions serverless':<40} "
          f"{couts.euros(serverless):>12}  le code")
    nombre = f"{appels_par_mois:,}".replace(",", " ")
    print(f"\n   (serverless : {nombre} appels de 400 ms a 512 Mio)")

    print("\n   Le rapport de 1 a "
          f"{vm / serverless:.0f} n'est pas une promesse : il tient")
    print("   entierement au PROFIL de charge. Une API consultee en")
    print("   permanence renverse le classement, et c'est la section")
    print("   suivante.")
    print("\n   ⚠️ Et ce que le tableau ne montre pas : le serverless")
    print("   facture la duree d'execution, donc un code lent coute")
    print("   proportionnellement plus cher — la performance devient une")
    print("   ligne de facture, pas seulement une qualite. Il impose aussi")
    print("   un demarrage a froid sur la premiere requete, et une duree")
    print("   d'execution maximale.")


def _le_point_de_bascule() -> None:
    print("\n\n2. LE POINT OU LE SERVERLESS CESSE D'ETRE ECONOMIQUE\n")
    machine = couts.cout_calcul("moyenne")
    print(f"   Une machine « moyenne » allumee en permanence : "
          f"{couts.euros(machine)} / mois\n")
    print(f"   {'APPELS / MOIS':>16} {'SERVERLESS':>14} {'VERDICT':>26}")
    for appels in (100_000, 1_000_000, 10_000_000, 50_000_000, 100_000_000):
        gio_secondes = appels * 0.4 * 0.512
        cout = (appels / 1e6 * tarifs.SERVERLESS["euros_par_million_d_appels"]
                + gio_secondes * tarifs.SERVERLESS["euros_par_gio_seconde"])
        verdict = ("serverless moins cher" if cout < machine
                   else "la machine devient moins chere")
        nombre = f"{appels:,}".replace(",", " ")
        print(f"   {nombre:>16} {couts.euros(cout):>14} {verdict:>30}")
    print("\n   Le serverless n'est pas « moins cher » : il est moins cher")
    print("   TANT QUE LA CHARGE EST INTERMITTENTE. Passe un certain")
    print("   volume, louer la machine en continu revient moins cher que")
    print("   payer chaque appel — et l'ecart se creuse ensuite.")
    print("\n   ⚠️ C'est exactement le genre de question posee a l'examen,")
    print("   et exactement le genre de reponse qu'on rate en repondant")
    print("   « serverless » par reflexe. La bonne reponse depend du")
    print("   profil de charge, qui est toujours donne dans l'enonce.")


def _les_trois_familles() -> None:
    print("\n\n3. TROIS FAMILLES DE STOCKAGE, JAMAIS INTERCHANGEABLES\n")
    familles = [
        ("objet", "une cle → un fichier entier", "images, sauvegardes, archives",
         "ne se monte PAS comme un disque ; pas de modification partielle"),
        ("bloc", "un disque brut attache a UNE machine",
         "systeme, base de donnees",
         "une seule machine a la fois ; il suit la zone, pas la region"),
        ("fichier", "un partage reseau (NFS/SMB)",
         "plusieurs machines qui lisent les memes fichiers",
         "le plus cher au Gio, et la latence d'un reseau"),
    ]
    for nom, quoi, usage, limite in familles:
        print(f"   {nom.upper()}")
        print(f"      ce que c'est : {quoi}")
        print(f"      pour         : {usage}")
        print(f"      ⚠️ limite    : {limite}\n")
    print("   Se tromper de famille ne produit pas une erreur : cela")
    print("   produit une architecture qui marche mal et coute cher. Monter")
    print("   un stockage objet en pseudo-disque avec un pilote de")
    print("   compatibilite en est l'exemple le plus courant — chaque")
    print("   ecriture devient une requete HTTP, et les performances s'en")
    print("   ressentent.")


def _le_cycle_de_vie() -> None:
    print("\n\n4. LA MESURE DU CHAPITRE : LA DONNEE REFROIDIT\n")
    gio = 4000
    mois = 36
    sans = couts.cout_sur_la_duree(gio, mois)
    regles = [couts.Regle(30, "acces-rare"), couts.Regle(90, "archive"),
              couts.Regle(365, "archive-profonde")]
    avec = couts.cout_sur_la_duree(gio, mois, regles)

    volume = f"{gio:,}".replace(",", " ")
    print(f"   {volume} Gio de journaux et de CV, conserves {mois} mois :\n")
    print(f"      sans regle de cycle de vie  {couts.euros(sans):>12}")
    print(f"      avec cycle de vie           {couts.euros(avec):>12}")
    print(f"      economie                    {couts.euros(sans - avec):>12}"
          f"   ({(1 - avec / sans) * 100:.0f} %)\n")
    print("   Les regles appliquees :\n")
    for regle in regles:
        prix = tarifs.PALIERS_STOCKAGE[regle.palier]["stockage"]
        print(f"      apres {regle.jours:>3} jours → {regle.palier:<18} "
              f"{prix:.4f} € / Gio / mois")
    print(f"      (au depart      → {'standard':<18} "
          f"{tarifs.PALIERS_STOCKAGE['standard']['stockage']:.4f} € / Gio / mois)")
    print("\n   Aucune intervention humaine, aucune modification de code :")
    print("   c'est une regle posee une fois sur le bucket. C'est le")
    print("   premier levier d'economie du stockage, et le plus oublie.")


def _le_piege_du_froid() -> None:
    print("\n\n5. ET LE PIEGE QUE LE TABLEAU PRECEDENT CACHE\n")
    gio = 4000
    volume = f"{gio:,}".replace(",", " ")
    print(f"   Descendre {volume} Gio au froid fait economiser. Mais les")
    print("   paliers froids facturent AUSSI la restitution :\n")
    print(f"   {'PALIER':<20} {'STOCKAGE / MOIS':>18} {'RESTITUER TOUT':>18} "
          f"{'DUREE MIN.':>12}")
    for palier, prix in tarifs.PALIERS_STOCKAGE.items():
        print(f"   {palier:<20} "
              f"{couts.euros(couts.cout_stockage(gio, palier)):>18} "
              f"{couts.euros(couts.cout_restitution(gio, palier)):>18} "
              f"{prix['jours_minimum']:>9} j")
    mensuel_archive = couts.cout_stockage(gio, "archive")
    mensuel_standard = couts.cout_stockage(gio, "standard")
    restitution = couts.cout_restitution(gio, "archive")
    economie_mensuelle = mensuel_standard - mensuel_archive
    print(f"\n   Une seule restitution complete depuis l'archive coute "
          f"{couts.euros(restitution)}.")
    print(f"   L'economie mensuelle apportee par l'archive est de "
          f"{couts.euros(economie_mensuelle)}.")
    print(f"   Il faut donc {restitution / economie_mensuelle:.1f} mois sans "
          f"aucune relecture pour que la")
    print("   descente au froid soit rentable — et une seule relecture")
    print("   remet le compteur a zero.")
    print("\n   ⚠️ Et la duree minimale de conservation est une vraie")
    print("   facture : supprimer un objet avant le delai du palier le")
    print("   facture quand meme jusqu'a ce delai. Un cycle de vie trop")
    print("   agressif sur des donnees a courte vie coute donc plus cher")
    print("   que pas de cycle de vie du tout.")
    print("\n   La regle pratique : faire descendre ce qui VIEILLIT, jamais")
    print("   ce qui est simplement gros.")
    print()


if __name__ == "__main__":
    main()
