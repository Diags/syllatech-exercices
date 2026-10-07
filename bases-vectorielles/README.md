# Job portal — projet de départ du cours **Bases de données vectorielles**

Un index vectoriel écrit à la main, **et** la vraie API Qdrant qui tourne —
sans Docker, sans serveur, sans clé d'API.

```
     m  ef_c   ef   rappel  comparaisons  du corpus
     4    16    8      71%            56        12%
     8    32   16      97%           103        22%
     8    32   64     100%           236        49%
    16    64  128     100%           442        92%
```

Le compromis rappel / coût du cours, **mesuré sur du code que vous pouvez
lire**, sur 480 vecteurs.

---

## Ce qui est réel, et ce qui est substitué

**Réel :** les trois distances et leurs relations, l'index à parcours glouton
avec ses paramètres `m` / `ef_construct` / `ef`, le calcul de rappel, et
**toute l'API Qdrant** — `create_collection`, `VectorParams`,
`Distance.COSINE`, `upsert`, `query_points`, `query_filter`, `retrieve`,
`count`, `delete`.

**Substitué :** les vecteurs viennent d'un **hachage de trigrammes**, pas d'un
modèle. La géométrie est authentique ; la sémantique non — « poste » et
« emploi » restent éloignés. Et l'index est un *petit monde navigable* : il lui
manque les couches hiérarchiques du vrai HNSW, mais le compromis qu'il expose
est celui d'un index de production.

**Qdrant tourne pour de vrai.** `QdrantClient(":memory:")` est le même client
que `QdrantClient("localhost", port=6333)` — une seule ligne change pour
passer à un serveur.

## Démarrer

```bash
uv sync --extra dev
uv run --extra dev pytest -q        # 13 tests

uv run python chapitres/chapitre_1_similarite.py   # les trois distances
uv run python chapitres/chapitre_2_pgvector.py     # <=> <-> <#> et leur piège
uv run python chapitres/chapitre_3_qdrant.py       # la vraie API, en mémoire
uv run python chapitres/chapitre_4_choisir.py      # pgvector, Qdrant, Weaviate, Milvus
uv run python chapitres/chapitre_5_index.py        # le compromis, mesuré
uv run python chapitres/chapitre_6_production.py   # upsert, suppression, RAM
```

## Quatre choses que le code enseigne

**Sur des vecteurs normalisés, cosinus et L2 disent la même chose.**
`||a - b||² = 2 - 2·cos(a, b)` — le chapitre 1 le vérifie numériquement, colonne
contre colonne. Conséquence pratique : choisir entre `<=>` et `<->` dans
pgvector **ne change pas le classement** si vos vecteurs sont normalisés, et la
plupart des modèles en rendent des normalisés. Le débat sur la métrique n'a de
sens que dans le cas contraire.

**Un index approché rate des résultats — c'est le contrat, pas un bug.** La
seule question est *combien*, et la réponse s'appelle le rappel. Un test du
projet vérifie qu'il rate effectivement : un index qui ne rate rien coûte
autant que la recherche exacte, et ne sert donc à rien.

**Le rendement décroît.** Passer de `m=8` à `m=16` ajoute des comparaisons pour
un rappel déjà à 100 %. On paie pour rien — exactement ce qu'on fait en réglant
ces paramètres « au cas où ».

**Un filtre pousse dans l'index n'est pas un `WHERE` d'après coup.** En
post-filtrage, l'index remonte ses *k* meilleurs, le filtre en élimine la
quasi-totalité, et l'on rend deux résultats au lieu de cinq. Ce bug ne plante
pas : il rend moins que demandé, en silence, et seulement sur les requêtes très
filtrées — donc rarement en test, souvent en production. Un test le vérifie.

## La carte du projet

| Fichier | Ce qu'il contient | Chapitre |
| --- | --- | --- |
| `jobportal/vecteurs.py` | Hachage de trigrammes, trois distances, leurs relations | 1, 2 |
| `jobportal/hnsw.py` | Petit monde navigable, écrit en entier | 5 |
| `jobportal/qdrant.py` | La vraie API Qdrant, en mémoire | 3, 6 |
| `jobportal/mesures.py` | Rappel et coût, comptés honnêtement | 5 |
| `jobportal/corpus.py` | 480 offres déterministes | tous |
| `tests/test_vecteurs.py` | 13 tests | tous |

## Pour aller plus loin

- Faites tomber le rappel : réglez `m=2`, et regardez le graphe se couper en morceaux.
- Retirez l'arête de retour dans `hnsw.py` et mesurez le rappel sur les derniers documents insérés, eux seuls.
- Branchez de vrais embeddings : seule `vectoriser()` change.

---

Cours associé : [Bases de données vectorielles](https://syllatech.pages.dev/cours/bases-vectorielles)
· Formation syllatech — Diaguily SYLLA
