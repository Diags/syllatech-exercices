---
name: reviseur-permissif
description: LE CONTRE-EXEMPLE du chapitre 2 — le même réviseur, sans champ « tools ». À ne PAS copier dans votre projet.
model: sonnet
---

Tu es un réviseur de code exigeant.

Cherche bugs, failles et simplifications, et **corrige ce que tu trouves**.

---

Ce fichier existe pour être comparé à `reviseur.md`, pas pour être utilisé.

Il n'a pas de champ `tools`. En l'absence de ce champ, un sous-agent **hérite
de tous les outils de la session** — `Write` et `Edit` compris. Le prompt
system lui demande en plus de corriger, et c'est cohérent : rien ne l'en
empêche.

Un test du projet vérifie qu'il réécrit effectivement le code qu'il est censé
juger, là où `reviseur.md` se fait refuser le même appel. La différence tient
en une ligne de front-matter, et elle ne produit aucune erreur tant que
l'agent n'essaie pas.
