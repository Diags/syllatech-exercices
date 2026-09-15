# Job Portal

## Commandes

- `npm run dev` : serveur local
- `npm run check` : la vérification complète
- `npm test -- --run` : tests unitaires

## Conventions

- Composants dans `src/components/`
- Les migrations vivent dans `db/migrations/`

## Outillage

- Sous-agent `reviseur` : relit le diff avant chaque commit
- Sous-agent `explorateur` : cartographie un module
- Skill `changelog` : met à jour le CHANGELOG
- Serveur MCP `db` : le schéma du portail
- Serveur MCP `github` : les PR et les issues
