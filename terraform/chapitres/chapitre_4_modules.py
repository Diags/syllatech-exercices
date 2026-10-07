"""Chapitre 4 — Modules : l'infrastructure reutilisable.

    uv run python chapitres/chapitre_4_modules.py

« Un module = un dossier avec variables (entrees), ressources et outputs
(sorties). » Ce chapitre instancie DEUX fois le meme dossier, et montre ce
que cela produit : des adresses prefixees par `module.`, des ressources
independantes, et un contrat d'entrees-sorties qu'on peut lire.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                  # noqa: E402
from jobportal.plan import rendre              # noqa: E402
from jobportal.terraform import Terraform      # noqa: E402

RACINE = Path(__file__).resolve().parent.parent
APPELANT = RACINE / "infra-modules"
MODULE = RACINE / "infra" / "modules" / "reseau"


def main() -> None:
    console.utf8()
    travail = Path(tempfile.mkdtemp(prefix="tf-chapitre4-"))
    tf = Terraform(APPELANT, etat=travail / "terraform.tfstate",
                   realite=travail / "realite.json")
    try:
        _un_module_est_un_dossier()
        _deux_instances(tf)
        _le_contrat(tf)
        _ce_quun_module_ne_fait_pas(tf)
    finally:
        shutil.rmtree(travail, ignore_errors=True)


def _un_module_est_un_dossier() -> None:
    print("1. UN MODULE N'EST RIEN D'AUTRE QU'UN DOSSIER\n")
    print(f"   {MODULE.relative_to(RACINE).as_posix()} contient :")
    for fichier in sorted(MODULE.glob("*.tf")):
        lignes = fichier.read_text(encoding="utf-8").count("\n")
        print(f"      {fichier.name:<16} {lignes:>3} lignes")
    print("\n   Aucune syntaxe particuliere, aucune declaration « je suis un")
    print("   module » : des fichiers `.tf` ordinaires. Ce qui en fait un")
    print("   module, c'est qu'on l'APPELLE — par un bloc `module` et son")
    print("   attribut `source`.")
    print("\n   La convention en trois fichiers n'est pas obligatoire, et")
    print("   elle est universelle : `variables.tf` (ce qui entre),")
    print("   `main.tf` (ce qui est cree), `outputs.tf` (ce qui sort). Un")
    print("   lecteur sait ou regarder sans ouvrir le reste.")


def _deux_instances(tf: Terraform) -> None:
    print("\n\n2. LE MEME DOSSIER, INSTANCIE DEUX FOIS\n")
    plan = tf.plan()
    for ligne in rendre(plan):
        print(f"   {ligne}")
    print("\n   Quatre ressources pour deux appels : chaque instance du")
    print("   module cree SES ressources, prefixees par son nom d'appel.")
    print("   `module.reseau_prod.reseau.ce` et")
    print("   `module.reseau_staging.reseau.ce` sont deux adresses")
    print("   differentes, donc deux ressources differentes.")
    tf.apply()
    print("\n   Apres l'apply, ce que la realite contient :\n")
    for identifiant, objet in sorted(tf.realite().tout().items()):
        plage = objet.get("plage", "-")
        print(f"      {identifiant:<38} plage={plage}")
    print("\n   Deux reseaux, deux passerelles, deux plages d'adresses. Le")
    print("   motif a ete ecrit UNE fois — c'est tout l'interet.")


def _le_contrat(tf: Terraform) -> None:
    print("\n\n3. LE CONTRAT : ENTREES ET SORTIES\n")
    print("   Ce que l'appelant fournit (`infra-modules/main.tf`) :\n")
    print('      module "reseau_prod" {')
    print('        source = "../infra/modules/reseau"')
    print('        nom    = "jobportal-prod"')
    print('        plage  = "10.0.0.0/16"')
    print('      }\n')
    configuration = tf.configuration()
    print("   Ce que l'appelant recupere :\n")
    for nom, valeur in sorted(configuration.sorties.items()):
        print(f"      {nom:<12} = {valeur}")
    print("\n   L'appelant n'a jamais eu besoin de savoir qu'un module")
    print("   `reseau` cree AUSSI un conteneur de passerelle. C'est")
    print("   l'encapsulation : des entrees, des sorties, et une boite")
    print("   noire entre les deux.")
    print("\n   ⚠️ Un output de module est donc un CONTRAT PUBLIC. Le")
    print("   renommer casse tous les appelants, exactement comme changer")
    print("   la signature d'une fonction publique. C'est pour cela que le")
    print("   Registry impose une version — et que `version = \"~> 3.0\"`")
    print("   n'est pas une precaution optionnelle.")


def _ce_quun_module_ne_fait_pas(tf: Terraform) -> None:
    print("\n\n4. CE QU'UN MODULE NE FAIT PAS\n")
    adresses = tf.state_list()
    print("   Les adresses suivies par l'etat :\n")
    for adresse in adresses:
        print(f"      {adresse}")
    print("\n   Un module ne cree PAS un etat separe. Tout vit dans le meme")
    print("   `terraform.tfstate`, sous des adresses prefixees. Un module")
    print("   n'est donc pas une frontiere de deploiement : appeler un")
    print("   module ne permet pas de deployer sa partie toute seule.")
    print("\n   Ce que cela implique en pratique : un `apply` touche TOUT")
    print("   ce que la configuration racine declare, modules compris. Pour")
    print("   deployer separement — et c'est souvent ce qu'on veut entre")
    print("   deux environnements — il faut deux configurations racines et")
    print("   deux etats. C'est l'objet du chapitre suivant.")
    print("\n   ⚠️ Et un piege qui coute des heures : un module ne devrait")
    print("   JAMAIS declarer son propre `provider` ni son `backend`. Les")
    print("   deux appartiennent a la racine ; les mettre dans un module le")
    print("   rend inutilisable ailleurs, et Terraform le signale tard.")
    print("\n\n   Le chapitre suivant separe ce qui doit l'etre : un etat")
    print("   par environnement, et la preuve que l'un n'affecte pas")
    print("   l'autre.")


if __name__ == "__main__":
    main()
