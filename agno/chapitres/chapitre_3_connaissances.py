"""Chapitre 3 — Les connaissances : la recherche agentique, et sa limite.

    uv run python chapitres/chapitre_3_connaissances.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                             # noqa: E402
from jobportal.agents import conseiller, conseiller_documente  # noqa: E402
from jobportal.connaissances import DOCUMENTS, recherche  # noqa: E402
from jobportal.modele import ModeleFactice                # noqa: E402


def main() -> None:
    console.utf8()

    print("1. LA BASE DOCUMENTAIRE\n")
    for titre, corps in DOCUMENTS:
        print(f"   {titre:<28}{len(corps):>4} signes")
    print(f"\n   {len(DOCUMENTS)} documents. Ce qu'une equipe met dans un wiki")
    print("   et que personne ne retrouve — le cas d'usage du RAG.")

    print("\n2. SANS CONNAISSANCES, L'AGENT NE PEUT PAS SAVOIR\n")
    question = "Combien de jours de teletravail par semaine ?"
    nu = ModeleFactice()
    print(f"   {conseiller(nu).run(question).content[:80]}")
    print("\n   Le modele n'a jamais vu votre politique interne. Il repondra")
    print("   quelque chose de plausible — c'est le pire des cas, parce que")
    print("   personne ne verifie une reponse plausible.")

    print("\n3. AVEC, IL CHERCHE AVANT DE REPONDRE\n")
    documente = ModeleFactice()
    resultat = conseiller_documente(documente).run(question)
    print(f"   outil expose  : {documente.outils_recus}")
    print(f"   outil appele  : {documente.appels}")
    print(f"   reponse       : {resultat.content[:130]}")
    print("\n   « search_knowledge=True » est la recherche AGENTIQUE : l'agent")
    print("   decide lui-meme de chercher, au lieu qu'on lui colle des")
    print("   extraits a chaque question. Sur une question hors sujet, il ne")
    print("   cherche pas — et on ne paie pas la recherche.")

    print("\n4. CE QUE LE RETRIEVER A REELLEMENT RENDU\n")
    for document in recherche(query=question, num_documents=3):
        print(f"   {document['note']:>6}  {document['titre']}")
    print("\n   Ce qu'il rate, le modele ne le verra JAMAIS. Un retriever muet")
    print("   ne produit pas d'erreur : il produit une reponse inventee. C'est")
    print("   pourquoi on mesure le retriever separement de l'agent.")

    print("\n5. LA LIMITE DE CETTE RECHERCHE — et ce qu'un embedding apporte\n")
    paires = [
        ("Combien de jours de teletravail ?", "les mots de la question sont dans le document"),
        ("Puis-je travailler depuis chez moi ?", "AUCUN mot commun avec « teletravail »"),
        ("Que touche-t-on en recommandant quelqu'un ?", "« cooptation » n'est pas dans la question"),
    ]
    for question, note in paires:
        trouves = recherche(query=question, num_documents=1)
        titre = trouves[0]["titre"] if trouves else "— RIEN —"
        print(f"   {question:<44}{titre}")
        print(f"     {note}")

    print("\n   Cette recherche est lexicale : elle compare des MOTS. Les deux")
    print("   dernieres questions sont parfaitement claires pour un humain et")
    print("   illisibles pour elle. C'est exactement le trou qu'un embedding")
    print("   comble — il compare du SENS — et c'est la vraie raison d'etre")
    print("   d'un LanceDb ou d'un pgvector, bien plus que la performance.")
    print("\n   Le cours branche « Knowledge(vector_db=LanceDb(...)) ». La")
    print("   forme cote agent est identique : knowledge=..., search_knowledge=True.")
    print("   Ce projet substitue un knowledge_retriever pour tourner sans")
    print("   dependance native ni cle — voir jobportal/connaissances.py.")


if __name__ == "__main__":
    main()
