"""Chapitre 5 — Couts et gouvernance.

    uv run python chapitres/chapitre_5_couts.py

La facture cloud est un compteur qui ne s'arrete jamais. Ce chapitre la
decompose ligne par ligne, et chiffre chacun des leviers.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                       # noqa: E402
from jobportal import couts, tarifs                 # noqa: E402


def facture_du_portail() -> couts.Facture:
    """La facture d'un mois ordinaire — avec ce qu'elle contient d'inutile."""
    return couts.Facture([
        couts.Ressource("prod-web-1", "moyenne", "production",
                        etiquettes={"projet": "jobportal", "equipe": "web",
                                    "environnement": "production"}),
        couts.Ressource("prod-web-2", "moyenne", "production",
                        etiquettes={"projet": "jobportal", "equipe": "web",
                                    "environnement": "production"}),
        couts.Ressource("prod-base", "grande", "production",
                        etiquettes={"projet": "jobportal", "equipe": "web",
                                    "environnement": "production"}),
        couts.Ressource("recette-web", "moyenne", "recette",
                        etiquettes={"projet": "jobportal", "equipe": "web",
                                    "environnement": "recette"}),
        couts.Ressource("recette-base", "moyenne", "recette",
                        etiquettes={"projet": "jobportal", "equipe": "web",
                                    "environnement": "recette"}),
        # ⚠️ Les quatre lignes qui suivent sont la vraie facture d'un mois
        # ordinaire : personne ne sait plus a qui elles appartiennent.
        couts.Ressource("demo-salon-mars", "grande", "?",
                        etiquettes={}, utilisee=False),
        couts.Ressource("essai-migration", "tres-grande", "?",
                        etiquettes={"projet": "jobportal"}, utilisee=False),
        couts.Ressource("analyse-ponctuelle", "memoire", "?",
                        etiquettes={}, utilisee=False),
        couts.Ressource("prod-batch", "grande", "production",
                        etiquettes={"projet": "jobportal", "equipe": "data",
                                    "environnement": "production"}),
    ])


def main() -> None:
    console.utf8()
    facture = facture_du_portail()
    _le_compteur(facture)
    _les_etiquettes(facture)
    _eteindre(facture)
    _ajuster()
    _les_engagements()
    _le_reseau()


def _le_compteur(facture: couts.Facture) -> None:
    print("1. UN COMPTEUR QUI NE S'ARRETE JAMAIS\n")
    print(f"   {'RESSOURCE':<22} {'GABARIT':<14} {'ENV.':<12} "
          f"{'PAR MOIS':>10}  ETIQUETEE")
    for ressource in facture.ressources:
        marque = "oui" if ressource.etiquetee else "⚠️ NON"
        vie = "" if ressource.utilisee else "   (personne ne l'utilise)"
        print(f"   {ressource.nom:<22} {ressource.gabarit:<14} "
              f"{ressource.environnement:<12} "
              f"{couts.euros(ressource.cout):>10}  {marque}{vie}")
    print(f"\n   {'TOTAL':<22} {'':<14} {'':<12} "
          f"{couts.euros(facture.total):>10}")
    print(f"   {'dont inutilise':<22} {'':<14} {'':<12} "
          f"{couts.euros(facture.gaspillage):>10}   "
          f"({facture.gaspillage / facture.total * 100:.0f} % de la facture)")
    print("\n   Aucune de ces trois ressources n'a plante, n'a alerte, n'a")
    print("   rien signale. Elles tournent, elles sont facturees, et")
    print("   personne ne se souvient de les avoir creees. C'est la derive")
    print("   ordinaire — pas un pic, une lente sedimentation.")
    print("\n   ⚠️ La premiere regle du FinOps n'est pas technique : celui")
    print("   qui deploie une ressource est responsable de son cout. Sans")
    print("   ce principe, aucun tableau de bord ne sert a rien.")


def _les_etiquettes(facture: couts.Facture) -> None:
    print("\n\n2. SANS ETIQUETTES, LA FACTURE EST AVEUGLE\n")
    for cle in ("environnement", "equipe"):
        print(f"   Repartition par « {cle} » :")
        for valeur, montant in facture.par_etiquette(cle).items():
            part = montant / facture.total * 100
            marque = "  ⚠️" if valeur == "(non etiquete)" else ""
            print(f"      {valeur:<24} {couts.euros(montant):>10}  "
                  f"{part:>5.1f} %{marque}")
        print()
    print(f"   Part de la facture qu'aucun tableau de bord ne peut")
    print(f"   attribuer : {facture.part_non_etiquetee * 100:.0f} %\n")
    print("   Un total mensuel n'apprend rien. « Qui depense quoi » est la")
    print("   seule question qui declenche une action — et elle demande")
    print("   trois etiquettes : projet, equipe, environnement.")
    print("\n   ⚠️ L'etiquetage se pose a la CREATION, jamais apres. Une")
    print("   politique qui refuse la creation d'une ressource sans")
    print("   etiquettes coute cinq minutes a mettre en place et evite")
    print("   l'archeologie de fin de trimestre. C'est exactement le genre")
    print("   de garde-fou qui vit dans le code d'infrastructure.")


