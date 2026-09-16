"""Chapitre 5 — Memory et Identity.

    uv run python chapitres/chapitre_5_memoire.py

Deux mémoires, et la ligne qui les sépare : le court terme est indexé par
SESSION, le long terme par ACTEUR. Tout le chapitre tient à cette phrase, et
la confondre produit les deux pannes symétriques — tout oublier à chaque
session, ou tout rejouer.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal.commun import ligne, titre, utf8              # noqa: E402
from jobportal.memoire import (Coffre, Memoire, Message,     # noqa: E402
                               sdk_reel)

LUNDI = [("USER", "Bonjour, je cherche un poste DevOps a Lyon"),
         ("ASSISTANT", "Trois offres correspondent."),
         ("USER", "Je prefere un CDI, et je vise 60k"),
         ("ASSISTANT", "Noté."),
         ("USER", "J'ai 8 ans d'experience"),
         ("ASSISTANT", "Votre profil est senior.")]

JEUDI = [("USER", "Du nouveau sur les offres ?")]


def rejouer(memoire: Memoire, acteur: str, session: str, tours) -> None:
    for role, texte in tours:
        memoire.create_event(actor_id=acteur, session_id=session,
                             messages=[Message(role, texte)])


def main() -> None:
    utf8()

    titre(1, "CE QUE LE SDK EXPOSE VRAIMENT")
    reel = sdk_reel()
    print(f"   {len(reel['strategies'])} strategies, {reel['total']} methodes "
          f"sur MemoryClient.\n")
    for nom in reel["strategies"]:
        print(f"      {nom}")
    print()
    print("   Les variantes « _and_wait » attendent que la strategie soit")
    print("   active avant de rendre la main : creer une memoire n'est pas")
    print("   instantane cote AWS, et un create_event envoye trop tot est")
    print("   accepte sans etre indexe.")

    titre(2, "COURT TERME ET LONG TERME")
    memoire = (Memoire().add_user_preference_strategy()
               .add_semantic_strategy())
    rejouer(memoire, "diaguily", "lundi", LUNDI)

    messages = memoire.list_events("lundi")
    utilisateur = [m for m in messages if m.role == "USER"]
    ligne("messages de la session lundi",
          f"{len(messages)}  ({len(utilisateur)} de l'utilisateur)", 32)
    ligne("souvenirs long terme",
          str(len(memoire.tout("diaguily"))), 32)
    print()
    for souvenir in memoire.tout("diaguily"):
        print(f"      {souvenir}")
    print()
    print(f"   {len(utilisateur)} messages d'utilisateur produisent "
          f"{len(memoire.tout('diaguily'))} souvenirs : la memoire longue")
    print("   n'est pas un RESUME de la conversation, c'est autre chose. Elle")
    print("   ne garde pas des tours de dialogue mais des faits extraits, et")
    print("   un seul message peut en contenir trois.")
    print()
    print("   Ce qui compte n'est donc pas qu'elle soit plus petite — a ce")
    print("   stade elle ne l'est pas — mais qu'elle ne grossisse PAS avec la")
    print("   longueur de la conversation. La section 6 le mesure.")

    titre(3, "UNE NOUVELLE SESSION REPART D'UN HISTORIQUE VIDE")
    rejouer(memoire, "diaguily", "jeudi", JEUDI)
    ligne("historique de « jeudi »",
          f"{len(memoire.list_events('jeudi'))} message(s)", 30)
    ligne("souvenirs de « diaguily »",
          f"{len(memoire.tout('diaguily'))} — inchanges", 30)
    trouves = memoire.retrieve_memories(
        "diaguily", {"searchQuery": "quelle ville et quel contrat ?"})
    print()
    print("   Ce que l'agent retrouve jeudi, sans avoir relu lundi :")
    for souvenir in trouves:
        print(f"      {souvenir}")
    print()
    print("   Les MESSAGES appartiennent a la session, les SOUVENIRS a")
    print("   l'acteur. C'est la distinction qui fait qu'un agent « vous")
    print("   connait » sans relire trois mois d'historique a chaque tour.")

    titre(4, "DEUX ACTEURS NE SE VOIENT PAS")
    rejouer(memoire, "marie", "lundi-marie",
            [("USER", "Je cherche un CDD a Nantes")])
    for acteur in ("diaguily", "marie"):
        contenus = [s.contenu for s in memoire.tout(acteur)]
        ligne(acteur, f"{len(contenus)} souvenirs", 14)
        for contenu in contenus:
            print(f"      · {contenu}")
    print()
    print("   L'isolation par acteur n'est pas un confort : deux candidats")
    print("   partagent le meme agent, et rien de l'un ne doit arriver dans")
    print("   la reponse faite a l'autre. C'est le meme cloisonnement que")
    print("   l'isolation par session du chapitre 1, un cran plus haut.")

    titre(5, "UN MESSAGE DE L'ASSISTANT NE NOURRIT PAS LA MEMOIRE")
    avant = len(memoire.tout("diaguily"))
    memoire.create_event("diaguily", "lundi", [Message(
        "ASSISTANT", "Je vous propose plutot Bordeaux en freelance")])
    apres = len(memoire.tout("diaguily"))
    ligne("souvenirs avant", str(avant), 22)
    ligne("souvenirs apres", str(apres), 22)
    print()
    print("   Extraire les mots de l'assistant lui ferait croire qu'il a")
    print("   APPRIS ce qu'il vient de dire. Au bout de trois tours, il")
    print("   defend une preference qu'il a inventee lui-meme — et il la")
    print("   defend d'autant mieux qu'elle est « en memoire ».")

    titre(6, "LA MEMOIRE PLAFONNE : REPETER N'AJOUTE PLUS RIEN")
    ligne("avant", f"{len(memoire.tout('diaguily'))} souvenirs", 24)
    for tour in range(1, 5):
        memoire.create_event("diaguily", "lundi",
                             [Message("USER", "Je prefere un CDI")])
        ligne(f"apres la repetition {tour}",
              f"{len(memoire.tout('diaguily'))} souvenirs", 24)
    print()
    print("   La premiere repetition ajoute UN souvenir — « je prefere un")
    print("   cdi » n'est pas le meme texte que « je prefere un cdi, et je")
    print("   vise 60k », et c'est bien une preference de plus. Les")
    print("   suivantes n'ajoutent rien : le contenu est deja la.")
    print()
    print("   C'est la propriete qui compte a la centieme session. Sans elle,")
    print("   la memoire grossirait a chaque tour sans rien apprendre, et la")
    print("   recherche remonterait dix fois le meme fait.")
    print()
    print("   ⚠️ Ce qu'on ne fait PAS ici : invalider un fait qui change.")
    print("   « Finalement, plutot Paris » ajoute un souvenir sans fermer")
    print("   l'ancien, et l'agent recoit alors Lyon ET Paris. Le cours")
    print("   « Zep » traite exactement ce probleme, avec des faits dates.")

    titre(7, "IDENTITY : AGIR AU NOM DE QUELQU'UN")
    coffre = Coffre()
    coffre.deposer("diaguily", "google-calendar", "ya29.dia-cal-7f21c")
    coffre.deposer("diaguily", "gmail", "ya29.dia-mail-04b9e")
    coffre.deposer("marie", "google-calendar", "ya29.mar-cal-be330")
    for acteur in ("diaguily", "marie", "inconnu"):
        jeton = coffre.obtenir(acteur, "google-calendar")
        ligne(f"jeton calendrier de {acteur}",
              jeton or "aucun", 32)
    ligne("revocation de diaguily",
          f"{coffre.revoquer('diaguily')} jeton(s) retire(s)", 32)
    ligne("son jeton gmail apres cela",
          str(coffre.obtenir("diaguily", "gmail")), 32)
    print()
    print("   Un jeton par acteur et par fournisseur. L'alternative — un")
    print("   compte de service partage — marche aussi, jusqu'a deux")
    print("   questions : « qui a fait cette action ? », et « comment")
    print("   retirer l'acces a quelqu'un qui part ? ». Aucune des deux n'a")
    print("   de reponse avec un compte partage.")

    print("\n   Au chapitre suivant : ce qu'on regarde quand tout cela")
    print("   tourne en production.\n")


if __name__ == "__main__":
    main()
