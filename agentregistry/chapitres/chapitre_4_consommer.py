"""Chapitre 4 — Consommer et déployer : découvrir, épingler, appliquer.

    uv run python chapitres/chapitre_4_consommer.py

Trois questions, trois réponses mesurées : comment on cherche dans le
catalogue (et ce qui n'existe pas pour cela), ce qu'« épingler une version »
veut dire quand une étiquette est un nom, et pourquoi l'ordre d'application
n'est pas un détail de présentation.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal.catalogue import Catalogue, Identite               # noqa: E402
from jobportal.commun import (                                    # noqa: E402
    AMONT, CATALOGUE, ligne, plier, tableau, titre, utf8,
)
from jobportal.manifeste import (                                 # noqa: E402
    Document, charger, charger_dossier,
)
from jobportal.schema_publie import document as openapi           # noqa: E402

PORTAIL = CATALOGUE / "portail"
ORDRE = ["mcp-offres", "mcp-scoring", "mcp-annuaire", "skill-tri",
         "prompt-entretien", "modele-defaut", "agent-recruteur"]


def portail() -> Catalogue:
    catalogue = Catalogue()
    for nom in ORDRE:
        catalogue.appliquer_tous(charger(PORTAIL / f"{nom}.yaml"))
    return catalogue


def principal() -> None:
    utf8()

    titre(1, "CHERCHER : CE QUI EXISTE, ET CE QUI N'EXISTE PAS")
    routes = sorted(openapi()["paths"])
    ligne("routes de l'API", str(len(routes)), 30)
    ligne("routes contenant « search »",
          str(sum(1 for r in routes if "search" in r)) + " — aucune", 30)
    cli = (AMONT / "declarative-cli.md").read_text(encoding="utf-8")
    ligne("« arctl search » dans la doc",
          "present" if "arctl search" in cli else "absent", 30)
    print()
    print("   Ce que le support de cours ecrit :\n")
    print("      $ arctl search mcp postgres")
    print("        postgres-tools  1.2.0  approved\n")
    for l in plier(
        "La commande n'existe pas dans le CLI publie, et l'API n'a pas de "
        "route de recherche. Ce qui existe : `arctl get mcps`, et les routes "
        "de liste. L'idee — decouvrir par capacite plutot que par URL "
        "d'installation — est juste ; la commande est inventee."):
        print(f"   {l}")

    titre(2, "CE SUR QUOI ON PEUT REELLEMENT FILTRER")
    parametres = openapi()["paths"]["/v0/mcpservers"]["get"]["parameters"]
    tableau(["parametre", "ce qu'il filtre"],
            [[p["name"], p["description"][:52]] for p in parametres],
            [22, 56])
    print()
    for l in plier(
        "Un seul filtre porte sur le CONTENU : `labels`. Il n'y a aucun champ "
        "« capability » dans le schema — une decouverte par capacite est donc "
        "une CONVENTION de libelles, que le registre ne definit pas et "
        "qu'aucun des dix manifestes d'exemple du depot ne montre."):
        print(f"   {l}")
    print()
    amont_avec_libelles = sum(
        1 for d in charger_dossier(AMONT / "exemples")
        if (d.metadonnees.get("labels")))
    ligne("exemples amont avec des libelles", f"{amont_avec_libelles} sur 10", 34)

    titre(3, "LA CONVENTION, INVENTEE ET APPLIQUEE")
    catalogue = portail()
    print("   Les trois serveurs du portail portent deux libelles chacun.\n")
    for selecteur in ["", "portail.emploi/donnees=candidats",
                      "portail.emploi/capacite=scoring",
                      "portail.emploi/capacite=postgres"]:
        trouves = catalogue.selectionner("MCPServer", selecteur)
        ligne(f"labels={selecteur or '(aucun)'}",
              ", ".join(i.nom for i in trouves) or "(rien)", 40)
    print()
    for l in plier(
        "C'est cela, « on cherche une capability » : un selecteur de libelles "
        "sur une convention maison. Elle vaut ce que vaut sa discipline — un "
        "serveur publie sans libelle est invisible a la recherche, et rien "
        "dans le registre ne le signale. Le chapitre 6 y revient : c'est le "
        "vrai travail de curation."):
        print(f"   {l}")

    titre(4, "EPINGLER : TROIS DEFAUTS QUE LA REFERENCE N'ECRIT PAS")
    agent = next(iter(charger(PORTAIL / "agent-recruteur.yaml")))
    sobre = Document({
        "apiVersion": "ar.dev/v1alpha1", "kind": "Agent",
        "metadata": {"name": "sobre", "namespace": "default"},
        "spec": {"compatibleHarnesses": [{"type": "claude-code"}],
                 "mcpServers": [{"name": "offres"}],
                 "skills": [{"name": "tri-candidatures"}]}})
    print("   Ce que le manifeste ecrit, et ce que le registre resout :\n")
    tableau(["ecrit dans le manifeste", "cible resolue"],
            [[str(r), str(c)] for (_, c, r) in
             Catalogue().references_de(sobre)], [34, 44])
    print()
    for l in plier(
        "Le type vient du CHAMP, l'espace de l'agent, et l'etiquette absente "
        "devient `latest`. Les trois defauts sont poses en silence, et le "
        "premier est ecrit dans l'objet stocke : « The defaulting must "
        "persist into the stored spec ». La fiche du catalogue ne dit donc "
        "deja plus ce que le fichier disait."):
        print(f"   {l}")
    print()
    ligne("references de l'agent du portail",
          str(len(catalogue.references_de(agent))), 36)
    ligne("  dont epinglees explicitement",
          str(sum(1 for _, _, r in catalogue.references_de(agent)
                  if r.get("tag"))), 36)

    titre(5, "CE QU'UNE ETIQUETTE GARANTIT, ET CE QU'ELLE NE GARANTIT PAS")
    republie = next(iter(charger(PORTAIL / "skill-tri.yaml")))
    identite = Catalogue.identite_de(republie)

    def sous_dossier() -> str:
        objet = catalogue.obtenir(identite)
        if not objet:              # branche « depart » : l'identite ne colle pas
            return "(introuvable au catalogue)"
        return objet["spec"]["source"]["repository"]["subfolder"]

    avant = sous_dossier()
    republie.brut["spec"]["source"]["repository"]["subfolder"] = \
        "skills/tri-candidatures-v2"
    resultat = catalogue.appliquer(republie)

    ligne(f"{identite}, avant", avant, 46)
    ligne("on republie la MEME etiquette",
          "accepte" if resultat.accepte else "refuse", 46)
    ligne(f"{identite}, apres", sous_dossier(), 46)
    ligne("objets au catalogue", str(len(catalogue)), 46)
    ligne("references de l'agent qui cassent",
          str(len(catalogue.resoudre(agent.avec_defauts()))), 46)
    print()
    for l in plier(
        "L'agent n'a pas bouge d'un octet, son manifeste dit toujours "
        "`tag: stable`, sa reference resout toujours — et elle designe autre "
        "chose. Une etiquette n'est pas une version : c'est un NOM, "
        "reattribuable. `tagRegex` accepte `stable`, `prod`, `v1.2.0` et "
        "`latest` de la meme facon, et rien n'empeche de republier dessus."):
        print(f"   {l}")
    print()
    for l in plier(
        "La seule chose qui ne bouge pas est ce que l'artefact DESIGNE quand "
        "il designe un contenu adressable : un digest OCI "
        "(`repo@sha256:...`), un commit git. C'est ce que fait le controleur "
        "de Skill — « deploys materialize from this pin, not from the "
        "(possibly moving) ref the user gave »."):
        print(f"   {l}")

    titre(6, "L'ORDRE D'APPLICATION N'EST PAS DE LA MISE EN PAGE")
    alpha = Catalogue()
    resultats = alpha.appliquer_tous(charger_dossier(PORTAIL))
    refuses = [r for r in resultats if not r.accepte]
    ligne("dossier applique dans l'ordre alphabetique",
          f"{len(alpha)} objets, {len(refuses)} refus", 44)
    for r in refuses:
        ligne(f"  {r.document.origine}",
              f"{len(r.references)} reference(s) pendante(s)", 44)
    ordonne = portail()
    ligne("applique dans l'ordre des dependances",
          f"{len(ordonne)} objets, 0 refus", 44)
    print()
    for l in plier(
        "`agent-recruteur.yaml` vient en tete de l'alphabet et depend des six "
        "autres. La doc amont le dit pour un fichier multi-documents — "
        "« Resources are applied in document order, so define dependencies "
        "first » — et cela vaut pour un dossier, ou l'ordre n'existe pas. "
        "D'ou `full-stack.yaml` : un seul fichier, l'ordre est lisible."):
        print(f"   {l}")

    titre(7, "LA DEPENDANCE QU'AUCUN MANIFESTE N'ECRIT")
    ligne("Model/default/default@latest au catalogue",
          "oui" if Identite("Model", "default", "default", "latest")
          in catalogue.objets else "NON", 44)
    print()
    for l in plier(
        "Un Deployment d'agent « harness » qui omet `spec.modelRef` resout "
        "`Model/<espace>/default@latest`. Ce nom n'apparait dans aucun "
        "manifeste d'agent : c'est une convention du registre. Sans ce "
        "Model, le Deployment est refuse pour reference pendante — « The "
        "registry never selects the first or only Model automatically, "
        "because catalog growth would make that behavior nondeterministic. »"):
        print(f"   {l}")

    titre(8, "BRANCHER SON IDE")
    readme = (AMONT / "README.md").read_text(encoding="utf-8")
    for reperage in ("Generate configuration for", "arctl configure cursor"):
        phrase = next(l for l in readme.splitlines() if reperage in l)
        for l in plier(phrase.strip("- "), 64):
            print(f"      {l}")
        print()
    for l in plier(
        "Deux choses a retenir de ces deux lignes. Quatre clients, pas un "
        "seul — et surtout : ce que `configure` ecrit pointe vers la "
        "PASSERELLE, pas vers chaque serveur. Ce n'est donc pas une liste de "
        "serveurs recopiee dans un fichier, c'est UNE adresse. Le chapitre "
        "suivant regarde pourquoi c'est la seule qui puisse porter une "
        "authentification."):
        print(f"   {l}")

    print("\n   Au chapitre suivant : ce que le catalogue ne sait pas porter.\n")


if __name__ == "__main__":
    principal()
