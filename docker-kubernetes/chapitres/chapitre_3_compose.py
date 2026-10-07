"""Chapitre 3 — Docker Compose : l'environnement complet.

    uv run python chapitres/chapitre_3_compose.py

Deux piles identiques a un detail pres : la forme de leur `depends_on`.
Le chapitre date chaque evenement des deux demarrages et compte les
connexions refusees.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import compose, console                # noqa: E402

RACINE = Path(__file__).resolve().parent.parent
PILE = RACINE / "pile"


def main() -> None:
    console.utf8()
    bonne, _ = compose.charger(PILE / "compose.yaml")
    naive, _ = compose.charger(PILE / "compose.naif.yaml")

    _un_fichier_une_pile(bonne)
    _le_graphe(bonne, naive)
    _la_mesure(bonne, naive)
    _le_healthcheck(bonne)
    _les_variables()


def _un_fichier_une_pile(projet: compose.Projet) -> None:
    print("1. UNE PILE DECRITE, PAS LANCEE A LA MAIN\n")
    print(f"   Projet « {projet.nom} » — {len(projet.services)} services, "
          f"{len(projet.volumes)} volume(s)\n")
    print(f"   {'SERVICE':<8} {'IMAGE / BUILD':<22} {'PUBLIE':<14} "
          f"{'DEPEND DE':<26} SANTE")
    for service in projet.services.values():
        source = service.image or f"build {service.construction}"
        publie = ", ".join(f"{h}→{c}" for h, c in service.ports_publies) \
            or (f"expose {service.exposes}" if service.exposes else "—")
        depend = ", ".join(f"{d.service} ({d.condition})"
                           for d in service.depend_de) or "—"
        sante = "oui" if service.sante.declaree else "—"
        print(f"   {service.nom:<8} {source:<22} {publie:<14} "
              f"{depend:<26} {sante}")

    print(f"\n   Compose cree un reseau prive, « {projet.reseau_par_defaut} »,")
    print("   et y joint tous les services. Chacun y est joignable PAR SON")
    print("   NOM, grace au DNS interne : l'application atteint la base par")
    print("   `db:5432`, jamais par une adresse IP ecrite quelque part.")
    print("\n   C'est pour cela que `DB_URL` vaut :")
    print(f"      {projet.services['app'].environnement['DB_URL']}")
    print("   Le nom `db` n'existe que dans ce reseau. Le meme fichier")
    print("   tourne donc a l'identique sur dix machines differentes.")
    print("\n   Le volume nomme, lui, survit aux recreations de conteneurs :")
    for volume in projet.volumes:
        print(f"      {volume}  →  monte dans « db » "
              f"sur /var/lib/postgresql/data")
    print("   Sans lui, un `docker compose down` puis `up` rendrait une")
    print("   base vide — la couche d'ecriture d'un conteneur meurt avec")
    print("   lui, on l'a vu au chapitre 1.")


def _le_graphe(bonne: compose.Projet, naive: compose.Projet) -> None:
    print("\n\n2. L'ORDRE DE DEMARRAGE EST UN TRI TOPOLOGIQUE\n")
    for titre, projet in (("compose.yaml", bonne),
                          ("compose.naif.yaml", naive)):
        print(f"   {titre:<20} {' → '.join(compose.ordre(projet))}")
    print("\n   `depends_on` construit un graphe ; Compose le trie et lance")
    print("   les conteneurs dans cet ordre. Un cycle est refuse — et c'est")
    print("   le seul cas ou Compose vous arrete :\n")
    cyclique = compose.Projet("cycle", {
        "a": compose.Service("a", depend_de=[compose.Dependance("b", "service_started")]),
        "b": compose.Service("b", depend_de=[compose.Dependance("a", "service_started")]),
    })
    try:
        compose.ordre(cyclique)
    except compose.ErreurCompose as erreur:
        print(f"      a depend de b, b depend de a  →  {erreur}")
    print("\n   ⚠️ Notez ce que ce tri NE dit pas : l'ordre de demarrage")
    print("   n'est pas l'ordre de disponibilite. C'est la section")
    print("   suivante, et c'est la seule chose a retenir du chapitre.")


def _la_mesure(bonne: compose.Projet, naive: compose.Projet) -> None:
    print("\n\n3. LA MESURE QUI TRANCHE : `depends_on` N'ATTEND PAS\n")
    for titre, projet, forme in (
            ("compose.naif.yaml", naive, "depends_on: [db]"),
            ("compose.yaml", bonne, "depends_on: db.condition: service_healthy")):
        evenements = compose.demarrer(projet)
        rates = compose.echecs(evenements)
        print(f"   ── {titre}   ({forme})\n")
        for evenement in evenements:
            print(f"      {evenement}")
        print(f"\n      → {len(rates)} connexion(s) refusee(s)\n")

    print("   La difference tient a une seule chose : la FORME COURTE de")
    print("   `depends_on` vaut `condition: service_started`. Elle attend")
    print("   que le conteneur soit demarre — pas que PostgreSQL ait fini")
    print("   son `initdb` et ouvert son port.")
    base = naive.services["db"]
    ecart = base.accepte_apres - base.demarre_en
    print(f"\n   Entre les deux, il y a ici {ecart:.1f} secondes.")
    print("   L'application, qui ouvre sa source de donnees pendant son")
    print("   propre demarrage, tombe dedans.")
    print("\n   ⚠️ Et le pire est que cela marche une fois sur deux. Sur une")
    print("   machine rapide, avec un volume deja initialise, la base est")
    print("   prete en une seconde et personne ne voit rien. Le bogue")
    print("   apparait sur la machine du nouveau collegue, ou en CI.")
    print("\n   La reponse n'est pas « ajouter un `sleep 10` » : c'est un")
    print("   `healthcheck` cote base, et `condition: service_healthy`")
    print("   cote application. La reponse complementaire, cote code, est")
    print("   un client qui REESSAIE — parce qu'en production, la base")
    print("   redemarrera un jour sans que l'application ne redemarre.")


def _le_healthcheck(projet: compose.Projet) -> None:
    print("\n\n4. LE HEALTHCHECK, ET SON RETARD STRUCTUREL\n")
    base = projet.services["db"]
    accepte = base.accepte_apres
    vert = compose.premier_vert(base.sante, accepte)
    print(f"   Le healthcheck declare : {' '.join(base.sante.commande)}")
    print(f"      intervalle : {base.sante.intervalle:g}s   "
          f"essais : {base.sante.essais}   "
          f"start_period : {base.sante.demarrage:g}s\n")
    print(f"      la base accepte des connexions a  t={accepte:.2f}s")
    print(f"      le healthcheck passe au vert a    t={vert:.2f}s")
    print(f"      retard                             {vert - accepte:.2f}s\n")
    print("   ⚠️ Ce retard n'est pas un defaut : c'est la definition d'une")
    print("   sonde periodique. Docker lance la premiere apres")
    print(f"   `interval` ({base.sante.intervalle:g}s ici), puis toutes les")
    print("   `interval`. Un service est donc declare sain au premier tick")
    print("   QUI SUIT sa disponibilite reelle.")
    print("\n   Consequence pratique : un `interval: 30s` — la valeur par")
    print("   defaut — ajoute jusqu'a trente secondes a chaque `compose")
    print("   up`. En developpement, on descend a 2 s ; en production sur")
    print("   Kubernetes, c'est le meme arbitrage, entre reactivite et")
    print("   charge sur le service sonde.")


def _les_variables() -> None:
    print("\n\n5. LES VARIABLES, ET LA CHAINE VIDE\n")
    fichier = PILE / ".env"
    variables = compose.lire_env(fichier.read_text(encoding="utf-8"))
    print(f"   `pile/.env` fournit : {sorted(variables)}\n")

    print("   Trois formes, et trois comportements :\n")
    exemples = [
        ("${DB_NOM}", "definie dans .env"),
        ("${PROFIL:-dev}", "absente, avec valeur par defaut"),
        ("${REGISTRE}", "absente, SANS valeur par defaut"),
    ]
    for modele, description in exemples:
        manquantes: list[str] = []
        rendu = compose.interpoler(modele, variables, manquantes)
        alerte = f"   ⚠️ {manquantes} non definie(s)" if manquantes else ""
        print(f"      {modele:<18} → « {rendu} »   ({description}){alerte}")

    projet, manquantes = compose.charger(
        PILE / "compose.yaml", {"PROFIL": "production"})
    print(f"\n   Avec PROFIL=production dans l'environnement :")
    print(f"      SPRING_PROFILES_ACTIVE = "
          f"{projet.services['app'].environnement['SPRING_PROFILES_ACTIVE']}")
    print("\n   ⚠️ Une variable non definie et sans defaut devient une")
    print("   CHAINE VIDE. Compose ecrit un avertissement et demarre quand")
    print("   meme — l'image part avec `DB_PASSWORD=`, et c'est le service")
    print("   qui echoue plus loin, avec un message sans rapport.")
    print("\n   D'ou deux habitudes : `${VAR:?message}` pour rendre une")
    print("   variable obligatoire, et un `.env.exemple` versionne a cote")
    print("   du `.env` qui, lui, ne l'est jamais. C'est exactement la")
    print("   meme discipline que le `required` de Helm, au chapitre 6.")
    print()


if __name__ == "__main__":
    main()
