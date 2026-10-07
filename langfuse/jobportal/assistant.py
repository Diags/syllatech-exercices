"""L'assistant carriere, observe de bout en bout.

Chaque etape porte son decorateur. Ce n'est pas de la decoration : c'est ce
qui permet de repondre a « ou est passee la seconde ? » sans deviner.
"""

from __future__ import annotations

from langfuse import observe

from . import donnees

MODELE = "haiku"


@observe()
def rechercher_contexte(question: str) -> list[str]:
    """La recuperation. Un span ENFANT : on veut sa duree separement."""
    return donnees.query(donnees.mot_cle(question))


@observe(as_type="generation")
def generer(question: str, docs: list[str], modele: str = MODELE) -> str:
    """L'appel au modele.

    ⚠️ `as_type="generation"` n'est pas cosmetique. C'est LUI qui fait de ce
    span une generation : sans lui, Langfuse enregistre un span ordinaire,
    sans tokens, sans cout, et sans ligne dans le tableau de bord des couts.
    L'etape apparait bien dans la trace — c'est ce qui rend l'oubli difficile
    a voir.
    """
    client = _client()
    reponse = (f"D'apres {len(docs)} offre(s) : " + " ; ".join(docs[:3])
               if docs else "Aucune offre ne correspond.")

    entree = donnees.tokens(question) + sum(donnees.tokens(d) for d in docs)
    sortie = donnees.tokens(reponse)
    if client is not None:
        # L'usage et le modele remontent par update_current_generation : c'est
        # a partir de la que Langfuse calcule le cout, cote serveur.
        client.update_current_generation(
            model=modele,
            usage_details={"input": entree, "output": sortie},
            metadata={"documents": len(docs)},
        )
    return reponse


@observe()
def repondre(question: str, utilisateur: str = "anonyme",
             session: str = "s-1") -> str:
    """Le span racine. C'est lui qui porte l'identite et la session.

    `user_id` et `session_id` ne servent pas a la trace elle-meme : ils
    servent a la RETROUVER. Sans eux, un tableau de bord montre des traces
    sans savoir de qui ni de quelle conversation elles viennent.
    """
    client = _client()
    if client is not None:
        client.update_current_trace(
            user_id=utilisateur, session_id=session,
            tags=["assistant-carriere"],
            metadata={"mot_cle": donnees.mot_cle(question)})
    return generer(question, rechercher_contexte(question))


def _client():
    from langfuse import get_client
    try:
        return get_client()
    except Exception:      # noqa: BLE001 — hors trace, il n'y a rien a mettre a jour
        return None
