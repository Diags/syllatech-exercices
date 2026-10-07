# Job portal — projet de départ du cours **Google ADK : l'Agent Development Kit**

Cinq formes d'agent — assistant, coordinateur, pipeline, éventail, boucle —
27 tests, **sans clé Google**.

```
     2 etapes en workflow     2 appel(s)
     3 etapes en workflow     3 appel(s)
     4 etapes en workflow     4 appel(s)
```

Un workflow paie **un appel par étape** : l'ordre est écrit en Python,
personne ne décide. Un coordinateur en paie un de plus à chaque passage de
main, pour choisir à qui.

---

## ⚠️ Ce projet corrige une erreur du cours

Le chapitre 5 écrit :

```python
session_service.create_session(
    app_name="syllatech", user_id="diaguily", session_id="s1")
```

**`create_session` est asynchrone sur ADK 1.x.** Sans `await`, cet appel rend
une coroutine que personne n'attend : la session n'est **jamais créée**, Python
émet au mieux un `coroutine was never awaited` dans un coin, et `run_async`
échoue plus loin avec un message qui ne parle pas de la session.

```python
await session_service.create_session(...)   # la forme correcte
```

Un test du projet vérifie que la méthode est bien une coroutine.

## Démarrer

```bash
uv sync --extra dev
uv run --extra dev pytest -q        # 27 tests

uv run python chapitres/chapitre_1_demarrer.py      # les trois objets obligatoires
uv run python chapitres/chapitre_2_outils.py        # la docstring EST le contrat
uv run python chapitres/chapitre_3_multiagents.py   # la description décide
uv run python chapitres/chapitre_4_workflow.py      # l'ordre sans appel de modèle
uv run python chapitres/chapitre_5_sessions.py      # session ≠ état ≠ mémoire
uv run python chapitres/chapitre_6_evaluation.py    # callbacks, eval, déploiement
```

## Ce qui est réel, et ce qui est substitué

**Réel :** `Agent`, `SequentialAgent`, `ParallelAgent`, `LoopAgent`,
`sub_agents` + `transfer_to_agent`, `output_key`, `Runner`,
`InMemorySessionService`, `InMemoryMemoryService`, `before_model_callback` —
le tout sur google-adk 1.39.

**Substitué :** le modèle. ADK est conçu pour Gemini :
`Agent(model="gemini-flash-latest")` résout un nom vers un client Google, qui
demande une clé. `BaseLlm` est la porte prévue pour un fournisseur maison, et
elle n'a **qu'une seule** méthode abstraite — `generate_content_async`. Le
modèle de ce projet appelle réellement les outils et construit sa réponse à
partir de ce qu'ils rendent.

## La carte du projet

| Fichier | Ce qu'il contient | Chapitre |
| --- | --- | --- |
| `jobportal/modele.py` | Un `BaseLlm` complet, et les trois pièges du protocole | tous |
| `jobportal/agents.py` | Cinq formes d'agent, chacune commentée | 1-4 |
| `jobportal/donnees.py` | La base et les outils — le `db` que les extraits appellent | 2 |
| `jobportal/harnais.py` | Runner + session, écrit une fois | tous |
| `tests/test_agents.py` | 27 tests, sans réseau | tous |

## Cinq choses que le code enseigne

**C'est la `description` d'un sous-agent qui décide de la délégation — jamais
son `instruction`.** ADK liste les sous-agents dans l'instruction du
coordinateur, avec leur description, et c'est tout ce que le modèle a pour
choisir. Un expert sans description est invisible au routage, et la délégation
se fait au hasard sans qu'aucune erreur ne le dise.

**`transfer_to_agent` va dans les deux sens.** ADK l'ajoute dès qu'un agent a
des `sub_agents` — et il le donne **aussi** aux sous-agents, pour qu'ils
puissent rendre la main. Un modèle qui le choisit systématiquement fait
rebondir la question jusqu'à épuisement de la pile : l'erreur qui sort alors
est un `RecursionError` dans un *deepcopy* Pydantic, qui ne parle ni d'agents
ni de délégation. La règle qui l'évite est celle d'un vrai modèle : *on délègue
quand on n'a pas l'outil qu'il faut.*

**Le `Returns: dict` n'est pas une convention de style.** ADK sérialise le
retour tel quel vers le modèle. Un dict nommé se relit — `status`, `offres`,
`message` ; une chaîne se devine, et le modèle devine mal. Le champ `status`
permet de distinguer « rien trouvé » d'une panne.

**Une clé d'état mal orthographiée lève une `KeyError` — et c'est une bonne
nouvelle.** Beaucoup de frameworks laissent le littéral `{analyze}` tel quel,
et l'agent travaille alors sur ce mot sans que rien ne le dise. ADK refuse. Le
défaut restant est que l'erreur arrive **à l'exécution**, pas à la construction
du pipeline : une branche rarement empruntée peut porter une faute de frappe
pendant des mois.

**Un callback qui rend une `LlmResponse` court-circuite l'appel.** Le modèle
n'est pas appelé du tout : pas de tokens, pas de latence, pas de fuite. C'est
le meilleur endroit pour un garde-fou — avant l'appel, pas après la réponse. Un
test vérifie que le compteur du modèle reste à zéro.

## Un mot sur les mesures

Le chapitre 4 compare un pipeline de deux agents à un coordinateur avec un
expert : **les deux coûtent trois appels**. Le dire est plus utile que
d'annoncer un gain qui n'existe pas à ce format. L'écart apparaît à chaque
maillon supplémentaire — et la vraie raison de préférer un workflow n'est pas
le coût, c'est qu'un ordre écrit en Python se teste et ne varie pas d'une
exécution à l'autre.

## Pour aller plus loin

- Retirez la `description` d'un expert et relancez le chapitre 3 : la délégation devient arbitraire, sans erreur.
- Donnez la même `output_key` aux deux branches de l'éventail : le dernier gagne, en silence.
- Écrivez un `before_tool_callback` qui refuse un outil selon l'utilisateur — c'est là que se pose un garde-fou, pas dans le prompt.
- Branchez un vrai Gemini (`uv add google-adk` + clé) : seul `modele()` change.

---

Cours associé : [Google ADK : l'Agent Development Kit](https://syllatech.pages.dev/cours/google-adk)
· Formation syllatech — Diaguily SYLLA
