"""Chapitre 3 — Spring Cloud Gateway devant le proxy.

    uv run python chapitres/chapitre_3_gateway.py

⚠️ Ce chapitre n'exécute pas Spring : il exécute **les mêmes étapes**, écrites
en Python pour être inspectables. Le code Java du cours reste la référence.

Ce que la ligne Spring `.oauth2ResourceServer(o -> o.jwt(withDefaults()))`
fait en une ligne, ce chapitre le fait en quatre — parce que ce sont ces
quatre-là qu'on rate quand on réimplémente la chaîne ailleurs.

Ce chapitre ne charge pas litellm : il est instantané.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal.commun import SECRET_JWT, ligne, titre, utf8      # noqa: E402
from jobportal.jetons import (JetonInvalide, lire_sans_verifier,  # noqa: E402
                              signer, verifier)


def main() -> None:
    utf8()

    titre(1, "UN JWT, DEMONTE")
    jwt = signer("diaguily@exemple.fr", "data", SECRET_JWT)
    entete, charge, signature = jwt.split(".")
    ligne("en-tete", f"{entete[:28]}…", 12)
    ligne("charge utile", f"{charge[:28]}…", 12)
    ligne("signature", f"{signature[:28]}…", 12)
    print()
    print("   Et voici la charge utile, lue SANS le secret :")
    print(f"      {lire_sans_verifier(jwt)}")
    print()
    print("   Rien n'est chiffre dans un JWT. Le secret ne sert qu'a prouver")
    print("   que personne ne l'a modifie. Y mettre une donnee confidentielle")
    print("   revient a la publier — c'est la premiere erreur, et elle ne")
    print("   provoque jamais d'incident visible.")

    titre(2, "LES QUATRE REFUS")
    autre = signer("mallory@exemple.fr", "data", "un-autre-secret")
    cas = [
        ("un jeton valide", jwt),
        ("signe avec un autre secret", autre),
        ("expire il y a une heure",
         signer("d", "data", SECRET_JWT, duree=-3600)),
        ("sans claim « team »", signer("d", "", SECRET_JWT)),
        ("avec « alg »: none", signer("d", "data", SECRET_JWT,
                                      algorithme="none")),
    ]
    for etiquette, candidat in cas:
        try:
            jeton = verifier(candidat, SECRET_JWT)
            ligne(etiquette, f"ACCEPTE — equipe « {jeton.equipe} »", 32)
        except JetonInvalide as erreur:
            ligne(etiquette, f"refuse  — {erreur}", 32)

    titre(3, "LE REFUS QU'ON OUBLIE")
    print("   « alg: none » est un jeton parfaitement bien forme, sans")
    print("   signature. Une bibliotheque qui lit l'algorithme DANS le jeton")
    print("   pour decider comment le verifier l'accepte — sans secret.\n")
    faux = signer("mallory@exemple.fr", "finance", SECRET_JWT,
                  algorithme="none")
    print(f"   le jeton  : {faux[:52]}…")
    print(f"   il annonce : {lire_sans_verifier(faux)}")
    print()
    print("   L'algorithme attendu est celui du SERVEUR. Le lire dans le")
    print("   jeton revient a laisser l'attaquant choisir comment on le")
    print("   verifie. C'est pour cela que jetons.py compare a une constante")
    print("   et jamais a entete[\"alg\"].")

    titre(4, "CE QUE CHAQUE MAILLON CONNAIT")
    for maillon, sait, ignore in (
            ("le client", "son JWT", "la cle virtuelle, les cles fournisseur"),
            ("la passerelle", "le secret JWT, les cles virtuelles",
             "les cles des fournisseurs"),
            ("le proxy", "les cles virtuelles et fournisseur",
             "vos utilisateurs, leur identite"),
            ("le fournisseur", "sa propre cle", "tout le reste")):
        print(f"   {maillon}")
        print(f"      connait  {sait}")
        print(f"      ignore   {ignore}")
    print()
    print("   Chaque maillon ne connait que le secret du SUIVANT, jamais")
    print("   celui d'apres. Une passerelle compromise ne livre donc pas les")
    print("   cles des fournisseurs, et un proxy compromis ne livre pas")
    print("   l'identite de vos utilisateurs.")

    titre(5, "LA SUBSTITUTION, ET POURQUOI CE N'EST PAS UN AJOUT")
    print("   Le filtre Spring REMPLACE le jeton client par la cle virtuelle")
    print("   de l'equipe. Il ne l'ajoute pas a cote.\n")
    ligne("ce que le client envoie", f"Authorization: Bearer {jwt[:24]}…", 26)
    ligne("ce que le proxy recoit", "Authorization: Bearer sk-data-001", 26)
    print()
    print("   Transmettre les deux « au cas ou » donnerait au proxy — et a ses")
    print("   journaux, et a sa base PostgreSQL — l'identite de chaque")
    print("   utilisateur final. Le proxy n'en a pas besoin : c'est la CLE qui")
    print("   porte l'equipe, donc le budget. Un en-tete « X-Team » ad hoc")
    print("   serait pire encore : il se falsifie, la cle non.")

    print("\n   Au chapitre suivant : ce que cette cle permet, et jusqu'ou.\n")


if __name__ == "__main__":
    main()
