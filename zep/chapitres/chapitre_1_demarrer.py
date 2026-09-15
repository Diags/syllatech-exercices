"""Chapitre 1 — La memoire en quatre appels.

    uv run python chapitres/chapitre_1_demarrer.py
"""
from __future__ import annotations
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                                # noqa: E402
from jobportal.memoire import Memoire, Message               # noqa: E402


def le(annee, mois, jour):
    return datetime(annee, mois, jour, tzinfo=timezone.utc)


def main() -> None:
    console.utf8()

    print("1. LA FORME REELLE, ET ELLE TIENT EN QUATRE APPELS\n")
    for ligne in (
            'client.user.add(user_id="diaguily", first_name="Diaguily")',
            'client.thread.create(thread_id=tid, user_id="diaguily")',
            'client.thread.add_messages(tid, messages=messages)',
            'contexte = client.thread.get_user_context(thread_id=tid)'):
        print(f"   {ligne}")
    print("\n   ⚠️ `zep-cloud` demande une cle et un service distant. Ce projet")
    print("   reimplemente la MEME forme sur un graphe local — pour que tout")
    print("   s'execute, et surtout pour qu'on puisse REGARDER ce qui se passe.")
    print("   Le mecanisme temporel est invisible depuis l'exterieur, et c'est")
    print("   lui que le cours enseigne.")

    print("\n2. LES QUATRE APPELS, EN VRAI\n")
    client = Memoire()
    client.user.add(user_id="diaguily", first_name="Diaguily", last_name="SYLLA")
    client.thread.create(thread_id="t-1", user_id="diaguily")
    faits = client.thread.add_messages("t-1", [
        Message(role="user", content="Je cherche un poste DevOps a Paris, en CDI",
                created_at=le(2026, 3, 1)),
        Message(role="assistant", content="Je note : Paris, CDI, DevOps."),
    ])
    print(f"   {len(faits)} fait(s) extrait(s) du message utilisateur :")
    for fait in faits:
        print(f"     {fait}")

    print("\n3. LE BLOC DE CONTEXTE\n")
    for ligne in client.thread.get_user_context("t-1").context.splitlines():
        print(f"   {ligne}")
    print("\n   Ce n'est PAS l'historique : c'est une synthese des faits encore")
    print("   valides, prete a coller dans un prompt systeme. La difference se")
    print("   voit sur une longue conversation — l'historique grossit sans fin,")
    print("   le bloc de contexte remplace un fait par un autre.")

    print("\n4. SEULS LES MESSAGES DE L'UTILISATEUR NOURRISSENT LA MEMOIRE\n")
    avant = len(client.graphe.faits)
    client.thread.add_messages("t-1", [
        Message(role="assistant",
                content="Je vous propose un poste a Bordeaux en freelance.")])
    print(f"   faits avant : {avant}, apres un message d'assistant : "
          f"{len(client.graphe.faits)}")
    print("\n   Extraire les mots de l'assistant ferait croire a l'agent qu'il")
    print("   a APPRIS ce qu'il vient de dire. Au bout de trois tours, il")
    print("   defend une preference qu'il a inventee lui-meme.")

    print("\n5. CE QUE ZEP APPORTE, EN UNE PHRASE\n")
    print("   Un RAG cherche des DOCUMENTS et rend les plus proches.")
    print("   Zep garde des FAITS DATES, et sait qu'un fait en a remplace un")
    print("   autre. Sur « je cherchais Paris » puis « finalement Lyon », un")
    print("   RAG rend les deux — et l'assistant propose Paris une fois sur")
    print("   deux. C'est le chapitre 3.")


if __name__ == "__main__":
    main()
