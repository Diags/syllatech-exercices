"""Chapitre 5 — Les faits metier, et la recherche.

    uv run python chapitres/chapitre_5_metier.py
"""
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                          # noqa: E402
from jobportal.memoire import Memoire, Message         # noqa: E402


def le(a, m, j):
    return datetime(a, m, j, tzinfo=timezone.utc)


def main() -> None:
    console.utf8()
    client = Memoire()
    client.user.add(user_id="diaguily", first_name="Diaguily")
    client.thread.create(thread_id="t", user_id="diaguily")
    client.thread.add_messages("t", [
        Message(role="user", content="Je cherche du DevOps a Lyon en CDI",
                created_at=le(2026, 7, 1))])

    print("1. TOUT N'EST PAS UNE CONVERSATION\n")
    print("   Une candidature envoyee est un FAIT. Personne ne l'a dit a")
    print("   l'assistant — c'est arrive dans le systeme. S'il ne le sait pas,")
    print("   il propose l'offre a laquelle l'utilisateur vient de postuler.")

    print("\n2. LA FORME\n")
    for ligne in (
            'client.graph.add(',
            '    user_id="diaguily",',
            '    type="json",',
            '    data=json.dumps({"event_type": "candidature_envoyee", …}))'):
        print(f"   {ligne}")

    fait = client.graph.add("diaguily", {
        "event_type": "candidature_envoyee",
        "offre": "DevOps Senior — CloudCorp Lyon",
        "salaire_propose": 62000,
    }, le(2026, 7, 20))
    print(f"\n   → {fait}")
    print(f"   source : {fait.source}")

    print("\n3. LES DEUX SOURCES, DANS LE MEME GRAPHE\n")
    for f in client.graphe.valides("Diaguily"):
        print(f"   [{f.source:<8}] {f.texte}")
    print("\n   Un fait metier et un fait de conversation vivent ensemble, et")
    print("   se ferment de la meme facon. C'est ce qui permet a l'assistant")
    print("   de dire « vous avez deja postule chez CloudCorp » sans qu'on le")
    print("   lui ait raconte.")

    print("\n4. LA RECHERCHE\n")
    for requete in ("candidature CloudCorp", "lieu du poste", "remuneration"):
        trouves = client.graph.search("diaguily", requete)
        print(f"   « {requete:<24} » → {[f.texte[:44] for f in trouves]}")

    print("\n5. ELLE NE CHERCHE QUE DANS LES FAITS VALIDES\n")
    client.thread.add_messages("t", [
        Message(role="user", content="En fait je vise Bordeaux",
                created_at=le(2026, 8, 1))])
    trouves = client.graph.search("diaguily", "lieu du poste")
    print(f"   apres « je vise Bordeaux » → {[f.texte for f in trouves]}")
    fermes = [f.texte for f in client.graphe.faits if not f.valide]
    print(f"   faits fermes, non cherches : {fermes}")
    print("\n   Chercher dans les faits fermes donnerait des reponses perimees")
    print("   avec l'assurance du present. C'est exactement ce que le graphe")
    print("   temporel evite — et ce qu'un RAG sur l'historique ne peut pas")
    print("   eviter, puisqu'il ne sait pas qu'un texte en a remplace un autre.")

    print("\n6. CE QU'IL FAUT ENVOYER, ET CE QU'IL NE FAUT PAS\n")
    for quoi, verdict in (
            ("une candidature envoyee", "oui — l'assistant doit le savoir"),
            ("un changement de statut", "oui — « entretien programme »"),
            ("chaque clic sur une offre", "non : du bruit, et il ferme des faits"),
            ("des donnees de paiement", "non — une memoire est une base de plus")):
        print(f"   {quoi:<32}{verdict}")
    print("\n   Le troisieme merite une explication : un evenement trop")
    print("   frequent, avec le meme predicat, ferme le precedent a chaque")
    print("   fois. On obtient une memoire qui ne retient que le dernier clic,")
    print("   et qui a coute cher a produire.")


if __name__ == "__main__":
    main()
