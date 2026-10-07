# Job portal — projet de départ du cours **Claude Code : Sous-agents & Orchestration**

Le cours affirme qu'un sous-agent « ne renvoie que sa conclusion ». Ici, on
compte.

```
   sans delegation                      6449 tokens
   avec delegation                        58 tokens
   reste chez l agent, puis disparait   6769 tokens

   La fenetre principale porte 111x moins.
```

Un dépôt de 52 fichiers à explorer, un runtime de sous-agents qui reproduit la
sémantique de Claude Code, et six chapitres qui **mesurent** ce que le cours
affirme — y compris quand déléguer fait perdre.

---

## Ce qui est réel, et ce qui est substitué

**Réel :** les fichiers `.claude/agents/*.md` (copiez-les, ils fonctionnent),
le front-matter et ses champs, `tools` comme **liste blanche appliquée**,
l'isolation des contextes, le fan-out parallèle, la vérification adversariale,
et tous les comptes de tokens.

**Substitué :** le modèle. L'analyse est déterministe — des motifs cherchés
dans le code. Ce que le cours enseigne n'est pas *comment un modèle trouve un
bug* : c'est l'orchestration, et elle est ici entièrement authentique.

La latence est simulée et **réellement attendue** (`time.sleep`), réduite d'un
facteur dix. Sans cela le fan-out ne gagnerait rien — le travail local est trop
rapide. Dans une vraie session c'est l'inverse : la latence domine tout.

## Démarrer

```bash
uv sync --extra dev
uv run --extra dev pytest -q        # 30 tests

uv run python chapitres/chapitre_1_pourquoi.py    # deleguer, et ne pas deleguer
uv run python chapitres/chapitre_2_creer.py       # « tools » n'est pas un conseil
uv run python chapitres/chapitre_3_parallele.py   # le fan-out, et sa limite
uv run python chapitres/chapitre_4_reviseur.py    # 28 constats bruts, 4 presentes
uv run python chapitres/chapitre_5_pipeline.py    # explorer → coder → relire
uv run python chapitres/chapitre_6_couts.py       # la facture, et le tableau de decision
```

## Installer ces agents dans votre projet

```bash
cp .claude/agents/explorateur.md .claude/agents/reviseur.md \
   /chemin/vers/votre/projet/.claude/agents/
```

Ne copiez **pas** `reviseur-permissif.md` : c'est le contre-exemple du
chapitre 2, livré pour être comparé.

## La carte du projet

| Fichier | Ce qu'il contient | Chapitre |
| --- | --- | --- |
| `.claude/agents/explorateur.md` | Lecture seule, Haiku, format de rapport imposé | 2, 3, 5 |
| `.claude/agents/reviseur.md` | Lecture seule, Sonnet, relecture adversariale | 4, 5 |
| `.claude/agents/reviseur-permissif.md` | Le même **sans** `tools` — le contre-exemple | 2 |
| `jobportal/agents.py` | Le runtime : contexte isolé, liste blanche, fan-out | tous |
| `jobportal/travaux.py` | L'analyse, et la seconde passe qui relit le code | 4 |
| `jobportal/depot.py` | 52 fichiers déterministes, avec de vrais défauts | tous |
| `tests/test_agents.py` | 30 tests | tous |

## Cinq choses que le code enseigne

**La délégation divise le contexte par cent, et elle se mesure.** Explorer
`offres/` en direct charge 6 449 tokens dans la fenêtre principale, et ils y
restent : chaque tour suivant les repaie. Déléguer en met 58. Un test vérifie
qu'aucun fichier lu par l'agent ne remonte dans la session — si cette promesse
tombe, la délégation ne sert plus à rien.

**`tools` n'est pas un conseil : c'est une garantie exécutée.** Le même
réviseur, avec et sans le champ, face au même ordre d'écrire :

```
   reviseur             REFUSE   → L'agent « reviseur » a appele Edit, absent de
                                   son « tools: Read, Grep, Glob ». Appel refuse.
   reviseur-permissif   A ECRIT  → « j'ai corrige le secret en dur »
```

En l'absence de `tools`, un sous-agent **hérite de tous les outils de la
session**, `Write` et `Edit` compris. La différence tient en une ligne de
front-matter, et elle ne produit aucune erreur tant que l'agent n'essaie pas.

**Un réviseur trouve toujours quelque chose — et c'est le problème.** Sur le
diff de la branche : **28 constats bruts, dont 24 de pur style**. Après
relecture de chaque constat *dans le code* : **4 présentés**, dont 3 confirmés
avec la conséquence nommée. Un rapport de 28 lignes où 4 comptent, on le lit
une fois, on le survole la deuxième, et on désactive le réviseur la troisième.

**Un constat n'est pas seulement vrai ou faux.** `DEPLOY_KEY=AKIAIOSFODNN7EXAMPLE`
est la clé d'exemple de la documentation AWS. La présenter comme un secret
fuité fait perdre du temps ; la jeter comme du bruit perd une information
réelle — elle n'a rien à faire là non plus. D'où un troisième verdict,
`DOUTEUX`, et la raison affichée avec lui.

**Déléguer une micro-tâche coûte quinze fois plus cher que de la faire.** Le
chapitre 6 le mesure dans le sens qui dérange : 467 tokens en direct, 6 778 via
un sous-agent, pour renommer une variable. La meilleure optimisation reste de
ne pas déléguer — et le fan-out de quatre agents, c'est quatre additions pour
un temps d'attente inchangé.

## Pour aller plus loin

- Retirez `tools:` de `reviseur.md` et relancez les tests : deux tombent, et c'est exactement le risque décrit.
- Ajoutez un agent `auditeur` (dépendances, licences) et mesurez son coût sur Haiku puis sur Sonnet.
- Faites échouer `conflit()` : donnez la même cible à deux tâches d'un fan-out, et regardez ce que le test refuse de laisser passer.
- Branchez le réviseur sur un hook `PreToolUse` de commit (voir le cours *les Hooks en pratique*).

---

Cours associé : [Claude Code : Sous-agents & Orchestration](https://syllatech.pages.dev/cours/cc-agents)
· Formation syllatech — Diaguily SYLLA
