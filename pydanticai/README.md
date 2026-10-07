# Job portal — projet de départ du cours **PydanticAI : les agents type-safe**

Des agents dont la sortie est **validée**, un graphe qui **branche pour de
vrai**, et 27 tests — sans clé d'API.

```
   partiel 1 : titre='Marche D'
   partiel 2 : titre='Marche DevOps 2026'
               · Kubernetes reste dominant
               · Le Go progresse sur le tooling
               · Les salaires se tassent en province
```

Un titre coupé au milieu d'un mot, livré comme un objet `Rapport` valide.
C'est ce que le streaming structuré résout, et ça se voit à l'exécution.

---

## ⚠️ Deux APIs du cours ont changé

**1. `Graph(nodes=[...])` lève `TypeError`.** `Graph` n'est plus construit
directement : il est **produit** par un `GraphBuilder`. Les étapes s'écrivent
comme des fonctions décorées `@constructeur.step`, les arêtes se déclarent,
et `build()` rend le graphe :

```python
constructeur = GraphBuilder(state_type=Etat, output_type=str)

@constructeur.step
async def collecter(ctx: StepContext[Etat, None, None]) -> Assez | TropPeu:
    ...

constructeur.add_edge(constructeur.start_node, collecter)
constructeur.add_edge(collecter, constructeur.decision()
                      .branch(constructeur.match(Assez).to(analyser))
                      .branch(constructeur.match(TropPeu).to(renoncer)))
graphe = constructeur.build()
```

Un test du projet vérifie que l'ancienne forme échoue bien — pour que personne
ne perde une heure à se demander pourquoi.

**2. `MCPServerStdio` n'existe plus.** PydanticAI 2.x a remplacé les classes
`MCPServer*` par une seule, `MCPToolset`, construite à partir de ce que FastMCP
sait interpréter : un chemin de script (stdio), une URL, ou un client
pré-configuré. Elle demande aussi un extra — `pydantic-ai-slim[mcp]` — sans
lequel l'import échoue **avant même** d'atteindre le nom de la classe, avec un
message qui parle d'installation là où l'on cherchait une erreur d'API.

## Démarrer

```bash
uv sync --extra dev
uv run --extra dev pytest -q        # 27 tests

uv run python chapitres/chapitre_1_demarrer.py    # la sortie est validée
uv run python chapitres/chapitre_2_deps.py        # deps injectées, deux niveaux de validation
uv run python chapitres/chapitre_3_messages.py    # instructions dynamiques, historique
uv run python chapitres/chapitre_4_streaming.py   # un objet partiel, déjà valide
uv run python chapitres/chapitre_5_graphe.py      # GraphBuilder, les deux branches
uv run python chapitres/chapitre_6_production.py  # tracer, borner, compter
```

Avec un vrai modèle — **rien d'autre ne change** :

```bash
uv sync --extra reel
export ANTHROPIC_API_KEY=...
```

## Ce qui est réel, et ce qui est substitué

**Réel :** toute l'API PydanticAI 2.43 — `output_type`, `deps_type`,
`@agent.tool`, `@agent.instructions`, `@agent.output_validator`, `ModelRetry`,
`run_stream` / `stream_output`, `message_history`, `capture_run_messages`,
`usage`, et le `GraphBuilder` avec sa décision typée.

**Substitué :** le modèle. Deux modèles de test, et les deux sont nécessaires.
`TestModel` vérifie la **plomberie** — le schéma passe-t-il, les outils
sont-ils appelés ? `FunctionModel` laisse écrire la réponse **en Python** :
c'est le seul moyen de vérifier qu'un agent se sert vraiment de ce que ses
outils lui rendent. Un agent qui ignore le retour de ses outils passe tous les
tests de plomberie et se trompe en production.

## La carte du projet

| Fichier | Ce qu'il contient | Chapitre |
| --- | --- | --- |
| `jobportal/agents.py` | Trois agents : sortie typée, outils, validateur de sens | 1, 2, 3 |
| `jobportal/donnees.py` | Le `DatabaseConn` que les extraits appellent sans le montrer | 2, 3, 5 |
| `jobportal/modele.py` | `TestModel`, un modèle qui se sert des outils, un qui diffuse | tous |
| `jobportal/graphe.py` | `GraphBuilder`, une décision typée, deux branches | 5 |
| `tests/test_agents.py` | 27 tests, sans réseau | tous |

## Cinq choses que le code enseigne

**Les contraintes Pydantic s'exécutent.** `risque: int = Field(ge=0, le=10)`
n'est pas de la documentation : un 42 lève une `ValidationError`, et PydanticAI
renvoie l'erreur **au modèle** pour qu'il se corrige. Vous n'écrivez pas ce
contrôle, donc vous ne l'oubliez jamais. Les bornes partent d'ailleurs dans le
schéma envoyé au modèle : une classe bien écrite est un meilleur prompt.

**Le schéma valide la forme, pas le sens.** Un modèle qui invente
« Astronaute — Mars, 900k » produit une sortie **parfaitement valide**. C'est
là que le schéma s'arrête et que `@agent.output_validator` commence : il relit
la base, et lève `ModelRetry` en nommant les offres fautives. Le message part
au modèle, qui recommence. Une offre inventée ne sort jamais de l'agent — un
test le vérifie en faisant mentir le modèle exprès.

**L'historique ne se transporte pas tout seul.** Sans `message_history`,
chaque `run` repart de zéro. C'est un choix explicite, et c'est mieux ainsi :
un agent qui accumulerait seul finirait par payer très cher un contexte dont il
n'a plus besoin. Attention au piège symétrique : passer `all_messages()` au
lieu de `new_messages()` duplique l'historique à chaque tour, et la facture
grandit en carré sans que rien ne le signale.

**Une branche de graphe vaut de l'argent.** Sur 20 candidats, 6 ont moins de
trois offres suivies : le graphe les écarte **sans appeler de modèle**. Dans un
agent unique, cette décision serait prise *par* le modèle — donc payée, et
parfois mal prise. Ici, trois lignes de code, testables sans modèle du tout. Un
test exige que les **deux** branches soient réellement empruntées : un graphe
dont une branche ne sert jamais n'enseigne rien.

**On peut tracer sans rien installer.** `capture_run_messages()` est dans la
bibliothèque — pas de compte, pas de réseau — et c'est exactement ce qu'on veut
dans un test qui échoue. Logfire vaut pour la production, et son vrai argument
n'est pas le produit : c'est qu'il émet de l'**OpenTelemetry standard**, donc
qu'instrumenter n'attache à personne.

## Pour aller plus loin

- Retirez `@agent.output_validator` de `agent_strict` : trois tests tombent, et c'est exactement le risque décrit.
- Baissez `SEUIL` à 1 dans `graphe.py` : la branche `renoncer` ne sert plus, et un test le refuse.
- Ajoutez une étape `rediger` après `analyser`, et regardez `graphe.render()` la dessiner.
- Branchez un vrai modèle (`uv sync --extra reel`) et comparez `usage` entre une question simple et une question qui déclenche l'outil.

---

Cours associé : [PydanticAI : les agents type-safe](https://syllatech.pages.dev/cours/pydanticai)
· Formation syllatech — Diaguily SYLLA
