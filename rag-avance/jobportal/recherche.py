"""Les deux recherches, et leur fusion.

⚠️ CE QUE CE PROJET SUBSTITUE, ET POURQUOI IL LE DIT

Un vrai système hybride associe une recherche **sémantique** — des vecteurs
produits par un modèle d'embedding — à une recherche **lexicale** comme BM25.
Le modèle d'embedding demanderait un téléchargement de plusieurs centaines de
méga-octets, ou une clé d'API. Ce projet doit tourner après un `uv sync`.

La jambe sémantique est donc remplacée par un cosinus sur des **trigrammes de
caractères**. Ce n'est pas de la sémantique : « poste » et « emploi » restent
étrangers l'un à l'autre. Mais c'est une complémentarité RÉELLE avec BM25 —
les trigrammes rattrapent un pluriel, un accent oublié, une faute de frappe,
là où BM25 exige le terme exact.

Premier essai : la seconde jambe était un TF-IDF de MOTS. Deux moteurs de
mots donnent presque le même classement — deux requêtes sur dix seulement se
comportaient différemment, et la fusion n'apportait rien. Avec les
trigrammes : quatre sur huit. La leçon vaut pour un vrai système — **deux
moteurs qui se ressemblent ne se complètent pas.**

**Le mécanisme de RRF, lui, est exactement celui d'un vrai système.** Il ne
regarde que des RANGS : ce qui les a produits lui est indifférent. Mettre de
vrais embeddings à la place des trigrammes ne change pas une ligne de
`rrf()`. C'est précisément ce que ce chapitre doit faire comprendre.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass


def mots(texte: str) -> list[str]:
    sans = unicodedata.normalize("NFD", texte)
    sans = "".join(c for c in sans if unicodedata.category(c) != "Mn").lower()
    return re.findall(r"[a-z0-9]{2,}", sans)


def _trigrammes(texte: str) -> dict[str, float]:
    """Le sac de trigrammes d'un texte, en frequences.

    On travaille sur le texte aplati (minuscules, sans accents) : sinon
    « Kubernetes » et « kubernetes » ne se ressembleraient deja plus.
    """
    plat = " ".join(mots(texte))
    if len(plat) < 3:
        return {}
    sac = Counter(plat[i:i + 3] for i in range(len(plat) - 2))
    total = sum(sac.values()) or 1
    return {t: n / total for t, n in sac.items()}


@dataclass
class Morceau:
    id: str
    texte: str
    metadonnees: dict


class Index:
    """Porte les deux recherches sur le même corpus de morceaux."""

    def __init__(self, morceaux: list[Morceau]) -> None:
        self.morceaux = morceaux
        self.sacs = [Counter(mots(m.texte)) for m in morceaux]
        self.longueurs = [sum(s.values()) for s in self.sacs]
        self.longueur_moyenne = (sum(self.longueurs) / len(self.longueurs)) if morceaux else 0.0
        self.df: Counter = Counter()
        for sac in self.sacs:
            self.df.update(sac.keys())
        self.n = len(morceaux)
        # Les trigrammes sont calculés une fois : les recalculer à chaque
        # requête ferait de la recherche la partie lente du pipeline.
        self.trigrammes = [_trigrammes(m.texte) for m in morceaux]
        self.normes_tri = [math.sqrt(sum(v * v for v in t.values())) for t in self.trigrammes]

    # ------------------------------------------------------------ BM25

    def bm25(self, requete: str, k: int = 10, k1: float = 1.5, b: float = 0.75) -> list[Morceau]:
        """BM25, l'algorithme lexical de référence.

        Deux idées y font tout le travail :
          · un terme rare vaut plus qu'un terme courant (l'IDF) ;
          · répéter un terme rapporte de moins en moins (la saturation par k1).
        Sans saturation, un document qui répète trente fois « Python » écrase
        un document pertinent qui le dit deux fois.
        """
        termes = mots(requete)
        scores = []
        for i, sac in enumerate(self.sacs):
            s = 0.0
            for t in termes:
                if t not in sac:
                    continue
                idf = math.log(1 + (self.n - self.df[t] + 0.5) / (self.df[t] + 0.5))
                tf = sac[t]
                norme = 1 - b + b * (self.longueurs[i] / (self.longueur_moyenne or 1))
                s += idf * (tf * (k1 + 1)) / (tf + k1 * norme)
            scores.append((s, i))
        return [self.morceaux[i] for s, i in sorted(scores, reverse=True) if s > 0][:k]

    # ------------------------------------------------ trigrammes de caractères

    def vectorielle(self, requete: str, k: int = 10) -> list[Morceau]:
        """Cosinus sur des trigrammes de CARACTERES.

        Pourquoi pas des mots : BM25 en fait déjà, et deux moteurs qui
        comparent des mots donnent presque toujours le même classement — la
        fusion n'apporte alors rien. Mesuré sur ce corpus : deux requêtes sur
        dix se comportaient différemment.

        Les trigrammes changent la nature de la comparaison. « accessible »
        et « accessibilité » partagent « acc », « cce », « ces »… : ils se
        ressemblent, là où un moteur de mots les tient pour étrangers. Même
        chose pour une faute de frappe, un pluriel, un accent oublié.

        Ce n'est pas de la sémantique — « poste » et « emploi » restent
        étrangers. Mais c'est une complémentarité RÉELLE avec BM25, et c'est
        elle qui donne un sens à la fusion. Un vrai système met des vecteurs
        d'embedding à cette place ; `rrf()` ne s'en apercevrait pas.
        """
        vq = _trigrammes(requete)
        nq = math.sqrt(sum(v * v for v in vq.values())) or 1
        scores = []
        for i, m in enumerate(self.morceaux):
            vd = self.trigrammes[i]
            nd = self.normes_tri[i] or 1
            produit = sum(vq[t] * vd[t] for t in vq.keys() & vd.keys())
            scores.append((produit / (nq * nd), i))
        return [self.morceaux[i] for s, i in sorted(scores, reverse=True) if s > 0][:k]


def rrf(listes: list[list[Morceau]], k: int = 60) -> list[Morceau]:
    """Reciprocal Rank Fusion — la fusion qui ne regarde QUE les rangs.

    C'est sa force : les scores de deux moteurs ne sont pas comparables (BM25
    rend des nombres non bornés, le cosinus vit entre 0 et 1). Les normaliser
    demanderait un réglage, et ce réglage se démoderait. Les RANGS, eux, sont
    toujours comparables.

    La constante k amortit le sommet : sans elle, la première place vaudrait
    le double de la deuxième, et un moteur sûr de lui imposerait son choix.
    """
    # TODO : ecrire la fusion RRF. Elle ne doit regarder que les RANGS, jamais les scores : ceux de deux moteurs ne sont pas comparables.
    return []


def hybride(index: Index, requete: str, k: int = 10) -> list[Morceau]:
    return rrf([index.vectorielle(requete, 20), index.bm25(requete, 20)])[:k]
