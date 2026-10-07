"""Chapitre 4 — Donnees et IA.

    uv run python chapitres/chapitre_4_donnees.py

« Manage » se chiffre en deux monnaies : des euros, et des couches de
responsabilite. Et faire tourner une analyse sur la base de production se
chiffre aussi — en disponibilite.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                                   # noqa: E402
from jobportal import couts, disponibilite, responsabilite, tarifs  # noqa: E402


def main() -> None:
    console.utf8()
    _manage_ou_pas()
    _ce_que_le_supplement_achete()
    _oltp_contre_olap()
    _lia_managee()


def _manage_ou_pas() -> None:
    print("1. « MANAGE » SE PAIE EN EUROS ET SE GAGNE EN COUCHES\n")
    nue = couts.cout_calcul("moyenne")
    managee = nue * tarifs.SUPPLEMENT_MANAGE
    avec_replica = managee * 2

    print(f"   {'OPTION':<48} {'PAR MOIS':>12}")
    print(f"   {'PostgreSQL installe sur une machine « moyenne »':<48} "
          f"{couts.euros(nue):>12}")
    print(f"   {'la meme base, managee, mono-zone':<48} "
          f"{couts.euros(managee):>12}")
    print(f"   {'managee avec replica de secours (2 zones)':<48} "
          f"{couts.euros(avec_replica):>12}")
    print(f"\n   Le supplement manage : x{tarifs.SUPPLEMENT_MANAGE:.2f}, "
          f"soit {couts.euros(managee - nue)} par mois.\n")

    heures = (managee - nue) / 55.0      # un taux horaire d'ingenierie
    print(f"   A 55 € de l'heure, ce supplement achete "
          f"{heures:.1f} heure d'ingenierie par")
    print("   mois. Sauvegardes, correctifs de securite, surveillance,")
    print("   bascule et restaurations testees prennent davantage — et")
    print("   c'est ce qui rend le calcul si souvent favorable au manage,")
    print("   meme quand le prix affiche fait tiquer.")
    print("\n   ⚠️ Le piege du calcul est de comparer le prix a zero. Le")
    print("   travail existe dans les deux cas : la seule difference est")
    print("   qui le fait, et a quelle heure de la nuit.")


def _ce_que_le_supplement_achete() -> None:
    print("\n\n2. CE QUE LE SUPPLEMENT DEPLACE, COUCHE PAR COUCHE\n")
    iaas = {c.nom for c in responsabilite.a_vous("IaaS")}
    paas = {c.nom for c in responsabilite.a_vous("PaaS")}
    deplacees = sorted(iaas - paas)
    print(f"   Sur une machine (IaaS), vous repondez de {len(iaas)} couches.")
    print(f"   Sur une base managee (PaaS), de {len(paas)}.\n")
    print("   Ce qui change de main :\n")
    for nom in deplacees:
        print(f"      • {nom}")
    print("\n   Ce qui NE change pas de main :\n")
    for couche in responsabilite.toujours_a_vous():
        print(f"      • {couche.nom}")
    print("\n   ⚠️ Une base managee ne sauvegarde pas vos donnees CONTRE")
    print("   VOUS. Une suppression applicative, une migration ratee ou un")
    print("   `DELETE` sans `WHERE` sont repliques fidelement sur le")
    print("   replica de secours, en quelques millisecondes.")
    print("\n   La restauration a un instant donne (`point-in-time`) couvre")
    print("   ce cas, et elle ne sert que si on l'a DEJA essayee. Une")
    print("   sauvegarde jamais restauree n'est pas une sauvegarde : c'est")
    print("   une intention.")


def _oltp_contre_olap() -> None:
    print("\n\n3. LA MESURE : UNE ANALYSE SUR LA PRODUCTION\n")
    print("   Les analystes veulent compter les candidatures par region sur")
    print("   trois ans. Trois endroits ou faire tourner la requete :\n")

    # ⚠️ ENTREES DECLAREES. Ces durees et ces effets sont des ordres de
    # grandeur d'une requete d'agregation sur 40 millions de lignes ; ils
    # ne sortent d'aucune mesure. Ce que le chapitre montre est leur
    # CONSEQUENCE sur la disponibilite, qui, elle, se calcule.
    scenarios = [
        ("sur la base de production", 0.985,
         "la base sert l'application ET l'analyse"),
        ("sur un replica de lecture", 0.9990,
         "la production est protegee, le moteur reste un OLTP"),
        ("dans un entrepot de donnees", 0.9995,
         "le bon moteur pour la bonne question"),
    ]
    print(f"   {'OU':<30} {'DISPO DU MOIS':>15} {'PANNE / MOIS':>18}")
    for nom, dispo, _ in scenarios:
        print(f"   {nom:<30} {disponibilite.pourcent(dispo, 3):>15} "
              f"{disponibilite.duree(disponibilite.panne_par_mois(dispo)):>18}")
    print()
    for nom, _, commentaire in scenarios:
        print(f"      {nom:<30} {commentaire}")

    ecart = (disponibilite.panne_par_mois(0.985)
             - disponibilite.panne_par_mois(0.9995))
    print(f"\n   L'ecart entre la premiere et la derniere ligne : "
          f"{disponibilite.duree(ecart)} de")
    print("   service degrade par mois, tous les mois, pour une requete que")
    print("   personne ne voit passer.")
    print("\n   (Ce que cette degradation coute depend de ce qu'elle")
    print("   bloque : une candidature perdue n'a pas le prix d'un")
    print("   paiement refuse. Ce projet ne le chiffre pas — il mesure le")
    print("   TEMPS, et laisse le prix a ceux qui le connaissent.)")
    print("\n   ⚠️ Un OLTP et un OLAP ne sont pas deux tailles du meme")
    print("   moteur : ce sont deux moteurs. L'un range les donnees par")
    print("   LIGNE pour ecrire vite une candidature ; l'autre par COLONNE")
    print("   pour lire vite trois ans de candidatures. Demander a l'un le")
    print("   travail de l'autre fonctionne — lentement, et en genant tout")
    print("   le monde.")
    print("\n   Entre les deux, un PIPELINE copie et transforme")
    print("   regulierement. Il introduit une latence — les analystes")
    print("   travaillent sur les donnees d'hier — et c'est presque")
    print("   toujours acceptable. Le demander explicitement evite la")
    print("   deuxieme erreur classique : construire un entrepot « temps")
    print("   reel » dont personne n'avait besoin.")


def _lia_managee() -> None:
    print("\n\n4. L'IA MANAGEE : ON NE PAIE PLUS DES MACHINES, MAIS DU VOLUME\n")
    # ⚠️ ENTREES DECLAREES, comme tout `tarifs.py` : ordres de grandeur.
    par_million_de_jetons_entree = 0.30
    par_million_de_jetons_sortie = 1.20
    jetons_par_cv = 1800
    jetons_de_reponse = 350

    print(f"   {'CV ANALYSES / MOIS':>20} {'JETONS':>14} {'COUT':>12}")
    for cv in (1_000, 10_000, 100_000, 1_000_000):
        entree = cv * jetons_par_cv
        sortie = cv * jetons_de_reponse
        cout = (entree / 1e6 * par_million_de_jetons_entree
                + sortie / 1e6 * par_million_de_jetons_sortie)
        nombre = f"{cv:,}".replace(",", " ")
        total = f"{(entree + sortie) / 1e6:.1f} M"
        print(f"   {nombre:>20} {total:>14} {couts.euros(cout):>12}")

    print("\n   Aucune machine, aucun GPU, aucune mise a l'echelle a")
    print("   regler : la facture suit le volume, lineairement, depuis le")
    print("   premier appel.")
    print("\n   ⚠️ Et c'est precisement ce qui la rend dangereuse. Une")
    print("   boucle de reessai qui part en vrille, un lot relance deux")
    print("   fois, un agent qui s'appelle lui-meme : la facture suit,")
    print("   toujours lineairement, sans plafond. Les garde-fous se")
    print("   posent AVANT — quota par cle, budget avec alerte, limite")
    print("   d'appels par minute.")
    print("\n   Trois questions a poser avant le premier appel, et qui ne")
    print("   sont pas techniques :")
    print("      • ou partent les donnees envoyees, et sous quelle")
    print("        juridiction ? Un CV est une donnee personnelle ;")
    print("      • sont-elles utilisees pour entrainer le modele ? La")
    print("        reponse depend du contrat, pas de l'API ;")
    print("      • que se passe-t-il quand le modele est retire ? Les")
    print("        fournisseurs deprecient leurs modeles, et la sortie")
    print("        d'un remplacant n'est jamais identique.")
    print()


if __name__ == "__main__":
    main()
