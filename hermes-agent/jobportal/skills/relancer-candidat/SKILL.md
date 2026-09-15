---
name: relancer-candidat
description: Relance un candidat reste sans reponse depuis plus de 7 jours, dans le ton des echanges precedents
version: 1.2.0
platforms: [linux, darwin, win32]
metadata:
  hermes:
    requires_tools: [read_file, write_file]
---

# Relancer un candidat

C'est la procedure que l'agent a ecrite lui-meme apres l'avoir faite a la
main trois fois. C'est cela, une skill : pas un outil, une PROCEDURE.

## Quand l'appliquer

Une candidature au statut `envoyee` dont la date depasse 7 jours.

## Les etapes

1. Lire `donnees/candidatures.json`.
2. Retenir celles au statut `envoyee` et vieilles de plus de 7 jours.
3. Pour chacune, rediger une relance de trois phrases au maximum, dans le
   ton des reponses precedentes du meme recruteur.
4. Passer le statut a `relancee` et noter la date.

## Ce qu'il ne faut pas faire

- Relancer deux fois la meme candidature : verifier le statut d'abord.
- Relancer un refus : `refusee` n'est pas `envoyee`.
