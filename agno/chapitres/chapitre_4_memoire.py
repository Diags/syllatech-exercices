"""Chapitre 4 — Memoire et session : deux choses distinctes.

    uv run python chapitres/chapitre_4_memoire.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agno.agent import Agent                              # noqa: E402
from agno.db.in_memory import InMemoryDb                  # noqa: E402

from jobportal import console                             # noqa: E402
from jobportal.agents import conseiller_avec_memoire      # noqa: E402
from jobportal.modele import ModeleFactice                # noqa: E402


class Voyeur(ModeleFactice):
    """Garde tout ce qui lui a ete envoye, tour par tour."""

    def invoke(self, messages=None, **kwargs):
        if not hasattr(self, "vus"):
            self.vus = []
        self.vus.append(list(messages or []))
        return super().invoke(messages=messages, **kwargs)


def taille(messages) -> int:
    return sum(len(str(m.content or "")) for m in messages)


def main() -> None:
    console.utf8()

    print("1. LE PARAMETRE DU COURS N'EXISTE PLUS\n")
    print("     Agent(..., enable_user_memories=True)   # TypeError sur Agno 3.x\n")
    try:
        Agent(model=ModeleFactice(), enable_user_memories=True)
        print("   (le parametre existe sur cette installation)")
    except TypeError as e:
        print(f"   TypeError: {str(e)[:84]}")
    print("\n   Il a ete scinde en trois interrupteurs, et c'est un progres :")
    print("     update_memory_on_run     extraire des memoires a chaque tour")
    print("     add_memories_to_context  les reinjecter dans le contexte")
    print("     enable_agentic_memory    laisser l'agent decider quoi retenir")
    print("\n   On peut donc ecrire sans relire, ou relire sans ecrire — ce")
    print("   qu'un booleen unique ne permettait pas.")

    print("\n2. L'HISTORIQUE DE SESSION GROSSIT A CHAQUE TOUR\n")
    base = InMemoryDb()
    modele = Voyeur()
    agent = conseiller_avec_memoire(modele, base)
    for n, question in enumerate(["Je cherche un poste DevOps a Lyon",
                                  "Et en Python ?",
                                  "Quel salaire viser ?"], start=1):
        agent.run(question, user_id="diaguily", session_id="s1")
        print(f"   tour {n} : {taille(modele.vus[-1]):>5} signes envoyes")
    print("\n   add_history_to_context rejoue les messages de CETTE session.")
    print("   C'est utile et ce n'est pas gratuit : la courbe ne redescend")
    print("   jamais. num_history_runs existe pour la borner.")

    print("\n3. LES MEMOIRES, ELLES, SURVIVENT A LA SESSION\n")
    memoires = base.get_user_memories(user_id="diaguily")
    for memoire in memoires:
        print(f"   · {memoire.memory}")
    print(f"\n   {len(memoires)} memoire(s), extraites par le modele au fil des tours.")

    print("\n4. LA PREUVE : UNE AUTRE SESSION, UN AUTRE AGENT\n")
    neuf = Voyeur()
    autre = conseiller_avec_memoire(neuf, base)
    autre.run("Que sais-tu de moi ?", user_id="diaguily", session_id="s2")
    envoye = "\n".join(str(m.content) for m in neuf.vus[-1])
    presentes = [m.memory for m in memoires if m.memory in envoye]
    print(f"   session s2, agent neuf, historique vide.")
    print(f"   memoires retrouvees dans le contexte : {presentes}")
    print(f"   taille du contexte : {taille(neuf.vus[-1])} signes")
    print("\n   L'historique de s1 n'est PAS la — c'etait une autre session.")
    print("   Les memoires, si. Un fait durable tient en une phrase et suit")
    print("   l'utilisateur ; un historique pese et reste dans sa session.")
    print("   Les confondre coute cher dans les deux sens : on paie un")
    print("   historique qui ne servira plus, et on perd un fait qui servait.")

    print("\n5. ET UN AUTRE UTILISATEUR NE VOIT RIEN\n")
    tiers = Voyeur()
    conseiller_avec_memoire(tiers, base).run(
        "Que sais-tu de moi ?", user_id="quelqu-un-dautre", session_id="s3")
    fuite = [m.memory for m in memoires
             if m.memory in "\n".join(str(x.content) for x in tiers.vus[-1])]
    print(f"   memoires de diaguily visibles par un autre : {fuite or 'aucune'}")
    print("\n   Le cloisonnement se fait par user_id. Le verifier une fois")
    print("   vaut mieux que de le supposer : c'est une fuite de donnees")
    print("   personnelles, pas un detail de confort.")


if __name__ == "__main__":
    main()
