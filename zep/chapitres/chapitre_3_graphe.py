"""Chapitre 3 — Le graphe temporel : ce qu'un RAG ne peut pas faire.

    uv run python chapitres/chapitre_3_graphe.py
"""
from __future__ import annotations
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                                       # noqa: E402
from jobportal.memoire import Memoire, MemoireNaive, Message        # noqa: E402


def le(a, m, j):
    return datetime(a, m, j, tzinfo=timezone.utc)


CONVERSATION = [
    (le(2026, 3, 1), "Je cherche un poste DevOps a Paris, en CDI"),
    (le(2026, 5, 12), "Je vise plutot 55k"),
    (le(2026, 7, 17), "Finalement je prefere Lyon, et du teletravail complet"),
]


def main() -> None:
    console.utf8()
    client = Memoire()
    client.user.add(user_id="diaguily", first_name="Diaguily")
    client.thread.create(thread_id="t", user_id="diaguily")
    naive = MemoireNaive()

    for quand, texte in CONVERSATION:
        client.thread.add_messages("t", [
            Message(role="user", content=texte, created_at=quand)])
        naive.ajouter("diaguily", texte)

    print("1. LA CONVERSATION\n")
    for quand, texte in CONVERSATION:
        print(f"   {quand.date()}  {texte}")

    print("\n2. CE QUE LE GRAPHE EN A TIRE\n")
    for fait in client.graphe.faits:
        print(f"   {fait}")

    print("\n3. LE FAIT INVALIDE — c'est tout le sujet\n")
    for fait in client.graphe.historique("Diaguily", "lieu"):
        etat = "VALIDE" if fait.valide else "ferme "
        print(f"   {etat}  {fait}")
    print("\n   Paris n'est pas SUPPRIME : il est ferme, a la date ou Lyon")
    print("   commence. On sait donc ce qui etait vrai en mai, et l'on ne")
    print("   ressert pas Paris en juillet.")

    print("\n4. LES DEUX MEMOIRES, COTE A COTE\n")
    print("   — graphe temporel —")
    for ligne in client.thread.get_user_context("t").context.splitlines():
        print(f"   {ligne}")
    print("\n   — memoire naive (tout garder) —")
    for ligne in naive.contexte("diaguily").splitlines():
        print(f"   {ligne}")

    print("\n   La memoire naive donne au modele Paris ET Lyon, sans dire")
    print("   lequel est actuel. Il choisit — souvent le premier, parfois le")
    print("   dernier, jamais de facon stable. C'est la difference, et elle")
    print("   ne se voit qu'a partir du deuxieme changement d'avis.")

    print("\n5. CE QU'ON CROYAIT A UNE DATE DONNEE\n")
    for date in (le(2026, 4, 1), le(2026, 6, 1), le(2026, 8, 1)):
        faits = client.graphe.a_la_date("Diaguily", date)
        lieux = [f.objet for f in faits if f.predicat == "lieu"]
        salaires = [f.objet for f in faits if f.predicat == "salaire"]
        print(f"   {date.date()}  lieu={lieux}  salaire={salaires}")
    print("\n   Impossible avec une memoire qui supprime. C'est ce que la")
    print("   fenetre de validite achete — et ce qui permet de repondre a")
    print("   « pourquoi m'as-tu propose Paris en mars ? ».")

    print("\n6. LA REGLE D'INVALIDATION, EN UNE PHRASE\n")
    print("   Deux faits de meme SUJET et meme PREDICAT ne peuvent pas etre")
    print("   vrais en meme temps : le nouveau ferme l'ancien.")
    print("\n   Tout depend donc du predicat. « lieu » et « salaire » sont")
    print("   deux predicats distincts : changer de ville n'efface pas le")
    print("   salaire vise. Un extracteur qui melangerait les deux ferait")
    print("   disparaitre des faits a chaque message.")
    repete = Memoire()
    repete.user.add(user_id="u", first_name="Test")
    repete.thread.create(thread_id="t", user_id="u")
    for quand in (le(2026, 1, 1), le(2026, 2, 1)):
        repete.thread.add_messages("t", [
            Message(role="user", content="Je cherche a Lyon", created_at=quand)])
    lieux = repete.graphe.historique("Test", "lieu")
    print(f"\n   Deux fois « Lyon » : {len(lieux)} fait(s), "
          f"le premier ouvert depuis {lieux[0].valid_at.date()}")
    print("   Un fait IDENTIQUE ne ferme rien — sinon repeter une preference")
    print("   la remettrait a zero, et l'on perdrait depuis quand elle tient.")


if __name__ == "__main__":
    main()
