# Job portal — projet de départ du cours **Microsoft AutoGen : multi-agents**

Quatre équipes, un agent Core, 27 tests — **sans clé d'API**.

```
   borne=3   3 messages rendus
   borne=5   5 messages rendus
   borne=8   8 messages rendus
```

`MaxMessageTermination` compte le **message de tâche** dedans. Une borne à 3
laisse donc deux prises de parole, pas trois — de quoi se tromper d'un cran en
réglant, et couper une réponse qu'on attendait.

---

## ⚠️ Trois paquets, pas un

**`autogen-ext` est un paquet séparé**, que `pip install autogen-agentchat` ne
tire pas. Le cours le dit et l'installe (`autogen-ext[openai]`) ; ce projet
s'en passe, parce qu'il demande une clé d'API.

| Paquet | Ce qu'il contient |
| --- | --- |
| `autogen-core` | Le socle : runtime, messages, `RoutedAgent` |
| `autogen-agentchat` | Les agents et les équipes |
| `autogen-ext` | Les clients de modèle et les outils tiers |

Ce projet n'utilise que les deux premiers. `ChatCompletionClient` est
l'interface commune : huit membres abstraits, et `jobportal/modele.py` en écrit
un. C'est ce qui rend le projet exécutable chez vous.

## Démarrer

```bash
uv sync --extra dev
uv run --extra dev pytest -q        # 27 tests

uv run python chapitres/chapitre_1_demarrer.py   # tout est asynchrone
uv run python chapitres/chapitre_2_outils.py     # ce que reflect_on_tool_use coûte
uv run python chapitres/chapitre_3_equipes.py    # ronde ou sélecteur
uv run python chapitres/chapitre_4_arret.py      # le mot seul ne suffit jamais
uv run python chapitres/chapitre_5_humain.py     # l'humain est un membre
uv run python chapitres/chapitre_6_core.py       # quand AgentChat ne suffit plus
```

## Ce qui est réel, et ce qui est substitué

**Réel :** `AssistantAgent`, `UserProxyAgent`, `RoundRobinGroupChat`,
`SelectorGroupChat`, `TextMentionTermination`, `MaxMessageTermination`,
`save_state` / `load_state`, `RoutedAgent` + `SingleThreadedAgentRuntime` — le
tout sur AutoGen 0.7.5.

**Substitué :** le client de modèle. Il **appelle réellement les outils** — un
`FunctionCall` dans `content`, comme un vrai — lit leur retour au tour suivant,
et construit sa réponse à partir de là. Un client factice qui répond toujours
la même chose vérifie la plomberie et rien d'autre.

## La carte du projet

| Fichier | Ce qu'il contient | Chapitre |
| --- | --- | --- |
| `jobportal/modele.py` | Un `ChatCompletionClient` complet, et les pièges du protocole | tous |
| `jobportal/equipes.py` | Quatre équipes, dont une qui ne s'arrête jamais toute seule | 3, 4, 5 |
| `jobportal/donnees.py` | La base et les outils — le `db` que les extraits appellent | 2 |
| `chapitres/chapitre_6_core.py` | Un `RoutedAgent` sans modèle ni prompt | 6 |
| `tests/test_equipes.py` | 27 tests, sans réseau | tous |

## Cinq choses que le code enseigne

**Le sélecteur a un prompt très particulier, et une réponse imparfaite ne lève
rien.** Il demande *« select the next role from [...]. Only return the role. »*
Une réponse qui n'est pas **exactement** un nom de participant fait retomber
AutoGen sur l'orateur précédent, avec un simple avertissement. L'équipe tourne
alors, mal : le même agent parle en boucle, et l'on croit que le sélecteur
*préfère* cet agent. Retirez `_selectionner` du client factice et relancez le
chapitre 3 : l'avertissement apparaît.

**Un sélecteur coûte un appel de plus à chaque tour.** Avant chaque prise de
parole, un modèle lit toute la conversation pour dire **un seul mot**. En
ronde, l'ordre est gratuit — la liste le dit. On passe au sélecteur quand
l'ordre dépend du sujet, pas parce qu'on a trois agents.

**Le mot de fin seul ne suffit jamais.** Il suffit qu'un agent reformule au
lieu de conclure pour que l'équipe tourne indéfiniment. La borne seule, elle,
coupe une conversation utile au milieu. Les deux en OU donnent : *« on s'arrête
quand c'est fini, et de toute façon on s'arrête. »* Un test lance une équipe de
deux agents qui ne prononcent **jamais** le mot de fin.

**`reflect_on_tool_use` ajoute un aller-retour.** À `False`, le retour brut de
l'outil *est* la réponse. À `True`, l'agent le reformule — plus lisible pour un
humain, inutile pour du code qui consomme du JSON, et payant dans les deux cas.
Un test vérifie que c'est exactement un appel de plus.

**`input_func` est ce qui rend le human-in-the-loop testable.** Un
`UserProxyAgent` branché en dur sur `input()` ne s'exécute que devant un
clavier — donc jamais en CI, donc jamais vérifié. Ici, une liste de réponses
préparées, et le test passe.

## Un piège Python, tant qu'on y est

`next(générateur)` dans une coroutine lève `StopIteration` quand rien ne
correspond, et asyncio la retransforme en `RuntimeError: coroutine raised
StopIteration` — un message qui ne parle pas du tout de la cause. Une
compréhension de liste avec une assertion dit ce qui manque. Le fichier de
tests le documente là où ça s'est produit.

## Pour aller plus loin

- Retirez la borne de `equipe_ronde` et donnez `dit_le_mot_de_fin=False` aux deux agents : l'équipe ne s'arrête plus.
- Passez `function_calling=False` dans `model_info` (en redéfinissant la
  propriété — la muter en place ne fait rien) : avec `tools=`, la
  construction échoue ; sans `tools=`, l'agent répond et n'appelle jamais rien.
- Remplacez `SingleThreadedAgentRuntime` par le runtime gRPC : le code des agents ne change pas.
- Écrivez un client qui **ignore** le retour de ses outils, et regardez lesquels de vos tests le remarquent.

---

Cours associé : [Microsoft AutoGen : multi-agents](https://syllatech.pages.dev/cours/autogen)
· Formation syllatech — Diaguily SYLLA
