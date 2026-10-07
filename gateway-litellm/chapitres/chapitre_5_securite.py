"""Chapitre 5 — Sécurité de bout en bout.

    uv run python chapitres/chapitre_5_securite.py

La chaîne tient si chaque maillon ne connaît que le secret du suivant. Ce
chapitre casse un maillon à la fois et regarde ce qui sort.

Ce chapitre ne charge pas litellm : il est instantané.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal.budgets import Registre                          # noqa: E402
from jobportal.commun import SECRET_JWT, ligne, titre, utf8     # noqa: E402
from jobportal.jetons import (JetonInvalide, lire_sans_verifier,  # noqa: E402
                              signer, verifier)


def main() -> None:
    utf8()
    registre = Registre()
    coffre = {equipe: registre.generer(equipe, 1.0).cle
              for equipe in ("data", "rh")}

    titre(1, "LA CHAINE")
    for de, vers, avec in (
            ("utilisateur", "passerelle", "son JWT"),
            ("passerelle", "proxy", "la cle virtuelle de l'equipe"),
            ("proxy", "fournisseur", "la cle du fournisseur")):
        ligne(f"{de} → {vers}", f"s'authentifie avec {avec}", 26)
    print()
    print("   Trois secrets, trois portees. Aucun ne traverse plus d'un")
    print("   maillon — c'est ce qui limite les degats de chaque fuite.")

    titre(2, "LA SUBSTITUTION, VERIFIEE")
    jwt = signer("diaguily@exemple.fr", "data", SECRET_JWT)
    try:
        equipe = verifier(jwt, SECRET_JWT).equipe
    except JetonInvalide as erreur:
        # Sur la branche « depart », verifier() est encore a ecrire. Le
        # chapitre doit le DIRE, pas s'interrompre sur une trace de pile.
        print(f"   verifier() refuse encore tout : {erreur}")
        print("   Completez jobportal/jetons.py, puis relancez ce chapitre.\n")
        equipe = "data"
    sortant = {"Authorization": f"Bearer {coffre[equipe]}"}
    ligne("recu par la passerelle", f"Bearer {jwt[:30]}…", 26)
    ligne("envoye au proxy", sortant["Authorization"], 26)
    ligne("le JWT est-il transmis ?",
          "OUI — fuite" if jwt in str(sortant) else "non", 26)
    print()
    print("   Si le JWT passait, le proxy — et sa base PostgreSQL, et ses")
    print("   journaux — detiendraient l'identite de chaque utilisateur final.")
    print("   Il n'en a pas besoin : c'est la CLE qui porte l'equipe, donc le")
    print("   budget. Et un en-tete « X-Team » ad hoc serait pire : il se")
    print("   falsifie, la cle non.")

    titre(3, "CE QU'UNE FUITE COUTE, MAILLON PAR MAILLON")
    for quoi, portee, degats in (
            ("un JWT vole", "un utilisateur, jusqu'a l'expiration",
             "le budget de son equipe, le temps du jeton"),
            ("une cle virtuelle volee", "une equipe",
             "son budget, jusqu'a la revocation — une ligne de commande"),
            ("la cle maitre volee", "tout le proxy",
             "generer des cles sans budget : tous les fournisseurs"),
            ("une cle fournisseur volee", "hors de votre controle",
             "depense illimitee, et la rotation est chez le fournisseur")):
        print(f"   {quoi}")
        print(f"      portee   {portee}")
        print(f"      degats   {degats}")
    print()
    print("   Le tableau se lit de haut en bas : plus le secret est profond,")
    print("   plus la fuite est chere et plus la reparation est lente. C'est")
    print("   exactement pourquoi on ne donne pas la cle maitre aux")
    print("   applications, meme « juste pour demarrer ».")

    titre(4, "UN JWT N'EST PAS UN COFFRE")
    print(f"   {lire_sans_verifier(jwt)}")
    print()
    print("   Lu sans le secret, en trois lignes de base64. Le secret ne")
    print("   prouve que l'INTEGRITE. Un numero de securite sociale, une")
    print("   adresse, un role interne places la sont publies — et rien ne")
    print("   leve d'erreur, jamais.")

    titre(5, "LES QUATRE REFUS, ET CE QU'ILS DISENT AU CLIENT")
    cas = [
        ("valide", jwt),
        ("signature d'un autre secret", signer("m", "data", "autre-secret")),
        ("expire", signer("d", "data", SECRET_JWT, duree=-1)),
        ("alg: none", signer("m", "finance", SECRET_JWT, algorithme="none")),
    ]
    for etiquette, candidat in cas:
        try:
            verifier(candidat, SECRET_JWT)
            ligne(etiquette, "accepte", 30)
        except JetonInvalide as erreur:
            ligne(etiquette, f"401 — {erreur}", 30)
    print()
    print("   Le detail part dans les journaux ; le client, lui, ne recoit")
    print("   qu'un 401. Lui dire « signature invalide » plutot que « jeton")
    print("   expire » indiquerait a un attaquant ce qu'il doit corriger.")

    titre(6, "LA ROTATION, ET POURQUOI os.environ")
    for ou, rotation in (
            ("cle en clair dans le config.yaml",
             "editer, commiter, relire en revue, redeployer — et elle reste "
             "dans l'historique git"),
            ("os.environ/NOM + coffre-fort",
             "changer la valeur dans le coffre, redemarrer le proxy")):
        print(f"   {ou}")
        print(f"      {rotation}")
    print()
    print("   La ligne qui compte est la fin de la premiere : une cle passee")
    print("   par git y reste apres correction. La faire tourner devient")
    print("   obligatoire, pas facultatif — et c'est ce cout-la qu'on")
    print("   s'epargne, pas les trois caracteres de « os.environ/ ».")

    print("\n   Au chapitre suivant : ce qui se mesure une fois que tout")
    print("   marche.\n")


if __name__ == "__main__":
    main()
