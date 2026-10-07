"""Chapitre 6 — Brancher la memoire sur un assistant qui existe deja.

    uv run python chapitres/chapitre_6_integration.py
"""
from __future__ import annotations
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                                  # noqa: E402
from jobportal.memoire import Memoire, MemoireNaive, Message   # noqa: E402

PROMPT = "Tu es le conseiller carriere du portail syllatech."


def assistant(question: str, contexte: str) -> str:
    """Un « modele » factice : il repond a partir du contexte qu'on lui donne.

    Il ne devine rien. C'est voulu : on mesure ce que la MEMOIRE apporte, pas
    ce qu'un modele saurait inventer.
    """
    lieu = next((l.split(" a ")[-1] for l in contexte.splitlines()
                 if "cherche un poste a" in l), None)
    if lieu:
        return f"Voici des offres a {lieu.strip()} qui correspondent."
    return "Dans quelle ville cherchez-vous ?"


def main() -> None:
    console.utf8()

    print("1. TROIS LIGNES AUTOUR DE CE QUI EXISTE\n")
    for ligne in (
            "ctx = client.thread.get_user_context(thread_id).context",
            "reponse = VOTRE_APPEL_HABITUEL(system=PROMPT + ctx, user=question)",
            "client.thread.add_messages(thread_id, [question, reponse])"):
        print(f"   {ligne}")
    print("\n   Rien d'autre ne change. C'est la promesse du chapitre, et elle")
    print("   tient : Zep ne remplace ni votre modele, ni votre framework, ni")
    print("   votre authentification.")

    print("\n2. L'IDENTITE VIENT DE VOTRE AUTH, PAS DE ZEP\n")
    print("   user_id   = celui de VOTRE systeme (Principal, JWT, session…)")
    print("   thread_id = celui de VOTRE conversation")
    print("\n   Zep ne sait pas qui sont vos utilisateurs. Un user_id genere")
    print("   au hasard a chaque session donne une memoire vide a chaque fois,")
    print("   sans qu'aucune erreur ne sorte — c'est le premier bug qu'on")
    print("   ecrit, et le plus long a voir.")

    print("\n3. LA MEME QUESTION, AVEC ET SANS MEMOIRE\n")
    client = Memoire()
    client.user.add(user_id="diaguily", first_name="Diaguily")
    client.thread.create(thread_id="lundi", user_id="diaguily")
    client.thread.add_messages("lundi", [
        Message(role="user", content="Je cherche du DevOps a Lyon",
                created_at=datetime(2026, 7, 1, tzinfo=timezone.utc))])

    # Jeudi : nouveau fil, historique vide.
    client.thread.create(thread_id="jeudi", user_id="diaguily")
    question = "Vous avez quelque chose pour moi ?"

    print(f"   question : « {question} »\n")
    print(f"   sans memoire : {assistant(question, '')}")
    contexte = client.thread.get_user_context("jeudi").context
    print(f"   avec memoire : {assistant(question, contexte)}")
    print("\n   Nouveau fil, historique vide — et l'assistant sait quand meme.")
    print("   C'est exactement ce qu'un utilisateur attend, et ce qu'un")
    print("   historique de session ne peut pas donner.")

    print("\n4. LE BUDGET DE LATENCE\n")
    debut = time.perf_counter()
    for _ in range(100):
        client.thread.get_user_context("jeudi")
    local = (time.perf_counter() - debut) / 100 * 1000
    print(f"   get_user_context local : {local:.3f} ms")
    print("   le vrai Zep, en reseau : ~100 a 200 ms annonces")
    print("\n   ⚠️ Ce chiffre-la n'est PAS mesure ici : c'est l'ordre de")
    print("   grandeur annonce par Zep, pas une mesure de ce projet. Ce qui")
    print("   compte est ailleurs : cet appel est SUR LE CHEMIN CRITIQUE de")
    print("   chaque reponse. Il s'ajoute a la latence du modele, et il faut")
    print("   prevoir ce qu'on fait s'il echoue.")

    print("\n5. QUE FAIRE SI LA MEMOIRE EST INJOIGNABLE\n")
    for quoi, verdict in (
            ("repondre sans contexte", "oui — degrade, pas casse"),
            ("faire echouer la requete", "non : la memoire est un confort"),
            ("reessayer trois fois", "non : trois fois la latence, pour rien"),
            ("mettre en cache le dernier bloc", "oui, si l'on accepte qu'il vieillisse")):
        print(f"   {quoi:<34}{verdict}")
    print("\n   Une memoire qui fait tomber le service est pire qu'une absence")
    print("   de memoire. Le repli par defaut doit etre « je reponds sans ».")

    print("\n6. CE QUE CE PROJET NE PROUVE PAS\n")
    print("   · L'extraction de faits est ici faite par des MOTIFS. Zep")
    print("     utilise un modele : il trouve plus de choses, et il se trompe")
    print("     autrement. La STRUCTURE qu'il produit est la meme.")
    print("   · Les latences reseau ne sont pas mesurees.")
    print("   · Le vrai Zep gere aussi les entites (« CloudCorp » comme nœud),")
    print("     la desambiguisation et le passage a l'echelle. Ce projet garde")
    print("     le mecanisme temporel, qui est ce que le cours enseigne.")


if __name__ == "__main__":
    main()
