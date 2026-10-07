# Passerelle IA — projet de départ du cours **AgentGateway**

Cinq configurations recopiées du support de cours, passées au schéma que le
proxy publie lui-même :

```
configs/du-cours/ch1-mcp-minimal.yaml            0 erreur
configs/du-cours/ch2-llm-deux-fournisseurs.yaml  3 erreurs
configs/du-cours/ch3-mcp-federation.yaml         3 erreurs
configs/du-cours/ch4-a2a-et-inference.yaml       6 erreurs
configs/du-cours/ch5-securite.yaml               2 erreurs
```

Quatre sur cinq : `agentgateway --file` ne démarrerait pas. Et les deux
réglages qui décident vraiment du niveau de sécurité ne sont dans aucun de
ces fichiers — ce sont des **valeurs par défaut** :

```
jwtAuth.mode   = optional   « Warning: this allows requests without a JWT. »
regex.action   = mask       (et non « reject »)
```

Les deux citations sont dans `amont/config.schema.json`, copié verbatim.

---

## Ce que ce projet est, et n'est pas

⚠️ **Ce n'est pas agentgateway.** Le vrai est un proxy écrit en Rust. Le
faire tourner demanderait des backends — des clés d'API, des serveurs MCP
lancés en `npx` — qu'un cours ne peut pas exiger.

Ce qui tourne ici :

| | Réalité |
|---|---|
| la **validation** | `amont/config.schema.json` est le document que le proxy publie, appliqué tel quel par `jsonschema`. **Zéro transcription.** |
| les **règles CEL** | compilées et évaluées par `cel-python`. Pas une comparaison de chaînes. |
| les **guardrails** | de vraies expressions régulières, sur un corpus étiqueté, avec le compte des faux positifs. |
| le **routage** | le prédicat d'une route, entièrement spécifié par le schéma. Ce qui ne l'est pas — la précédence entre candidates — n'est **pas** reproduit. |

Le garde-fou : `tests/test_amont.py` exige que les **27 configurations
d'exemple du dépôt**, livrées dans `amont/exemples/`, passent toutes.
Voir [`amont/PROVENANCE.md`](amont/PROVENANCE.md).

## Démarrer

```bash
uv sync --extra dev
uv run --extra dev pytest -q        # 213 tests

uv run python chapitres/chapitre_1_demarrer.py     # la grammaire, et le défaut qui attrape tout
uv run python chapitres/chapitre_2_llm.py          # où vivent vraiment bascule et répartition
uv run python chapitres/chapitre_3_mcp.py          # fédérer, et ce que la fédération renomme
uv run python chapitres/chapitre_4_a2a.py          # deux mécanismes, deux étages
uv run python chapitres/chapitre_5_securite.py     # `mode: optional`, et le `deny` qui laisse passer
uv run python chapitres/chapitre_6_integration.py  # repointer une base URL, et ce que ça coûte
```

Les deux outils s'utilisent aussi seuls, sur **votre** configuration :

```bash
uv run python outils/verifier_config.py MON.yaml
uv run python outils/essayer_route.py MON.yaml /v1/chat --methode POST
```

`verifier_config.py` sort avec le nombre de fichiers refusés : il se met dans
une CI tel quel. Il ajoute trois avertissements que le schéma ne peut pas
exprimer — une route sans `matches`, un `jwtAuth` sans `mode`, un garde sans
`action`.

> **Sous Git Bash (Windows)**, préfixer `essayer_route.py` de
> `MSYS_NO_PATHCONV=1` : sans cela le shell réécrit `/v1/chat` en chemin
> Windows avant que l'outil ne le voie.

## Les configurations

```
configs/portail/
  01-mcp.yaml        3 cibles MCP hétérogènes, un endpoint, `prefixMode: always`
  02-llm.yaml        3 modèles internes, 2 modèles virtuels (conditionnel + bascule)
  03-securite.yaml   jwtAuth strict, 3 règles CEL défensives, guardrail `reject`

configs/du-cours/    les cinq exemples du support, recopiés SANS correction
```

**Ne pas « réparer » `configs/du-cours/`** : ces fichiers sont la pièce à
conviction, et `tests/test_du_cours.py` mesure dessus.

## Ce que les six chapitres mesurent

| | Mesure |
|---|---|
| 1 | `binds` porte sa propre étiquette : « the **low-level** API ». 20 des 27 exemples l'utilisent. Une route sans `matches` attrape **tout** — le défaut est dans le schéma, pas dans le fichier. |
| 2 | `match` n'existe pas (`matches`, une liste) ; `openai` non plus (`openAI`). Deux backends `ai` sur une route font une **répartition 50/50**, pas une bascule : celle-ci vit sous `llm.virtualModels[].routing.failover`. Le routage conditionnel est évalué **pour de bon**. |
| 3 | Quatre façons d'atteindre un serveur MCP ; la cible `openapi` prend `schema` + `host`, pas `url`. Et le piège : avec `prefixMode: conditional` (le défaut), **ajouter un second serveur renomme les outils du premier**. |
| 4 | `a2a` n'est pas un backend mais une **politique de route** ; `selfHosted` n'est pas un fournisseur. Le routage d'inférence délègue à un **Endpoint Picker** externe — les signaux GPU sont réels, mais ils vivent là-bas. |
| 5 | `mode` vaut `optional` par défaut : un `jwtAuth` sans cette ligne **laisse entrer sans jeton**. Une règle `deny` dont l'expression lève **laisse passer** — mesuré. `credit_card` n'existe pas (`creditCard`), et un garde sans `action` masque au lieu de refuser. |
| 6 | Repointer une base URL ne change rien au code — et déplace la clé d'API, les prompts et la disponibilité. Deux routes qui se chevauchent passent le schéma sans un mot. |

## Ce que le projet ne prouve pas

- le proxy ne tourne pas : aucune latence, aucun coût, aucun repli mesuré ;
- la **précédence** entre routes candidates n'est pas reproduite — elle n'est
  écrite nulle part dans `amont/`, et ce projet liste les candidates au lieu
  de désigner un vainqueur ;
- les motifs des builtins de guardrails sont **ceux de ce projet** : le
  chapitre 5 mesure un garde-fou regex, pas celui d'agentgateway ;
- les 25 fonctions CEL propres à agentgateway (`default`, `coalesce`…) ne
  sont pas évaluées — elles sont **signalées**, ce qui vaut mieux que devinées.
