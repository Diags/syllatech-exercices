# Job portal — projet de départ du cours **Claude Code : les Skills réutilisables**

Trois skills qui fonctionnent, trois skills délibérément cassées, et surtout
**de quoi voir ce qu'une skill devient** — sans lancer une session.

```
  SKILL.md écrit       1037 signes  ~  288 tokens
  + !`git log --since="1 week ago" --pretty=fo`         ~  761 tokens  (exécutée ici)
  + !`git shortlog -sn HEAD --since="1 week ag`         ~    6 tokens  (exécutée ici)
  = reçu par le modèle 3938 signes  ~ 1094 tokens
```

Une skill n'est pas le fichier qu'on écrit : c'est le texte qui arrive dans le
contexte du modèle. Ici, les deux sont mesurés côte à côte.

---

## ⚠️ Ce projet corrige une erreur du cours

La vidéo du chapitre 3 livre cette skill :

```
---
name: capture-ecrans
description: Capture toutes les pages du job portal
---
Lance le script fourni :
    node scripts/captures.js --toutes-les-pages
```

**`scripts/captures.js` est résolu depuis le dossier de travail, pas depuis la
skill.** Le script vit dans `.claude/skills/capture-ecrans/scripts/` ; la
commande le cherche dans `./scripts/`. Il est introuvable — et on ne l'apprend
qu'à l'instant où la skill s'exécute, en pleine tâche.

La documentation impose un chemin absolu, construit depuis la variable fournie
à la skill :

```
python ${CLAUDE_SKILL_DIR}/scripts/captures.py --toutes-les-pages
```

(`${CLAUDE_PLUGIN_ROOT}` pour une skill distribuée dans un plugin.)

La skill fautive est livrée telle quelle dans `skills-a-corriger/`, et
`outils/verifier.py` l'attrape. Un test du projet vérifie qu'il l'attrape.

**Deuxième défaut, plus discret :** sa description dit *ce qu'elle fait*
(« Capture toutes les pages du job portal ») sans dire *quand l'employer*. Or
c'est le seul texte dont le modèle dispose pour choisir. Une skill dont la
description ne décrit pas son déclencheur ne se déclenche jamais toute seule —
et rien ne vous en avertit. Les deux autres skills de `skills-a-corriger/`
portent chacune leur propre défaut silencieux : `descriptio` au lieu de
`description`, et un `$ARGUMENTS` sans `argument-hint`.

---

## Démarrer

```bash
uv sync --extra dev
uv run --extra dev pytest -q        # 22 tests, doivent tous passer
```

Voir ce qui est chargé en permanence, et ce qui ne l'est pas :

```bash
uv run python outils/rendre.py --index      # nom + description, rien d'autre
uv run python outils/rendre.py --cout       # la facture des deux
```

Voir ce qu'une skill devient une fois rendue :

```bash
uv run python outils/rendre.py rapport-hebdo 2025-S37
uv run python outils/rendre.py captures
uv run python outils/rendre.py migration "ajoute une colonne statut"
```

Vérifier des skills avant de les livrer :

```bash
uv run python outils/verifier.py                    # les trois du projet : 0 erreur
uv run python outils/verifier.py skills-a-corriger  # 2 erreurs, 5 avertissements
```

## Installer ces skills dans votre projet

```bash
cp -r .claude/skills /chemin/vers/votre/projet/.claude/
```

Vérifiez avec `/doctor` dans la session, et tapez `/` pour les voir listées.

## La carte du projet

| Fichier | Ce qu'il contient | Chapitre |
| --- | --- | --- |
| `.claude/skills/rapport-hebdo/` | Injection de contexte par commandes, arguments | 2, 4 |
| `.claude/skills/migration/` | Les invariants d'équipe gravés dans la procédure | 5 |
| `.claude/skills/captures/` | Un script embarqué, appelé **par le bon chemin** | 3 |
| `skills-a-corriger/` | Trois skills à réparer, dont celle de la vidéo | 2, 3, 4 |
| `outils/rendre.py` | Ce que le modèle reçoit vraiment, et ce qu'il coûte | 1, 2 |
| `outils/verifier.py` | Le linter : ce que `/doctor` ne dit pas | tous |
| `tests/test_skills.py` | 22 tests, sans session Claude Code | tous |

## Quatre choses que le code enseigne

**Le chargement à la demande est arithmétique, et il se mesure.**
`rendre.py --cout` met l'index permanent (nom + description) face au contenu
complet : **5,9× moins de contexte consommé en permanence**, pour un contenu
identique. À trois skills l'écart est modeste ; il ne l'est plus à trente, ni
quand une skill embarque 300 lignes de charte de style. Un test vérifie que le
corps d'une skill n'apparaît **pas** dans l'index.

**Ce que vous relisez n'est pas ce que le modèle lit.** Les commandes injectées
s'exécutent sur la machine au moment du rendu, et leur sortie est collée telle
quelle — sans résumé, sans troncature. Un `git log` de retour de congés pèse
vingt fois la skill qui l'appelle. `rapport-hebdo` fait 288 tokens sur le
disque et 1 094 dans le contexte ; `rendre.py` affiche les deux.

**Une commande injectée n'a pas d'entrée standard.** `git shortlog -sn` sans
révision lit `stdin`, ne trouve rien, et rend une section **vide** — sans
erreur, sans avertissement. La skill du projet porte donc un `HEAD` explicite,
et un test vérifie que le harnais ferme bien `stdin` comme le vrai rendu.

**Une skill qui ne se déclenche jamais ne lève aucune erreur.** C'est toute la
raison d'être de `verifier.py` : description absente ou muette sur le
déclencheur, `name` qui diffère du dossier (la skill s'invoque par le nom du
**dossier**), champ mal orthographié — `descriptio` est ignoré en silence —,
script référencé mais absent, arguments sans `argument-hint`. Aucun de ces
défauts ne plante. Tous se voient à l'usage, trop tard.

## Pour aller plus loin

- Réparez les trois skills de `skills-a-corriger/` jusqu'à `0 erreur(s), 0 avertissement(s)`.
- Ajoutez une skill `nouvelle-page` au projet, et regardez `--cout` bouger.
- Remplacez le `git log` de `rapport-hebdo` par `git log --stat` et mesurez le rendu : c'est le genre de changement d'une ligne qui triple une facture.
- Branchez `verifier.py` sur un hook `PreToolUse` (voir le cours *les Hooks en pratique*) pour qu'il refuse un `SKILL.md` invalide à l'écriture.

---

Cours associé : [Claude Code : les Skills réutilisables](https://syllatech.pages.dev/cours/cc-skills)
· Formation syllatech — Diaguily SYLLA
