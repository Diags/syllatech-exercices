"""Les connaissances du job portal — le RAG, sans la pile lourde.

CE QUE LE COURS MONTRE, ET CE QUE CE FICHIER FAIT

Le chapitre 3 branche un `Knowledge` sur un `LanceDb` :

    from agno.knowledge.knowledge import Knowledge
    from agno.vectordb.lancedb import LanceDb

    knowledge = Knowledge(vector_db=LanceDb(uri="tmp/lancedb", table_name="docs"))
    agent = Agent(model=..., knowledge=knowledge, search_knowledge=True)

C'est la bonne forme, et elle marche. Elle demande deux choses que ce projet
ne peut pas exiger : `lancedb` (une dependance native de plusieurs dizaines
de mega-octets) et un **embedder**, qui appelle un fournisseur — donc une cle.

Ce fichier utilise l'autre point d'entree d'Agno, `knowledge_retriever` : une
simple fonction que l'agent appelle a la place de la recherche vectorielle.
La FORME est identique cote agent — il cherche, il cite — et la recherche est
ici ecrite en entier, donc lisible. On y gagne meme quelque chose : on voit
pourquoi une recherche lexicale rate certaines questions, et donc a quoi sert
vraiment un embedding.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter

# La base documentaire : ce qu'une equipe met dans un wiki et que personne ne
# retrouve. C'est exactement le cas d'usage du RAG.
DOCUMENTS = [
    ("Processus de recrutement",
     "Un recrutement du job portal comporte quatre etapes : preselection sur "
     "dossier, entretien technique de 45 minutes, entretien avec l'equipe, "
     "puis proposition. Le delai median entre la candidature et la proposition "
     "est de 18 jours."),
    ("Grille de remuneration",
     "Les fourchettes 2026 : developpeur junior 38 a 45k, confirme 45 a 58k, "
     "senior 58 a 72k. Un ecart de plus de 10 pour cent au-dessus de la "
     "fourchette demande une validation de la direction."),
    ("Politique de teletravail",
     "Trois jours de teletravail par semaine au maximum, deux jours de presence "
     "obligatoires dont le mardi. Le teletravail total est reserve aux postes "
     "explicitement ouverts en remote, signales par la mention 'full remote'."),
    ("Periode d'essai",
     "Quatre mois pour un cadre, renouvelable une fois. La rupture pendant la "
     "periode d'essai demande un delai de prevenance de 48 heures la premiere "
     "semaine, deux semaines apres un mois de presence."),
    ("Mobilite interne",
     "Un salarie peut candidater a un poste interne apres douze mois dans son "
     "poste actuel. La candidature interne est prioritaire a competences "
     "egales, et l'ancien manager est informe apres le premier entretien."),
    ("Cooptation",
     "La prime de cooptation est de 1500 euros, versee apres la periode "
     "d'essai du coopte. Elle ne s'applique pas aux candidats deja presents "
     "dans la base de recrutement depuis moins de six mois."),
]


def plat(texte: str) -> list[str]:
    sans = unicodedata.normalize("NFD", texte)
    sans = "".join(c for c in sans if unicodedata.category(c) != "Mn").lower()
    return re.findall(r"[a-z0-9]{3,}", sans)


class Index:
    """Un index BM25 minimal — la recherche, ecrite en entier.

    BM25 plutot qu'un simple compte de mots parce que c'est ce qui distingue
    une recherche utilisable d'une recherche qui remonte toujours le document
    le plus long : la saturation (`k1`) empeche une repetition de dominer, et
    la normalisation par la longueur (`b`) empeche un long document de gagner
    par sa seule taille.
    """

    K1 = 1.5
    B = 0.75

    def __init__(self, documents: list[tuple[str, str]]) -> None:
        self.documents = documents
        self.mots = [plat(f"{titre} {corps}") for titre, corps in documents]
        self.longueurs = [len(m) for m in self.mots]
        self.moyenne = sum(self.longueurs) / len(self.longueurs)
        self.frequences = [Counter(m) for m in self.mots]
        self.documents_par_mot: Counter[str] = Counter()
        for mots in self.mots:
            self.documents_par_mot.update(set(mots))

    def idf(self, mot: str) -> float:
        n = self.documents_par_mot.get(mot, 0)
        return math.log(1 + (len(self.documents) - n + 0.5) / (n + 0.5))

    def chercher(self, requete: str, combien: int = 3) -> list[dict]:
        notes = []
        # >>> depart: calculer la note BM25 de chaque document. Pour chaque mot de la requete present dans le document : idf(mot) * f * (K1+1) / (f + K1 * norme), ou norme = 1 - B + B * longueur / moyenne. Ne garder que les notes > 0. Quatre tests le verifient, dont un qui exige que le document le plus LONG ne gagne pas par sa seule taille.
        #     pass
        for i, frequences in enumerate(self.frequences):
            note = 0.0
            for mot in plat(requete):
                f = frequences.get(mot, 0)
                if not f:
                    continue
                norme = 1 - self.B + self.B * self.longueurs[i] / self.moyenne
                note += self.idf(mot) * f * (self.K1 + 1) / (f + self.K1 * norme)
            if note > 0:
                notes.append((note, i))
        # <<<
        notes.sort(reverse=True)
        return [{"titre": self.documents[i][0],
                 "contenu": self.documents[i][1],
                 "note": round(note, 3)}
                for note, i in notes[:combien]]


INDEX = Index(DOCUMENTS)


def recherche(agent=None, query: str = "", num_documents: int | None = None,
              **kwargs) -> list[dict]:
    """La signature exacte qu'attend `Agent(knowledge_retriever=...)`.

    Agno appelle cette fonction a la place de la recherche vectorielle. Ce
    qu'elle rend est insere dans le contexte du modele — donc ce qu'elle rate,
    le modele ne le verra jamais. Un retriever muet ne produit pas d'erreur :
    il produit une reponse inventee.
    """
    return INDEX.chercher(query, num_documents or 3)
