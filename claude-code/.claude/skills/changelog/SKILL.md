---
name: changelog
description: Met à jour CHANGELOG.md après une modification du job portal. À utiliser après un correctif, un ajout de fonctionnalité, ou avant de préparer une release.
allowed-tools: Read Write Bash(git log *)
---

# Mise à jour du CHANGELOG

## Ce qui a changé
!`git log --oneline -5 --no-merges`

## Ce que tu dois faire

1. Résume le changement en une ligne, à l'impératif : « Corrige… », « Ajoute… ».
2. Ajoute-la sous la section `[Unreleased]` de `CHANGELOG.md`.
3. Choisis la bonne rubrique : **Ajouté**, **Corrigé** ou **Modifié**.
4. Vérifie le résultat :

   ```
   python ${CLAUDE_SKILL_DIR}/scripts/verifier_changelog.py
   ```

## Règles

- Une ligne par changement visible par un utilisateur. Un refactor invisible
  n'a rien à faire dans un CHANGELOG.
- Pas de numéro de commit : personne ne le lit.
