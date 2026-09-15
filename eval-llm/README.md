# Job portal — projet de départ du cours **Évaluation & tests des applications LLM**

Un harnais d'évaluation complet, qui **tourne sans clé d'API** et qui met en
évidence, chiffres à l'appui, le piège central du sujet.

```
      global   nominal   limite   advers.
 v1      69%      100%      28%       40%
 v2      87%      100%      88%       50%
 v3      97%      100%      88%      100%
```

Regardez la colonne `nominal` : **elle ne bouge jamais**. C'est la seule que
regarderait une évaluation mal construite — et elle donne 100 % à un agent qui
invente quand il ne sait pas.

---

## Pourquoi l'agent évalué est déterministe

Un projet d'évaluation a besoin de quelque chose à évaluer. Un agent
déterministe rend l'évaluation **reproductible** : quand le score bouge, c'est
que le code a bougé, pas que le modèle a eu une autre idée. On isole ainsi ce
que le cours enseigne — la mesure — de ce qu'il n'enseigne pas — le hasard.

Les trois versions ne diffèrent pas au hasard : v1 invente, v2 sait dire
« je ne sais pas », v3 refuse en plus ce qui sort de son rôle. Chaque
progression est visible dans une colonne différente.

## Démarrer

```bash
uv sync --extra dev
uv run --extra dev pytest -q       # 18 tests, dont le test de non-régression

uv run python chapitres/chapitre_1_pourquoi.py      # tester des propriétés, pas l'égalité
uv run python chapitres/chapitre_2_dataset.py       # le jeu nominal qui rassure à tort
uv run python chapitres/chapitre_3_juge.py          # ce qu'on confie à un juge LLM
uv run python chapitres/chapitre_4_metriques.py     # les poids, et le score qui ment
uv run python chapitres/chapitre_5_ci.py            # le seuil de non-régression
uv run python chapitres/chapitre_6_gardefous.py     # entrée et sortie
```

## Quatre choses que le code enseigne

**Un juge LLM coûte cher pour ce qu'une règle sait faire.** L'ancrage — est-ce
que la réponse s'appuie sur les sources ? — se calcule mot à mot : trois
verdicts en moins d'une milliseconde, sans réseau, reproductibles. Gardez le
modèle pour le ton, la nuance, la comparaison de deux réponses également
justes. Ce projet implémente la partie gratuite, et dit où s'arrête sa portée.

**Un refus ne doit pas être pénalisé.** « Information non disponible »
n'affirme rien : lui donner un mauvais score d'ancrage pousserait l'agent à
inventer plutôt qu'à se taire — exactement l'inverse du but. Un test le fige.

**Un score global masque toujours quelque chose.** v1 affiche 69 % avec un
type à 28 %. Un test du projet vérifie qu'aucun type ne s'effondre, en plus du
score d'ensemble.

**L'évaluation trouve ce que la relecture ne trouve pas.** Il reste un échec
en v3 : la question « Combien de candidats **ont** postulé ? » fait remonter
une offre, parce que la recherche travaille par sous-chaîne et que « ont » se
trouve dans « fr**ont** » de « Développeur front React ». Personne ne trouve ça
en relisant du code. Le bug est **gardé exprès**, expliqué au chapitre 4, et
sa correction est l'exercice laissé au lecteur.

## La carte du projet

| Fichier | Ce qu'il contient | Chapitre |
| --- | --- | --- |
| `jobportal/agent.py` | L'agent évalué, en trois versions | tous |
| `jobportal/jeu.py` | 15 cas : nominal, limite, adversarial | 2 |
| `jobportal/juge.py` | Le juge d'ancrage, sans modèle | 1, 3 |
| `jobportal/metriques.py` | Exactitude, ancrage, latence, score agrégé | 4 |
| `jobportal/evaluation.py` | Le harnais et la ventilation par type | 2, 4 |
| `jobportal/gardefous.py` | Injection, données personnelles, ancrage | 6 |
| `tests/test_eval.py` | 18 tests, dont la non-régression | 5 |

## Pour aller plus loin

- Corrigez la recherche par sous-chaîne, et regardez le score de v3 finir à 100 %.
- Ajoutez cinq cas adversariaux : le taux de blocage devient un score suivi.
- Branchez un vrai juge LLM **en plus** du juge d'ancrage, et comparez leurs verdicts sur les mêmes cas.

---

Cours associé : [Évaluation & tests des applications LLM](https://syllatech.pages.dev/cours/eval-llm)
· Formation syllatech — Diaguily SYLLA
