"""Le decoupage — la decision la plus lourde de consequences du RAG.

Un morceau trop grand noie la reponse dans du bruit ; trop petit, il perd le
contexte qui la rend comprehensible. Et surtout : on ne recupere JAMAIS ce que
le decoupage a separe. Une information coupee en deux est perdue pour la
recherche, quel que soit le modele derriere.
"""

from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter

from .corpus import DOCUMENTS
from .recherche import Morceau

# Les separateurs sont essayes DANS L'ORDRE : on coupe d'abord aux titres,
# puis aux paragraphes, puis aux phrases, et seulement en dernier recours au
# milieu d'une phrase. C'est ce qui garde les morceaux lisibles.
SEPARATEURS = ["\n### ", "\n## ", "\n\n", "\n", ". ", " "]


def decouper(taille: int = 420, chevauchement: int = 80) -> list[Morceau]:
    """Decoupe le corpus et attache les metadonnees a chaque morceau.

    Le chevauchement n'est pas du gaspillage : il donne a une phrase coupee
    une seconde chance d'etre retrouvee entiere dans le morceau suivant.
    """
    decoupeur = RecursiveCharacterTextSplitter(
        chunk_size=taille, chunk_overlap=chevauchement, separators=SEPARATEURS)

    morceaux: list[Morceau] = []
    for doc_id, texte in DOCUMENTS.items():
        for n, bout in enumerate(decoupeur.split_text(texte)):
            morceaux.append(Morceau(
                id=f"{doc_id}#{n}",
                texte=bout,
                # Sans metadonnees, un morceau retrouve est un texte orphelin :
                # on ne peut ni le citer, ni filtrer, ni expliquer d'ou il vient.
                metadonnees={"source": doc_id, "rang": n,
                             "section": _section(bout)},
            ))
    return morceaux


def _section(bout: str) -> str:
    for ligne in bout.splitlines():
        if ligne.startswith("### "):
            return ligne.removeprefix("### ").strip()
        if ligne.startswith("## "):
            return "en-tete"
    return "suite"
