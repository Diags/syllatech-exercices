# Job portal — projet de départ du **Claude Code Bootcamp**

Une configuration `.claude/` complète, une configuration qui a **pourri**, et
le vérificateur qui fait la différence — en une seconde.

```
  ERREUR     CLAUDE.md
             « npm run check » n'existe pas dans package.json (scripts : dev, lint)
  ERREUR     hooks/PreToolUsage
             evenement inconnu : ce hook ne se declenchera JAMAIS.
  ERREUR     deny / mcp__analytics__export
             le serveur « analytics » n'est pas dans .mcp.json. La regle ne
             protege rien, et aucun avertissement ne le dit.
```

**Aucun de ces défauts ne lève d'erreur.** Tous se voient à l'usage, une fois.

---

## Le sujet de ce projet

Hooks, MCP, sous-agents, skills, `CLAUDE.md` : cinq mécanismes qui marchent
bien séparément, et qui pourrissent **ensemble**.

`/hooks` liste les hooks. `/doctor` relit les skills. `claude mcp list` teste
les serveurs. Chacun vérifie **sa** pièce — personne ne vérifie la cohérence
entre les pièces. C'est exactement là que se trouve la dégradation réelle d'un
`.claude/` après six mois :

| Le défaut | Ce qu'il produit |
| --- | --- |
| un hook appelle un script supprimé | il échoue à chaque déclenchement, en silence |
| `PreToolUsage` au lieu de `PreToolUse` | le hook ne se déclenche **jamais** |
| un `tools:` nomme un outil renommé | l'agent ne l'a pas, et rien ne le dit |
| une règle MCP nomme un serveur retiré | elle a l'air de protéger, elle ne protège rien |
| `CLAUDE.md` documente `npm run check` | **répété à l'agent à chaque session** |

Le dernier est le plus coûteux : `CLAUDE.md` est relu **à chaque session**. Une
commande fausse y est répétée des centaines de fois — et à chaque fois, l'agent
découvre qu'elle échoue et improvise autre chose.

## Démarrer

```bash
uv sync --extra dev
uv run --extra dev pytest -q            # 33 tests

uv run python outils/verifier_config.py                  # 0 erreur
uv run python outils/verifier_config.py config-pourrie   # 9 erreurs, 2 avertissements

uv run python chapitres/chapitre_1_demarrer.py       # ce qui est lu, et quand
uv run python chapitres/chapitre_2_hooks.py          # deux défauts muets
uv run python chapitres/chapitre_3_mcp.py            # la règle qui ne protège rien
uv run python chapitres/chapitre_4_agents_skills.py  # deux choses qu'on confond
uv run python chapitres/chapitre_5_memoire.py        # le fichier qu'on paie toujours
uv run python chapitres/chapitre_6_production.py     # le mode sans tête, et sa CI
```

## Installer cette configuration dans votre projet

```bash
cp -r .claude CLAUDE.md .mcp.json /chemin/vers/votre/projet/
```

Puis **relancez le vérificateur** : il vous dira ce qui ne colle pas avec votre
projet — un `npm run` qui n'existe pas chez vous, un serveur MCP absent.

## La carte du projet

| Fichier | Ce qu'il contient |
| --- | --- |
| `CLAUDE.md` | Court, actionnable, et **vérifié** contre `package.json` |
| `.claude/settings.json` | Permissions et deux hooks, chemins en `$CLAUDE_PROJECT_DIR` |
| `.mcp.json` | Un serveur, version **épinglée**, DSN en `${VAR:-défaut}` |
| `.claude/agents/reviseur.md` | Lecture seule — un réviseur ne réécrit pas ce qu'il juge |
| `.claude/skills/changelog/` | Une skill avec son script, appelé par `${CLAUDE_SKILL_DIR}` |
| `config-pourrie/` | La même chose, six mois plus tard |
| `outils/verifier_config.py` | Les cinq contrôles croisés | 
| `tests/test_config.py` | 33 tests |

## Cinq choses que le code enseigne

**Ce qui est lu à chaque session, et ce qui ne l'est pas.** `CLAUDE.md` en
entier, les permissions, les serveurs MCP, et la **description** de chaque agent
et de chaque skill. Le corps d'une skill, non — il n'entre qu'au déclenchement.
Cette distinction décide de ce qui doit rester court : ici, 1 424 signes à
chaque session.

**Un événement de hook mal orthographié est accepté.** `PreToolUsage` au lieu
de `PreToolUse` : le hook est enregistré et ne se déclenche jamais. On croit son
projet protégé pendant des mois.

**Un chemin de hook doit partir de `$CLAUDE_PROJECT_DIR`.** Un hook s'exécute
depuis le dossier courant de l'agent, qui n'est pas forcément la racine. Un
chemin relatif marche tant qu'on ne fait pas `cd` dans la session.

**Épingler la version d'un serveur MCP n'est pas de la prudence.** La
description d'un outil MCP est **du texte que le modèle lit**. Une montée de
version silencieuse peut donc changer ce que votre agent croit devoir faire —
sans commit, sans revue, sans trace.

**Un sous-agent isole un contexte ; une skill fige une procédure.** On prend un
sous-agent quand la tâche est volumineuse **en lecture**. On prend une skill
quand elle est répétitive et que l'ordre des étapes compte. Une skill qui
explore cinquante fichiers remplit votre contexte ; un sous-agent qui suit une
procédure la réinvente à chaque fois.

## Une précaution assumée

`OUTILS_CONNUS` est un **instantané**. Claude Code en ajoute ; un nom absent de
cette liste n'est donc pas forcément une faute. C'est pourquoi un outil inconnu
produit un **avertissement**, jamais une erreur — un vérificateur qui crie faux
finit désactivé, et il emporte avec lui les contrôles qui étaient justes.

## Pour aller plus loin

- Renommez un script dans `package.json` sans toucher à `CLAUDE.md` : un test tombe.
- Supprimez `.claude/hooks/formate.py` : le hook reste, et le vérificateur le dit.
- Branchez `verifier_config.py --ci` **avant** votre appel `claude -p` en CI : lancer un agent sur une configuration incohérente, c'est payer un appel pour un résultat faussé.
- Ajoutez un contrôle : un `allowed-tools` de skill qui nomme un outil inconnu.

---

Cours associé : [Claude Code Bootcamp](https://syllatech.pages.dev/cours/claude-code)
· Formation syllatech — Diaguily SYLLA
