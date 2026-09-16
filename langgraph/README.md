# Job portal — projet de départ du cours **LangGraph**

Les six chapitres du cours, en état de marche : un graphe minimal, des
réducteurs, un cycle, la boucle agentique, la validation humaine, et une
équipe d'agents.

**Tout tourne sans clé d'API.** Le cours enseigne une *structure* — nœuds,
arêtes, état, boucle — et cette structure s'observe parfaitement avec un
modèle factice. Poser une clé ne change qu'une ligne, et rien d'autre.

---

## Démarrer

Prérequis : [uv](https://docs.astral.sh/uv/) et Python ≥ 3.11.

```bash
uv sync                       # installe tout
uv run --extra dev pytest -q  # 12 tests, doivent tous passer
```

Puis, dans l'ordre du cours :

```bash
uv run python chapitres/chapitre_1_hello_graph.py      # état, nœuds, arêtes
uv run python chapitres/chapitre_2_etat.py             # les réducteurs, démontrés
uv run python chapitres/chapitre_3_conditionnel.py     # le cycle
uv run python chapitres/chapitre_4_react.py            # la boucle agentique
uv run python chapitres/chapitre_5_persistance.py      # arrêt, validation, reprise
uv run python chapitres/chapitre_6_multi_agents.py     # superviseur et spécialistes
```

Chaque fichier s'exécute seul et **montre** ce qu'il explique. Le chapitre 2
ne dit pas que `operator.add` concatène : il fait écrire la même clé par deux
nœuds et affiche ce qu'il en reste.

## Le chaînon manquant : `jobportal/modele.py`

La vidéo écrit `llm.invoke(...)` sans jamais montrer d'où vient `llm`. C'est
normal dans un extrait, et c'est ce qui empêche de l'exécuter.

Ici, `modele()` rend un modèle **factice** qui sait deux choses, et ce sont
exactement les deux dont les six chapitres ont besoin :

1. répondre du texte ;
2. **demander un outil** quand la question s'y prête.

Sans la seconde, la boucle du chapitre 4 ne tournerait jamais : on verrait le
graphe, pas le cycle. Le faux modèle appelle toujours **le premier outil qui
lui a été lié** — pas un nom codé en dur, sinon deux agents aux outils
différents se marcheraient dessus (c'est un bug réel de ce projet, corrigé, et
un test le garde).

Pour parler au vrai modèle :

```bash
uv sync --extra reel
export ANTHROPIC_API_KEY=...          # $env:ANTHROPIC_API_KEY = "..." sous Windows
```

puis `modele(reel=True)` dans le chapitre de votre choix. Aucun graphe ne
change : c'est le propos.

## La carte du projet

| Fichier | Ce qu'il contient | Chapitre |
| --- | --- | --- |
| `jobportal/modele.py` | Le `llm` du cours : factice, ou réel | tous |
| `jobportal/donnees.py` | Les offres d'emploi du fil rouge | tous |
| `jobportal/outils.py` | Les outils annotés `@tool` | 4, 6 |
| `chapitres/chapitre_1_hello_graph.py` | État, nœuds, arêtes | 1 |
| `chapitres/chapitre_2_etat.py` | Réducteurs, démontrés par l'exemple | 2 |
| `chapitres/chapitre_3_conditionnel.py` | Arête conditionnelle et cycle | 3 |
| `chapitres/chapitre_4_react.py` | `ToolNode`, `tools_condition` | 4 |
| `chapitres/chapitre_5_persistance.py` | `InMemorySaver`, `interrupt`, `Command` | 5 |
| `chapitres/chapitre_6_multi_agents.py` | Sous-graphes et superviseur | 6 |
| `tests/test_graphes.py` | 12 tests, dont deux nés de vrais bugs | tous |

## Ce que le code enseigne, au-delà du cours

**Un nœud rend une mise à jour PARTIELLE.** Jamais l'état complet. C'est ce
qui permet à plusieurs nœuds d'écrire sans se marcher dessus — et c'est le
réducteur, pas l'ordre d'exécution, qui décide de la fusion.

**Un cycle sans condition de sortie n'est pas une erreur : c'est dix mille
tours, puis une erreur.** Le chapitre 3 met un garde-fou explicite, et un test
le vérifie. Ce bug est arrivé pendant l'écriture de ce projet.

**Routez d'après une clé dédiée de l'état.** Le chapitre 6 met le nom du
prochain agent dans `courant`. Router d'après le dernier message ou un journal
fonctionne — jusqu'au jour où deux nœuds y écrivent la même chose, et la
boucle devient infinie. C'est l'autre bug réel de ce projet.

**`create_react_agent` est déprécié** depuis LangGraph V1 : il a déménagé vers
`langchain.agents`, dans un paquet séparé, et disparaîtra en V2. Le chapitre 4
le montre et le dit ; les graphes écrits à la main, eux, ne bougeront pas.

## Pour aller plus loin

- Ajoutez un troisième spécialiste au chapitre 6 — le superviseur n'a pas à changer.
- Remplacez `InMemorySaver` par un point de reprise sur base : le graphe survit au redémarrage.
- Passez `modele(reel=True)` et observez que rien d'autre ne bouge.

---

Cours associé : [LangGraph](https://syllatech.pages.dev/cours/langgraph)
· Formation syllatech — Diaguily SYLLA
