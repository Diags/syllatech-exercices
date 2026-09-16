# Dev container — projet de départ du cours **Dev Containers**

Douze `devcontainer.json` fautifs, passés au schéma que la spécification
publie :

```
configs/a-corriger/     5 refusés par le schéma
                        7 acceptés — et six d'entre eux méritent un mot
```

Sept fautes sur douze passent la validation. C'est la mesure centrale du
projet : un schéma dit si un fichier est **bien formé**, pas s'il fait ce
qu'on croit.

Et une surprise avant même de lire le fichier :

```
"allowComments":        true      →  les commentaires // sont autorisés
"allowTrailingCommas":  false     →  la virgule finale ne l'est pas
```

Les deux lignes sont les deux premières clés du schéma publié. `json.load`,
lui, refuse les deux — d'où la panne la plus banale d'une CI qui veut relire
ce fichier.

---

## Ce que ce projet est, et n'est pas

⚠️ **Aucune image n'est construite.** Docker et le CLI `devcontainer` sont
absents : un cours ne peut pas les exiger. Ce projet **lit des descriptions
et applique leurs règles**.

Ce qui est réel :

| | Réalité |
|---|---|
| la **validation** | `amont/devContainer.base.schema.json`, copié verbatim, appliqué tel quel par `jsonschema`. **Zéro transcription.** |
| l'**ordre des Features** | l'algorithme de `amont/feature-dependencies.md` — (B1) graphe, (B2) `roundPriority`, (B3) tri par tours — sur les **28 manifestes officiels**. |
| le **nommage des variables** | la règle donnée en JavaScript par la spécification, transcrite substitution par substitution. |
| le **cycle de vie** | l'ordre et la fréquence, lus dans les descriptions du schéma — chaque commande y cite ses voisines. |

Voir [`amont/PROVENANCE.md`](amont/PROVENANCE.md) : dépôts, commits, licences.

Le dev container de `.devcontainer/` **est celui de ce projet** : ouvrez
`exemples/devcontainer/` dans un éditeur qui les gère, et c'est lui qui se
lance.

## Démarrer

```bash
uv sync --extra dev
uv run --extra dev pytest -q        # 195 tests

uv run python chapitres/chapitre_1_pourquoi.py   # le fichier n'est pas du JSON
uv run python chapitres/chapitre_2_image.py      # `context: "."`, et le pom.xml qui disparaît
uv run python chapitres/chapitre_3_features.py   # l'ordre, tour par tour
uv run python chapitres/chapitre_4_cycle.py      # ce qui a fini quand on vous rend la main
uv run python chapitres/chapitre_5_ports.py      # deux options, une seule variable
uv run python chapitres/chapitre_6_compose.py    # la branche Compose, et ses trois obligations
```

Les deux outils s'utilisent aussi seuls, sur **votre** fichier :

```bash
uv run python outils/verifier_devcontainer.py MON.json
uv run python outils/ordre_features.py MON.json --tours --env
```

`verifier_devcontainer.py` sort avec le nombre de fichiers refusés par le
schéma : il se met dans une CI tel quel. Les **sept avertissements** qu'il
ajoute ne le font pas échouer — une configuration correcte ne doit pas
casser une CI parce qu'elle mérite un commentaire.

## Ce que les six chapitres mesurent

| | Mesure |
|---|---|
| 1 | `allowComments: true`, `allowTrailingCommas: **false**` — et aucun des 13 fichiers du projet n'est lisible par `json.load`. Le `oneOf` de la racine donne un verdict juste et un message inutilisable ; le projet le montre, puis explique pourquoi il en produit un second. |
| 2 | `build.context: "."` est **valide** — et le `pom.xml` n'est plus dans le contexte. Le contexte fautif *existe*, c'est ce qui rend l'erreur déroutante. |
| 3 | `dependsOn` est dur et récursif : 2 Features demandées, **3 installées**. `installsAfter` est mou : ajouter `oryx` change l'ordre de `python`. Et `github-cli` s'installe **deux fois** quand les options diffèrent — la spécification le prévoit. |
| 4 | L'ordre est dans le schéma, pas dans une convention. `waitFor` vaut `updateContentCommand` **par défaut** : vos migrations ne sont pas finies quand vous tapez. Un tableau n'a **pas** de shell — `&&` y est un argument. |
| 5 | `2fa` et `22fa` produisent **la même** variable `_FA`. Une option mal nommée n'est pas exportée — et la bonne l'est quand même, avec sa valeur par défaut. |
| 6 | La branche Compose exige **trois** propriétés. `shutdownAction` n'accepte pas les mêmes valeurs des deux côtés. |

## Ce que le projet ne prouve pas

- aucune image n'est construite : ce qui est vérifié n'est pas la
  construction, c'est ce que les chemins **désignent** ;
- aucune Feature n'est installée : l'ordre est **calculé**, pas observé ;
- aucune commande du cycle de vie n'est exécutée : leur ordre et leur
  fréquence viennent du schéma, pas d'une mesure ;
- les motifs de substitution de variables (`${localEnv:…}`) sont affichés
  tels quels.

**Ne pas « réparer » `configs/a-corriger/`** : ces douze fichiers sont la
pièce à conviction, et `tests/test_a_corriger.py` mesure dessus.
