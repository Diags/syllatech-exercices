# Job portal — projet de départ du cours **Zep : la mémoire de vos agents IA**

Le graphe temporel écrit **en entier** — parce que c'est ce que le cours
enseigne, et que c'est invisible depuis l'extérieur.

```
   ferme   Diaguily cherche un poste a paris  [2026-03-01 → 2026-07-17]
   VALIDE  Diaguily cherche un poste a lyon   [2026-07-17 → present]
```

Paris n'est pas **supprimé** : il est **fermé**, à la date où Lyon commence. On
sait donc ce qui était vrai en mai, et l'on ne ressert pas Paris en juillet.

---

## Pourquoi réimplémenter plutôt qu'appeler Zep

`zep-cloud` demande une clé et un service distant. On ne peut donc ni
l'exécuter chez soi, ni — et c'est le plus gênant — **regarder ce qu'il fait**.
Or le cours n'enseigne pas l'API en quatre appels : il enseigne le mécanisme
temporel, et celui-là ne se voit pas de l'extérieur.

Les **noms et la forme** de l'API sont respectés :

```python
client.user.add(user_id="diaguily", first_name="Diaguily")
client.thread.create(thread_id=tid, user_id="diaguily")
client.thread.add_messages(tid, messages=messages)
contexte = client.thread.get_user_context(thread_id=tid).context
```

**Ce qui est substitué :** l'extraction de faits. Zep utilise un modèle ; ici,
des motifs. Un vrai extracteur trouve plus de choses et se trompe autrement —
mais la **structure** qu'il produit est la même, et c'est elle qui décide du
comportement de l'assistant.

## Démarrer

```bash
uv sync --extra dev
uv run --extra dev pytest -q        # 20 tests

uv run python chapitres/chapitre_1_demarrer.py     # les quatre appels
uv run python chapitres/chapitre_2_threads.py      # qui possède quoi
uv run python chapitres/chapitre_3_graphe.py       # le fait invalidé
uv run python chapitres/chapitre_4_contexte.py     # le bloc qui plafonne
uv run python chapitres/chapitre_5_metier.py       # les faits qui ne viennent pas d'une conversation
uv run python chapitres/chapitre_6_integration.py  # trois lignes autour de l'existant
```

## La différence avec un RAG, en une mesure

```
   tour    bloc de contexte   historique naif
   1                 127 sig             57 sig
   6                 191 sig            185 sig     ← elles se croisent
   12                192 sig            332 sig
```

Un RAG cherche des **documents** et rend les plus proches. Un graphe temporel
garde des **faits datés** et sait qu'un fait en a remplacé un autre.

Sur « je cherchais Paris » puis « finalement Lyon », un historique donne au
modèle **les deux**, sans dire lequel est actuel — il choisit, jamais de façon
stable. Et il ne redescend jamais : chaque message s'ajoute. Le bloc de
contexte, lui, **plafonne** : un fait qui en remplace un autre ne s'ajoute pas,
il se substitue.

## La carte du projet

| Fichier | Ce qu'il contient | Chapitre |
| --- | --- | --- |
| `jobportal/graphe.py` | Les faits, leur validité, et l'invalidation | 3 |
| `jobportal/memoire.py` | La forme de l'API Zep, sur le graphe local | 1, 2, 4, 5 |
| `jobportal/memoire.py` → `MemoireNaive` | Ce qu'on écrit avant Zep, pour comparer | 3, 4 |
| `tests/test_memoire.py` | 20 tests, dont six sur l'invalidation | tous |

## Cinq choses que le code enseigne

**La règle d'invalidation tient en une phrase.** Deux faits de même **sujet**
et même **prédicat** ne peuvent pas être vrais en même temps : le nouveau ferme
l'ancien, à la date où le nouveau commence. Tout dépend donc du prédicat —
`lieu` et `salaire` sont distincts, changer de ville n'efface pas le salaire
visé. Un extracteur qui les mélangerait ferait disparaître des faits à chaque
message.

**Un fait identique ne ferme rien.** Sinon répéter une préférence la remettrait
à zéro, et l'on perdrait *depuis quand* elle tient.

**Une ingestion dans le désordre produirait un intervalle inversé.** « Valide
du 17 juillet au 1er mars » n'est pas une donnée bizarre : elle rend toute
lecture à une date passée fausse, **pour toujours**, sans lever la moindre
erreur. Le graphe place donc le fait en retard *avant* celui qu'il a déjà, et
c'est lui qu'il ferme. Un test le vérifie.

**Les messages appartiennent au fil, les faits appartiennent à l'utilisateur.**
Un nouveau fil repart d'un historique vide **et de la même mémoire**. Confondre
les deux fait soit tout oublier à chaque session, soit tout rejouer.

**Seuls les messages de l'utilisateur nourrissent la mémoire.** Extraire les
mots de l'assistant lui ferait croire qu'il a *appris* ce qu'il vient de dire.
Au bout de trois tours, il défend une préférence qu'il a inventée lui-même.

## Ce que ce projet ne prouve pas

- L'extraction est faite par des **motifs**, pas par un modèle.
- Les latences réseau ne sont **pas** mesurées. Le « ~100 à 200 ms » du chapitre 6
  est l'ordre de grandeur annoncé par Zep, pas une mesure d'ici.
- Le vrai Zep gère aussi les **entités** (« CloudCorp » comme nœud), la
  désambiguïsation et le passage à l'échelle. Ce projet garde le mécanisme
  temporel, qui est ce que le cours enseigne.

## Pour aller plus loin

- Ajoutez un prédicat à `MOTIFS` — « disponibilité », par exemple — et regardez-le s'invalider tout seul.
- Faites partager un prédicat à deux motifs différents : des faits commencent à disparaître.
- Ingérez un historique dans le désordre et vérifiez les intervalles.
- Branchez le vrai `zep-cloud` (`uv sync --extra reel` + clé) : seul `memoire.py` change.

---

Cours associé : [Zep : la mémoire de vos agents IA](https://syllatech.pages.dev/cours/zep)
· Formation syllatech — Diaguily SYLLA
