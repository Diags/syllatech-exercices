# Job portal — projet de départ du cours **Sécuriser les Agents IA**

Six défenses, six attaques de l'OWASP Top 10, et un harnais qui **les rejoue
contre vos propres défenses** en une seconde.

```
  2. CHAQUE COUCHE, PRISE SEULE

     couche                  passent  arretees
     delimitation                  1         4
     validation_sortie             5         0
     liste_blanche                 3         2
     validation_humaine            3         2
     garde_entree                  4         1
     anonymisation                 5         0
```

**Aucune couche seule n'arrête tout.** C'est ce que « défense en profondeur »
veut dire — et ici c'est mesuré, pas affirmé.

---

## ⚠️ Une note sur le langage

Le cours est en Java/Spring AI. Ce projet est en Python, et c'est délibéré :
les six défenses sont des **propriétés d'architecture**, pas de framework.
`@Tool` + `SecurityContextHolder` ou une liste blanche Python : la question est
la même — *qu'est-ce que l'agent peut provoquer, et qui l'a autorisé ?*

Ce qui change, en revanche, c'est qu'ici **ça s'exécute**. Le code Java des
vidéos ne peut pas être attaqué dans une vidéo.

## Le résultat, et il est plus honnête qu'un zéro triomphant

| Configuration | Injections suivies | Conséquences réelles |
| --- | --- | --- |
| aucune défense | 6/6 | **5/6** |
| toutes les couches | **1/6** | **0/6** |

La défense en profondeur ne fait pas tomber la première colonne à zéro —
aucune consigne de prompt n'y arrive, c'est une propriété du modèle et non de
votre code. Elle fait tomber la **seconde**, et c'est le seul objectif
réellement atteignable : *l'injection réussit, et elle ne peut rien.*

Un rapport qui annoncerait « zéro injection » serait faux, et c'est le genre de
faux qui coûte cher.

## Démarrer

```bash
uv sync --extra dev
uv run --extra dev pytest -q            # 40 tests

uv run python outils/redteam.py                     # le tableau complet
uv run python outils/redteam.py --couche liste_blanche   # une couche seule
uv run python outils/redteam.py --ci                # code de sortie 1 si ça passe

uv run python chapitres/chapitre_1_menaces.py       # l'anti-patron, exécuté
uv run python chapitres/chapitre_2_injection.py     # délimiter, puis valider
uv run python chapitres/chapitre_3_outils.py        # les trois mécanismes
uv run python chapitres/chapitre_4_mcp.py           # la description empoisonnée
uv run python chapitres/chapitre_5_guardrails.py    # la liste noire ne tient pas
uv run python chapitres/chapitre_6_redteam.py       # mesurer, surveiller, borner
```

## Ce qui est réel, et ce qui est substitué

**Réel :** les six défenses, les six attaques, et toutes les mesures.

**Substitué :** le modèle. `jobportal/modele.py` reproduit **le seul défaut qui
compte** — un modèle de langage ne distingue pas, par nature, une instruction
d'une donnée. Tout arrive dans la même fenêtre, sous la même forme : du texte.

Un paramètre mérite d'être lu avant tout le reste : `TAUX_DE_FUITE = 0.35`,
la part des attaques auxquelles un modèle **correctement cadré** obéit quand
même. C'est une hypothèse de travail, pas une mesure — mais la mettre à zéro
rendrait la délimitation suffisante à elle seule, ce qui serait le contraire de
la vérité. Mesurez-la sur *votre* modèle : c'est exactement ce que fait
`redteam.py`.

## La carte du projet

| Fichier | Ce qu'il contient | Chapitre |
| --- | --- | --- |
| `jobportal/modele.py` | Un modèle crédule, et la seule hypothèse du projet | 1, 2 |
| `jobportal/attaques.py` | 6 attaques OWASP, avec la défense qui les neutralise | tous |
| `jobportal/defenses.py` | Les six couches, activables une à une | 2-5 |
| `outils/redteam.py` | Le harnais : combien passent, avec quoi | 6 |
| `tests/test_defenses.py` | 40 tests, dont la moitié vérifie des **échecs** | tous |

## Cinq choses que le code enseigne

**Le filtre d'outils MCP par nom ne protège PAS d'une description empoisonnée.**
La vidéo du chapitre 4 présente la liste blanche comme la parade — le texte
du cours a depuis été complété sur ce point. Elle arrête
un outil *ajouté* en 1.5.0 — mais `chercher_offres` est dans la liste : si sa
**description** devient hostile, elle entre au contexte avec lui. Un test du
projet le démontre. D'où l'épinglage de version et le diff des descriptions :
le filtre et la revue ne se remplacent pas.

**Une liste noire est un détecteur, pas une serrure.** Quatre contournements en
une ligne chacun — un caractère invisible, un tiret typographique, la même
demande sans le mot, la même demande en anglais. Quatre tests le vérifient. Ses
deux mérites réels ne sont pas la sécurité : la requête bloquée ne part pas
(pas de fuite, pas de tokens), et elle produit un signal.

**Le critère d'une validation humaine n'est pas « dangereux », c'est
« irréversible ».** Un envoi d'e-mail ne se rattrape pas ; une lecture, si.
C'est la seule couche qui protège contre une attaque **qu'on n'a pas imaginée**,
parce qu'elle ne repose sur aucune reconnaissance. L'agent ne *possède* aucun
outil d'envoi direct : il ne peut que proposer.

**Un refus est un signal d'attaque, et il doit être compté.** Sans journal, une
attaque bloquée est indiscernable d'une journée calme. Bloquer sans compter,
c'est ignorer qu'on est attaqué.

**La bonne question n'est pas « la défense bloque-t-elle ? » mais « que perd-on
si elle échoue ? ».** Une exfiltration réussie de données anonymisées ne fait
pas de victime. C'est pourquoi la minimisation est la défense la plus solide du
lot : ce que le modèle n'a jamais vu ne peut pas fuir.

## Ce que ce projet ne prouve pas

- Il rejoue **6 attaques connues**. Un corpus ne prouve que ce qu'il contient :
  zéro conséquence ne veut pas dire zéro vulnérabilité, et ne le voudra jamais.
- Le modèle est simulé. Un vrai modèle résiste mieux à certaines attaques et
  moins bien à d'autres.
- `promptfoo redteam run` (chapitre 6) génère des variantes et attaque
  l'application HTTP réelle. C'est **complémentaire, pas redondant** : ce
  harnais sert à écrire les défenses, promptfoo à les éprouver.

## Pour aller plus loin

- Ajoutez une attaque au corpus et regardez combien de couches la laissent passer.
- Retirez deux couches à la fois : le compte remonte, là où en retirer une seule ne changeait rien.
- Branchez `redteam.py --ci` sur la CI : une règle ajoutée au prompt fait baisser la couverture sans qu'aucun test fonctionnel ne bouge.
- Remplacez le modèle simulé par un vrai et mesurez `TAUX_DE_FUITE` pour de bon — c'est le seul chiffre qui vous concerne.

---

Cours associé : [Sécuriser les Agents IA](https://syllatech.pages.dev/cours/securite-agents)
· Formation syllatech — Diaguily SYLLA