def _eteindre(facture: couts.Facture) -> None:
    print("\n\n3. LA MESURE QUI TRANCHE : ETEINDRE LE SOIR\n")
    print(f"   Heures facturees par mois, en permanence : "
          f"{couts.HEURES_PAR_MOIS:.0f} h")
    print(f"   Heures ouvrees (8 h x 5 j)               : "
          f"{couts.HEURES_OUVREES_PAR_MOIS:.0f} h")
    print(f"   Facteur                                  : "
          f"x{couts.FACTEUR_ALLUME_EN_PERMANENCE:.2f}\n")
    print("   Ce facteur ne depend d'AUCUN prix : c'est un rapport")
    print("   d'heures. Il vaut la meme chose chez tous les fournisseurs,")
    print("   et il ne bougera pas avec la prochaine grille tarifaire.\n")

    recette = [r for r in facture.ressources if r.environnement == "recette"]
    total = sum(r.cout for r in recette)
    economie = sum(couts.eteindre_la_nuit(r) for r in recette)
    print(f"   {'RESSOURCE':<22} {'24 / 7':>12} {'HEURES OUVREES':>16} "
          f"{'ECONOMIE':>12}")
    for ressource in recette:
        eteinte = couts.cout_calcul(ressource.gabarit,
                                    couts.HEURES_OUVREES_PAR_MOIS)
        print(f"   {ressource.nom:<22} {couts.euros(ressource.cout):>12} "
              f"{couts.euros(eteinte):>16} "
              f"{couts.euros(couts.eteindre_la_nuit(ressource)):>12}")
    print(f"\n   Sur l'environnement de recette seul : "
          f"{couts.euros(economie)} par mois,")
    print(f"   soit {couts.euros(economie * 12)} par an, pour un arret")
    print("   programme et une ligne de planification.")
    print("\n   ⚠️ Et c'est le levier le plus simple de tous : il ne demande")
    print("   ni refonte, ni negociation, ni engagement. Il demande")
    print("   seulement que l'environnement supporte d'etre eteint — ce")
    print("   qui est une bonne chose a verifier de toute facon.")


def _ajuster() -> None:
    print("\n\n4. LE RIGHT-SIZING : ON PAIE LA TAILLE, PAS L'USAGE\n")
    observations = [
        couts.Observation("tres-grande", cpu_moyen=0.05, cpu_pointe=0.11,
                          memoire_moyenne=0.10),
        couts.Observation("grande", cpu_moyen=0.30, cpu_pointe=0.55,
                          memoire_moyenne=0.40),
        couts.Observation("moyenne", cpu_moyen=0.62, cpu_pointe=0.88,
                          memoire_moyenne=0.70),
    ]
    for marge in (2.0, 1.3):
        print(f"   ── marge de securite sur la pointe : x{marge:g}\n")
        print(f"      {'ACTUEL':<14} {'CPU MOY.':>9} {'POINTE':>8} "
              f"{'PROPOSE':<14} {'ECART / MOIS':>14}")
        for observation in observations:
            cible, gain = couts.economie(observation, marge)
            propose = cible if cible != observation.gabarit else "— (juste)"
            print(f"      {observation.gabarit:<14} "
                  f"{observation.cpu_moyen * 100:>8.0f} % "
                  f"{observation.cpu_pointe * 100:>7.0f} % "
                  f"{propose:<14} {couts.euros(gain):>14}")
        print()

    print("   Trois choses, dans ce tableau :\n")
    print("      • la premiere machine est trop grande dans les deux cas :")
    print("        une pointe a 11 % ne justifie aucun des deux gabarits")
    print("        au-dessus. C'est le cas d'ecole du right-sizing ;")
    print("      • les deux autres CHANGENT DE VERDICT selon la marge. Le")
    print("        right-sizing ne descend pas toujours : une pointe a")
    print("        55 % avec une marge de 2 ne tient pas dans le gabarit")
    print("        actuel, et l'outil propose de grandir ;")
    print("      • la marge est donc une DECISION, pas un detail")
    print("        d'implantation. Elle doit etre ecrite quelque part, et")
    print("        assumee — x2 pour un service dont la charge double d'un")
    print("        jour a l'autre, x1,3 pour un traitement par lots dont")
    print("        on connait le profil.\n")
    print("   ⚠️ Et l'on dimensionne sur la POINTE, jamais sur la moyenne.")
    print("   Une machine taillee pour sa moyenne tombe a chaque pic — et")
    print("   la moyenne de la premiere ligne (5 %) ferait proposer un")
    print("   gabarit que la pointe mettrait a genoux.")


