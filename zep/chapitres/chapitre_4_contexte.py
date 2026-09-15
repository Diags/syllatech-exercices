"""Chapitre 4 — Le bloc de contexte : ce qu'on colle dans le prompt.

    uv run python chapitres/chapitre_4_contexte.py
"""
from __future__ import annotations
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                                     # noqa: E402
from jobportal.memoire import Memoire, MemoireNaive, Message      # noqa: E402


def le(a, m, j):
    return datetime(a, m, j, tzinfo=timezone.utc)


def main() -> None:
    console.utf8()
    client = Memoire()
    client.user.add(user_id="diaguily", first_name="Diaguily")
    client.thread.create(thread_id="t", user_id="diaguily")
    naive = MemoireNaive()

    print("1. LA BOUCLE COMPLETE, EN TROIS TEMPS\n")
    for ligne in (
            "ctx = client.thread.get_user_context(thread_id).context   # 1. lire",
            "reponse = llm.chat(system=PROMPT + ctx, user=question)    # 2. repondre",
            "client.thread.add_messages(thread_id, [q, r])             # 3. nourrir"):
        print(f"   {ligne}")
    print("\n   Le troisieme temps est celui qu'on oublie. Sans lui, la")
    print("   memoire ne grandit jamais : on lit toujours le meme contexte, et")
    print("   l'assistant « n'apprend rien » — sans qu'aucune erreur ne sorte.")

    print("\n2. CE QUE LE BLOC PESE, AU FIL D'UNE CONVERSATION\n")
    echanges = [
        (le(2026, 3, 1), "Je cherche un poste DevOps a Paris, en CDI"),
        (le(2026, 4, 2), "Je vise plutot 55k"),
        (le(2026, 5, 3), "En fait je prefere Nantes"),
        (le(2026, 6, 4), "Et du teletravail complet"),
        (le(2026, 7, 5), "Finalement Lyon, plutot"),
        (le(2026, 8, 6), "Je vise 62k maintenant"),
        (le(2026, 9, 7), "Je repasse sur Paris finalement"),
        (le(2026, 10, 8), "Plutot du freelance"),
        (le(2026, 11, 9), "Je vise 70k"),
        (le(2026, 12, 10), "Et je reviens a Lyon"),
        (le(2027, 1, 11), "Du Java plutot que du DevOps"),
        (le(2027, 2, 12), "Sur site, finalement"),
    ]
    print(f"   {'tour':<6}{'bloc de contexte':>18}{'historique naif':>18}")
    for n, (quand, texte) in enumerate(echanges, start=1):
        client.thread.add_messages("t", [
            Message(role="user", content=texte, created_at=quand)])
        naive.ajouter("diaguily", texte)
        bloc = len(client.thread.get_user_context("t").context)
        histo = len(naive.contexte("diaguily"))
        print(f"   {n:<6}{bloc:>15} sig{histo:>15} sig")

    bloc = len(client.thread.get_user_context("t").context)
    histo = len(naive.contexte("diaguily"))
    print(f"\n   Apres {len(echanges)} tours : {bloc} contre {histo} signes, "
          f"soit {histo / bloc:.1f}x.")
    print("\n   L'historique ne redescend JAMAIS : chaque message s'ajoute. Le")
    print("   bloc de contexte PLAFONNE — un fait qui en remplace un autre ne")
    print("   s'ajoute pas, il se substitue. Les deux courbes se croisent au")
    print("   septieme tour, et l'ecart ne fait que grandir ensuite.")
    print("\n   A la centieme session, l'historique est illisible et impayable ;")
    print("   le bloc fait toujours la meme taille.")

    print("\n3. LE BLOC, TEL QU'IL PART DANS LE PROMPT\n")
    for ligne in client.thread.get_user_context("t").context.splitlines():
        print(f"   {ligne}")

    print("\n4. OU LE COLLER, ET OU NE PAS LE COLLER\n")
    for ou, verdict in (
            ("dans le message systeme", "oui — c'est du contexte, pas une question"),
            ("dans le message utilisateur", "non : le modele croira que l'utilisateur vient de le dire"),
            ("a chaque tour", "oui — il change entre deux tours"),
            ("une fois au debut", "non : il serait perime des le second tour")):
        print(f"   {ou:<32}{verdict}")

    print("\n5. LE COUT, ET IL EST REEL\n")
    bloc = client.thread.get_user_context("t").context
    print(f"   {len(bloc)} signes, soit ~{len(bloc) // 4} tokens, A CHAQUE TOUR.")
    print("\n   C'est peu. Mais c'est paye a chaque appel, et il s'ajoute au")
    print("   prompt systeme et a l'historique recent. Une memoire qui")
    print("   grossirait sans borne rendrait chaque reponse plus chere que la")
    print("   precedente — c'est exactement ce que la fermeture des faits")
    print("   evite, et c'est la raison technique de tout le chapitre 3.")


if __name__ == "__main__":
    main()
