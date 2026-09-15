"""Chapitre 6 — Production : CI/CD et bonnes pratiques.

    uv run python chapitres/chapitre_6_production.py

Trois reflexes de production, chacun mesure : appliquer le plan qu'on a LU
et pas un autre, detecter une derive, et refuser une destruction.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                          # noqa: E402
from jobportal.plan import DestructionEmpechee, rendre  # noqa: E402
from jobportal.terraform import Terraform              # noqa: E402

RACINE = Path(__file__).resolve().parent.parent
INFRA = RACINE / "infra"
PROTEGEE = RACINE / "infra-protegee"


def main() -> None:
    console.utf8()
    travail = Path(tempfile.mkdtemp(prefix="tf-chapitre6-"))
    try:
        _le_plan_enregistre(travail)
        _la_derive(travail)
        _prevent_destroy(travail)
        _ce_qui_reste(travail)
    finally:
        shutil.rmtree(travail, ignore_errors=True)


def _le_plan_enregistre(travail: Path) -> None:
    print("1. APPLIQUER LE PLAN QU'ON A LU, ET PAS UN AUTRE\n")
    tf = Terraform(INFRA, etat=travail / "a.tfstate",
                   realite=travail / "a.json")
    enregistre = tf.plan()
    print(f"   Le plan calcule, et relu par un humain :")
    for ligne in rendre(enregistre)[:4]:
        print(f"   {ligne}")
    print("\n   Entre ce plan et son application, quelqu'un modifie le code")
    print("   — ici, on change le prefixe. Deux facons de proceder :\n")

    sans = tf.plan({"prefixe": "autre"})
    print("      apply SANS plan enregistre, ce qui serait cree :")
    for changement in sans.changements:
        print(f"         {changement.apres.get('nom')}")
    print("        → c'est le NOUVEAU code qui part, pas celui qu'on a lu\n")

    applique = tf.apply(plan=enregistre)
    print("      apply DU plan enregistre, ce qui a ete cree :")
    for identifiant in sorted(tf.realite().tout()):
        print(f"         {identifiant.replace('conteneur-', '')}")
    print("        → exactement ce qui avait ete relu")
    print(f"        → {applique.resume}")
    print("\n   C'est la raison d'etre de `terraform plan -out=fichier`")
    print("   suivi de `terraform apply fichier` : en CI, le plan est")
    print("   calcule dans une etape, relu — voire approuve — dans une")
    print("   autre, puis applique. Sans le fichier, l'etape d'approbation")
    print("   ne garantit rien : le code a pu changer entre-temps.")
    print("\n   ⚠️ Et un plan enregistre PERIME : Terraform refuse de")
    print("   l'appliquer si l'etat a change depuis son calcul. C'est")
    print("   voulu — un plan est une photo, pas une intention.")


def _la_derive(travail: Path) -> None:
    print("\n\n2. LA DERIVE : QUAND LA REALITE CHANGE TOUTE SEULE\n")
    tf = Terraform(INFRA, etat=travail / "b.tfstate",
                   realite=travail / "b.json")
    tf.apply()
    print(f"   Apres l'apply : {tf.plan().resume}\n")

    # Quelqu'un modifie la realite en dehors de Terraform — une console
    # web, un script d'urgence, un collegue presse.
    realite = tf.realite()
    realite.modifier("conteneur-jobportal-prod",
                     {"nom": "jobportal-prod", "image": "jobportal:0.1.0",
                      "memoire": 64})
    print("   Quelqu'un modifie la production A LA MAIN :")
    print("      image   : jobportal:1.4.0 → jobportal:0.1.0")
    print("      memoire : 512 → 64\n")

    # ⚠️ Terraform ne voit RIEN tant qu'il n'a pas relu la realite. C'est
    # ce que fait `terraform refresh`, aujourd'hui integre au plan.
    print("   Le plan, SANS relire la realite :")
    print(f"      {tf.plan().resume}")
    print("        → Terraform compare le CODE a l'ETAT, et les deux")
    print("          concordent toujours. La derive est invisible.\n")

    etat = tf.etat()
    for ressource in etat.ressources.values():
        for instance in ressource.instances:
            reel = realite.lire(instance.attributs.get("id", ""))
            if reel is not None:
                instance.attributs = dict(reel)
    etat.ecrire()
    print("   Le plan, APRES un rafraichissement :")
    plan = tf.plan()
    for ligne in rendre(plan):
        print(f"   {ligne}")
    print("\n   La derive apparait, attribut par attribut. Terraform")
    print("   propose de REVENIR au code — c'est le principe : le code est")
    print("   la reference, la realite doit s'y conformer.")
    print("\n   ⚠️ Le point a retenir est le precedent : SANS")
    print("   rafraichissement, la derive est INVISIBLE. Le plan compare le")
    print("   code a l'etat, pas a la realite. C'est pourquoi un `plan`")
    print("   quotidien en CI — qui rafraichit — est le detecteur de")
    print("   derive le plus simple qui soit : s'il n'est pas vide alors")
    print("   que personne n'a touche au code, quelqu'un a modifie la")
    print("   production a la main.")


def _prevent_destroy(travail: Path) -> None:
    print("\n\n3. REFUSER UNE DESTRUCTION\n")
    tf = Terraform(PROTEGEE, etat=travail / "c.tfstate",
                   realite=travail / "c.json")
    tf.apply()
    print("   Deux ressources, dont une portant `prevent_destroy = true` :")
    for adresse in tf.state_list():
        print(f"      {adresse}")
    print("\n   On tente de changer le nom de la base — ce qui, on l'a vu")
    print("   au chapitre 1, force un remplacement donc une destruction :\n")
    contenu = (PROTEGEE / "main.tf").read_text(encoding="utf-8")
    modifie = contenu.replace('nom   = "jobportal-base"',
                              'nom   = "jobportal-base-v2"')
    (PROTEGEE / "main.tf").write_text(modifie, encoding="utf-8")
    try:
        plan = tf.plan()
        for ligne in rendre(plan)[:3]:
            print(f"      {ligne}")
        try:
            tf.apply()
            verdict = "applique (!)"
        except DestructionEmpechee as erreur:
            verdict = str(erreur)
        print(f"\n      apply → {verdict}")
    finally:
        (PROTEGEE / "main.tf").write_text(contenu, encoding="utf-8")
    print("\n   Le plan MONTRE le remplacement ; c'est l'`apply` qui")
    print("   refuse. `prevent_destroy` est un garde-fou de dernier")
    print("   recours, pas une regle metier : il ne dit pas « ceci est")
    print("   important », il dit « arrete-toi ».")
    print("\n   On le pose sur ce qui ne se recree pas : une base de")
    print("   donnees, un bucket de sauvegardes, un enregistrement DNS de")
    print("   production. Et on l'assume : le jour ou la destruction est")
    print("   VOULUE, il faut retirer la ligne, ce qui est exactement le")
    print("   moment de reflexion qu'on cherchait a provoquer.")


def _ce_qui_reste(travail: Path) -> None:
    print("\n\n4. CE QU'UNE CHAINE DE PRODUCTION AJOUTE ENCORE\n")
    print("   Ce projet mesure le cœur de Terraform. Une vraie chaine y")
    print("   ajoute quatre choses, et aucune n'est optionnelle :\n")
    print("      • `terraform fmt -check` et `validate` en premiere etape :")
    print("        un formatage et une syntaxe verifies avant tout le")
    print("        reste, pour que les revues portent sur le fond ;")
    print("      • une analyse de securite statique (tfsec, Checkov) : un")
    print("        bucket public ou un groupe de securite ouvert a 0.0.0.0/0")
    print("        se detectent dans le HCL, avant l'apply ;")
    print("      • l'estimation de COUT (Infracost) sur la pull request :")
    print("        c'est la seule facon de voir « +420 €/mois » avant de")
    print("        fusionner, et non a la facture suivante ;")
    print("      • une approbation humaine entre le `plan` et l'`apply` de")
    print("        production — avec le plan enregistre de la section 1,")
    print("        sans quoi l'approbation ne porte sur rien.")
    print("\n   ⚠️ Et une regle qui n'est pas technique : les identifiants")
    print("   de la CI n'ont de droits que sur leur environnement. Un jeton")
    print("   unique qui peut tout faire partout transforme chaque erreur")
    print("   de pipeline en incident de production.")
    print("\n   Ce que ce projet ne fait pas, et qu'il faut savoir : il n'a")
    print("   ni `terraform init` (aucun provider a telecharger), ni")
    print("   verrouillage de versions (`.terraform.lock.hcl`), ni graphe")
    print("   de dependances explicite. Le fichier de verrouillage, en")
    print("   particulier, est ce qui rend un `apply` reproductible six")
    print("   mois plus tard : il se versionne, au meme titre qu'un")
    print("   `package-lock.json`.")
    print()


if __name__ == "__main__":
    main()
