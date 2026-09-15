"""Un index HNSW, écrit à la main — et c'est le seul moyen de comprendre.

Le cours cite trois paramètres — `m`, `ef_construct`, `ef` — et dit qu'ils
pilotent le compromis rappel / vitesse. Les lire ne suffit pas : on les règle
au hasard tant qu'on n'a pas vu ce qu'ils font.

Cet index est une version simplifiée mais FIDÈLE du principe : un graphe de
voisinage qu'on parcourt gloutonnement, en gardant une file des `ef`
meilleurs candidats. Il n'a pas les couches hiérarchiques du vrai HNSW — d'où
le nom « petit monde navigable » — mais le compromis qu'il expose est
exactement celui d'un index de production, et il se mesure.

CE QU'IL FAUT EN RETENIR, et que ce fichier permet de vérifier soi-même :
un index approché **rate des résultats**. Ce n'est pas un bug, c'est le
contrat. La seule question est de savoir combien, et la réponse s'appelle le
rappel.
"""

from __future__ import annotations

import heapq
import random

from .vecteurs import cosinus


class PetitMondeNavigable:
    """Graphe de voisinage, parcouru gloutonnement.

    m            nombre de voisins gardés par nœud. Plus il est grand, plus le
                 graphe est connecté, meilleur est le rappel, plus l'index
                 pèse en mémoire.
    ef_construct largeur de la recherche PENDANT la construction. Un graphe
                 construit à la va-vite garde de mauvais voisins, et aucune
                 valeur de `ef` ne le rattrapera à la recherche.
    """

    def __init__(self, m: int = 8, ef_construct: int = 32, graine: int = 7) -> None:
        self.m = m
        self.ef_construct = ef_construct
        self.alea = random.Random(graine)     # reproductible : sinon le rappel
        self.vecteurs: list[list[float]] = []  # varierait d'une mesure à l'autre
        self.charges: list[dict] = []
        self.voisins: list[list[int]] = []
        self.visites = 0                       # le coût, compté honnêtement

    # ------------------------------------------------------------ insertion

    def ajouter(self, vecteur: list[float], charge: dict) -> int:
        i = len(self.vecteurs)
        self.vecteurs.append(vecteur)
        self.charges.append(charge)
        self.voisins.append([])
        if i == 0:
            return i

        candidats = self._parcourir(vecteur, self.ef_construct, depart=self.alea.randrange(i))
        proches = [j for _, j in sorted(candidats, reverse=True)[:self.m]]
        self.voisins[i] = proches
        # Le graphe doit être BIDIRECTIONNEL : sans l'arête de retour, un
        # nœud inséré tard n'est atteignable depuis nulle part, et il devient
        # invisible à la recherche. Symptôme : un rappel qui s'effondre sur
        # les derniers documents insérés, et sur eux seulement.
        # >>> depart: poser l'arete de RETOUR. Sans elle, un noeud insere tard n'est atteignable depuis nulle part et devient invisible a la recherche. Un test le verifie.
        #     pass
        for j in proches:
            if i not in self.voisins[j]:
                self.voisins[j].append(i)
                if len(self.voisins[j]) > self.m * 2:
                    self.voisins[j] = self._meilleurs(j, self.m * 2)
        # <<<
        return i

    def _meilleurs(self, j: int, k: int) -> list[int]:
        vj = self.vecteurs[j]
        return [v for _, v in sorted(((cosinus(vj, self.vecteurs[v]), v)
                                      for v in self.voisins[j]), reverse=True)[:k]]

    # ------------------------------------------------------------ recherche

    def _parcourir(self, requete: list[float], ef: int, depart: int) -> list[tuple[float, int]]:
        """Parcours glouton : on part d'un nœud, on va vers ce qui rapproche.

        `ef` est la largeur de la file. Avec ef=1 on descend tout droit et on
        se coince dans le premier minimum local venu ; plus il est grand, plus
        on explore de chemins — et plus on paie.
        """
        vus = {depart}
        d0 = cosinus(requete, self.vecteurs[depart])
        self.visites += 1
        candidats = [(-d0, depart)]     # tas-min sur la distance inverse
        resultats = [(d0, depart)]

        while candidats:
            neg, courant = heapq.heappop(candidats)
            if -neg < min(resultats)[0] and len(resultats) >= ef:
                break                    # plus rien de meilleur à espérer
            for v in self.voisins[courant]:
                if v in vus:
                    continue
                vus.add(v)
                d = cosinus(requete, self.vecteurs[v])
                self.visites += 1
                if len(resultats) < ef or d > min(resultats)[0]:
                    heapq.heappush(candidats, (-d, v))
                    resultats.append((d, v))
                    if len(resultats) > ef:
                        resultats.remove(min(resultats))
        return resultats

    def chercher(self, requete: list[float], k: int = 5, ef: int = 32) -> list[tuple[float, dict]]:
        if not self.vecteurs:
            return []
        ef = max(ef, k)
        res = self._parcourir(requete, ef, depart=0)
        return [(d, self.charges[i]) for d, i in sorted(res, reverse=True)[:k]]


def exact(vecteurs: list[list[float]], charges: list[dict],
          requete: list[float], k: int = 5) -> list[tuple[float, dict]]:
    """La référence : on compare à TOUT. Exact, et impraticable à l'échelle —
    c'est précisément pour cela que les index approchés existent."""
    notes = sorted(((cosinus(requete, v), i) for i, v in enumerate(vecteurs)), reverse=True)
    return [(d, charges[i]) for d, i in notes[:k]]
