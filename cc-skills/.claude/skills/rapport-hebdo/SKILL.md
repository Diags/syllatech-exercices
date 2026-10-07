---
name: rapport-hebdo
description: Génère le rapport hebdomadaire du projet — commits, PR fusionnées, blocages. À utiliser quand on demande « le rapport de la semaine » ou un point d'avancement.
argument-hint: [semaine]
allowed-tools: Bash(git log *) Bash(git shortlog *) Read Write
---

# Rapport hebdomadaire du job portal

Le contexte est injecté ci-dessous **avant** que tu lises ces instructions :
la commande s'exécute sur la machine au moment où la skill est rendue, et sa
sortie remplace le bloc — telle quelle, sans résumé.

> `git shortlog` porte ici un `HEAD` explicite. Sans révision, il lirait
> l'**entrée standard** — qui est fermée au rendu — et rendrait du vide sans
> rien signaler. Vérifiez toujours une commande injectée avec
> `outils/rendre.py` avant de la livrer.

## Commits de la semaine
!`git log --since="1 week ago" --pretty=format:"%h %an %s" --no-merges`

## Contributeurs
!`git shortlog -sn HEAD --since="1 week ago" --no-merges`

## Ce que tu dois produire

Un rapport en trois sections, dans `rapports/semaine-$ARGUMENTS.md` :

1. **Fait** — ce qui est terminé, groupé par thème, pas par commit.
2. **En cours** — ce qui a bougé sans aboutir.
3. **Blocages** — ce qui n'a pas bougé et aurait dû.

## Règles

- Ne liste **jamais** les commits bruts : l'intérêt d'un rapport est le
  regroupement. Un journal git, le lecteur peut le lire lui-même.
- Si une section est vide, écris-le. Une section absente laisse croire à un
  oubli ; une section vide est une information.
- Pas de superlatif. « Sept correctifs » vaut mieux que « une semaine très
  productive ».