def _les_engagements() -> None:
    print("\n\n5. LES ENGAGEMENTS : UNE DECISION FINANCIERE\n")
    reference = couts.cout_calcul("grande")
    print(f"   {'ENGAGEMENT':<16} {'PAR MOIS':>12} {'PART':>7} "
          f"{'SUR 3 ANS':>14}  CE QU'ON ACCEPTE")
    engagements = [
        ("a la demande", "rien"),
        ("reserve 1 an", "un an de facture, meme si le service change"),
        ("reserve 3 ans", "trois ans — une eternite en informatique"),
        ("spot", "⚠️ une interruption a deux minutes de preavis"),
    ]
    for nom, contrepartie in engagements:
        mensuel = couts.cout_calcul("grande", engagement=nom)
        part = tarifs.ENGAGEMENTS[nom]
        print(f"   {nom:<16} {couts.euros(mensuel):>12} {part * 100:>6.0f} % "
              f"{couts.euros(mensuel * 36):>14}  {contrepartie}")
    print("\n   Un engagement de trois ans divise la facture par")
    facteur = f"{1 / tarifs.ENGAGEMENTS['reserve 3 ans']:.1f}".replace('.', ',')
    print(f"   {facteur}. On ne reserve donc que ce dont on est SUR qu'il")
    print("   tournera encore dans trois ans — le socle, jamais la pointe.")
    print("\n   ⚠️ Le spot est le plus mal utilise des quatre. Il ne convient")
    print("   qu'aux charges INTERRUPTIBLES : traitements par lots,")
    print("   compilation, encodage, entrainement avec points de reprise.")
    print("   Le mettre sous une API en production revient a accepter une")
    print("   coupure aleatoire pour economiser 72 % d'une ligne de")
    print("   facture qui n'est pas la plus grosse.")
    print("\n   L'ordre a suivre est toujours le meme : d'abord ETEINDRE ce")
    print("   qui ne sert pas, puis AJUSTER ce qui reste, et seulement")
    print("   ensuite ENGAGER. Reserver trois ans une machine trois tailles")
    print("   trop grande fige l'erreur pour trois ans.")


def _le_reseau() -> None:
    print("\n\n6. LA LIGNE QU'ON DECOUVRE SUR LA FACTURE : LE RESEAU\n")
    print(f"   {'SENS':<28} {'€ / Gio':>9} {'POUR 2 000 Gio':>16}")
    for sens, prix in tarifs.RESEAU.items():
        print(f"   {sens:<28} {prix:>9.3f} "
              f"{couts.euros(couts.cout_reseau(2000, sens)):>16}")
    print("\n   L'ENTREE est gratuite, la SORTIE ne l'est pas. C'est le")
    print("   modele de tous les fournisseurs, et c'est ce qui rend une")
    print("   migration vers un autre cloud si couteuse : faire entrer ses")
    print("   donnees ne coute rien, les faire sortir se paie au Gio.")
    print("\n   ⚠️ Et le trafic entre deux zones est facture DES DEUX")
    print("   COTES.")
    for zones in (1, 2, 3):
        print(f"      500 Gio ecrits, repliques sur {zones} zone(s) → "
              f"{couts.euros(couts.cout_replication(500, zones))} / mois")
    print("\n   Cette ligne n'apparait sur aucun tableau de bord")
    print("   applicatif : elle est produite par la REPLICATION, pas par")
    print("   les utilisateurs. C'est aussi pourquoi on garde une")
    print("   application et sa base dans la MEME zone quand on le peut —")
    print("   le trafic y est gratuit, et la latence plus basse.")
    print("\n   Les trois garde-fous a poser le premier jour :")
    print("      • un budget avec alerte a 50 % et 90 %, pas a 100 % ;")
    print("      • des quotas qui interdisent les tres gros gabarits ;")
    print("      • une politique qui refuse toute ressource sans etiquettes.")
    print("   Les trois vivent dans le code d'infrastructure, se relisent")
    print("   en revue, et coutent moins d'une heure a mettre en place.")
    print()


if __name__ == "__main__":
    main()
