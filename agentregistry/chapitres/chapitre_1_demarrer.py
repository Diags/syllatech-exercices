"""Chapitre 1 — Démarrer avec AgentRegistry.

    uv run python chapitres/chapitre_1_demarrer.py

AgentRegistry est un service Go devant une base PostgreSQL, qu'on lève avec
Docker Compose. Ce projet ne le lève pas. Ce qu'il a, c'est **le contrat que
ce service publie** — `amont/openapi.yaml` — et les manifestes d'exemple du
dépôt. Tout ce qui suit se lit dans ces fichiers.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import schema_publie                              # noqa: E402
from jobportal.catalogue import Catalogue                        # noqa: E402
from jobportal.commun import (                                   # noqa: E402
    AMONT, EXEMPLES_AMONT, SCHEMA, ligne, plier, tableau, titre, utf8,
)
from jobportal.manifeste import (                                # noqa: E402
    GROUPE_VERSION, TYPES, charger, charger_dossier,
)


def principal() -> None:
    utf8()

    titre(1, "CE QUI EST INSTALLE, ET CE QUI NE L'EST PAS")
    for quoi, etat in [
        ("agentregistry (le service Go)", "absent — une image Docker + PostgreSQL"),
        ("arctl (le CLI)", "absent — il s'installe par curl | bash"),
        ("l'interface web", "absente — elle vit dans le service"),
        ("le contrat OpenAPI publie", f"{len(SCHEMA.read_text(encoding='utf-8').splitlines())} lignes, ici"),
        ("les manifestes d'exemple", f"{len(list(EXEMPLES_AMONT.glob('*.yaml')))} fichiers, ici"),
    ]:
        ligne(quoi, etat, 32)
    print()
    for l in plier(
        "Ce projet ne simule donc pas le registre : il applique ses regles a "
        "des manifestes. C'est le decoupage de l'amont lui-meme — la "
        "validation d'un manifeste n'a besoin ni de base, ni de reseau, et "
        "elle decide de tout ce qui entre au catalogue."):
        print(f"   {l}")

    titre(2, "CE QU'IL FAUT VRAIMENT POUR LEVER LE REGISTRE")
    readme = (AMONT / "README.md").read_text(encoding="utf-8").splitlines()
    debut = next(i for i, l in enumerate(readme) if l.startswith("# 1. Install"))
    for l in readme[debut:debut + 10]:
        print(f"      {l}")
    print()
    for l in plier(
        "Trois etapes, et la troisieme est un `docker compose up`. Le support "
        "de cours en annonce une seule — « le premier appel a arctl version "
        "leve le daemon tout seul ». Dans la procedure publiee, `arctl "
        "version` sert a LIRE le numero de version, pour telecharger le "
        "fichier Compose qui correspond."):
        print(f"   {l}")
    print()
    print("   Consequence pratique : sans Docker Desktop et Compose v2, il")
    print("   n'y a pas de registre — et sur un poste d'entreprise, c'est la")
    print("   vraie premiere difficulte du chapitre 1.")

    titre(3, "UN MANIFESTE, C'EST DU YAML DE FORME KUBERNETES")
    print("   amont/exemples/mcp.yaml, tel quel :\n")
    for l in (EXEMPLES_AMONT / "mcp.yaml").read_text(
            encoding="utf-8").splitlines()[:16]:
        print(f"      {l}")
    print()
    doc = next(iter(charger(EXEMPLES_AMONT / "mcp.yaml")))
    ligne("apiVersion", doc.api, 22)
    ligne("kind", doc.type, 22)
    ligne("metadata.name", doc.nom, 22)
    ligne("champs de spec", ", ".join(sorted(doc.spec)), 22)

    titre(4, "L'apiVersion N'EST PAS CELLE DU SUPPORT DE COURS")
    ligne("dans le depot", GROUPE_VERSION, 26)
    ligne("dans le support", "registry.agentregistry.dev/v1", 26)
    print()
    documents = _tous_les_documents_amont()
    conformes = sum(1 for d in documents if d.api == GROUPE_VERSION)
    ligne("documents d'exemple conformes",
          f"{conformes} sur {len(documents)}", 26)
    print()
    for l in plier(
        "Ce n'est pas une coquille sans effet : `Scheme.Decode` refuse une "
        "apiVersion inconnue AVANT d'appeler le moindre validateur — "
        "« unsupported apiVersion %q (want %q) ». Un manifeste copie du "
        "support de cours ne depasse donc pas le decodage."):
        print(f"   {l}")

    titre(5, "CE QUE LE FICHIER NE DIT PAS")
    print("   Le registre stocke une identite en trois morceaux. Combien de")
    print("   manifestes d'exemple les ecrivent tous les trois ?\n")
    documents = _tous_les_documents_amont()
    sans_etiquette = sum(1 for d in documents if not d.etiquette)
    tableau(["manifeste", "espace", "etiquette", "identite stockee"],
            [[d.origine,
              d.espace or "(absent)",
              d.etiquette or "(absent)",
              str(Catalogue.identite_de(d))]
             for d in documents],
            [22, 12, 12, 48])
    print()
    for l in plier(
        f"Aucun n'ecrit son espace de noms, et {sans_etiquette} sur "
        f"{len(documents)} n'ecrivent pas leur etiquette. Le serveur les "
        "remplit : l'espace devient `default`, l'etiquette `latest`. Ce "
        "qu'on relit en revue et ce que le registre stocke ne sont donc deja "
        "plus le meme objet — et l'ecart porte precisement sur les deux "
        "champs qui font l'identite."):
        print(f"   {l}")

    titre(6, "NEUF TYPES, ET UN CONTRAT QUI LES PORTE TOUS")
    tableau(["kind", "persistance", "identite"],
            [[t, s, "(espace, nom, etiquette)"
              if s == "TaggedArtifact" else "(espace, nom)"]
             for t, s in sorted(TYPES.items())], [16, 20, 30])
    print()
    ligne("types avec un schema publie",
          str(len(schema_publie.types_publies())), 32)
    ligne("dont le cours en presente", "4 — « les 4 artefacts du registre »", 32)
    print()
    print("   Le chapitre 2 regarde ce que sont les cinq autres, et pourquoi")
    print("   la distinction « artefact etiquete / objet mutable » compte plus")
    print("   que le compte.")

    titre(7, "CE QUE LE PROJET VA MESURER")
    for quoi, ou in [
        ("trois couches de controle, et ce que chacune rate", "chapitre 3"),
        ("un `spec.source: {}` que personne n'attrape", "chapitre 3"),
        ("une reference sans `kind` : valide ici, refusee la", "chapitre 3"),
        ("ce qu'« epingler une version » veut vraiment dire", "chapitre 4"),
        ("l'ordre d'application, et le dossier qui casse", "chapitre 4"),
        ("le champ du schema qui ne sait pas porter un secret", "chapitre 5"),
        ("la version publiee quand il n'y en a plus", "chapitre 6"),
    ]:
        print(f"   {quoi:<54}{ou}")

    print("\n   Au chapitre suivant : les artefacts, et leur nombre exact.\n")


def _tous_les_documents_amont():
    return charger_dossier(EXEMPLES_AMONT)


if __name__ == "__main__":
    principal()
