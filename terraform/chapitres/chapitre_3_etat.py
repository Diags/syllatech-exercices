"""Chapitre 3 — L'etat : le cœur de Terraform.

    uv run python chapitres/chapitre_3_etat.py

« Le state est la source de verite qui rend les apply suivants
intelligents — d'ou l'importance capitale de ne jamais l'editer a la main. »
Ce chapitre ouvre le fichier, montre ce qu'il contient de plus genant, puis
le DETRUIT pour mesurer ce qui se passe ensuite.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                      # noqa: E402
from jobportal.etat import EtatVerrouille, Verrou  # noqa: E402
from jobportal.plan import rendre                  # noqa: E402
from jobportal.terraform import Terraform          # noqa: E402

INFRA = Path(__file__).resolve().parent.parent / "infra"


def main() -> None:
    console.utf8()
    travail = Path(tempfile.mkdtemp(prefix="tf-chapitre3-"))
    tf = Terraform(INFRA, etat=travail / "terraform.tfstate",
                   realite=travail / "realite.json")
    try:
        tf.apply()
        _ce_que_le_state_contient(tf)
        _le_state_perdu(tf, travail)
        _import(tf)
        _mv_et_rm(tf)
        _le_verrou(tf)
    finally:
        shutil.rmtree(travail, ignore_errors=True)


def _ce_que_le_state_contient(tf: Terraform) -> None:
    print("1. CE QUE LE FICHIER D'ETAT CONTIENT\n")
    donnees = json.loads(tf.chemin_etat.read_text(encoding="utf-8"))
    entete = {cle: valeur for cle, valeur in donnees.items()
              if cle != "resources"}
    print("   L'en-tete :")
    for cle, valeur in entete.items():
        print(f"      {cle:<20} {valeur}")
    premiere = donnees["resources"][0]["instances"][0]
    print("\n   La premiere instance, telle qu'elle est ecrite :\n")
    for ligne in json.dumps(premiere, indent=2,
                            ensure_ascii=False).splitlines():
        print(f"      {ligne}")
    print("\n   ⚠️ REGARDEZ `mot_de_passe`. Il n'apparait nulle part dans")
    print("   votre code : c'est le provider qui l'a engendre, et l'etat le")
    print("   stocke EN CLAIR. C'est vrai de tout attribut calcule — mots")
    print("   de passe engendres, cles d'acces, certificats.")
    print("\n   Trois consequences, toutes pratiques :")
    print("      • le state ne va JAMAIS dans Git ;")
    print("      • un backend distant se chiffre (`encrypt = true`) ;")
    print("      • qui lit le state a les secrets — les droits d'acces au")
    print("        bucket sont donc des droits d'acces a la production.")
    print("\n   Le `serial` s'incremente a chaque ecriture, et le `lineage`")
    print("   identifie la lignee : deux etats de lignees differentes ne")
    print("   decrivent pas la meme infrastructure, et Terraform refuse de")
    print("   les confondre.")


def _le_state_perdu(tf: Terraform, travail: Path) -> None:
    print("\n\n2. CE QUI SE PASSE SI ON PERD L'ETAT\n")
    sauvegarde = tf.chemin_etat.read_text(encoding="utf-8")
    avant = len(tf.realite().tout())
    tf.chemin_etat.unlink()
    plan = tf.plan()
    print(f"   Objets reellement existants : {avant}")
    print(f"   Etat supprime               : oui")
    print(f"   Plan calcule                : {plan.resume}\n")
    for ligne in rendre(plan)[:4]:
        print(f"   {ligne}")
    print("\n   Terraform veut TOUT recreer. Non parce que l'infrastructure")
    print("   a disparu — elle est toujours la — mais parce qu'il ne sait")
    print("   plus qu'elle lui appartient. Sans etat, le code et la realite")
    print("   n'ont plus aucun lien.")
    print("\n   Et un `apply` echouerait : les conteneurs existent deja.")
    print("   Dans un vrai cloud, il n'echouerait PAS — il creerait des")
    print("   doublons facturables, qui ne seraient suivis par personne.")
    print("\n   C'est la raison d'etre du backend distant : un fichier sur")
    print("   le poste de quelqu'un est un point de defaillance unique.")
    tf.chemin_etat.write_text(sauvegarde, encoding="utf-8")
    print(f"\n   (etat restaure pour la suite du chapitre)")


def _import(tf: Terraform) -> None:
    print("\n\n3. `import` : FAIRE ADOPTER UNE RESSOURCE EXISTANTE\n")
    # On fabrique une ressource « creee a la main », hors de Terraform.
    realite = tf.realite()
    realite.creer("conteneur", {"nom": "jobportal-legacy",
                                "image": "jobportal:0.9.0"})
    print("   Un conteneur a ete cree A LA MAIN, hors de Terraform :")
    print("      conteneur-jobportal-legacy")
    print(f"\n   Avant l'import, l'etat suit : {len(tf.state_list())} adresses")
    tf.importer("conteneur.reprise", "conteneur-jobportal-legacy")
    print(f"   Apres l'import, l'etat suit  : {len(tf.state_list())} adresses")
    print("\n   Ce que l'import fait, et ce qu'il ne fait pas :")
    print("      • il ECRIT une entree dans l'etat ;")
    print("      • il ne touche PAS a la ressource reelle ;")
    print("      • il n'ecrit PAS votre code — c'est a vous de rediger le")
    print("        bloc `resource` correspondant, sinon le plan suivant")
    print("        proposera de detruire ce que vous venez d'importer.")
    print("\n   C'est l'operation qui fait passer une infrastructure")
    print("   existante sous Terraform, ressource par ressource. Elle est")
    print("   fastidieuse, et c'est normal : chaque import est une")
    print("   affirmation — « cet objet m'appartient desormais ».")


def _mv_et_rm(tf: Terraform) -> None:
    print("\n\n4. `state mv` ET `state rm` : RENOMMER, OUBLIER\n")
    avant_reel = len(tf.realite().tout())
    tf.state_mv("conteneur.reprise", "conteneur.ancienne_plateforme")
    print("   Apres `state mv conteneur.reprise"
          " conteneur.ancienne_plateforme` :")
    for adresse in tf.state_list():
        print(f"      {adresse}")
    print(f"\n   Objets reels avant : {avant_reel}")
    print(f"   Objets reels apres : {len(tf.realite().tout())}")
    print("\n   Rien n'a bouge dans la realite : `state mv` renomme une")
    print("   ENTREE D'ETAT. C'est l'operation qui accompagne un")
    print("   renommage dans le code — sans elle, Terraform verrait une")
    print("   ressource disparue et une nouvelle a creer.")
    tf.state_rm("conteneur.ancienne_plateforme")
    print("\n   Apres `state rm conteneur.ancienne_plateforme` :")
    print(f"      adresses suivies : {len(tf.state_list())}")
    print(f"      objets reels     : {len(tf.realite().tout())}")
    print("\n   La ressource EXISTE TOUJOURS, et Terraform ne la suit plus.")
    print("   C'est exactement ce qu'on veut quand on sort une ressource de")
    print("   son perimetre — et exactement ce qu'on ne veut pas quand on")
    print("   croyait la supprimer.")
    print("\n   ⚠️ Ces trois commandes sont les seules facons legitimes de")
    print("   toucher a l'etat. Editer le JSON a la main casse le `serial`,")
    print("   la coherence des attributs calcules, et parfois la lignee.")


def _le_verrou(tf: Terraform) -> None:
    print("\n\n5. LE VERROU : DEUX `apply` EN MEME TEMPS\n")
    verrou = Verrou(tf.chemin_etat)
    verrou.prendre("collegue")
    print(f"   Un premier apply tient le verrou : {verrou.pris}")
    try:
        tf.apply()
        verdict = "passe (!)"
    except EtatVerrouille as erreur:
        verdict = str(erreur)
    print(f"   Un second apply         →  {verdict}")
    verrou.rendre()
    print(f"\n   Verrou rendu : {not verrou.pris}")
    plan = tf.apply()
    print(f"   L'apply repasse        →  {plan.resume}")
    print("\n   Sans verrou, deux `apply` simultanes lisent le meme etat,")
    print("   agissent chacun de leur cote, et le dernier a ecrire ecrase")
    print("   l'autre. L'etat ne decrit alors NI l'une NI l'autre des deux")
    print("   realites — et plus rien ne correspond a rien.")
    print("\n   En backend S3, ce verrou est une ligne dans une table")
    print("   DynamoDB ; ici c'est un fichier `.lock`. Le mecanisme change,")
    print("   la propriete est la meme : un seul ecrivain a la fois.")
    print("\n\n   Le chapitre suivant sort du fichier unique : un module,")
    print("   ecrit une fois, instancie deux fois.")


if __name__ == "__main__":
    main()
