# Job portal — projet de départ du cours **Mission IA**

Une application IA menée comme une mission chez un client : un dossier de
cadrage écrit avant le code, un banc d'évaluation, un assistant qui répond aux
candidats et aux recruteurs sur les offres du portail, ses traces, ses
défenses, et un conteneur prêt à livrer. Tout tourne en local avec Ollama :
aucune donnée ne quitte la machine.

Le modèle de données reprend celui de l'application **JobPortal**
(job-portal-ui) : 24 offres, avec titre, entreprise, catégorie, ville,
contrat, mode de travail, salaire et description.

---

## Démarrer

```bash
uv sync --extra dev
uv run --extra dev pytest -q        # 47 tests, hors ligne : un faux serveur Ollama

ollama pull qwen2.5:1.5b-instruct-q4_K_M
ollama pull bge-m3
uv run uvicorn jobportal.api:app --port 8000
#   POST /question {"question": "..."}   GET /sante   GET /metriques
```

Les mesures se rejouent, une commande chacune (contre le vrai Ollama) :

```bash
uv run python mesures/banc.py guide-relie      # le banc et la validation, deux passages
uv run python mesures/attaquer.py              # les six attaques, sans et avec défenses
uv run python mesures/observer.py              # 22 requêtes à travers le service
uv run python mesures/conteneur.py             # l'image, construite, démarrée, mesurée
```

## Ce que contient le projet

| Fichier | Rôle |
|---|---|
| `docs/cadrage.md` | le besoin, le périmètre, les critères de réussite **écrits avant le code** |
| `jobportal/banc.py` | 14 cas notés automatiquement, et 8 cas de **validation** jamais utilisés pour régler l'assistant |
| `jobportal/agent.py` | les approches comparées : RAG, agent avec outils, guidée, références reliées |
| `jobportal/securite.py` | six attaques et quatre défenses |
| `jobportal/observabilite.py` | une ligne JSON par requête, et leur résumé |
| `jobportal/roi.py` | le retour sur investissement, **calculé** sur les hypothèses du client |
| `jobportal/api.py`, `Dockerfile` | le service, et son conteneur |

## Ce qui a été mesuré

Les 6 et 7 octobre 2026, Qwen2.5 1,5B en local (Ollama 0.35), sur un
portable sans GPU dont le processeur était déjà occupé par d'autres programmes.

**L'assistant, étape par étape** (deux passages ; détail dans `mesures/progression.md`) :

| Étape | Banc (14) | Validation (8) |
|---|---|---|
| Modèle seul | 1 / 1 | 1 / 1 |
| RAG | 6 / 5 | 2 / 2 |
| Agent avec outils | 4 / 4 | 1 / 1 |
| Guidée (le code compte, classe, cherche) | 7 / 8 | 3 / 3 |
| + références reliées par le code | 11 / 11 | 4 / 4 |
| + descriptions données au modèle | **12 / 12** | **6 / 6** |
| + défenses du code (version livrée) | **12 / 12** | **6 / 6** |

**La sécurité** (détail dans `mesures/securite.md`) : sans défense, 1 attaque
sur 6 réussit (le modèle recopie l'adresse d'une offre piégée) ; avec les
défenses du code, aucune. La consigne défensive n'arrêtait aucune attaque de
plus et faisait tomber le banc à 10/14 : elle est désactivée.

**Le service** (`mesures/observabilite.json`, `mesures/conteneur.json`) :

| | |
|---|---|
| Durée d'une requête, médiane / 95e centile | 3,9 s / 7,5 s |
| Jetons par requête, entrée / sortie | 565 / 33 |
| Construction de l'index | 5,1 s, une fois |
| Image Docker, compressée / sur disque | 84 Mo / 363 Mo |
| Conteneur : jusqu'à `/sante`, mémoire | 5,9 s, 43 Mio (le modèle tourne dans Ollama, sur l'hôte) |

## Ce que le projet ne prouve pas

- **Le retour sur investissement** : `roi.py` calcule ; les volumes, temps et
  coûts sont des hypothèses du client, jamais des mesures.
- **Les durées sur une autre machine** : elles varient avec le matériel et la
  charge. Ce qui doit se retrouver, ce sont les scores et les constats.
- **La sécurité face à d'autres attaques** : six attaques rejouées sont des
  régressions à rejouer, pas une garantie.
- **Un modèle plus grand, ou une API** : non mesurés ici. Le Qwen2.5 3B a été
  écarté pour sa licence, non commerciale ; un modèle d'API se brancherait par
  le client compatible OpenAI, sans changer le banc.
