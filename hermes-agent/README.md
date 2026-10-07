# Hermes Agent — projet de départ du cours **Hermes Agent**

Hermes est **auto-hébergé et open source**, et c'est ce qui rend ce projet
possible : le paquet s'installe depuis PyPI, son code s'importe, et tout ce
que les six chapitres affirment se vérifie en appelant **Hermes lui-même**.

```
   entrees ecrites (memory)       3
   bloc injecte au prompt         0 signes
```

Trois écritures réussies, un prompt système inchangé. Ce n'est pas un bug :
`format_for_system_prompt` rend l'instantané **figé au chargement**, et sa
docstring le dit — *« Mid-session writes do not affect this. This keeps the
system prompt stable across all turns, preserving the prefix cache. »*

Ce que l'agent apprend aujourd'hui, il l'utilisera demain. Tester « il ne se
souvient pas de ce que je viens de lui dire » dans la même session ne teste
rien.

---

## Ce qui est réel, et ce qui ne l'est pas

**Réel** — `hermes-agent` 0.19 en entier. Les chapitres appellent :

| module de Hermes | ce qu'il fournit |
| --- | --- |
| `tools.memory_tool` | `MemoryStore`, ses deux plafonds, son filtre d'injection |
| `agent.skill_utils` | l'analyseur de `SKILL.md` que Hermes exécute |
| `toolsets` / `model_tools` | 57 ensembles, 79 outils, leurs schémas |
| `tools.approval` | 70 motifs « dangereux », 12 « hardline » |
| `tools.skills_guard` | 121 motifs de menace, 17 caractères invisibles |
| `cron.jobs` / `cron.scheduler` | la création de tâches, et leur résolution |

**Substitué** — le MODÈLE. Aucun appel de modèle n'est fait, donc l'agent ne
tourne pas : la boucle d'auto-amélioration n'est pas exécutée. Les cinq
`SKILL.md` sont écrites à la main, dans la forme que l'agent aurait produite.

⚠️ **Aucun état n'est laissé sur votre machine.** Importer Hermes suffit à
créer son dossier de travail — `SOUL.md`, `state.db`, `sessions/`,
`memories/`. `jobportal/commun.py` bascule donc `HERMES_HOME` vers un dossier
temporaire **avant le premier import**, et `tests/conftest.py` fait de même.

## Démarrer

```bash
uv sync --extra dev
uv run --extra dev pytest -q        # 36 tests

uv run python chapitres/chapitre_1_decouvrir.py         # ce qui est installé
uv run python chapitres/chapitre_2_memoire.py           # deux plafonds, un instantané figé
uv run python chapitres/chapitre_3_skills.py            # le vrai analyseur de frontmatter
uv run python chapitres/chapitre_4_outils.py            # 57 ensembles, et ce qu'ils coûtent
uv run python chapitres/chapitre_5_automatisations.py   # cron, et l'agent sans surveillance
uv run python chapitres/chapitre_6_securite.py          # les deux gardes, mesurées
```

Le vérificateur s'utilise sur **vos** skills, avant de les installer :

```bash
uv run python outils/verifier_skill.py jobportal/skills/piegee
uv run python outils/verifier_skill.py ~/.hermes/skills/une-skill-trouvee
```

## La carte du projet

| Fichier | Ce qu'il contient | Chapitre |
| --- | --- | --- |
| `jobportal/memoire.py` | autour du vrai `MemoryStore` | 2 |
| `jobportal/competences.py` | autour du vrai analyseur de skills | 3 |
| `jobportal/outillage.py` | autour de `toolsets` et `model_tools` | 4 |
| `jobportal/gardes.py` | autour de `approval` et `skills_guard` | 6 |
| `jobportal/skills/*/SKILL.md` | cinq skills, dont une piégée et une fautive | 3, 6 |
| `outils/verifier_skill.py` | forme **et** menaces, avant installation | 6 |
| `tests/test_hermes.py` | 36 tests — sur le comportement de Hermes | tous |

