# Job portal — projet de départ du cours **MCP : le Model Context Protocol**

Le fil rouge du cours, en état de marche : un serveur MCP qui expose un portail
d'offres d'emploi, avec ses trois primitives, ses transports et ses tests.

Ce projet **tourne tel quel**. C'est son intérêt principal : les extraits de la
vidéo appellent un `db` qui n'est jamais montré — ici, il existe
(`jobportal/donnees.py`), et le code du cours s'exécute pour de bon.

---

## ⚠️ Une différence assumée avec la vidéo

La vidéo écrit :

```python
from mcp.server.fastmcp import FastMCP      # SDK v1
```

Le SDK Python `mcp` est depuis passé en **2.x**, où `FastMCP` a été **renommé
`MCPServer`**. Le code ci-dessus lève maintenant une `ModuleNotFoundError`
explicite. Ce projet utilise donc le nom actuel :

```python
from mcp.server.mcpserver import MCPServer  # SDK 2.x
```

C'est le **même objet**, renommé : les décorateurs `@serveur.tool()`,
`@serveur.resource(...)` et `@serveur.prompt()` n'ont pas changé, ni la façon
de lancer le serveur. Si vous devez faire tourner du code v1 existant, épinglez
`mcp<2` ; pour tout nouveau projet, gardez 2.x.

---

## Démarrer

Prérequis : [uv](https://docs.astral.sh/uv/) et Python ≥ 3.11.

```bash
uv sync                       # installe tout
uv run --extra dev pytest -q  # 9 tests, doivent tous passer
```

Puis, dans l'ordre du cours :

```bash
uv run python chapitres/chapitre_1_pourquoi.py      # M×N contre M+N, chiffré
uv run python chapitres/chapitre_2_consommer.py     # lire et comprendre .mcp.json
uv run python chapitres/chapitre_3_primitives.py    # outil, resource, prompt
uv run python chapitres/chapitre_5_transports.py    # comparer les trois
uv run python chapitres/chapitre_6_production.py    # tracer un appel d'outil
```

Chaque fichier s'exécute seul et explique ce qu'il montre. Ouvrez-les : ils
sont écrits pour être lus autant que lancés.

## Brancher le serveur dans un vrai client

```bash
cp .mcp.json /chemin/vers/votre/projet/
```

Relancez votre client (Claude Code, Cursor…). Il lance le serveur comme
processus enfant et présente ses outils au modèle. Rien n'écoute sur le réseau.

Pour le lancer à la main :

```bash
uv run jobportal-serveur          # stdio (défaut)
uv run jobportal-serveur --http   # streamable HTTP, port 8080
```

## La carte du projet

| Fichier | Ce qu'il contient | Chapitre |
| --- | --- | --- |
| `jobportal/donnees.py` | Le `db` du cours : offres, recherche, candidatures | tous |
| `jobportal/serveur.py` | Le serveur complet : 3 outils, 2 resources, 2 prompts | 1, 3 |
| `jobportal/console.py` | Sortie UTF-8 même sous Windows | — |
| `chapitres/chapitre_1_pourquoi.py` | M×N contre M+N, calculé | 1 |
| `chapitres/chapitre_2_consommer.py` | Lecture commentée de `.mcp.json` | 2 |
| `chapitres/chapitre_3_primitives.py` | Les trois primitives, appelées | 3 |
| `chapitre_4_java/` | Le même serveur en Spring AI | 4 |
| `chapitres/chapitre_5_transports.py` | stdio, HTTP, SSE — et la sécurité | 5 |
| `chapitres/chapitre_6_production.py` | Traces, versions, périmètre | 6 |
| `tests/test_serveur.py` | Ce que le serveur doit garantir | tous |

## Ce que vous devez retenir du code

**Un outil agit, une resource se lit.** Ce n'est pas une nuance de style :
un client MCP peut lire une resource sans rien vous demander, parce qu'elle ne
modifie rien par construction. Il doit demander avant d'appeler un outil, parce
qu'il ne peut pas savoir de l'extérieur lequel écrit. Regardez
`creer_candidature` : c'est un outil, et il écrit.

**Un outil qui écrit doit refuser bruyamment.** `creer_candidature("JP-999", …)`
lève une exception au lieu de renvoyer une liste vide. Un agent qui reçoit un
succès silencieux continue sur une fausse hypothèse, et l'erreur se manifeste
trois étapes plus loin, là où elle est incompréhensible.

**Le transport décide du périmètre de sécurité.** En stdio, le périmètre est le
processus. En HTTP, votre serveur devient une porte : il lui faut OAuth 2.1, une
vérification du scope avant exécution, et un périmètre minimal.

## Pour aller plus loin

- Ajoutez un outil `retirer_candidature` — et écrivez son test d'abord.
- Remplacez `jobportal/donnees.py` par une vraie base : rien d'autre ne bouge.
- Branchez le serveur dans Claude Code et demandez-lui de vous trouver un poste.

---

Cours associé : [MCP : le Model Context Protocol](https://syllatech.pages.dev/cours/mcp)
· Formation syllatech — Diaguily SYLLA
