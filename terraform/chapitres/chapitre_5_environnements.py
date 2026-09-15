"""Chapitre 5 — Environnements multiples.

    uv run python chapitres/chapitre_5_environnements.py

Un seul code, plusieurs environnements. Ce chapitre montre les deux facons
de s'y prendre — un etat par environnement, ou un dossier par
environnement — et MESURE ce qui compte : appliquer sur l'un ne touche
jamais l'autre.
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

INFRA = Path(__file__).resolve().parent.parent / "infra"

ENVIRONNEMENTS = {
    "dev": {"prefixe": "jobportal-dev", "environnements": ["web"],
            "memoire": 256, "version_image": "1.5.0-rc1"},
    "prod": {"prefixe": "jobportal-prod",
             "environnements": ["web", "api", "batch"],
             "memoire": 1024, "version_image": "1.4.0"},
}


def main() -> None:
    console.utf8()
    travail = Path(tempfile.mkdtemp(prefix="tf-chapitre5-"))
    try:
        bancs = _un_etat_par_environnement(travail)
        _lisolation(bancs)
        _ce_qui_differe(bancs)
        _les_deux_approches()
    finally:
        shutil.rmtree(travail, ignore_errors=True)


def _un_etat_par_environnement(travail: Path) -> dict[str, Terraform]:
    print("1. UN CODE, DEUX ETATS\n")
    bancs: dict[str, Terraform] = {}
    for nom, valeurs in ENVIRONNEMENTS.items():
        tf = Terraform(INFRA,
                       etat=travail / f"{nom}.tfstate",
                       realite=travail / f"{nom}-realite.json")
        plan = tf.apply(valeurs)
        bancs[nom] = tf
        print(f"   {nom:<6} apply → {plan.resume}")
        print(f"          etat  → {tf.chemin_etat.name}")
    print("\n   Le MEME dossier `infra/` a servi deux fois. Rien n'a ete")
    print("   duplique : ce qui change est un jeu de VARIABLES, et surtout")
    print("   un fichier d'ETAT distinct.")
    print("\n   C'est exactement ce que font les `workspaces` de Terraform :")
    print("   ils ne changent pas le code, ils changent le chemin de")
    print("   l'etat. `terraform workspace select prod` revient a dire")
    print("   « utilise l'etat de prod ».")
    return bancs


def _lisolation(bancs: dict[str, Terraform]) -> None:
    print("\n\n2. LA MESURE QUI COMPTE : L'ISOLATION\n")
    avant = {nom: sorted(tf.realite().tout()) for nom, tf in bancs.items()}
    print("   Avant toute modification :")
    for nom, objets in avant.items():
        print(f"      {nom:<6} {len(objets)} objets : "
              f"{', '.join(o.replace('conteneur-', '') for o in objets)}")

    # On detruit tout en dev, et on regarde la prod.
    bancs["dev"].destroy()
    apres = {nom: sorted(tf.realite().tout()) for nom, tf in bancs.items()}
    print("\n   Apres un `destroy` complet sur dev :")
    for nom, objets in apres.items():
        print(f"      {nom:<6} {len(objets)} objets : "
              f"{', '.join(o.replace('conteneur-', '') for o in objets) or '—'}")
    print("\n   La production n'a pas bouge. C'est toute la raison d'etre")
    print("   d'un etat par environnement : une erreur de manipulation ne")
    print("   peut atteindre que le perimetre de l'etat charge.")
    print("\n   ⚠️ Et c'est aussi ce qui rend l'erreur inverse si grave :")
    print("   pointer par megarde l'etat de production depuis un poste de")
    print("   developpement. Le code est le meme, la commande est la meme,")
    print("   et seul le chemin de l'etat distingue un essai d'un")
    print("   incident.")
    print("\n   La protection pratique tient en trois habitudes : des")
    print("   backends distincts par environnement, des identifiants qui")
    print("   n'ont de droits que sur le leur, et un `plan` relu avant tout")
    print("   `apply` en production.")


def _ce_qui_differe(bancs: dict[str, Terraform]) -> None:
    print("\n\n3. CE QUI DIFFERE D'UN ENVIRONNEMENT A L'AUTRE\n")
    print(f"   {'variable':<18} {'dev':<22} {'prod':<22}")
    print(f"   {'-' * 18} {'-' * 22} {'-' * 22}")
    cles = sorted(set(ENVIRONNEMENTS["dev"]) | set(ENVIRONNEMENTS["prod"]))
    for cle in cles:
        dev = ENVIRONNEMENTS["dev"].get(cle, "(defaut)")
        prod = ENVIRONNEMENTS["prod"].get(cle, "(defaut)")
        print(f"   {cle:<18} {str(dev):<22} {str(prod):<22}")
    print("\n   Quatre variables, et deux infrastructures de tailles")
    print("   differentes. Aucune ligne de HCL n'a ete dupliquee.")
    print("\n   ⚠️ Notez la version d'image : `1.5.0-rc1` en dev,")
    print("   `1.4.0` en prod. C'est le cas le plus frequent, et le plus")
    print("   dangereux si on l'oublie — un `apply` de prod avec les")
    print("   variables de dev deploie une version candidate en")
    print("   production. Le fichier de variables fait donc partie du")
    print("   perimetre a proteger, au meme titre que l'etat.")


def _les_deux_approches() -> None:
    print("\n\n4. WORKSPACES OU DOSSIERS : CHOISIR\n")
    print(f"   {'':<28} {'workspaces':<20} {'un dossier par env.'}")
    print(f"   {'-' * 28} {'-' * 20} {'-' * 22}")
    lignes = [
        ("code partage", "oui, entierement", "oui, via modules"),
        ("etat separe", "oui", "oui"),
        ("backend separe", "NON", "oui"),
        ("droits separes", "difficile", "naturel"),
        ("divergence possible", "non", "oui — et parfois utile"),
        ("mise en place", "une commande", "un dossier a creer"),
    ]
    for quoi, workspace, dossier in lignes:
        print(f"   {quoi:<28} {workspace:<20} {dossier}")
    print("\n   Les workspaces sont commodes pour des environnements")
    print("   JUMEAUX — memes ressources, memes droits, seule la taille")
    print("   change. Ils partagent le backend, donc les droits d'acces :")
    print("   qui peut appliquer en dev peut appliquer en prod.")
    print("\n   Des dossiers separes coutent un peu de duplication et")
    print("   apportent ce que les workspaces ne peuvent pas donner : un")
    print("   backend par environnement, des identifiants distincts, et la")
    print("   possibilite d'assumer une difference structurelle — une")
    print("   replique de secours en prod, absente ailleurs.")
    print("\n   La regle pratique : workspaces pour des variantes, dossiers")
    print("   des que la PRODUCTION entre dans le tableau.")
    print("\n\n   Le chapitre suivant met tout cela en CI : un plan qu'on")
    print("   relit, une derive qu'on detecte, et une destruction qu'on")
    print("   refuse.")


if __name__ == "__main__":
    main()
