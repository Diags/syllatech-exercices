# Ce dossier n'est pas de moi

Tout ce qui est ici vient des dépôts de la spécification Dev Containers,
copié verbatim, sans une ligne modifiée.

| Fichier | Dépôt et chemin d'origine |
|---|---|
| `devContainer.base.schema.json` | `devcontainers/spec` — `schemas/devContainer.base.schema.json` |
| `devContainerFeature.schema.json` | `devcontainers/spec` — `schemas/devContainerFeature.schema.json` |
| `feature-dependencies.md` | `devcontainers/spec` — `docs/specs/feature-dependencies.md` |
| `devcontainer-features.md` | `devcontainers/spec` — `docs/specs/devcontainer-features.md` |
| `devcontainerjson-reference.md` | `devcontainers/spec` — `docs/specs/devcontainerjson-reference.md` |
| `devcontainer-reference.md` | `devcontainers/spec` — `docs/specs/devcontainer-reference.md` |
| `features-user-env-variables.md` | `devcontainers/spec` — `docs/specs/features-user-env-variables.md` |
| `parallel-lifecycle-script-execution.md` | `devcontainers/spec` — `docs/specs/parallel-lifecycle-script-execution.md` |
| `features/<nom>.json` | `devcontainers/features` — `src/<nom>/devcontainer-feature.json` |

- **Spécification** : <https://github.com/devcontainers/spec> — commit `c95ffee`
- **Features officielles** : <https://github.com/devcontainers/features> — commit `fbd13b8`
- **Récupéré le** : 14 septembre 2026
- **Licence** : MIT (les deux dépôts)

## Pourquoi ces fichiers sont ici

`devContainer.base.schema.json` n'est pas une pièce justificative : c'est
**le vérificateur**. C'est le schéma que les éditeurs appliquent à votre
`devcontainer.json`, et c'est du JSON Schema draft 2019-09 — la bibliothèque
`jsonschema` le lit tel quel. La couche A de ce projet ne transcrit donc
rien.

`feature-dependencies.md` spécifie l'**algorithme d'ordre d'installation**
— (B1) graphe, (B2) `roundPriority`, (B3) tri par tours — assez précisément
pour être implanté ligne à ligne. `jobportal/features.py` le fait, et cite
chaque étape.

Les 28 manifestes de `features/` sont ceux des Features officielles. Ils
portent les vraies relations `installsAfter` et `dependsOn` : c'est sur eux
que le chapitre 3 mesure, pas sur un exemple inventé.

## Ce qui n'est pas ici

Le CLI `devcontainer` (Node) et Docker. Construire une image et lancer un
conteneur demande les deux, et un cours ne peut pas l'exiger. Ce projet
**lit des descriptions et applique leurs règles** : la validation, l'ordre
des Features, l'ordre du cycle de vie, la résolution des chemins et le
nommage des variables d'option.

## Mettre à jour

```bash
s=https://raw.githubusercontent.com/devcontainers/spec/main
f=https://raw.githubusercontent.com/devcontainers/features/main/src
curl -sSo amont/devContainer.base.schema.json    $s/schemas/devContainer.base.schema.json
curl -sSo amont/devContainerFeature.schema.json  $s/schemas/devContainerFeature.schema.json
for d in feature-dependencies devcontainer-features devcontainerjson-reference \
         devcontainer-reference features-user-env-variables \
         parallel-lifecycle-script-execution; do
  curl -sSo "amont/$d.md" "$s/docs/specs/$d.md"
done
for n in $(ls amont/features | sed 's/.json//'); do
  curl -sSo "amont/features/$n.json" "$f/$n/devcontainer-feature.json"
done
uv run --extra dev pytest -q      # ce qui casse ici dit ce qui a bougé là-bas
```
