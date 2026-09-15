"""Chapitre 6 — Gouvernance : la curation, la version publiée, et la promesse.

    uv run python chapitres/chapitre_6_gouvernance.py

« Le même artefact, du laptop au cluster » est la promesse du registre. Ce
chapitre la prend au mot et regarde ce qui voyage vraiment : une identité en
trois morceaux, dont deux peuvent être réattribués. Puis il cherche la
curation dans le contrat publié — et dit ce qu'il y trouve.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import vue_mcp                                     # noqa: E402
from jobportal.catalogue import Catalogue                         # noqa: E402
from jobportal.commun import (                                    # noqa: E402
    AMONT, CATALOGUE, ligne, plier, tableau, titre, utf8,
)
from jobportal.manifeste import charger, charger_dossier          # noqa: E402
from jobportal.schema_publie import document as openapi           # noqa: E402

PORTAIL = CATALOGUE / "portail"
ORDRE = ["mcp-offres", "mcp-scoring", "mcp-annuaire", "skill-tri",
         "prompt-entretien", "modele-defaut", "agent-recruteur"]


def portail() -> Catalogue:
    catalogue = Catalogue()
    for nom in ORDRE:
        catalogue.appliquer_tous(charger(PORTAIL / f"{nom}.yaml"))
    return catalogue


def adressable(doc) -> str:
    """Ce qu'un manifeste epingle de facon NON reattribuable, s'il le fait.

    Un digest OCI et un commit git designent un contenu : republier ne les
    change pas. Tout le reste — une etiquette, un tag d'image, une branche —
    est un nom.
    """
    source = doc.spec.get("source") or {}
    paquet = source.get("package") or {}
    origine = paquet.get("origin") or {}
    identifiant = origine.get("identifier") or ""
    if "@sha256:" in identifiant:
        return "digest OCI"
    depot = source.get("repository") or {}
    if depot.get("commit"):
        return "commit git"
    if doc.type == "Agent" and "@sha256:" in (source.get("image") or ""):
        return "digest OCI"
    return "—"


def principal() -> None:
    utf8()
    catalogue = portail()

    titre(1, "LA CURATION, CHERCHEE DANS LE CONTRAT PUBLIE")
    schemas = openapi()["components"]["schemas"]
    routes = openapi()["paths"]
    texte = str(schemas)
    ligne("champ « approved » dans un schema",
          "oui" if "approved" in texte.lower() else "aucun", 38)
    ligne("champ « status » d'un artefact",
          ", ".join(schemas["Status"]["properties"]), 38)
    ligne("route d'approbation",
          ", ".join(r for r in routes if "approv" in r.lower()) or "aucune", 38)
    print()
    readme = (AMONT / "README.md").read_text(encoding="utf-8")
    phrase = next(l for l in readme.splitlines()
                  if "Curate and approve" in l)
    for l in _plier_ligne(phrase):
        print(f"      {l}")
    print()
    for l in plier(
        "La capacite est annoncee dans le README ; elle n'est pas dans le "
        "modele de donnees v1alpha1. Il n'y a ni champ d'approbation, ni "
        "route pour approuver, ni statut « pending ». Ce que le cours decrit "
        "— un artefact qui attend sa revue puis passe a `approved` — n'est "
        "donc pas une mecanique du registre libre."):
        print(f"   {l}")
    print()
    for l in plier(
        "Ce n'est pas une critique du produit : la curation est un travail "
        "d'organisation avant d'etre un champ. C'est une precision "
        "importante pour qui va l'installer, parce qu'elle dit ou sera le "
        "travail — dans une convention, et dans ce qui la fait respecter."):
        print(f"   {l}")

    titre(2, "CE QUE LE SCHEMA OFFRE POUR LA CONSTRUIRE")
    tableau(["champ", "indexe ?", "a quoi il sert"], [
        ["metadata.labels", "oui (GIN)", "filtrer, selectionner — `?labels=`"],
        ["metadata.annotations", "non", "raconter : qui, quand, pourquoi"],
        ["status.conditions", "ecrit par un controleur", "l'etat observe"],
    ], [24, 26, 38])
    print()
    print("   Une curation sur libelles, appliquee au portail :\n")
    approuves = catalogue.selectionner("MCPServer", "portail.emploi/revue=ok")
    tous = catalogue.selectionner("MCPServer")
    ligne("serveurs au catalogue", str(len(tous)), 38)
    ligne("serveurs marques revus", str(len(approuves)), 38)
    print()
    for l in plier(
        "Zero. Aucun manifeste du portail ne porte de libelle de revue — "
        "exactement comme aucun des dix exemples amont ne porte de libelle "
        "du tout. Et c'est le point : la selection par defaut d'un registre "
        "libre rend TOUT. Un catalogue sans convention de curation n'est pas "
        "« ouvert », il est indistinct."):
        print(f"   {l}")

    titre(3, "LA VERSION PUBLIEE, ET SA CASCADE")
    lignes = []
    for doc in [d for d in charger_dossier(PORTAIL) if d.type == "MCPServer"] \
            + [d for d in charger(CATALOGUE / "a-corriger.yaml")
               if d.type == "MCPServer"]:
        f = vue_mcp.fiche(doc)
        lignes.append([f["name"], f["version"],
                       {"paquet": "le paquet", "etiquette": "metadata.tag",
                        "repli": "⚠ un repli"}[f["_origine"]["version"]]])
    tableau(["fiche publiee", "version", "d'ou elle vient"], lignes,
            [32, 14, 22])
    print()
    for l in plier(
        "La specification amont exige un champ `version` non vide. Quand le "
        "manifeste n'en donne pas, la projection en fabrique un : le paquet, "
        "puis l'etiquette si elle n'est pas « latest », puis `0.0.0`. Trois "
        "etages, et la fiche ne dit pas lequel a repondu."):
        print(f"   {l}")
    print()
    for l in plier(
        "Deux consequences. `annuaire-pro` publie « stable » comme numero de "
        "version, parce qu'un serveur distant n'a pas de paquet d'ou la "
        "deduire. Et `sans-version` publie « 0.0.0 » — une image qui suivra "
        "`:latest` a chaque redemarrage, presentee au catalogue comme une "
        "version."):
        print(f"   {l}")

    titre(4, "CE QUI VOYAGE VRAIMENT DU LAPTOP AU CLUSTER")
    tableau(["artefact", "identite", "epingle sur un contenu ?"],
            [[str(i), "espace + nom + etiquette", adressable(
                next(d for d in charger_dossier(PORTAIL)
                     if d.nom == i.nom and d.type == i.type))]
             for i in sorted(catalogue.objets, key=str)], [40, 26, 26])
    print()
    adressables = sum(1 for d in charger_dossier(PORTAIL)
                      if adressable(d) != "—")
    ligne("artefacts du portail", str(len(catalogue)), 38)
    ligne("epingles sur un contenu adressable", str(adressables), 38)
    print()
    for l in plier(
        "Aucun. Tous sont epingles sur des NOMS : une etiquette `stable`, un "
        "tag d'image `1.4.0`, une branche par defaut. La promesse « ce qui a "
        "ete valide est exactement ce qui tourne » tient donc tant que "
        "personne ne republie sous le meme nom — et le chapitre 4 a montre "
        "que republier est accepte, silencieux, et ne casse aucune "
        "reference."):
        print(f"   {l}")
    print()
    for l in plier(
        "Ce qui rendrait la promesse vraie existe pourtant dans le schema : "
        "un identifiant OCI par digest (`repo@sha256:...`), un "
        "`repository.commit`, et le `status.resolvedSource` qu'un controleur "
        "de Skill ecrit — « the reproducibility anchor: deploys materialize "
        "from this pin, not from the (possibly moving) ref the user gave ». "
        "C'est une discipline d'ecriture, pas une option a cocher."):
        print(f"   {l}")

    titre(5, "LE CLUSTER, ET L'ADRESSE DU CHART")
    for reperage in ("Deploy Agent Registry into Kubernetes",
                     "Consistent path from laptop to cluster"):
        phrase = next(l for l in readme.splitlines() if reperage in l)
        for l in _plier_ligne(phrase.strip("- ")):
            print(f"      {l}")
        print()
    publication = (AMONT / "releasing.md").read_text(encoding="utf-8")
    reference = next(l.strip(" `\\") for l in publication.splitlines()
                     if "oci://" in l)
    ligne("chart publie (docs/releasing.md)", reference, 36)
    ligne("dans le support de cours",
          "oci://ghcr.io/agentregistry-dev/charts/agentregistry", 36)
    print()
    for l in plier(
        "Un segment de chemin manque au support : le chart est publie sous "
        "`agentregistry-dev/agentregistry/charts/agentregistry`, pas sous "
        "`agentregistry-dev/charts/agentregistry`. Une commande `helm` a un "
        "segment pres ne s'installe pas — elle echoue sur un 404 de registre, "
        "et rien dans le message ne dit que c'est le chemin."):
        print(f"   {l}")
    print()
    for l in plier(
        "Au-dela de l'adresse, ce projet n'a pas de cluster : ce qui se passe "
        "APRES le `helm install` n'est pas mesure ici. C'est une limite a "
        "dire, pas a combler par une supposition."):
        print(f"   {l}")

    titre(6, "CE QUE CE PROJET NE PROUVE PAS")
    for limite in [
        "le registre ne tourne pas : pas de service Go, pas de PostgreSQL,",
        "  pas d'interface web, pas de `arctl` ;",
        "la couche B est une TRANSCRIPTION du validateur Go. Son garde-fou",
        "  est `tests/test_amont.py` : les dix manifestes d'exemple du depot",
        "  doivent passer. Une regle mal transcrite se voit la, pas ailleurs ;",
        "la couche C modelise la resolution, pas la base : ni transactions,",
        "  ni suppression differee, ni concurrence ;",
        "rien n'est deploye, donc rien de ce qui suit l'apply n'est mesure —",
        "  ni le resolveur de deploiement, ni la passerelle, ni le cluster.",
    ]:
        print(f"   {limite}" if limite.startswith("  ") else f"   · {limite}")
    print()
    for l in plier(
        "Ce qui EST reel : le document OpenAPI est celui que le registre "
        "publie, copie sans retouche, et la couche A valide contre lui sans "
        "une ligne de transcription. Les dix manifestes d'exemple sont ceux "
        "du depot. Les trois trous du chapitre 3, l'inversion des deux "
        "contrats, l'absence de champ d'approbation et la cascade de version "
        "se lisent dans ces fichiers — pas dans ma parole."):
        print(f"   {l}")

    print("\n   uv run python outils/verifier_manifeste.py VOTRE.yaml \\")
    print("       --registre catalogue/portail\n")


def _plier_ligne(texte: str, largeur: int = 64) -> list[str]:
    """Le README amont melange markdown et HTML : on rend le texte seul."""
    sans_balise = re.sub(r"<[^>]+>", "", texte)
    lisible = (sans_balise.replace("&amp;", "&").replace("&quot;", '"')
               .replace("&lt;", "<").replace("&gt;", ">").replace("**", ""))
    return plier(lisible.strip(" -"), largeur)


if __name__ == "__main__":
    principal()
