# Job portal — projet de départ du cours **API Claude : construire vos propres agents**

L'assistant du portail d'emploi, écrit avec le SDK Python officiel
`anthropic` (1.11) : un premier appel, le streaming et les erreurs, une boucle
agentique avec deux outils, le Tool Runner, les sorties structurées, le
prompt caching, la Batches API et une requête de production.

Le modèle de données reprend celui de l'application **JobPortal**
(job-portal-ui) : offres avec titre, entreprise, catégorie, ville, contrat,
mode de travail et fourchette de salaire.

---

## Sans clé d'API, et pourtant le vrai SDK

`jobportal/fausse_api.py` remplace **seulement le transport HTTP** du SDK
(`httpx2.MockTransport`). Le SDK construit ses vraies requêtes, gère ses
vraies erreurs et ses vraies nouvelles tentatives ; seules les réponses de
Claude sont écrites à l'avance. C'est ce qui permet de **mesurer** ce que le
cours affirme : ce que le SDK envoie, combien de fois il réessaie, ce qu'il
refuse avant même d'envoyer.

Pour parler au vrai Claude, passez `anthropic.Anthropic()` (la clé vient de
`ANTHROPIC_API_KEY`) aux fonctions de `jobportal/assistant.py` à la place de
`FausseAPI().client()`.

## Démarrer

Prérequis : [uv](https://docs.astral.sh/uv/) et Python ≥ 3.11.

```bash
uv sync                       # installe tout
uv run --extra dev pytest -q  # 24 tests, doivent tous passer
```

Puis, dans l'ordre du cours :

```bash
uv run python chapitres/chapitre_1_premier_appel.py     # ce que le SDK envoie
uv run python chapitres/chapitre_2_flux_et_erreurs.py   # flux, 429, 400, max_tokens
uv run python chapitres/chapitre_3_boucle_agentique.py  # deux outils, une erreur
uv run python chapitres/chapitre_4_tool_runner.py       # schéma tiré de la docstring
uv run python chapitres/chapitre_5_cache_et_couts.py    # préfixe, coûts, lots
uv run python chapitres/chapitre_6_production.py        # repli, effort, refus
```

## Ce que les tests mesurent (SDK 1.11.0)

| Chapitre | Mesure |
|---|---|
| 1 | Le premier bloc d'une réponse d'Opus 5.5 peut être un bloc de réflexion : `content[0].text` lève une `AttributeError`. On filtre par `type`. |
| 1 | L'API est sans état : au second tour, 3 messages repartent. |
| 2 | Un 429 persistant : **3 requêtes** (l'appel et 2 nouvelles tentatives) puis `RateLimitError`. Un 429 suivi d'un succès est invisible pour l'appelant. |
| 2 | Un 400 n'est **jamais** retenté : 1 requête. |
| 2 | `max_tokens=128000` sans flux : `ValueError` levée **avant** tout envoi (0 requête). |
| 3 | Les deux `tool_result` d'un tour repartent dans **un seul** message utilisateur ; une erreur d'outil repart en `is_error`. |
| 4 | Le Tool Runner tire le schéma de la signature et de la docstring (`Args:`), avec `additionalProperties: false`, et fait la boucle : un appel d'outil puis la réponse, 2 requêtes. |
| 4 | `messages.parse` envoie le schéma Pydantic dans `output_config.format` et rend un objet validé. |
| 5 | Le prompt système avec `cache_control` est identique d'un appel à l'autre ; avec l'heure en tête, il change à chaque seconde. |
| 6 | La requête de production envoie `fallbacks: "default"`, `output_config.effort` et l'en-tête `server-side-fallback-2026-07-01`. |

## Ce que le projet ne prouve pas

- **Le cache lui-même** : il se vérifie sur la vraie API, en lisant
  `usage.cache_read_input_tokens` à partir du deuxième appel. Le projet prouve
  seulement que le préfixe envoyé reste identique, condition nécessaire.
- **La taille de `CONSIGNES`** : environ 300 mots. Sous 512 jetons, Opus 5.5
  ne met rien en cache, sans erreur ; mesurez-la avec
  `client.messages.count_tokens(...)` avant de compter sur le cache. Les
  2 000 jetons du calcul de coût sont un exemple, pas la taille de ce prompt.
- **Les coûts** sont calculés à partir des prix publiés d'Opus 5.5 (4 $ et
  20 $ par million de jetons, lecture en cache à 0,20 $, écriture à 1,25 fois
  le prix d'entrée), pas relevés sur une facture.
- **Le découpage du flux** : la fausse API découpe par mots ; la vraie découpe
  à sa façon. Seule la reconstitution du message final est mesurée.
- **Les réponses de Claude** sont écrites à l'avance : le projet teste votre
  code et le SDK, pas la qualité des réponses du modèle.
