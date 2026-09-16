"""Chapitre 1 — Declarer, pas ordonner.

    uv run python chapitres/chapitre_1_declaratif.py

« Terraform compare ce que vous decrivez a ce qui existe reellement, puis
calcule le chemin le plus court pour aligner les deux. » Ce chapitre fait
tourner ce calcul — celui de `jobportal/plan.py` — sur les vrais fichiers
`.tf` du dossier `infra/`, et imprime le plan a chaque etape.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                      # noqa: E402
from jobportal.plan import rendre                  # noqa: E402
from jobportal.terraform import Terraform          # noqa: E402

INFRA = Path(__file__).resolve().parent.parent / "infra"


def main() -> None:
    console.utf8()
    travail = Path(tempfile.mkdtemp(prefix="tf-chapitre1-"))
    tf = Terraform(INFRA, etat=travail / "terraform.tfstate",
                   realite=travail / "realite.json")
    try:
        _le_premier_plan(tf)
        _appliquer_puis_replanifier(tf)
        _modifier_en_place(tf)
        _ce_qui_force_un_remplacement(tf)
        _lordre_des_lignes(tf)
    finally:
        shutil.rmtree(travail, ignore_errors=True)


def _le_premier_plan(tf: Terraform) -> None:
    print("1. LE PREMIER PLAN : QUE DES CREATIONS\n")
    plan = tf.plan()
    for ligne in rendre(plan):
        print(f"   {ligne}")
    print("\n   Rien n'existe encore, donc tout est a creer. Le signe `+`")
    print("   annonce une creation, `~` une modification, `-` une")
    print("   destruction, et `-/+` une destruction SUIVIE d'une creation.")
    print("\n   Remarquez ce que le plan n'est pas : ce n'est pas une suite")
    print("   d'ordres que vous auriez ecrite. Le fichier `infra/main.tf`")
    print("   declare UNE ressource avec un `for_each` ; le moteur en a")
    print("   deduit trois instances, une par environnement. Vous avez")
    print("   decrit un ETAT, il a calcule les OPERATIONS.")


def _appliquer_puis_replanifier(tf: Terraform) -> None:
    print("\n\n2. APPLIQUER, PUIS REPLANIFIER : L'IDEMPOTENCE\n")
    applique = tf.apply()
    print(f"   apply  →  {applique.resume}")
    ensuite = tf.plan()
    print(f"   plan   →  {ensuite.resume}")
    print("\n   Le second plan est VIDE. C'est la propriete qui distingue un")
    print("   outil declaratif d'un script : lancer deux fois un script de")
    print("   creation cree deux fois ; lancer deux fois un `apply` ne")
    print("   change rien la seconde fois.")
    print("\n   Ce qui rend cela possible est l'ETAT — le fichier")
    print("   `terraform.tfstate`, qui retient quelle ressource du code")
    print("   correspond a quel objet reel. Le chapitre 3 l'ouvre.")
    print("\n   Ce que la realite contient maintenant :")
    for identifiant, objet in sorted(tf.realite().tout().items()):
        print(f"      {identifiant:<28} image={objet.get('image')}")


def _modifier_en_place(tf: Terraform) -> None:
    print("\n\n3. UNE MODIFICATION EN PLACE\n")
    plan = tf.plan({"version_image": "1.5.0"})
    for ligne in rendre(plan):
        print(f"   {ligne}")
    print("\n   Changer l'image ne detruit rien : le moteur sait que cet")
    print("   attribut se modifie sur une ressource existante. Trois")
    print("   modifications, zero destruction.")
    tf.apply({"version_image": "1.5.0"})


def _ce_qui_force_un_remplacement(tf: Terraform) -> None:
    print("\n\n4. CE QUI FORCE UN REMPLACEMENT\n")
    plan = tf.plan({"version_image": "1.5.0", "prefixe": "portail"})
    for ligne in rendre(plan):
        print(f"   {ligne}")
    print("\n   Changer le PREFIXE change le `nom` de chaque conteneur, et")
    print("   le nom ne se modifie pas : il se remplace. Trois `-/+` —")
    print("   trois destructions suivies de trois creations, sur les memes")
    print("   adresses.")
    print("\n   Le meme fichier, un seul caractere de difference, et un plan")
    print("   qui passe de « 3 modifications » a « 3 remplacements ».")
    print("\n   ⚠️ C'est LA raison de lire un plan avant d'appliquer. Une")
    print("   modification d'apparence anodine — un nom, une zone, un type")
    print("   d'instance — peut detruire et recreer, avec la coupure de")
    print("   service que cela suppose. Le plan le dit AVANT ; sans lui, on")
    print("   l'apprend pendant.")
    print("\n   Le provider de ce projet declare quels attributs forcent un")
    print("   remplacement (`jobportal/fournisseur.py`, champ")
    print("   `forcent_un_remplacement`). Un vrai provider fait la meme")
    print("   chose, et c'est sa documentation qui vous le dit : cherchez")
    print("   « forces new resource ».")


def _lordre_des_lignes(tf: Terraform) -> None:
    print("\n\n5. L'ORDRE DES LIGNES NE COMPTE PAS\n")
    configuration = tf.configuration()
    print("   Les fichiers lus, dans l'ordre alphabetique :")
    for fichier in sorted(INFRA.glob("*.tf")):
        print(f"      {fichier.name}")
    print("\n   Les instances voulues, telles que le moteur les a deduites :")
    for instance in configuration.instances:
        print(f"      {instance.adresse_complete:<28} "
              f"nom={instance.attributs.get('nom')}")
    print("\n   `variables.tf` est lu APRES `main.tf`, et pourtant `main.tf`")
    print("   utilise ses variables. Aucun ordre n'est a respecter : le")
    print("   moteur resout les references, pas les lignes.")
    print("\n   C'est ce qui permet a une ressource d'en citer une autre")
    print("   declaree plus bas, et c'est aussi ce qui rend l'ordre")
    print("   d'execution IMPREVISIBLE quand on n'a pas declare de")
    print("   dependance. Terraform construit un graphe ; ce projet fait")
    print("   plus simple, mais la lecon est la meme.")
    print("\n\n   Le chapitre suivant mesure ce que `for_each` fait que")
    print("   `count` ne fait pas — et ce que cela detruit.")


if __name__ == "__main__":
    main()
