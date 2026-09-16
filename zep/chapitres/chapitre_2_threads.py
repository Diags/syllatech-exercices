"""Chapitre 2 — Users, threads, messages : qui possede quoi.

    uv run python chapitres/chapitre_2_threads.py
"""
from __future__ import annotations
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                    # noqa: E402
from jobportal.memoire import Memoire, Message   # noqa: E402


def main() -> None:
    console.utf8()
    client = Memoire()
    client.user.add(user_id="diaguily", first_name="Diaguily")
    client.user.add(user_id="marie", first_name="Marie")

    print("1. TROIS NIVEAUX, ET LE MILIEU EST CELUI QU'ON RATE\n")
    for quoi, porte in (
            ("user", "les FAITS — ils survivent a tous les fils"),
            ("thread", "les MESSAGES — un fil de conversation"),
            ("message", "un tour : role, contenu, date, nom de l'orateur")):
        print(f"   {quoi:<12}{porte}")

    print("\n2. DEUX FILS, UN UTILISATEUR\n")
    client.thread.create(thread_id="lundi", user_id="diaguily")
    client.thread.add_messages("lundi", [
        Message(role="user", content="Je cherche du DevOps a Lyon, en CDI")])

    client.thread.create(thread_id="jeudi", user_id="diaguily")
    fil = client.threads["jeudi"]
    print(f"   fil « jeudi » : {len(fil.messages)} message(s) — historique vide")
    contexte = client.thread.get_user_context("jeudi")
    print(f"   mais {len(contexte.faits)} fait(s) connus :")
    for fait in contexte.faits:
        print(f"     {fait.texte}")
    print("\n   C'est LA distinction du chapitre. Un nouveau fil repart d'un")
    print("   historique vide et de la MEME memoire. Confondre les deux fait")
    print("   soit tout oublier a chaque session, soit tout rejouer.")

    print("\n3. DEUX UTILISATEURS NE SE VOIENT PAS\n")
    client.thread.create(thread_id="m1", user_id="marie")
    client.thread.add_messages("m1", [
        Message(role="user", content="Je cherche du Java a Nantes")])
    for utilisateur, fil in (("diaguily", "jeudi"), ("marie", "m1")):
        faits = client.thread.get_user_context(fil).faits
        print(f"   {utilisateur:<10}{[f.objet for f in faits]}")
    print("\n   Le cloisonnement se fait par utilisateur. Le verifier une fois")
    print("   vaut mieux que de le supposer : c'est une fuite de donnees")
    print("   personnelles, pas un detail de confort.")

    print("\n4. CE QU'UN MESSAGE PORTE, ET POURQUOI\n")
    for champ, pourquoi in (
            ("role", "user ou assistant — decide si le message nourrit le graphe"),
            ("content", "le texte dont les faits sont tires"),
            ("created_at", "LA date de validite du fait, pas celle de l'ingestion"),
            ("name", "qui parle — utile quand plusieurs personnes ecrivent")):
        print(f"   {champ:<14}{pourquoi}")
    print("\n   `created_at` est le champ qu'on oublie. Ingerer un historique")
    print("   ancien sans dater les messages ecrase toute la chronologie : les")
    print("   faits de 2024 deviennent aussi recents que ceux d'aujourd'hui,")
    print("   et l'ordre d'invalidation devient celui de l'ingestion.")

    print("\n5. LA PREUVE\n")
    autre = Memoire()
    autre.user.add(user_id="u", first_name="Test")
    autre.thread.create(thread_id="t", user_id="u")
    # Ingere dans le DESORDRE, mais date correctement.
    autre.thread.add_messages("t", [
        Message(role="user", content="Finalement je prefere Lyon",
                created_at=datetime(2026, 7, 17, tzinfo=timezone.utc)),
        Message(role="user", content="Je cherche a Paris",
                created_at=datetime(2026, 3, 1, tzinfo=timezone.utc)),
    ])
    for fait in autre.graphe.historique("Test", "lieu"):
        print(f"   {fait}")
    print("\n   Ingeres dans le DESORDRE, les intervalles restent justes : le")
    print("   fait en retard se place AVANT celui qu'on avait deja, et c'est")
    print("   lui qu'on ferme.")
    print("\n   Le traiter comme le cas normal produirait « valide du 17")
    print("   juillet au 1er mars » — un intervalle inverse. Ce n'est pas une")
    print("   donnee bizarre : il rend toute lecture a une date passee fausse,")
    print("   pour toujours, sans lever la moindre erreur.")
    print("\n   Ingerez quand meme dans l'ordre chronologique quand vous le")
    print("   pouvez : c'est ce que fait la Batch API, et cela evite d'avoir")
    print("   a faire confiance a ce rattrapage.")


if __name__ == "__main__":
    main()