## Sept choses que le code enseigne

**L'écriture en session n'arrive pas au prompt.** Voir l'encadré du haut. Un
arbitrage explicite : la stabilité du cache de préfixe contre la fraîcheur du
souvenir.

**Le refus de dépassement est une consigne, pas une erreur.** À 2 200 signes,
`add` refuse — et joint la marche à suivre (`replace`, `remove`), le moment
(« maintenant, dans ce tour ») et la liste des 29 entrées actuelles. Le
message est écrit pour son lecteur, qui est un modèle.

**Le fichier de mémoire est une surface d'attaque.** Une entrée qui déclenche
le détecteur est remplacée par `[BLOCKED: …]` dans l'instantané, et **le texte
d'origine reste dans la liste vivante** : le faire disparaître cacherait
l'attaque à la personne qu'elle vise.

**Un `MEMORY.md` édité à la main n'a qu'une entrée.** Le séparateur est
`\n§\n`. Trois lignes à tirets ne font qu'un bloc, et une seule ligne fautive
emporte alors les deux souvenirs légitimes.

**Les conditions d'une skill ne se déclarent pas où l'on croit.** Hermes les
lit sous `metadata.hermes.*`. Écrites à la racine du frontmatter, elles sont
**ignorées sans un mot** — et la skill est proposée même sans ses outils.

**Ce qu'on active n'est pas ce qu'on reçoit.** 57 ensembles déclarés, 29 avec
une condition, 11 remplies ici. Et un second filtre en dessous : chaque outil
peut poser la sienne. `coding` annonce 32 outils et en offre 15.

**Les deux gardes échouent différemment, et c'est leur seul intérêt.** Le
scanner de fichier ne voit pas `rm -rf ~/.hermes/logs` ; la garde de commande,
si. `history -c` passe les deux.

## La démonstration accidentelle

Le scanner de skills a trouvé trois menaces dans `jobportal/skills/piegee/` :
un `curl | bash`, une exfiltration de `~/.hermes/config.yaml`, et —

```
[high] injection  invisible unicode character zero-width space
                  ligne 27 : U+200B (zero-width space)
```

Cette espace de largeur nulle **n'a pas été mise là exprès**. Elle a été tapée
en écrivant la phrase, et personne ne l'a vue : ni à l'écran, ni en relecture,
ni dans un diff. C'est exactement le vecteur que le motif traque, et le fait
que la démonstration soit involontaire est le meilleur argument du chapitre 6.

## Ce que ce projet ne prouve pas

- **L'agent ne tourne pas.** Pas de modèle, pas de clé, pas de boucle. Ce qui
  est mesuré est le *code* de Hermes, pas son comportement avec un modèle.
- La **boucle d'auto-amélioration** — l'agent qui écrit ses propres skills —
  n'est donc pas exécutée.
- Aucun outil n'est appelé, aucune commande exécutée, aucune skill installée :
  les gardes sont interrogées, pas franchies.
- Les backends d'exécution (conteneur, VPS), les canaux (Discord, Slack) et
  MCP demandent des services joignables et ne sont pas branchés.
- Les 121 motifs de menace n'ont pas été audités un par un : le chapitre 6
  montre ce qu'ils attrapent sur un cas, et deux choses qu'ils laissent passer.

## Pour aller plus loin

- Passez vos propres commandes à `jobportal.gardes.juger` avant de les
  automatiser en cron — c'est là que « demande » devient « exécute ».
- Écrivez un `SKILL.md`, lancez `outils/verifier_skill.py` dessus, et
  regardez ce que Hermes en lit vraiment.
- Déplacez `requires_toolsets` sous `metadata.hermes` dans
  `exporter-rapport` : le défaut disparaît, et la condition s'applique.
- Sur une machine Linux ou macOS, relancez le chapitre 3 : `exporter-rapport`
  y est proposée, et le tableau change.

---

Cours associé : [Hermes Agent](https://syllatech.pages.dev/cours/hermes-agent)
· Formation syllatech — Diaguily SYLLA
