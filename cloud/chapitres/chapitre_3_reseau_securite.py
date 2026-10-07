"""Chapitre 3 — Reseaux et securite.

    uv run python chapitres/chapitre_3_reseau_securite.py

Deux calculs, et ce sont ceux qu'on fait toujours trop tard : le decoupage
d'adresses, et ce qu'une politique IAM accorde VRAIMENT.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                       # noqa: E402
from jobportal import iam, reseau                   # noqa: E402

RACINE = Path(__file__).resolve().parent.parent
POLITIQUES = RACINE / "politiques"

CATALOGUE = [
    "s3:GetObject", "s3:ListBucket", "s3:PutObject", "s3:DeleteObject",
    "s3:DeleteBucket", "s3:PutBucketPolicy", "s3:PutBucketAcl",
    "iam:CreateUser", "iam:AttachUserPolicy", "ec2:RunInstances",
    "rds:DeleteDBInstance", "kms:Decrypt",
]


def main() -> None:
    console.utf8()
    _le_decoupage()
    _les_adresses_qui_manquent()
    _lecture_seule()
    _le_not_action()
    _la_condition_absente()
    _le_deny_qui_gagne()


def _le_decoupage() -> None:
    print("1. UN VPC SE DECOUPE UNE FOIS, ET POUR LONGTEMPS\n")
    plan = reseau.planifier("jobportal", "10.0.0.0/16", ["a", "b", "c"])
    for ligne in reseau.rendre(plan.vpc):
        print(f"   {ligne}")
    print(f"\n   Plages encore libres dans le VPC : {len(plan.laisses)}\n")
    print("   Les sous-reseaux PRIVES sont plus grands que les PUBLICS, et")
    print("   ce n'est pas un caprice : le public n'accueille qu'une")
    print("   passerelle et un repartiteur de charge ; le prive accueille")
    print("   toutes les charges de travail.")
    print("\n   ⚠️ Une base de donnees n'a JAMAIS d'adresse publique. La")
    print("   segmentation ne decore pas un schema : si le composant expose")
    print("   est compromis, elle empeche l'attaquant d'atteindre")
    print("   directement ce qui est derriere.")


def _les_adresses_qui_manquent() -> None:
    print("\n\n2. CINQ ADRESSES QUI DISPARAISSENT DANS CHAQUE SOUS-RESEAU\n")
    print(f"   {'PREFIXE':>8} {'ADRESSES':>10} {'UTILISABLES':>13} "
          f"{'PERDUES':>9}")
    for prefixe in (16, 20, 24, 26, 27, 28):
        sous = reseau.SousReseau("x", reseau.reseau(f"10.0.0.0/{prefixe}"))
        perdu = (sous.total - sous.utilisables) / sous.total * 100
        print(f"   {'/' + str(prefixe):>8} {sous.total:>10} "
              f"{sous.utilisables:>13} {perdu:>8.0f} %")
    print(f"\n   ({reseau.RESERVEES_PAR_SOUS_RESEAU} adresses par sous-reseau :")
    print("   l'adresse de reseau, la passerelle, le DNS, une reservee, et")
    print("   le broadcast.)\n")
    print("   ⚠️ Sur un /28, c'est 31 % des adresses. Le calcul mental")
    print("   « 16 adresses, ca suffira » donne 11 adresses reelles.\n")

    petit = reseau.SousReseau("prive-a", reseau.reseau("10.0.0.0/24"))
    for noeuds, pods in ((6, 30), (10, 30), (12, 30)):
        tient, besoin, dispo = reseau.tiendrait(petit, pods, noeuds)
        verdict = "tient" if tient else "⚠️ NE TIENT PAS"
        print(f"   un /24 pour {noeuds:>2} noeuds x {pods} pods : "
              f"{besoin:>4} adresses pour {dispo} → {verdict}")
    print("\n   Avec un reseau de pods qui pioche dans le VPC, un noeud")
    print("   consomme une adresse pour lui-meme PLUS une par pod. C'est le")
    print("   calcul qu'on ne fait jamais avant, et toujours apres — quand")
    print("   les nouveaux pods restent `Pending` sans message clair.")

    print("\n   Et le chevauchement, qui ne se repare pas :\n")
    for a, b in (("10.0.0.0/16", "10.0.128.0/17"),
                 ("10.0.0.0/16", "10.1.0.0/16"),
                 ("172.16.0.0/12", "172.20.0.0/16")):
        marque = "⚠️ se chevauchent" if reseau.chevauchent(a, b) else "disjoints"
        print(f"      {a:<16} et {b:<16} → {marque}")
    prod = reseau.Vpc("prod", reseau.reseau("10.0.0.0/16"))
    rachat = reseau.Vpc("rachat", reseau.reseau("10.0.0.0/16"))
    possible, raison = reseau.appairable(prod, rachat)
    print(f"\n   Appairer les deux VPC « 10.0.0.0/16 » : "
          f"{'oui' if possible else 'NON'}")
    print(f"      {raison}")
    print("\n   ⚠️ Tout le monde prend `10.0.0.0/16` par defaut. Le jour")
    print("   d'un rachat, d'une fusion ou d'une connexion a un")
    print("   partenaire, les deux reseaux ne peuvent pas se parler — et la")
    print("   seule sortie est de renumeroter un cote entier. C'est pour")
    print("   cela qu'on planifie l'adressage AVANT le premier deploiement.")


def _lecture_seule() -> None:
    print("\n\n3. LA MESURE QUI TRANCHE : CE QUE LA POLITIQUE ACCORDE\n")
    fautive = iam.charger_fichier(POLITIQUES / "lecture-seule.json")
    corrigee = iam.charger_fichier(POLITIQUES / "lecture-seule-corrigee.json")
    ressource = "arn:aws:s3:::cv-candidats/cv-001.pdf"

    for nom, politique in (("lecture-seule.json", fautive),
                           ("lecture-seule-corrigee.json", corrigee)):
        accordees = iam.actions_accordees(politique, CATALOGUE, ressource)
        print(f"   {nom}")
        print(f"      declarations : "
              f"{[d.identifiant for d in politique.declarations]}")
        print(f"      accorde {len(accordees)} action(s) sur {len(CATALOGUE)} :")
        for action in accordees:
            danger = " ⚠️" if action.startswith(("s3:Delete", "s3:Put")) else ""
            print(f"         {action}{danger}")
        print()

    print("   La politique s'appelle « lecture seule ». Elle accorde la")
    print("   suppression du bucket.")
    print("\n   La cause tient en une declaration ajoutee « pour debloquer")
    print("   un incident » et jamais retiree. Les declarations d'une")
    print("   politique ne se limitent pas les unes les autres : elles")
    print("   s'ADDITIONNENT. Seule une declaration `Deny` retranche.")
    print("\n   ⚠️ Et on ne le voit pas en LISANT. On le voit en ESSAYANT,")
    print("   action par action — ce que fait `iam.actions_accordees`, et")
    print("   ce que font les simulateurs de politique des fournisseurs.")
    print("   Une revue de politique qui se contente de lire le JSON ne")
    print("   sert a rien.")


def _le_not_action() -> None:
    print("\n\n4. `NotAction` EST UNE INVERSION, PAS UNE EXCLUSION\n")
    politique = iam.charger_fichier(POLITIQUES / "tout-sauf-iam.json")
    accordees = iam.actions_accordees(politique, CATALOGUE,
                                      "arn:aws:s3:::n-importe-quoi/objet")
    refusees = [a for a in CATALOGUE if a not in accordees]
    print(f"   « Tout sauf IAM » — ce qu'elle accorde : "
          f"{len(accordees)} sur {len(CATALOGUE)}")
    print(f"      refuse : {refusees}")
    print(f"      accorde : {accordees[:4]} …\n")
    print("   `NotAction: iam:*` ne veut pas dire « tout ce que j'ai")
    print("   autorise, sauf IAM ». Cela veut dire « absolument tout ce qui")
    print("   n'est pas IAM » — y compris les services qui n'existaient pas")
    print("   le jour ou la politique a ete ecrite, et qui seront couverts")
    print("   automatiquement.")
    print("\n   ⚠️ C'est une politique qu'on ne peut pas relire : son")
    print("   perimetre grandit tout seul. Elle a sa place dans un `Deny`")
    print("   (« refuser tout sauf depuis cette region »), presque jamais")
    print("   dans un `Allow`.")


def _la_condition_absente() -> None:
    print("\n\n5. LE TROU QUI NE SE VOIT PAS : UNE CLE ABSENTE\n")
    fautive = iam.charger_fichier(POLITIQUES / "sans-mfa.json")
    corrigee = iam.charger_fichier(POLITIQUES / "sans-mfa-corrigee.json")
    ressource = "arn:aws:s3:::cv-candidats/cv-001.pdf"

    cas = [
        ("appel avec MFA", {"aws:MultiFactorAuthPresent": True}),
        ("appel sans MFA declare", {"aws:MultiFactorAuthPresent": False}),
        ("appel qui n'annonce RIEN", {}),
    ]
    print(f"   {'CAS':<28} {'Bool':>26} {'BoolIfExists':>26}")
    for libelle, contexte in cas:
        demande = iam.Demande("s3:PutObject", ressource, contexte)
        gauche = iam.evaluer(fautive, demande).resultat
        droite = iam.evaluer(corrigee, demande).resultat
        print(f"   {libelle:<28} {gauche:>26} {droite:>26}")

    print("\n   La troisieme ligne est le trou. Une condition dont la CLE")
    print("   EST ABSENTE du contexte ne correspond pas — donc la")
    print("   declaration `Deny` ne s'applique pas — donc l'`Allow` passe.")
    print("\n   Le raisonnement du moteur, sur ce cas precis :\n")
    demande = iam.Demande("s3:PutObject", ressource, {})
    for ligne in iam.expliquer(iam.evaluer(fautive, demande), demande):
        print(f"      {ligne}")
    print("\n   ⚠️ `BoolIfExists` corrige exactement cela : la condition est")
    print("   satisfaite quand la cle est absente, donc le refus")
    print("   s'applique. C'est la raison d'etre de toute la famille")
    print("   `...IfExists`, et la raison pour laquelle une politique de")
    print("   refus se TESTE — y compris sur les appels qui n'annoncent")
    print("   rien.")


def _le_deny_qui_gagne() -> None:
    print("\n\n6. UN `Deny` EXPLICITE NE SE RATTRAPE JAMAIS\n")
    developpeur = iam.charger_fichier(POLITIQUES / "developpeur.json")
    garde_fou = iam.charger_fichier(POLITIQUES / "garde-fou.json")
    administrateur = iam.charger({
        "Version": "2012-10-17",
        "Statement": [{"Sid": "Administrateur", "Effect": "Allow",
                       "Action": "*", "Resource": "*"}]}, "administrateur")

    essais = [
        ("developpeur", [developpeur], "s3:GetObject",
         "arn:aws:s3:::cv-candidats/cv-001.pdf"),
        ("developpeur", [developpeur], "s3:PutObject",
         "arn:aws:s3:::cv-candidats/cv-001.pdf"),
        ("developpeur", [developpeur], "s3:PutObject",
         "arn:aws:s3:::bac-a-sable/essai.txt"),
        ("developpeur", [developpeur], "rds:DeleteDBInstance",
         "arn:aws:rds:eu-west-3:1:db:jobportal-prod"),
        ("administrateur", [administrateur], "s3:DeleteObject",
         "arn:aws:s3:::journaux-audit/2026-09.log"),
        ("admin + garde-fou", [administrateur, garde_fou], "s3:DeleteObject",
         "arn:aws:s3:::journaux-audit/2026-09.log"),
        ("admin + garde-fou", [administrateur, garde_fou], "s3:DeleteObject",
         "arn:aws:s3:::cv-candidats/cv-001.pdf"),
    ]
    print(f"   {'IDENTITE':<20} {'ACTION':<22} {'RESSOURCE':<34} VERDICT")
    for identite, politiques, action, ressource in essais:
        verdict = iam.evaluer(politiques, iam.Demande(action, ressource))
        court = ressource.split(":::")[-1] if ":::" in ressource \
            else ressource.rsplit(":", 1)[-1]
        print(f"   {identite:<20} {action:<22} {court:<34} {verdict.resultat}")

    print("\n   Les deux dernieres lignes sont l'essentiel. Le meme")
    print("   administrateur, avec les memes droits, est refuse sur les")
    print("   journaux et autorise ailleurs — parce qu'une politique de")
    print("   garde-fou porte un `Deny` explicite sur ces ressources.")
    print("\n   L'ordre d'evaluation n'a que trois marches :")
    print("      1. un `Deny` qui correspond  → REFUS, sans appel ;")
    print("      2. sinon un `Allow`          → autorisation ;")
    print("      3. sinon                     → refus implicite.")
    print("\n   ⚠️ C'est ce qui rend les garde-fous d'organisation utiles :")
    print("   aucune politique locale, aucun ticket, aucun droit")
    print("   d'administration ne peut les contourner. C'est aussi ce qui")
    print("   les rend dangereux — un `Deny` trop large bloque des equipes")
    print("   entieres, et il faut souvent du temps pour comprendre")
    print("   d'ou vient le refus.")
    print()


if __name__ == "__main__":
    main()
