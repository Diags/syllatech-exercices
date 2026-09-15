---
name: migration
description: Crée une migration de schéma de base pour le job portal, avec son rollback, et l'applique en local. À utiliser quand on demande d'ajouter, modifier ou supprimer une table ou une colonne.
argument-hint: [description de la migration]
allowed-tools: Read Write Bash(python *)
---

# Migration de schéma — $ARGUMENTS

## État actuel
!`cat db/schema.sql 2>/dev/null || echo "(pas de db/schema.sql — première migration)"`

## Migrations déjà appliquées
!`ls -1 db/migrations/ 2>/dev/null || echo "(aucune)"`

## Ce que tu dois faire

1. Lis le schéma ci-dessus.
2. Écris `db/migrations/<horodatage>_<nom>.sql`, contenant **deux sections** :

   ```sql
   -- up
   ALTER TABLE ...

   -- down
   ALTER TABLE ...
   ```

3. Vérifie ta migration avant de l'appliquer :

   ```
   python ${CLAUDE_SKILL_DIR}/scripts/verifier_migration.py db/migrations/<fichier>.sql
   ```

4. Applique-la, puis lance les tests.

## Règles absolues

- **TOUJOURS un `down`.** Une migration sans rollback est une décision
  irréversible prise un mardi après-midi.
- **NE TOUCHE JAMAIS à une migration déjà appliquée.** Elle l'est peut-être
  aussi en production. On corrige avec une NOUVELLE migration.
- Une migration, un changement. Deux changements dans un fichier, et le
  rollback devient un pari.
