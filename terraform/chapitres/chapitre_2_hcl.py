"""Chapitre 2 — HCL : variables, outputs et expressions.

    uv run python chapitres/chapitre_2_hcl.py

« `for_each` (par cle) est plus stable que `count` (par index) quand la
liste change. » Ce chapitre le MESURE : on retire un element au milieu, et
on compte les ressources detruites de chaque cote. L'ecart est de trois
contre une.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                              # noqa: E402
from jobportal.configuration import ErreurConfiguration    # noqa: E402
from jobportal.plan import Action, rendre                  # noqa: E402
from jobportal.terraform import Terraform                  # noqa: E402

RACINE = Path(__file__).resolve().parent.parent
INFRA = RACINE / "infra"

FOR_EACH = """
resource "conteneur" "app" {
  for_each = var.environnements
  nom      = "jobportal-${each.key}"
  image    = "jobportal:1.4.0"
}
variable "environnements" {
  type    = list(string)
  default = ["dev", "recette", "staging", "prod"]
}
"""

COUNT = """
resource "conteneur" "app" {
  count = length(var.environnements)
  nom   = "jobportal-${var.environnements[count.index]}"
  image = "jobportal:1.4.0"
}
variable "environnements" {
  type    = list(string)
  default = ["dev", "recette", "staging", "prod"]
}
"""


def main() -> None:
    console.utf8()
    travail = Path(tempfile.mkdtemp(prefix="tf-chapitre2-"))
    try:
        _les_variables_typees(travail)
        _la_validation(travail)
        _for_each_contre_count(travail)
        _les_outputs(travail)
    finally:
        shutil.rmtree(travail, ignore_errors=True)


def _les_variables_typees(travail: Path) -> None:
    print("1. DES VARIABLES TYPEES, ET CE QUE LE TYPE ATTRAPE\n")
    tf = Terraform(INFRA, etat=travail / "a.tfstate",
                   realite=travail / "a.json")
    configuration = tf.configuration()
    print("   Les variables declarees, et leurs valeurs par defaut :")
    for nom, valeur in sorted(configuration.variables.items()):
        print(f"      {nom:<18} {valeur!r}")
    print("\n   Ce qui arrive quand le type ne colle pas :")
    for nom, valeur in (("memoire", "beaucoup"), ("prefixe", 42)):
        try:
            tf.configuration({nom: valeur})
            verdict = "acceptee (!)"
        except ErreurConfiguration as erreur:
            verdict = str(erreur)
        print(f"      {nom} = {valeur!r:<12} → {verdict}")
    print("\n   Le type n'est pas de la documentation : c'est un controle.")
    print("   Une valeur mal saisie s'arrete ici, avant le plan — donc")
    print("   avant qu'une seule ressource ne soit touchee.")
    print("\n   ⚠️ Nuance honnete : Terraform est plus SOUPLE que ce projet.")
    print("   Il convertit quand il peut (un nombre ecrit en chaine devient")
    print("   un nombre). Ce moteur refuse. La lecon reste la meme, et le")
    print("   choix est documente dans `jobportal/configuration.py`.")


def _la_validation(travail: Path) -> None:
    print("\n\n2. LA VALIDATION : UNE REGLE METIER, PAS UN TYPE\n")
    tf = Terraform(INFRA, etat=travail / "b.tfstate",
                   realite=travail / "b.json")
    print("   La regle declaree dans `infra/variables.tf` :\n")
    print('      validation {')
    print('        condition     = contains(["small", "medium"], var.taille)')
    print('        error_message = "taille doit valoir small ou medium."')
    print('      }\n')
    for valeur in ("small", "medium", "enorme"):
        try:
            tf.configuration({"taille": valeur})
            verdict = "acceptee"
        except ErreurConfiguration as erreur:
            verdict = str(erreur)
        print(f"      taille = {valeur!r:<10} → {verdict}")
    print("\n   Le type dit « c'est une chaine » ; la validation dit")
    print("   « c'est une chaine PARMI CELLES-CI ». La seconde attrape ce")
    print("   que la premiere laisse passer, et elle le fait au moment ou")
    print("   l'erreur coute le moins cher : avant le plan.")
    print("\n   Le message est le VOTRE. C'est ce qui separe un outil")
    print("   utilisable d'un outil subi : « taille doit valoir small ou")
    print("   medium » se corrige tout seul, « invalid value » non.")


def _for_each_contre_count(travail: Path) -> None:
    print("\n\n3. `for_each` CONTRE `count` : LA MESURE QUI TRANCHE\n")
    quatre = ["dev", "recette", "staging", "prod"]
    trois = ["dev", "staging", "prod"]      # on retire « recette », au milieu

    print(f"   Au depart : {quatre}")
    print(f"   Ensuite   : {trois}   (« recette » retiree, AU MILIEU)\n")

    for libelle, source in (("for_each (par cle)", FOR_EACH),
                            ("count (par position)", COUNT)):
        dossier = travail / libelle.split()[0]
        dossier.mkdir(parents=True, exist_ok=True)
        (dossier / "main.tf").write_text(source, encoding="utf-8")
        tf = Terraform(dossier, etat=dossier / "s.tfstate",
                       realite=dossier / "r.json")
        tf.apply({"environnements": quatre})
        plan = tf.plan({"environnements": trois})
        detruites = plan.compter(Action.DETRUIRE) + plan.compter(
            Action.REMPLACER)
        creees = plan.compter(Action.CREER) + plan.compter(Action.REMPLACER)
        print(f"   ── {libelle}")
        for ligne in rendre(plan):
            print(f"      {ligne}")
        print(f"      → {detruites} detruite(s), {creees} creee(s)\n")

    print("   Voila l'ecart, et il n'est pas theorique : retirer UN element")
    print("   au milieu detruit UNE ressource avec `for_each`, et TROIS")
    print("   avec `count`.")
    print("\n   La raison tient a l'adresse. `for_each` indexe par CLE :")
    print("   `conteneur.app[\"prod\"]` reste `conteneur.app[\"prod\"]` quoi")
    print("   qu'il arrive a ses voisins. `count` indexe par POSITION :")
    print("   retirer le rang 1 fait glisser tout ce qui suit, et le moteur")
    print("   voit des ressources dont les attributs ont change.")
    print("\n   ⚠️ En production, cela se traduit par des destructions que")
    print("   personne n'a demandees — et qu'on ne remarque qu'en LISANT le")
    print("   plan. C'est la seule protection.")
    print("\n   La regle pratique : `count` pour un nombre (« trois")
    print("   repliques identiques »), `for_each` des qu'il s'agit d'une")
    print("   collection d'elements NOMMES.")


def _les_outputs(travail: Path) -> None:
    print("\n\n4. LES OUTPUTS : LE CONTRAT DE SORTIE\n")
    tf = Terraform(INFRA, etat=travail / "c.tfstate",
                   realite=travail / "c.json")
    configuration = tf.configuration()
    print("   Declare dans `infra/main.tf` :\n")
    print("      output \"conteneurs\" {")
    print("        value = { for cle, instance in conteneur.app :"
          " cle => instance.nom }")
    print("      }\n")
    print("   Ce que cela produit :\n")
    for cle, valeur in sorted(configuration.sorties["conteneurs"].items()):
        print(f"      {cle:<10} → {valeur}")
    print("\n   Une expression `for` a parcouru les instances et construit")
    print("   une carte. HCL n'est pas qu'un format de donnees : c'est un")
    print("   petit langage d'expressions, et les outputs en sont la")
    print("   vitrine.")
    print("\n   Leur vrai role apparait au chapitre 4 : un output de module")
    print("   est ce qu'un autre module peut consommer. C'est le contrat")
    print("   d'une boite noire — des entrees, des sorties, et rien a")
    print("   savoir de l'interieur.")
    print("\n\n   Le chapitre suivant ouvre le fichier d'etat, et montre ce")
    print("   qu'il contient de plus genant.")


if __name__ == "__main__":
    main()
