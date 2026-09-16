# Ce dossier n'est pas de moi

Tout ce qui est ici vient de **`agentregistry-dev/agentregistry`**, copié
verbatim, sans une ligne modifiée.

| Fichier | Chemin d'origine dans le dépôt |
|---|---|
| `openapi.yaml` | `openapi.yaml` |
| `README.md` | `README.md` |
| `declarative-cli.md` | `docs/declarative-cli.md` |
| `releasing.md` | `docs/releasing.md` |
| `exemples/*.yaml` | `examples/*.yaml` |

- **Dépôt** : <https://github.com/agentregistry-dev/agentregistry>
- **Commit** : `82bbd6c2d5cfa12664a85fa972e27463ffd85215` (branche `main`)
- **Récupéré le** : 14 septembre 2026
- **Version publiée la plus récente à cette date** : `v0.4.0`
- **Licence** : Apache 2.0

## Pourquoi le copier plutôt que le citer

Parce qu'un cours qui affirme « le vrai champ s'appelle `origin.type` » doit
pouvoir se faire **contredire hors ligne**. Les six chapitres et les 182 tests
ne s'appuient sur aucune citation de mémoire : ils lisent ces fichiers.

`openapi.yaml` n'est pas qu'une référence : c'est la **couche A** du
vérificateur. OpenAPI 3.1 est du JSON Schema 2020-12, donc le projet valide
vos manifestes contre le contrat que le registre publie, sans rien réécrire.

## Ce qui n'est pas ici

Le code Go (`pkg/api/v1alpha1/*_validate.go`, `pkg/mcpregistry/translate.go`)
n'est pas copié : il ne s'exécuterait pas. `jobportal/regles.py` et
`jobportal/vue_mcp.py` le **transcrivent**, chaque règle avec la citation de
la fonction dont elle sort. C'est la partie faillible du projet, et
`tests/test_amont.py` est son garde-fou : les dix manifestes d'exemple
ci-contre doivent passer.

## Mettre à jour

```bash
d=https://raw.githubusercontent.com/agentregistry-dev/agentregistry/main
curl -sSo amont/openapi.yaml        $d/openapi.yaml
curl -sSo amont/README.md           $d/README.md
curl -sSo amont/declarative-cli.md  $d/docs/declarative-cli.md
curl -sSo amont/releasing.md        $d/docs/releasing.md
for f in mcp mcp-remote skill agent prompt model full-stack; do
  curl -sSo "amont/exemples/$f.yaml" "$d/examples/$f.yaml"
done
uv run --extra dev pytest -q      # ce qui casse ici dit ce qui a bougé là-bas
```
