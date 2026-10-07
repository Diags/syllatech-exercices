# Job Portal

## Commandes

- `npm run dev` : serveur local (port 5173)
- `npm test -- --run` : tests unitaires
- `npm run lint` : ESLint, zéro avertissement toléré

## Conventions

- Composants dans `src/components/`, un dossier par composant
- Jamais de `any` : typage strict
- Les migrations vivent dans `db/migrations/`, jamais modifiées après application

## Outillage

- Sous-agent `reviseur` : relit le diff avant chaque commit
- Skill `changelog` : met à jour `CHANGELOG.md` après une modification
- Serveur MCP `db` : le schéma et les données du portail
