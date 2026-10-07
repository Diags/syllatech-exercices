# Job portal — projet de départ du cours **Claude Code : MCP en pratique**

Un serveur MCP qui tourne sur une vraie base, et **le vérificateur de
permissions que Claude Code ne fournit pas**.

```
  ERREUR     deny / mcp__jobportal__supprimer_ofre
             ne correspond a AUCUN outil expose. Les noms MCP contiennent
             « _ » : Claude Code n'avertit donc pas. La regle ne protege rien.
  ERREUR     mcp__jobportal__supprimer_offre
             outil d'ECRITURE couvert par aucune regle deny ou ask : il
             s'executera apres une seule approbation, puis sans rien demander.
```

Une lettre en moins dans une règle `deny`, et l'outil de suppression redevient
autorisé — **sans le moindre message**.

---

## ⚠️ Le défaut que ce projet met en évidence

La documentation des permissions dit :

> *A deny or ask rule whose tool name matches no known tool produces a startup
> warning to catch typos. **Tool names containing `_` or `*` are exempt from
> the check.***

Or **tout** nom d'outil MCP contient `_` : il commence par `mcp__`. Les règles
MCP sont donc **exemptes du contrôle de faute de frappe**. Écrivez
`supprimer_ofre` au lieu de `supprimer_offre` et :

- aucun avertissement au démarrage,
- la règle ne correspond à rien,
- l'outil de suppression reste **autorisé**.

C'est la même famille de défaut que la variable de hook qui n'existe pas : il
ne casse rien, il ne dit rien, il réussit en apparence. `outils/verifier_acces.py`
interroge le serveur pour connaître ses **vrais** noms d'outils, puis les
compare aux règles.

**Deux autres pièges, vérifiés contre la documentation :**

- `allow: ["mcp__*"]` **n'autorise rien.** Un glob d'autorisation n'est accepté
  qu'après un préfixe `mcp__<serveur>__` littéral ; le segment serveur doit
  être sans glob. La règle est ignorée avec un avertissement.
- `mcp__jobportal__.*` ne correspond à aucun outil. La forme `.*` vient des
  *matchers* de hooks, qui sont des expressions régulières ; les règles de
  permission, elles, sont des **globs**.

## ⚠️ Et le SDK a changé de nom

Le SDK 2.x expose `MCPServer` (`from mcp.server.mcpserver import MCPServer`) ;
les extraits qui montrent `FastMCP` datent du 1.x. Celui-là échoue bruyamment.
Le vrai piège est la borne : `mcp[cli]>=1.2` autorise la résolution vers une
1.x où `MCPServer` n'existe pas. Ce projet borne des deux côtés — `mcp>=2.2,<3`.

## Démarrer

```bash
uv sync --extra dev
uv run --extra dev pytest -q        # 32 tests

uv run python outils/verifier_acces.py                     # 0 erreur
uv run python outils/verifier_acces.py config-a-corriger   # 4 erreurs, 3 avertissements

uv run python chapitres/chapitre_1_protocole.py     # outils, ressources, ce que l'agent voit
uv run python chapitres/chapitre_2_installer.py     # les 3 portées, l'expansion ${VAR}
uv run python chapitres/chapitre_3_creer.py         # MCPServer, la docstring comme interface
uv run python chapitres/chapitre_4_securite.py      # la précédence, et la règle muette
uv run python chapitres/chapitre_5_projet.py        # le serveur base, de bout en bout
uv run python chapitres/chapitre_6_distribution.py  # empaqueter, borner, ne pas renommer
```

Les outils réellement exposés, demandés au serveur lui-même :

```bash
uv run python -m jobportal.serveur --lister
```

## Brancher le serveur dans votre Claude Code

```bash
claude mcp add --scope project jobportal -- uvx --from . jobportal-mcp
claude mcp list          # un serveur déclaré n'est pas un serveur connecté
```

Puis reprenez le bloc `permissions` de `.claude/settings.json`.

## La carte du projet

| Fichier | Ce qu'il contient | Chapitre |
| --- | --- | --- |
| `jobportal/serveur.py` | 4 outils, 1 ressource, `MCPServer` | 1, 3, 5 |
| `jobportal/donnees.py` | La base — le `db` que les extraits appellent sans le montrer | 5 |
| `outils/verifier_acces.py` | Le vérificateur : 5 contrôles que rien d'autre ne fait | 2, 4, 6 |
| `.mcp.json` | Deux serveurs, `${VAR}` et `${VAR:-défaut}` | 2 |
| `.claude/settings.json` | Les règles, dans la bonne forme | 4 |
| `config-a-corriger/` | La même chose, avec cinq défauts silencieux | 4 |
| `tests/test_mcp.py` | 32 tests | tous |

## Cinq choses que le code enseigne

**Une ressource n'est pas un outil.** Le schéma de la base est exposé comme
ressource : l'agent la lit pour se situer, sans appel ni effet. En faire un
outil l'obligerait à « l'appeler » pour savoir où il est, et le rendrait
interdisable par une règle — alors qu'il n'y a rien à interdire dans la lecture
d'un schéma. Un test vérifie que le schéma n'est **pas** dans la liste d'outils.

**La docstring est l'interface.** Le corps de la fonction, ses commentaires,
votre README : rien n'arrive jusqu'au modèle. Il ne voit que le nom, la
description et le schéma déduit des annotations de type. Une docstring vague
produit un outil qui ne se déclenche jamais — un défaut de qualité, pas de
syntaxe, donc invisible aux tests habituels. Un test exige ici plus de
40 signes de description sur chaque outil.

**Lecture et écriture dans des outils séparés.** Ce n'est pas du style : c'est
ce qui rend une règle de permission écrivable. Un `gerer_offre(action=...)` qui
lit *et* supprime selon son paramètre ne peut être ni autorisé, ni interdit —
seulement approuvé à l'aveugle.

**`deny`, puis `ask`, puis `allow` — la spécificité ne change rien.** Un `deny`
large l'emporte sur un `allow` précis, donc une règle `deny` ne peut pas porter
d'exception : il faut la restreindre, pas l'annoter. Le chapitre 4 met les deux
combinaisons côte à côte.

**Un nom d'outil est un contrat.** Il est écrit dans les règles de permission
de chaque poste de l'équipe. Le renommer rend caduques toutes les règles qui le
nommaient — **sans avertissement**, puisque les noms MCP échappent au contrôle.
C'est une rupture : version majeure, et une ligne dans le message de commit.

## Pour aller plus loin

- Réparez `config-a-corriger/` jusqu'à `0 erreur(s), 0 avertissement(s)`.
- Ajoutez un outil `creer_offre` et relancez le vérificateur : il le signale comme non couvert. C'est exactement ce qu'on oublie en production.
- Renommez `rechercher_offres` et regardez combien de tests tombent — puis comptez ceux qui ne tomberaient pas chez vos collègues.
- Branchez `verifier_acces.py` sur la CI : un outil ajouté sans règle échoue la construction au lieu d'attendre la production.

---

Cours associé : [Claude Code : MCP en pratique](https://syllatech.pages.dev/cours/cc-mcp)
· Formation syllatech — Diaguily SYLLA
