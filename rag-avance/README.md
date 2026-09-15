# Job portal — projet de départ du cours **RAG avancé**

Un pipeline RAG complet et **mesuré**, qui tourne sans clé d'API et sans
télécharger un modèle.

```
           rappel   precision     F1
 naïf         92%         44%    58%
 avancé      100%         53%    69%
```

---

## Ce que ce projet substitue, et pourquoi il le dit

Un vrai système hybride associe une recherche **sémantique** — des vecteurs
produits par un modèle d'embedding — à une recherche **lexicale** comme BM25.
Le modèle demanderait plusieurs centaines de méga-octets. Ce projet doit
tourner après un `uv sync`.

**BM25 est le vrai algorithme**, écrit ici en entier : IDF, saturation,
normalisation par la longueur. **RRF est le vrai mécanisme** — il ne regarde
que des rangs, donc il est indifférent à ce qui les produit. Mettre de vrais
embeddings à la place ne change pas une ligne de `rrf()`.

Ce qui est substitué : la jambe sémantique devient un cosinus sur des
**trigrammes de caractères**, et le cross-encoder devient un reclasseur à trois
règles lisibles. C'est moins bon, et chaque fichier le dit en tête.

## Une erreur de conception, gardée et expliquée

Le premier essai mettait un **TF-IDF de mots** en face de BM25. Mesuré : deux
requêtes sur dix seulement donnaient un classement différent. Deux moteurs de
mots classent presque pareil — **la fusion ne fusionnait rien**.

Avec les trigrammes : quatre requêtes sur huit divergent, et « kubernete »
(sans `s`) ou « automatise » (au singulier) sont rattrapés là où BM25 exige le
terme exact.

**La leçon vaut pour un vrai système : deux moteurs qui se ressemblent ne se
complètent pas.** Si votre recherche hybride n'améliore rien, vérifiez d'abord
que ses deux jambes travaillent vraiment différemment. Un test du projet fige
cette divergence.

## Démarrer

```bash
uv sync --extra dev
uv run --extra dev pytest -q        # 14 tests

uv run python chapitres/chapitre_1_naif.py        # ce que le naïf manque
uv run python chapitres/chapitre_2_decoupage.py   # la taille des morceaux
uv run python chapitres/chapitre_3_hybride.py     # deux moteurs, une fusion
uv run python chapitres/chapitre_4_rerank.py      # récupérer large, trier fin
uv run python chapitres/chapitre_5_agentique.py   # quand une recherche ne suffit pas
uv run python chapitres/chapitre_6_evaluer.py     # mesurer ce qui coûte zéro
```

## Trois choses que le code enseigne

**Une métrique qui ne bouge jamais vous cache un angle mort.** Le chapitre 2
fait varier la taille des morceaux de 160 à 2000 signes : la précision
s'effondre de 67 % à 39 %, et le rappel **ne bouge pas d'un point**. Ce n'est
pas que le découpage soit sans effet — c'est que la métrique compte les
*documents*, et qu'un document reste retrouvé quelle que soit la façon dont on
l'a coupé. Le dégât se produit *à l'intérieur*, là où cette mesure ne regarde
pas.

**Un passage manqué est définitivement perdu ; un passage en trop n'est que du
bruit.** Aucun modèle ne répondra avec un document qu'il n'a pas reçu.
Surveillez le rappel en premier, et n'échangez jamais du rappel contre de la
précision sans une raison écrite.

**Commencez par ce qui ne coûte rien.** Deux des quatre métriques du cours —
rappel et précision du contexte — se calculent exactement, sans juge. Un RAG
qui échoue échoue presque toujours à la récupération ; un juge LLM sur une
récupération cassée ne vous apprendra que ce que vous saviez déjà.

## La carte du projet

| Fichier | Ce qu'il contient | Chapitre |
| --- | --- | --- |
| `jobportal/corpus.py` | Cinq fiches de poste, assez longues pour être coupées | tous |
| `jobportal/decoupe.py` | Le découpeur du cours, et les métadonnées | 2 |
| `jobportal/recherche.py` | BM25 complet, trigrammes, RRF | 1, 3 |
| `jobportal/rerank.py` | Couverture, proximité, densité | 4 |
| `jobportal/rag.py` | Le pipeline, naïf et avancé | 1, 5 |
| `jobportal/evaluation.py` | Rappel et précision, jeu annoté à la main | 6 |
| `tests/test_rag.py` | 14 tests | tous |

## Pour aller plus loin

- Ajoutez une métrique au **passage** : le morceau qui porte la réponse est-il récupéré ? C'est elle qui révélera l'effet du découpage.
- Remplacez les trigrammes par de vrais embeddings : seule `Index.vectorielle` change.
- Annotez dix questions de plus. C'est la vraie dépense d'une évaluation, et c'est pour cela qu'on l'évite.

---

Cours associé : [RAG avancé](https://syllatech.pages.dev/cours/rag-avance)
· Formation syllatech — Diaguily SYLLA
