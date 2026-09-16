# Ce dossier n'est pas de moi

Tout ce qui est ici vient de **`agentgateway/agentgateway`**, copié verbatim,
sans une ligne modifiée.

| Fichier | Chemin d'origine dans le dépôt |
|---|---|
| `config.schema.json` | `schema/config.json` |
| `cel.json` | `schema/cel.json` |
| `cel.md` | `schema/cel.md` |
| `cel-functions.md` | `schema/cel-functions.md` |
| `README.md` | `README.md` |
| `exemples/<nom>.yaml` | `examples/<nom>/config.yaml` |

- **Dépôt** : <https://github.com/agentgateway/agentgateway>
- **Commit** : `5e5633bffe6dc5fdd29256648987197f366e462a` (branche `main`)
- **Récupéré le** : 14 septembre 2026
- **Version publiée la plus récente à cette date** : `v1.5.0`
- **Licence** : Apache 2.0 — projet de la Linux Foundation

## Ce que `config.schema.json` fait ici

Ce n'est pas une pièce justificative : c'est **le vérificateur**.
`schema/README.md` du dépôt le présente ainsi — *« The schema for the
configuration file (passed with `--file` to agentgateway) »* — et c'est du
JSON Schema **draft 2020-12**, que la bibliothèque `jsonschema` applique
telle quelle. La couche A de ce projet ne transcrit donc rien : elle valide
vos configurations contre le contrat que le proxy publie, 305 définitions
comprises.

Les 27 fichiers de `exemples/` sont son banc d'essai : `tests/test_amont.py`
exige qu'ils passent tous. C'est ce qui rend l'outil crédible quand il
refuse une configuration.

## Ce qui n'est pas ici

Le binaire Rust. `agentgateway` est un proxy : le faire tourner demanderait
des backends (fournisseurs LLM avec clés, serveurs MCP lancés en `npx`), et
un cours ne peut pas exiger cela. Ce projet **lit des configurations et fait
circuler des requêtes fictives** à travers le routage qu'elles décrivent.

Trois choses sont malgré tout exécutées pour de bon :

- la **validation** contre le schéma publié ci-dessus ;
- les **expressions CEL** des règles d'autorisation et des modèles virtuels,
  évaluées par `cel-python` — pas par une comparaison de chaînes ;
- les **expressions régulières** des guardrails, appliquées à un corpus.

## Mettre à jour

```bash
d=https://raw.githubusercontent.com/agentgateway/agentgateway/main
curl -sSo amont/config.schema.json $d/schema/config.json
curl -sSo amont/cel.json           $d/schema/cel.json
curl -sSo amont/cel.md             $d/schema/cel.md
curl -sSo amont/cel-functions.md   $d/schema/cel-functions.md
curl -sSo amont/README.md          $d/README.md
# les exemples : examples/<nom>/config.yaml → amont/exemples/<nom>.yaml
uv run --extra dev pytest -q      # ce qui casse ici dit ce qui a bougé là-bas
```
