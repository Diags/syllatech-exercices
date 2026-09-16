"""Chapitre 1 — Demarrer avec Docker.

    uv run python chapitres/chapitre_1_docker.py

Une image n'est pas un dossier : c'est un empilement de calques en lecture
seule. Tout ce que le chapitre montre decoule de cette phrase — la taille
transportee, ce qu'un `rm` n'enleve pas, et pourquoi `latest` n'est pas
une version.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                                  # noqa: E402
from jobportal import compose, construction, contexte          # noqa: E402
from jobportal import dockerfile, image                        # noqa: E402

RACINE = Path(__file__).resolve().parent.parent
CONTEXTE = RACINE / "contexte"


def main() -> None:
    console.utf8()
    ctx = contexte.charger(CONTEXTE)
    nu = contexte.charger(CONTEXTE, appliquer_dockerignore=False)
    bonne = construction.construire(
        dockerfile.analyser_fichier(CONTEXTE / "Dockerfile"), ctx,
        construction.Cache(), "jobportal:1.0")
    naive = construction.construire(
        dockerfile.analyser_fichier(CONTEXTE / "Dockerfile.naif"), nu,
        construction.Cache(), "jobportal:naif")

    _un_empilement(bonne)
    _ce_que_lon_transporte(naive)
    _le_tag_qui_bouge()
    _le_pid_1(bonne, naive)
    _les_ports()


def _un_empilement(bonne: construction.Construction) -> None:
    print("1. UNE IMAGE EST UN EMPILEMENT DE CALQUES\n")
    print("   `docker history jobportal:1.0` — ce que le build a produit :\n")
    for ligne in image.rendre(bonne.image):
        print(f"   {ligne}")
    print("\n   Chaque instruction qui touche au systeme de fichiers pose un")
    print("   calque en LECTURE SEULE. Les autres — `WORKDIR`, `USER`,")
    print("   `ENV`, `EXPOSE`, `ENTRYPOINT` — ne changent que des")
    print("   metadonnees : elles apparaissent dans l'historique avec une")
    print("   taille nulle.")
    print("\n   Un CONTENEUR, c'est cet empilement plus une fine couche")
    print("   d'ecriture par-dessus. Lancer dix conteneurs de cette image")
    print("   ne copie donc pas dix fois les 233 Mo : les calques sont")
    print("   partages, seules les couches d'ecriture different. C'est ce")
    print("   qui rend un conteneur si rapide a demarrer, et c'est aussi")
    print("   pourquoi tout ce qui est ecrit hors d'un volume disparait")
    print("   avec le conteneur.")


def _ce_que_lon_transporte(naive: construction.Construction) -> None:
    print("\n\n2. CE QUE L'ON VOIT, ET CE QUE L'ON TRANSPORTE\n")
    finale = naive.image
    print("   La meme application, construite par `Dockerfile.naif` :\n")
    print(f"      somme des calques (ce qui est transfere) : "
          f"{image.octets(finale.taille):>9}")
    print(f"      vue fusionnee (ce que `ls` montre)       : "
          f"{image.octets(finale.taille_visible):>9}")
    print(f"      ecart                                    : "
          f"{image.octets(finale.poids_mort):>9}\n")
    print("   Cet ecart a un nom et une cause : deux `RUN rm` places apres")
    print("   les couches qu'ils pretendent nettoyer.\n")
    for couche in finale.couches:
        if couche.supprimes:
            print(f"      {couche.instruction:<28} efface "
                  f"{', '.join(sorted(couche.supprimes))}")
    print("\n   ⚠️ Un calque ne peut RIEN retirer de ceux d'en dessous. Il")
    print("   pose une marque de suppression (`whiteout`) : le fichier")
    print("   disparait de la vue, et reste dans l'image. Il est transfere")
    print("   a chaque `docker pull`, sur chaque noeud, a chaque")
    print("   deploiement.")

    trouves = finale.fouiller("/app/.env")
    print("\n   La demonstration qui fait mal — le fichier `.env` du projet,")
    print("   copie par le `COPY . .` puis efface par un `RUN rm` :\n")
    print(f"      visible dans le conteneur : {finale.lire('/app/.env')}")
    for couche, fichier in trouves:
        print(f"      present dans le calque    : {couche.identifiant}")
        contenu = (fichier.contenu or b"").decode("utf-8")
        for ligne in contenu.splitlines():
            if "=" in ligne and not ligne.startswith("#"):
                print(f"         {ligne}")
    print("\n   `docker save` puis `tar -x` suffisent a le lire. Un secret")
    print("   entre dans une image ne s'en retire pas : il se REVOQUE.")
    print("   Et la seule facon de ne pas l'embarquer est de ne jamais le")
    print("   poser dans un calque — c'est-a-dire `.dockerignore`, les")
    print("   montages de secrets BuildKit, ou un etage de construction")
    print("   separe. Le chapitre 2 mesure les trois.")


def _le_tag_qui_bouge() -> None:
    print("\n\n3. `latest` N'EST PAS UNE VERSION\n")
    exemples = [
        "eclipse-temurin:21-jre",
        "maven:3.9-eclipse-temurin-21",
        "openjdk",
        "registry.exemple.fr/jobportal",
        "postgres:16",
    ]
    print("   Le tag reellement utilise, selon ce qui est ecrit :\n")
    for base in exemples:
        etape = dockerfile.Etape(base, None, 0, [])
        tag = dockerfile.tag_de_base(etape)
        marque = "  ⚠️ tag mobile" if tag == "latest" else ""
        print(f"      FROM {base:<38} → {tag}{marque}")
    print("\n   Un tag n'est pas un identifiant : c'est une etiquette")
    print("   DEPLACABLE. `openjdk` vaut `openjdk:latest`, et l'image")
    print("   derriere ce nom change sans que rien ne bouge chez vous.")
    print("   Deux constructions du meme Dockerfile, a deux semaines")
    print("   d'intervalle, peuvent donc produire deux images differentes.")
    print("\n   Le seul identifiant immuable est le condensat :")
    print("      FROM eclipse-temurin@sha256:1a2b3c…")
    print("   C'est ce que fait le verrouillage de dependances, et c'est ce")
    print("   que le chapitre 6 refait cote deploiement, avec le SHA du")
    print("   commit a la place de `latest`.")


def _le_pid_1(bonne: construction.Construction,
              naive: construction.Construction) -> None:
    print("\n\n4. LA FORME DE L'`ENTRYPOINT`, ET LE SIGTERM PERDU\n")
    for nom, resultat in (("Dockerfile", bonne), ("Dockerfile.naif", naive)):
        img = resultat.image
        forme = "exec" if img.forme_exec else "shell"
        print(f"   {nom:<18} forme {forme:<6} "
              f"PID 1 = {'votre programme' if img.forme_exec else '/bin/sh'}")
        print(f"   {'':<18} utilisateur : {img.utilisateur}")
    print("\n   ⚠️ En forme SHELL, Docker lance `/bin/sh -c \"votre")
    print("   commande\"`. Le PID 1 est donc le shell, et un shell POSIX ne")
    print("   transmet pas les signaux a son enfant. A l'arret, le SIGTERM")
    print("   part au shell, votre application ne le recoit jamais, et")
    print("   c'est le SIGKILL de fin de delai de grace qui la tue —")
    print("   requetes coupees, transactions perdues, a chaque")
    print("   deploiement.")
    print("\n   En forme EXEC (`[\"java\", \"-jar\", …]`), il n'y a pas de")
    print("   shell : votre programme EST le PID 1, il recoit le SIGTERM,")
    print("   et il peut fermer proprement. La contrepartie est qu'il n'y a")
    print("   plus ni variables d'environnement etendues, ni `&&` — ce qui")
    print("   se regle avec un script d'entree, pas en revenant a la forme")
    print("   shell.")
    print("\n   Et la seconde ligne du tableau : sans `USER`, un conteneur")
    print("   tourne en ROOT. Ce n'est pas le root de la machine, mais")
    print("   c'est le root du conteneur — et toute faille d'echappement")
    print("   part de la.")


def _les_ports() -> None:
    print("\n\n5. `EXPOSE` NE PUBLIE RIEN\n")
    pile, _ = compose.charger(RACINE / "pile" / "compose.yaml")
    naive_pile, _ = compose.charger(RACINE / "pile" / "compose.naif.yaml")

    print("   Ce que les deux piles ouvrent sur la MACHINE :\n")
    for titre, projet in (("compose.yaml", pile),
                          ("compose.naif.yaml", naive_pile)):
        print(f"      {titre}")
        for service in projet.services.values():
            publies = service.ports_publies
            if publies:
                for hote, conteneur in publies:
                    marque = ("  ⚠️ la base est joignable depuis la machine"
                              if conteneur == 5432 else "")
                    print(f"         {service.nom:<8} hote:{hote} → "
                          f"conteneur:{conteneur}{marque}")
            elif service.exposes:
                print(f"         {service.nom:<8} expose {service.exposes} "
                      f"— rien sur l'hote")
            else:
                print(f"         {service.nom:<8} rien")
        print()
    print("   `EXPOSE` dans un Dockerfile et `expose:` dans un Compose sont")
    print("   de la DOCUMENTATION : ils declarent le port sur lequel le")
    print("   service ecoute, et n'ouvrent rien. Seul `-p` — `ports:` en")
    print("   Compose — publie un port sur la machine.")
    print("\n   ⚠️ La consequence est de securite. `ports: [\"5432:5432\"]`")
    print("   ouvre PostgreSQL sur toutes les interfaces de l'hote, et")
    print("   `docker` ecrit ses regles directement dans le pare-feu : un")
    print("   `ufw deny 5432` ne suffit pas a le refermer. Les services")
    print("   internes se joignent par leur nom sur le reseau du projet —")
    print("   ici `db:5432` — et n'ont aucune raison d'etre publies.")
    print()


if __name__ == "__main__":
    main()
