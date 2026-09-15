# Job portal — projet de départ du cours **Claude Code : les Hooks en pratique**

Des hooks qui marchent, et surtout **de quoi les mettre au point sans lancer
une session**. C'est ce qui manque le plus quand on écrit son premier hook :
on modifie un script, on relance Claude Code, on provoque l'action, on
regarde… et on recommence. Ici, la boucle dure une seconde.

---

## ⚠️ Ce projet corrige une erreur du cours

La vidéo du chapitre 3 propose ceci pour formater le fichier édité :

```json
"command": "npx eslint --fix $CLAUDE_FILE_PATHS"
```

**`CLAUDE_FILE_PATHS` n'existe pas.** Les seules variables d'environnement
fournies aux hooks sont `CLAUDE_PROJECT_DIR`, `CLAUDE_PLUGIN_ROOT`,
`CLAUDE_PLUGIN_DATA`, `CLAUDE_EFFORT`, `CLAUDE_CODE_REMOTE` et
`CLAUDE_CODE_BRIDGE_SESSION_ID`.

La variable inconnue s'étend donc à la chaîne vide et la commande devient
`npx eslint --fix`, sans fichier. **Le hook ne formate rien, ne signale rien**,
et l'on croit son projet formaté pendant des semaines. C'est la pire catégorie
de défaut : celui qui réussit en apparence.

Le chemin arrive dans le **JSON de l'entrée standard**, sous
`tool_input.file_path` — c'est ce que fait `.claude/hooks/formate.py`, et un
test le vérifie en posant délibérément `CLAUDE_FILE_PATHS` à une valeur absurde.

---

## Démarrer

```bash
uv sync --extra dev
uv run --extra dev pytest -q        # 24 tests, doivent tous passer
```

Essayez un hook sans lancer Claude Code :

```bash
uv run python outils/essayer.py .claude/hooks/garde_bash.py PreToolUse Bash "rm -rf /"
uv run python outils/essayer.py .claude/hooks/garde_bash.py PreToolUse Bash "ls -la"
uv run python outils/essayer.py .claude/hooks/formate.py PostToolUse Edit exemple_mal_formate.py
```

Le harnais affiche le code de sortie, les deux flux, et surtout **la
conclusion** : ce que Claude Code aurait fait de tout ça.

## Installer ces hooks dans votre projet

```bash
cp -r .claude/hooks /chemin/vers/votre/projet/.claude/
```

puis reprenez le bloc `hooks` de `.claude/settings.json`. Vérifiez avec
`/hooks` dans la session, et `claude --debug` pour voir leur exécution.

## La carte du projet

| Fichier | Ce qu'il fait | Chapitre |
| --- | --- | --- |
| `.claude/hooks/garde_bash.py` | Refuse les commandes destructrices | 1, 2 |
| `.claude/hooks/formate.py` | Formate le fichier édité — **sans** la variable fantôme | 3 |
| `.claude/settings.json` | Déclare les deux, prêt à copier | 1, 5 |
| `outils/essayer.py` | Envoie un événement factice à un hook | 6 |
| `tests/test_hooks.py` | 24 tests, sans session Claude Code | tous |

## Trois choses que le code enseigne

**Deux façons de refuser, et l'une est meilleure.** Le code de sortie `2` bloque
et montre `stderr`. Mais un objet JSON sur la sortie standard, avec
`permissionDecision: "deny"` et une raison, est plus précis : la raison arrive
dans un champ prévu pour elle, et Claude peut proposer autre chose au lieu de
réessayer la même commande. `garde_bash.py` utilise la seconde.

**Le code 2 ne bloque pas partout.** `PreToolUse`, `UserPromptSubmit`, `Stop`,
`SubagentStop` — oui. `PostToolUse` — non : l'action est déjà faite. Écrire un
« garde-fou » sur `PostToolUse` est une erreur courante, et le harnais la
signale explicitement au lieu de vous laisser croire qu'il protège.

**Des motifs, pas des chaînes.** `"rm -rf" in commande` laisse passer
`rm  -rf` avec deux espaces, `RM -RF`, et `rm -fr`. Un test paramétré couvre
les trois. À l'inverse, `git push --force-with-lease` doit **passer** : un
garde-fou qui bloque la bonne pratique sera désactivé dans la semaine.

## Pour aller plus loin

- Ajoutez un hook `UserPromptSubmit` qui injecte la branche git courante en contexte.
- Ajoutez un hook `Stop` qui joue un son — et vérifiez au harnais qu'il ne bloque rien.
- Faites refuser `garde_bash.py` selon le dossier : `tool_input.command` et `cwd` sont tous deux dans l'événement.

---

Cours associé : [Claude Code : les Hooks en pratique](https://syllatech.pages.dev/cours/cc-hooks)
· Formation syllatech — Diaguily SYLLA
