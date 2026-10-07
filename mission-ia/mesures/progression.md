# La progression mesurée, étape par étape

Qwen2.5 1,5B instruct q4_K_M en local (Ollama 0.35), température 0, graine
42, `num_predict` 400. Chaque ligne : deux passages, sur le banc (14 cas,
`jobportal/banc.py`) et sur le jeu de validation (8 cas jamais regardés pour
régler l'assistant). Mesuré les 6 et 7 octobre 2026.

| Étape | Ce qui change | Banc | Validation | Fichier |
|---|---|---|---|---|
| 1 | Le modèle seul, sans données | 1 / 1 | 1 / 1 | `banc-modele-seul.json` |
| 2 | RAG : les 5 offres les plus proches données au modèle | 6 / 5 | 2 / 2 | `banc-rag.json` |
| 3 | Agent : le modèle choisit ses outils | 4 / 4 | 1 / 1 | `banc-agent.json` |
| 4 | Guidée : le code compte, classe et cherche ; le modèle rédige | 7 / 8 | 3 / 3 | `banc-guide.json` (code de l'étape 4) |
| 5 | + références reliées par le code | 11 / 11 | 4 / 4 | journal seul (fichier remplacé par l'étape 6) |
| 6 | + la description des offres donnée au modèle | **12 / 12** | **6 / 6** | `banc-guide-relie.json` |

Ce que chaque étape a appris :

- **1 → 2** : sans données, le modèle invente (« OFF-001 », donné « en exemple »).
- **2 → 3** : l'agent fait MOINS bien que le RAG. Le petit modèle annonce « je
  vais rechercher les offres » sans émettre d'appel d'outil.
- **3 → 4** : ne plus dépendre de cet appel. Une règle repère une référence
  citée (« OFF-103 ») ou « le plus de candidatures » ; sinon, recherche.
- **4 → 5** : le modèle donnait le bon fait sans la référence (« l'offre
  Ingénieur IA, 21 candidatures »). Le code relie le titre nommé à sa
  référence, sur les seules offres fournies.
- **5 → 6** : la recherche trouvait l'offre par sa description (« Kubernetes »,
  « tests d'intrusion »), mais la fiche transmise au modèle l'omettait : il
  répondait « aucune offre ». Revers mesuré : le cas « alternance », juste à
  l'étape 5, échoue à l'étape 6 — le modèle énumère désormais les cinq offres
  reçues. Plus de contexte, c'est aussi plus de bruit pour un petit modèle.

Échecs restants à l'étape 6, les mêmes aux deux passages :

- banc : « data-a-distance » (OFF-108 oubliée), « alternance » (trois offres
  de trop) ;
- validation : « v-cdi-marseille » (une offre sur trois citée), et
  « v-plus-demandee » — la règle de classement, écrite d'après la seule
  formulation du banc (« le plus de candidatures »), ne reconnaît pas « le
  plus de candidats ». C'est le prix d'une règle écrite à la main, et c'est
  le jeu de validation qui le montre.

Le critère du cadrage (au moins 12 cas justes sur 14, sur deux passages) est
atteint au banc. La validation, à 6 sur 8, dit ce que le banc seul ne dit pas.
