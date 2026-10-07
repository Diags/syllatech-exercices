# Job portal — projet de départ du cours **Agno : le framework d'agents IA complet**

Agno rend la mémoire, les connaissances et les équipes faciles à **activer**.
Ce projet montre ce qu'elles font, et ce qu'elles coûtent.

```
   tour 1 :   709 signes envoyes
   tour 2 :  1148 signes envoyes
   tour 3 :  1336 signes envoyes
```

Un historique de session ne redescend jamais. C'est une ligne de configuration,
et c'est une facture.

---

## ⚠️ Ce projet corrige une erreur du cours

Le chapitre 4 écrit :

```python
agent = Agent(
    model=Claude(id="claude-sonnet-5"),
    db=SqliteDb(db_file="agents.db"),
    add_history_to_context=True,
    enable_user_memories=True,      # TypeError sur Agno 3.x
)
```

**`enable_user_memories` n'existe plus.** Il a été scindé en trois
interrupteurs distincts, et la séparation est un progrès :

| Paramètre | Ce qu'il fait |
| --- | --- |
| `update_memory_on_run` | extraire des mémoires à chaque tour |
| `add_memories_to_context` | les réinjecter dans le contexte |
| `enable_agentic_memory` | laisser l'agent décider quoi retenir |

On peut donc écrire sans relire, ou relire sans écrire — ce qu'un booléen
unique ne permettait pas. Un test du projet vérifie que l'ancien nom lève bien
`TypeError`.

## ⚠️ Et quatre dépendances que la vidéo ne mentionne pas

Agno 3.x est modulaire : le cœur n'embarque ni client de fournisseur, ni base,
ni vecteurs, ni serveur web. Un projet qui suit le cours de bout en bout échoue
**quatre fois**, chaque fois sur une erreur d'import qui ne dit rien du
chapitre en cours :

```
Claude(...)              → pip install anthropic
SqliteDb(db_file=...)    → SQLAlchemy
LanceDb(...)             → lancedb, plus un embedder (donc une clé)
AgentOS(...)             → fastapi
```

Ce n'est pas un défaut : c'est un choix d'installation légère. Mais il vaut
mieux le savoir avant le chapitre 3 qu'après.

## Démarrer

```bash
uv sync --extra dev
uv run --extra dev pytest -q        # 28 tests

uv run python chapitres/chapitre_1_demarrer.py      # ce que l'agent envoie vraiment
uv run python chapitres/chapitre_2_outils.py        # ce qu'un appel d'outil coûte
uv run python chapitres/chapitre_3_connaissances.py # le RAG, et la limite du lexical
uv run python chapitres/chapitre_4_memoire.py       # session ≠ mémoire
uv run python chapitres/chapitre_5_equipe.py        # la facture d'une équipe
uv run python chapitres/chapitre_6_agentos.py       # avant de déployer
```

Avec un vrai modèle — **rien d'autre ne change** :

```bash
uv sync --extra reel
export ANTHROPIC_API_KEY=...
```

## Ce qui est réel, et ce qui est substitué

**Réel :** `Agent`, `Team`, `ReasoningTools`, `InMemoryDb`, les mémoires
utilisateur et leur cloisonnement, `add_history_to_context`,
`knowledge_retriever` + `search_knowledge`, la délégation d'équipe — le tout
sur Agno 3.0.9.

**Substitué :** le modèle, et le magasin vectoriel.

Agno ne fournit **aucun modèle de test** — contrairement à PydanticAI et son
`TestModel`. `jobportal/modele.py` en écrit un, et c'est instructif : six
méthodes abstraites, avec un piège. `invoke()` doit rendre un **`ModelResponse`
déjà construit** ; `_parse_provider_response` est un helper que les vrais
fournisseurs appellent depuis *leur propre* `invoke`, jamais la classe de base.
Rendre un dict produit `'dict' object has no attribute 'role'`, qui ne dit rien
de la cause.

Le magasin vectoriel du chapitre 3 est remplacé par un `knowledge_retriever` —
un BM25 écrit en entier — parce que `LanceDb` demande une dépendance native et
un embedder (donc une clé). La forme côté agent est identique.

## La carte du projet

| Fichier | Ce qu'il contient | Chapitre |
| --- | --- | --- |
| `jobportal/modele.py` | Un `Model` Agno complet, écrit à la main | tous |
| `jobportal/agents.py` | Cinq agents : nu, outillé, documenté, à mémoire, en équipe | 1-5 |
| `jobportal/donnees.py` | La base et les outils — le `db` que les extraits appellent | 2, 5 |
| `jobportal/connaissances.py` | BM25 écrit en entier, et le retriever qu'Agno attend | 3 |
| `tests/test_agents.py` | 28 tests, sans réseau | tous |

## Cinq choses que le code enseigne

**Un agent « nu » envoie 171 signes ; avec historique et mémoires, 1 336 au
troisième tour.** Chaque fonction activée fait grossir ce qui part à chaque
appel. Agno les rend faciles à activer, pas gratuites — et `num_history_runs`
existe pour borner ce qui, sinon, ne redescend jamais.

**Session et mémoire ne sont pas la même chose, et les confondre coûte dans
les deux sens.** `add_history_to_context` rejoue *cette* session : il pèse et
meurt avec elle. Une mémoire tient en une phrase et suit l'utilisateur dans
toutes ses sessions. Le chapitre 4 le démontre — un agent neuf, une session
neuve, et les mémoires de la session précédente sont là. Un autre test vérifie
qu'un **autre `user_id` ne les voit pas** : c'est une fuite de données
personnelles, pas un détail de confort.

**`ReasoningTools` n'est pas un modèle de raisonnement : c'est un outil.** Il
donne à l'agent de quoi poser ses étapes avant de répondre, fonctionne avec
n'importe quel modèle, et **ajoute des tours**. À réserver aux questions qui se
décomposent vraiment ; sur une recherche simple, il coûte sans rien apporter.

**Une recherche lexicale rate ce qui n'a aucun mot commun — et c'est la vraie
raison d'être d'un embedding.** « Puis-je travailler depuis chez moi ? » ne
partage aucun mot avec « télétravail » : BM25 remonte le mauvais document.
« Que touche-t-on en recommandant quelqu'un ? » n'en remonte aucun. Les deux
questions sont limpides pour un humain. Le chapitre 3 le montre plutôt que de
l'affirmer.

**Une équipe de deux coûte deux fois un agent seul.** Le coordinateur
réfléchit, délègue, attend, puis synthétise — et chaque membre est un agent
complet. Il délègue par **identifiant** dérivé du nom (« Analyste offres » →
`analyste-offres`) : déléguer au nom échoue avec *Member with ID … not found*,
que le modèle corrige au prix d'un tour de plus. Des noms courts et distincts
ne sont donc pas de la cosmétique.

## Pour aller plus loin

- Posez `num_history_runs=2` sur `conseiller_avec_memoire` et refaites la mesure du chapitre 4.
- Remplacez `knowledge_retriever` par un vrai `Knowledge(vector_db=LanceDb(...))` et reposez les deux questions que le BM25 rate.
- Ajoutez un troisième membre à l'équipe et comptez les appels : la courbe n'est pas linéaire.
- Écrivez un `ModeleFactice` qui rend des réponses **incohérentes** exprès, et regardez lesquels de vos tests le remarquent.

---

Cours associé : [Agno : le framework d'agents IA complet](https://syllatech.pages.dev/cours/agno)
· Formation syllatech — Diaguily SYLLA
