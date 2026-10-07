# Job portal — projet de départ du cours **CrewAI : les équipes d'agents IA**

Cinq équipages, un flux à deux branches, 28 tests — **sans clé d'API**.

```
   un agent outille                2 appel(s) au modele
   sequentiel (2 agents)           3 appel(s) au modele
   hierarchique (3 + manager)      4 appel(s) au modele
```

Le manager est un agent de plus. Une équipe de trois, ce sont **quatre
additions** — et c'est mesuré, pas affirmé.

---

## ⚠️ Trois choses ont changé dans CrewAI 1.x

**1. Le code du chapitre 5 ne se construit pas.** La vidéo écrit :

```python
@router(collecter)
def evaluer(self): ...

@listen("publier")
def publier(self): ...        # ← refusé
```

CrewAI 1.x rejette la classe à sa création : *« a listener triggered by its own
completion creates an infinite loop »*. Un handler ne peut pas porter le nom de
l'événement qu'il écoute. Ici, l'événement s'appelle `publier` et le handler
`envoyer_newsletter`. Un test du projet vérifie que l'ancienne forme échoue.

**2. `crewai_tools` est un paquet séparé.** Le chapitre 3 écrit
`from crewai_tools import SerperDevTool, ScrapeWebsiteTool` sans le dire :
installer `crewai` ne le tire pas. Et `SerperDevTool` demande en plus une clé
d'API — deux obstacles pour une ligne d'import.

**3. LiteLLM n'est plus embarqué.** Le cœur ne connaît qu'une liste fermée de
fournisseurs (openai, anthropic, google, bedrock, ollama…) ; tout le reste passe
par l'extra `crewai[litellm]`. `LLM(model="autre-chose")` lève `ImportError`
avant tout appel — avec un message qui parle d'installation là où l'on
cherchait autre chose.

## Démarrer

```bash
uv sync --extra dev
uv run --extra dev pytest -q        # 28 tests

uv run python chapitres/chapitre_1_demarrer.py    # role, goal, backstory
uv run python chapitres/chapitre_2_taches.py      # CrewAI valide, il ne demande pas
uv run python chapitres/chapitre_3_outils.py      # le troisième nom d'un outil
uv run python chapitres/chapitre_4_processus.py   # ce que coûte un manager
uv run python chapitres/chapitre_5_flows.py       # les deux branches, parcourues
uv run python chapitres/chapitre_6_production.py  # coûts, mémoire, versions
```

## Ce qui est réel, et ce qui est substitué

**Réel :** `Agent`, `Task`, `Crew`, `Process.sequential` et `.hierarchical`,
`@tool`, `output_pydantic`, `context=[...]`, `Flow` avec `@start` / `@router` /
`@listen`, `delegate_work_to_coworker` — le tout sur CrewAI 1.15.

**Substitué :** le modèle. CrewAI n'en fournit aucun pour les tests ;
`jobportal/modele.py` en écrit un sur `BaseLLM`, et l'écrire une fois apprend
plus que n'importe quelle page de documentation. Il **appelle réellement les
outils et construit sa réponse à partir de ce qu'ils rendent** — un modèle
factice qui répond toujours la même chose vérifie la plomberie et rien d'autre.

## La carte du projet

| Fichier | Ce qu'il contient | Chapitre |
| --- | --- | --- |
| `jobportal/modele.py` | Un `BaseLLM` CrewAI complet, et les trois pièges du protocole | tous |
| `jobportal/equipe.py` | Cinq équipages : simple, typé, outillé, séquentiel, hiérarchique | 1-4 |
| `jobportal/donnees.py` | La base et les outils — le `db` que les extraits appellent | 3 |
| `jobportal/flux.py` | Le Flow, avec ses deux branches et ses deux pièges | 5 |
| `tests/test_equipe.py` | 28 tests, sans réseau | tous |

## Cinq choses que le code enseigne

**CrewAI ne passe pas les outils par un paramètre : il les décrit dans le
prompt.** `tools` et `available_functions` arrivent **vides** ; les outils
apparaissent en texte sous `Tool Name:`. Les chercher là où on les cherche
d'habitude — dans les arguments de la fonction — donne un agent qui n'appelle
jamais rien, **sans la moindre erreur**.

**Un outil a trois noms, et un seul marche.** Le libellé passé à `@tool`
(« Recherche d'offres internes »), le nom de la fonction Python
(`rechercher_offres`), et l'identifiant que l'agent doit émettre
(`recherche_doffres_internes`). Émettre l'un des deux premiers fait échouer
l'action — et l'erreur revient au modèle **comme une observation ordinaire**,
donc sans rien interrompre. La réponse finale cite alors le message d'erreur,
ce qui a tout l'air d'un résultat.

**Le gabarit ReAct contient lui-même le mot `Observation:`.** Le prompt de
CrewAI inclut `Observation: the result of the action` à titre d'exemple. Un
modèle qui le prend pour un vrai retour conclut avant d'avoir rien appelé, et
cite le gabarit. Le projet distingue les deux, et un test le vérifie.

**Le contexte ne circule pas tout seul.** Sans `context=[veille]`, la seconde
tâche repart de rien — et l'on obtient deux rapports indépendants là où l'on
croyait avoir une chaîne. Les deux tâches réussissent ; rien ne le signale.

**Ce qui doit être fiable ne va pas dans un crew.** La branche « resoumettre »
du Flow n'appelle **aucun agent** : un test vérifie qu'elle coûte zéro. Dans un
crew, la même décision serait prise par un modèle — donc payée, et parfois mal
prise. Le seuil est du code : il se teste sans modèle et ne varie pas.

## Un piège Python, tant qu'on y est

`BaseLLM` est un modèle Pydantic. Un attribut de classe non annoté y est refusé
(*« A non-annotated attribute was detected »*), et un attribut d'instance non
déclaré ne peut pas être posé. Les compteurs des chapitres passent donc par
`ClassVar`, et les mouchards du modèle par `__dict__`. C'est le genre de détail
qui coûte vingt minutes la première fois.

## Pour aller plus loin

- Retirez `context=[veille]` de `equipe_sequentielle` : un test tombe, et la chaîne devient deux rapports sans rapport.
- Donnez le même `role` à deux agents et relancez le chapitre 1 : une équipe de clones coûte trois fois plus pour le même résultat.
- Activez `memory=True` avec une vraie clé et comparez la taille des prompts entre deux runs.
- Écrivez un `ModeleFactice` qui **ignore** le retour de ses outils, et regardez lesquels de vos tests le remarquent.

---

Cours associé : [CrewAI : les équipes d'agents IA](https://syllatech.pages.dev/cours/crewai)
· Formation syllatech — Diaguily SYLLA
