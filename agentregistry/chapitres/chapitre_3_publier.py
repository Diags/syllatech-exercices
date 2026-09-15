"""Chapitre 3 — Créer et publier : trois contrôles, et ce qu'ils ratent.

    uv run python chapitres/chapitre_3_publier.py

Publier un artefact, c'est passer trois contrôles. Ils n'ont pas lieu au même
moment, ils ne lisent pas le même contrat, et ils n'attrapent pas les mêmes
fautes. Sur les onze manifestes de `catalogue/a-corriger.yaml`, ce chapitre
compte lequel attrape quoi — et les trois que personne n'attrape.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import regles, schema_publie                      # noqa: E402
from jobportal.catalogue import Catalogue                        # noqa: E402
from jobportal.commun import (                                   # noqa: E402
    AMONT, CATALOGUE, EXEMPLES_AMONT, ligne, plier, tableau, titre, utf8,
)
from jobportal.manifeste import Document, charger                # noqa: E402

PORTAIL = CATALOGUE / "portail"
ORDRE = ["mcp-offres", "mcp-scoring", "mcp-annuaire", "skill-tri",
         "prompt-entretien", "modele-defaut", "agent-recruteur"]


def portail() -> Catalogue:
    catalogue = Catalogue()
    for nom in ORDRE:
        catalogue.appliquer_tous(charger(PORTAIL / f"{nom}.yaml"))
    return catalogue


def couches(doc: Document, catalogue: Catalogue) -> tuple[int, int, int]:
    return (len(schema_publie.verifier(doc)),
            len(regles.verifier(doc.avec_defauts())),
            len(catalogue.resoudre(doc.avec_defauts())))


def principal() -> None:
    utf8()
    catalogue = portail()

    titre(1, "TROIS CONTROLES, TROIS MOMENTS")
    tableau(["couche", "ce qu'elle lit", "quand", "a-t-elle besoin du registre ?"], [
        ["A schema publie", "amont/openapi.yaml", "avant l'envoi", "non"],
        ["B validateur", "pkg/api/v1alpha1/*_validate.go", "a l'apply", "non"],
        ["C references", "le catalogue", "a l'apply", "OUI"],
    ], [18, 34, 16, 30])
    print()
    for l in plier(
        "Le decoupage n'est pas un choix de ce projet : il est dans l'amont. "
        "`Validate()` porte le commentaire « No network I/O; ref existence is "
        "covered by ResolveRefs » — et `ResolveRefs` est une methode separee, "
        "qui prend un resolveur. La consequence pratique : les couches A et B "
        "tournent dans une CI, sur un poste, hors ligne. La C ne peut pas."):
        print(f"   {l}")

    titre(2, "LA MATRICE, SUR ONZE MANIFESTES BIEN FORMES")
    documents = list(charger(CATALOGUE / "a-corriger.yaml"))
    lignes = []
    for doc in documents:
        a, b, c = couches(doc, catalogue)
        lignes.append([
            f"{doc.rang + 1}. {doc.nom}"[:26],
            str(a) if a else "·", str(b) if b else "·", str(c) if c else "·",
            "refuse" if (a or b or c) else "← personne",
        ])
    tableau(["manifeste", "A", "B", "C", "verdict"], lignes, [30, 5, 5, 5, 14])
    print()
    muets = [d for d in documents if couches(d, catalogue) == (0, 0, 0)]
    ligne("documents", str(len(documents)), 34)
    ligne("refuses par au moins une couche",
          str(len(documents) - len(muets)), 34)
    ligne("acceptes par les trois", str(len(muets)), 34)
    print()
    print("   Aucun de ces onze fichiers n'a de faute de YAML. Tous se")
    print("   relisent sans broncher. C'est la seule chose qu'ils ont en")
    print("   commun.")

    titre(3, "LES DEUX CONTRATS NE DISENT PAS LA MEME CHOSE")
    sans_kind = Document({
        "apiVersion": "ar.dev/v1alpha1", "kind": "Agent",
        "metadata": {"name": "a", "namespace": "default"},
        "spec": {"mcpServers": [{"name": "offres", "tag": "stable"}]}})
    sans_espace = next(iter(charger(EXEMPLES_AMONT / "mcp.yaml")))
    tableau(["manifeste", "A schema publie", "B validateur"], [
        ["une reference sans `kind`",
         "REFUSE (required)", "accepte (defaut pose)"],
        ["un manifeste sans `namespace`",
         "accepte (facultatif)", "REFUSE — avant defaut"],
    ], [32, 24, 26])
    print()
    ligne("  mesure : sans kind → A",
          f"{len(schema_publie.verifier(sans_kind))} erreur(s)", 34)
    ligne("  mesure : sans kind → B",
          f"{len(regles.verifier(sans_kind))} erreur(s)", 34)
    ligne("  mesure : sans namespace → A",
          f"{len(schema_publie.verifier(sans_espace))} erreur(s)", 34)
    ligne("  mesure : sans namespace → B",
          f"{len(regles.verifier(sans_espace))} erreur(s)", 34)
    print()
    for l in plier(
        "Les deux inversions se compensent parce que le serveur pose ses "
        "defauts entre les deux. Un outil tiers, lui, ne les pose pas : un "
        "client genere depuis l'OpenAPI refusera une reference sans `kind` "
        "que le registre accepte, et validera un manifeste sans `namespace` "
        "que le registre exige. Les dix exemples du depot sont dans ce "
        "second cas — tous."):
        print(f"   {l}")

    titre(4, "LES TROIS TROUS")
    for nom, quoi, pourquoi in [
        ("source-vide", "`spec.source: {}`",
         "validateMCPServerSource sort si Package est nil, sans rien exiger"),
        ("sans-version", "une image OCI sans tag",
         "la regle « tag or digest » n'est pas dans la validation structurelle"),
        ("consignes-entretien", "un Prompt sans contenu",
         "« Content MAY be empty (a prompt can be purely descriptive) »"),
    ]:
        doc = next(d for d in documents if d.nom == nom)
        print(f"   {quoi}")
        ligne("     couches A / B / C",
              " / ".join(str(x) for x in couches(doc, catalogue)), 26)
        for l in plier(pourquoi, 58):
            print(f"        {l}")
    print()
    for l in plier(
        "Les deux premiers sont des oublis ; le troisieme est une decision, "
        "ecrite dans le commentaire du validateur. La distinction compte : "
        "on peut signaler les deux premiers a l'amont, pas le troisieme. Un "
        "controle maison a donc sa place — et il doit dire de quel cote il "
        "est."):
        print(f"   {l}")

    titre(5, "CE QUE `arctl init` / `build` / `apply` FONT VRAIMENT")
    cli = (AMONT / "declarative-cli.md").read_text(encoding="utf-8")
    debut = cli.index("arctl init agent summarizer")
    for l in cli[debut:debut + 230].splitlines()[:3]:
        print(f"      {l}")
    print()
    tableau(["commande", "ce qu'elle produit"], [
        ["arctl init agent NOM", "un squelette : agent.yaml + Dockerfile"],
        ["arctl build ./NOM --push", "une image, poussee — FACULTATIF"],
        ["arctl apply -f agent.yaml", "l'enregistrement au registre"],
    ], [30, 44])
    print()
    for l in plier(
        "Le « --push » est marque `optional` dans la doc amont, et c'est "
        "important : `apply` n'exige pas que l'image existe. On peut donc "
        "publier au catalogue un agent dont l'image n'a jamais ete "
        "construite. Les trois couches valideront, et l'echec attendra le "
        "deploiement."):
        print(f"   {l}")

    titre(6, "CE QU'UNE CI PEUT FAIRE, ET CE QU'ELLE NE PEUT PAS")
    print("   $ uv run python outils/verifier_manifeste.py \\")
    print("         catalogue/a-corriger.yaml --registre catalogue/portail\n")
    a_total = sum(couches(d, catalogue)[0] for d in documents)
    b_total = sum(couches(d, catalogue)[1] for d in documents)
    c_total = sum(couches(d, catalogue)[2] for d in documents)
    ligne("erreurs A (hors ligne)", str(a_total), 34)
    ligne("erreurs B (hors ligne)", str(b_total), 34)
    ligne("erreurs C (registre requis)", str(c_total), 34)
    ligne("code de sortie", str(len(documents) - len(muets)), 34)
    print()
    for l in plier(
        "Sans `--registre`, l'outil affiche « references NON VERIFIEES » "
        "plutot qu'un OK. C'est la seule ligne de ce projet qu'il faut "
        "recopier dans ses propres outils : un controle qui ne distingue pas "
        "« je n'ai pas trouve d'erreur » de « il n'y en a pas » ment a celui "
        "qui le lit."):
        print(f"   {l}")

    print("\n   Au chapitre suivant : consommer, et ce qu'epingler veut dire.\n")


if __name__ == "__main__":
    principal()
