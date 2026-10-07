"""Chapitre 1 — Les fondamentaux du cloud.

    uv run python chapitres/chapitre_1_fondamentaux.py

Deux calculs, et ils rangent le reste du cours : ce dont vous repondez
selon le modele de service, et ce que vaut vraiment une chaine de SLA.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                       # noqa: E402
from jobportal import couts, disponibilite, responsabilite   # noqa: E402


def main() -> None:
    console.utf8()
    _la_responsabilite()
    _les_neuf()
    _la_chaine()
    _les_zones()
    _le_sla_nest_pas_une_garantie()


def _la_responsabilite() -> None:
    print("1. LE MODELE DE RESPONSABILITE PARTAGEE, COUCHE PAR COUCHE\n")
    for ligne in responsabilite.rendre():
        print(f"   {ligne}")
    compte = responsabilite.compter()
    print(f"\n   De {compte['sur site']} couches a {compte['SaaS']} : voila ce")
    print("   que « deleguer » veut dire, chiffre. IaaS, PaaS et SaaS ne")
    print("   sont pas un classement du meilleur au pire — c'est un curseur")
    print("   entre le controle et la tranquillite, et on le place par")
    print("   service, pas une fois pour toute l'entreprise.")

    toujours = responsabilite.toujours_a_vous()
    print(f"\n   ⚠️ ET LES {len(toujours)} LIGNES QUI NE BOUGENT JAMAIS :\n")
    for couche in toujours:
        print(f"      • {couche.nom}")
    print("\n   Aucun modele ne vous en decharge. Pas meme le SaaS. C'est")
    print("   pour cela que l'immense majorite des fuites de donnees")
    print("   rendues publiques sont des fautes de CONFIGURATION — un")
    print("   stockage laisse ouvert, une cle d'acces dans un depot — et")
    print("   presque jamais une faille de l'hyperviseur.")
    print("\n   La question a poser devant un service manage n'est donc pas")
    print("   « est-ce securise ? » mais « qu'est-ce qui reste a ma")
    print("   charge, et l'ai-je fait ? »")


def _les_neuf() -> None:
    print("\n\n2. « TROIS NEUF », EN HEURES\n")
    print(f"   {'ENGAGEMENT':<12} {'DISPONIBILITE':>14} {'PANNE PAR AN':>20} "
          f"{'PAR MOIS':>16}")
    for nombre in (2, 3, 4, 5):
        valeur = disponibilite.neuf(nombre)
        print(f"   {nombre} neuf{'s' if nombre > 1 else ' ':<7} "
              f"{disponibilite.pourcent(valeur):>14} "
              f"{disponibilite.duree(disponibilite.panne_par_an(valeur)):>20} "
              f"{disponibilite.duree(disponibilite.panne_par_mois(valeur)):>16}")
    print("\n   Un neuf de plus divise la panne par dix, et multiplie le")
    print("   cout bien davantage : chaque neuf supplementaire demande une")
    print("   redondance de plus, et souvent une region de plus.")
    print("\n   ⚠️ Le piege est de lire « 99,9 % » comme « presque")
    print("   parfait ». C'est presque neuf heures d'indisponibilite par")
    print("   an — et elles ne tombent jamais un dimanche a 4 h.")


def _la_chaine() -> None:
    print("\n\n3. LA MESURE QUI TRANCHE : LES SLA SE MULTIPLIENT\n")
    trois = disponibilite.Chaine("trois services a 99,9 %", [
        disponibilite.Composant(f"service {i}", 0.999) for i in (1, 2, 3)])
    seul = 0.999
    print(f"   un seul service a 99,9 %       → "
          f"{disponibilite.pourcent(seul)}  "
          f"{disponibilite.duree(disponibilite.panne_par_an(seul))} par an")
    print(f"   trois en serie, chacun a 99,9 % → "
          f"{disponibilite.pourcent(trois.disponibilite)}  "
          f"{disponibilite.duree(disponibilite.panne_par_an(trois.disponibilite))}"
          f" par an\n")
    print("   Une requete qui traverse trois services a besoin des TROIS.")
    print("   Les disponibilites se multiplient donc, et le resultat est")
    print("   toujours PIRE que le maillon le plus faible.\n")

    portail = disponibilite.Chaine("le portail de l'emploi", [
        disponibilite.Composant("repartiteur de charge", 0.9999),
        disponibilite.Composant("service web", 0.999, repliques=2),
        disponibilite.Composant("base managee", 0.9995),
        disponibilite.Composant("API de paiement", 0.999),
    ])
    print("   Le portail, composant par composant :\n")
    for ligne in disponibilite.rendre(portail):
        print(f"      {ligne}")
    faible = portail.maillon_faible
    print(f"\n   Maillon le plus faible : {faible.nom} "
          f"({disponibilite.pourcent(faible.effective)})")
    print("\n   Deux lecons dans ce tableau :\n")
    print("      • DOUBLER un composant fait s'effondrer sa panne : le")
    print("        service web passe de 8 h 46 min a 32 s par an. Ce sont")
    print("        les INDISPONIBILITES qui se multiplient, pas les")
    print("        disponibilites ;")
    print("      • et le total reste plombe par ce qu'on ne controle pas.")
    print("        L'API de paiement d'un tiers fixe le plafond ; ajouter")
    print("        une troisieme replique du service web n'y changerait")
    print("        rien.")
    print("\n   ⚠️ Ce calcul suppose des pannes INDEPENDANTES. Elles ne le")
    print("   sont pas : deux repliques partagent un plan de controle, une")
    print("   configuration et une equipe. Le chiffre obtenu est un")
    print("   PLAFOND theorique, jamais une promesse.")


def _les_zones() -> None:
    print("\n\n4. UNE ZONE EST UN BATIMENT, UNE REGION EST UNE VILLE\n")
    une = disponibilite.Chaine("une zone", [
        disponibilite.Composant("service", 0.995, repliques=1)])
    deux = disponibilite.Chaine("deux zones", [
        disponibilite.Composant("service", 0.995, repliques=2)])
    trois = disponibilite.Chaine("trois zones", [
        disponibilite.Composant("service", 0.995, repliques=3)])
    precedente = None
    for nom, chaine in (("1 zone", une), ("2 zones", deux), ("3 zones", trois)):
        valeur = chaine.disponibilite
        panne = disponibilite.panne_par_an(valeur)
        facteur = (f"   ÷ {precedente / panne:.0f}" if precedente else "")
        print(f"   {nom:<9} {disponibilite.pourcent(valeur, 6):>13}  "
              f"{disponibilite.duree(panne):>18} par an{facteur}")
        precedente = panne
    print("\n   Chaque zone supplementaire divise la panne par le meme")
    print("   facteur — mais pas avec les memes consequences. La deuxieme")
    print("   fait passer de presque deux jours a un quart d'heure : elle")
    print("   n'est pas negociable. La troisieme fait passer d'un quart")
    print("   d'heure a quelques secondes, et double encore la facture de")
    print("   replication. C'est la que s'arrete la plupart des")
    print("   architectures, et c'est un choix raisonnable.")
    print("\n   ⚠️ Et le cout de ce trafic n'est pas nul : le transfert")
    print("   entre deux zones est facture A L'EMISSION ET A LA RECEPTION.")
    print(f"      500 Gio ecrits, repliques sur 3 zones → "
          f"{couts.euros(couts.cout_replication(500, 3))} par mois")
    print("   Le chapitre 5 revient sur cette ligne de facture, qui")
    print("   n'apparait sur aucun tableau de bord applicatif.")


def _le_sla_nest_pas_une_garantie() -> None:
    print("\n\n5. UN SLA N'EST PAS UNE GARANTIE, C'EST UN BAREME DE REMISE\n")
    incident = disponibilite.Incident(minutes=240, facture_mensuelle=4200,
                                      chiffre_daffaires_par_heure=9000)
    part, palier = disponibilite.remise(incident.disponibilite_du_mois)
    print(f"   Une panne de {incident.minutes:.0f} minutes dans le mois :\n")
    print(f"      disponibilite du mois  "
          f"{disponibilite.pourcent(incident.disponibilite_du_mois)}"
          f"   ({palier})")
    print(f"      remise contractuelle   {part * 100:.0f} % de la facture "
          f"= {couts.euros(incident.remise)}")
    print(f"      chiffre d'affaires perdu               "
          f"= {couts.euros(incident.perte)}")
    print(f"      reste a votre charge                   "
          f"= {couts.euros(incident.reste_a_charge)}\n")
    print("   Le fournisseur rend un pourcentage de ce que VOUS lui avez")
    print("   paye. Il ne rend pas ce que vous avez perdu — et c'est ecrit")
    print("   noir sur blanc dans le contrat que personne ne lit.")
    print("\n   ⚠️ Consequence pratique : la disponibilite ne s'achete pas,")
    print("   elle se CONSTRUIT. Choisir un fournisseur a 99,99 % ne vous")
    print("   donne pas 99,99 % — le calcul de la section 3 s'applique a")
    print("   votre architecture, pas a sa brochure.")
    print("\n   Et il faut demander, pour chaque SLA : sur quoi porte-t-il")
    print("   exactement ? Beaucoup couvrent la disponibilite de l'API de")
    print("   gestion, pas celle de votre charge de travail ; presque")
    print("   aucun ne couvre la PERTE DE DONNEES, qui se traite par des")
    print("   sauvegardes testees, jamais par un contrat.")
    print()


if __name__ == "__main__":
    main()
