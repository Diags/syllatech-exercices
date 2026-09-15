# Job portal — projet de départ du cours **Prompt & Context Engineering**

Six chapitres qui **mesurent** au lieu d'affirmer. Le cours dit qu'un prompt
mieux construit donne de meilleurs résultats ; ici, on le voit :

```
v1  1/6   17%  ████
v2  3/6   50%  ████████████
v3  5/6   83%  ████████████████████
```

Et sans clé d'API.

---

## Pourquoi ces chiffres ne sont pas truqués

Un projet de prompt engineering sans modèle, c'est une contradiction. La
solution n'est pas de simuler la conclusion — ce serait une démonstration
creuse. C'est de construire un **vrai classifieur minuscule** dont la qualité
dépend réellement du prompt :

- il **lit** les exemples few-shot écrits dans le prompt et s'en sert pour
  comparer. Sans exemple, il n'a rien pour décider ;
- il **honore** une consigne de raisonnement pas à pas ;
- il **refuse** de répondre quand le prompt lui interdit d'inventer et que le
  contexte ne contient rien d'utile.

Le mécanisme est donc authentique, à petite échelle : le prompt porte
vraiment l'information, donc l'améliorer améliore vraiment le score. Ce que ce
modèle ne fait pas : comprendre. **Les chiffres valent pour la méthode, pas
comme mesure d'un vrai LLM.**

## Démarrer

```bash
uv sync --extra dev
uv run --extra dev pytest -q      # 13 tests

uv run python chapitres/chapitre_1_structure.py     # les 4 sections d'un prompt
uv run python chapitres/chapitre_2_few_shot.py      # ce que les exemples apportent
uv run python chapitres/chapitre_3_cot.py           # raisonner avant de conclure
uv run python chapitres/chapitre_4_structuree.py    # le schéma comme spécification
uv run python chapitres/chapitre_5_contexte.py      # ordre et compaction
uv run python chapitres/chapitre_6_fiabilite.py     # ancrage, score, versions
```

## Trois choses que le code enseigne, et que le cours ne dit pas

**Un exemple few-shot doit être discriminant, pas seulement correct.**
L'exemple `"Process trop long mais recruteur au top" → MITIGÉ` est
parfaitement juste. Mais il contient « recruteur au top », du vocabulaire
franchement positif : il attire donc vers MITIGÉ tout feedback qui parle d'un
bon recruteur. C'est le dernier échec qui résiste en v3, et il est **gardé
exprès** — avec son explication.

**Un prompt à 100 % sur son propre jeu de test doit inquiéter.** C'est
généralement le jeu qui a été taillé pour le prompt. Un test du projet vérifie
qu'aucune version n'atteint 100 %.

**Un diagnostic n'est pas un raisonnement.** « Je n'ai pas su décider » est
une trace pour vous ; le raisonnement pas à pas est une sortie pour
l'utilisateur, et il n'apparaît que s'il a été demandé. Confondre les deux
fait apparaître un « raisonnement » que personne n'a réclamé — l'erreur a été
commise en écrivant ce projet, un test la garde.

## La carte du projet

| Fichier | Ce qu'il contient | Chapitre |
| --- | --- | --- |
| `jobportal/modele.py` | Le classifieur-jouet, qui lit vraiment le prompt | tous |
| `jobportal/prompts.py` | v1, v2, v3 et le jeu de test commenté | 2, 3, 6 |
| `jobportal/schemas.py` | Le contrat de sortie, en pydantic | 4 |
| `jobportal/evaluation.py` | Le harnais de score | 6 |
| `tests/test_prompts.py` | 13 tests | tous |

## Pour aller plus loin

- Écrivez une v4 qui corrige l'exemple ambigu — et vérifiez au score qu'elle gagne.
- Ajoutez un cas au jeu de test, avec son `pourquoi` : un test du projet l'exige.
- Branchez un vrai modèle : seule `jobportal/modele.py` change.

---

Cours associé : [Prompt & Context Engineering](https://syllatech.pages.dev/cours/prompt-engineering)
· Formation syllatech — Diaguily SYLLA
