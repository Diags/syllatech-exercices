# Job portal — projet de départ du cours **Sandboxing sécurisé**

Quatre niveaux d'isolation, neuf évasions publiques, et un harnais qui dit
**exactement où se situe la frontière** — sur votre machine, en une seconde.

```
     cls = ().__class__.__bases__[0]
     for s in cls.__subclasses__():
         if s.__name__ == 'BuiltinImporter':
             os = s().load_module('os')
             print(os.getcwd())
             break

   resultat : ECHAPPE — C:\Users\...\sandbox-securise
```

Six lignes, publiées depuis vingt ans, et la liste blanche de builtins ne sert
plus à rien. **On ne peut pas isoler Python depuis Python.**

---

## ⚠️ Ce qui s'exécute ici, et ce qui ne s'exécute pas

| Niveau | État |
| --- | --- |
| `naif` — aucune isolation | **exécuté** |
| `restreint` — builtins retirés, même processus | **exécuté** |
| `processus` — interprète séparé, délai, bornes | **exécuté** |
| `conteneur` — namespaces, cgroups, seccomp, gVisor | **généré et vérifié, pas lancé** |

Le quatrième demande un noyau Linux et Docker. Ce projet ne le simule pas : il
construit la ligne de commande et **relit la vôtre** (`jobportal/conteneur.py`),
ce qui tourne partout. Prétendre isoler sans rien faire serait exactement le
défaut que ce cours dénonce.

Sous Windows, `resource` n'existe pas : le niveau `processus` applique un délai
mais **aucune borne mémoire**. Le harnais l'affiche en tête au lieu de laisser
croire le contraire.

## Le résultat, et il demande de l'attention

```
     naif            0/9 ligne(s) arretee(s)
     restreint       6/9 ligne(s) arretee(s)
     processus       1/9 ligne(s) arretee(s)
```

**`restreint` arrête plus de lignes que `processus`, et il est infiniment moins
sûr.** Les deux ne font pas la même chose, et les compter ensemble mélange deux
axes :

- **`restreint` retire des NOMS.** Rien n'est contenu : ce qui s'en échappe
  s'échappe dans *votre* processus, avec vos droits.
- **`processus` ne retire AUCUN nom** — `import os` y marche. Mais le dommage
  meurt avec le sous-processus.

La bonne question n'est donc pas « combien de lignes bloquées ? » mais
**« qu'est-ce qui atteint l'hôte ? »**. Un test du projet vérifie cette
inversion, pour qu'on ne lise pas le tableau comme une échelle.

## Démarrer

```bash
uv sync --extra dev
uv run --extra dev pytest -q          # 39 tests

uv run python outils/evasion.py       # le tableau complet
uv run python outils/evasion.py --ci  # code 1 si un niveau tient moins que prévu

uv run python chapitres/chapitre_1_menace.py        # ce que l'anti-patron concède
uv run python chapitres/chapitre_2_systeme.py       # processus, puis noyau
uv run python chapitres/chapitre_3_runtimes.py      # runc, gVisor, microVM
uv run python chapitres/chapitre_4_wasm.py          # pourquoi Python ne peut pas
uv run python chapitres/chapitre_5_integrer.py      # dans un service existant
uv run python chapitres/chapitre_6_durcissement.py  # rejouer, mesurer, surveiller
```

## La carte du projet

| Fichier | Ce qu'il contient | Chapitre |
| --- | --- | --- |
| `jobportal/evasions.py` | 9 évasions publiques, sur **deux axes** : nommage et dommage | tous |
| `jobportal/niveaux.py` | Les trois niveaux exécutables, et ce que chacun promet | 1, 2, 4 |
| `jobportal/conteneur.py` | La commande durcie, construite **et relue** | 2, 3, 6 |
| `outils/evasion.py` | Le harnais : où se situe la frontière, ici | 6 |
| `tests/test_isolation.py` | 39 tests, dont la moitié vérifie des **échecs** | tous |

## Cinq choses que le code enseigne

**Ce n'est pas un bug de Python.** Le langage est *conçu* pour l'introspection :
c'est ce qui rend les ORM, les sérialiseurs et les frameworks de test possibles.
La même propriété rend l'isolation en-langage impossible. Le module `rexec` de
la bibliothèque standard a été **retiré** pour cette raison. Refaire ce que le
langage a abandonné en 2003 n'est pas un projet.

**Un sandbox qu'on ne peut pas mesurer sans risque n'est pas un sandbox.** Le
corpus contient une boucle infinie ; la mesurer en-processus figerait le harnais
lui-même. `restreint()` lance donc la restriction dans un sous-processus **pour
la mesurer** — et le fichier dit clairement que ce délai n'appartient pas au
niveau. Ce détour est en lui-même l'argument du chapitre 4.

**Un drapeau dont on ignore ce qu'il empêche est un drapeau qu'on retire.** Les
huit drapeaux obligatoires sont chacun rattachés à l'évasion qu'ils neutralisent,
et `verifier()` le dit dans son message. Le chapitre 6 montre trois commandes
vues en vrai, dont celle-ci : `-v /data:/data --user root --privileged`. Elle a
été écrite par quelqu'un qui savait, un soir où il fallait que ça marche.

**Les contresens sont plus dangereux que les oublis**, parce que la commande a
l'air durcie. `--user root`, `--privileged`, `--network=host`, un montage sans
`:ro` : quatre tests paramétrés les attrapent.

**Le code honnête passe avant tout le reste.** Le premier test du fichier
vérifie qu'une soumission légitime fonctionne aux trois niveaux. Une isolation
qui casse l'usage légitime sera retirée dans la semaine — et le taux de faux
positifs fait partie de la mesure, pas des bonnes intentions.

## Ce que ce projet ne prouve pas

- Le niveau `conteneur` n'est **pas exécuté** ici.
- Le corpus contient 9 évasions **publiques**. Zéro évasion réussie ne veut pas
  dire zéro vulnérabilité.
- Les temps de démarrage des runtimes (chapitre 3) sont des **ordres de
  grandeur** tirés de la littérature, pas des mesures : aucun des trois ne
  tourne sur cette machine.

Un bac à sable dont on surestime la portée est plus dangereux que pas de bac à
sable du tout — parce qu'on lui confie ce qu'on ne lui confierait pas.

## Pour aller plus loin

- Lancez le projet sur Linux : `bornes_disponibles()` devient vrai, et deux lignes du tableau changent.
- Ajoutez une évasion au corpus ; le harnais dira si votre annonce tient.
- Branchez `outils/evasion.py --ci` et `verifier()` sur la CI : un drapeau retiré « le temps de déboguer » y reste, sauf si quelque chose le dit.
- Écrivez le niveau `conteneur` pour de vrai, et comparez le tableau.

---

Cours associé : [Sandboxing sécurisé](https://syllatech.pages.dev/cours/sandbox-securise)
· Formation syllatech — Diaguily SYLLA
