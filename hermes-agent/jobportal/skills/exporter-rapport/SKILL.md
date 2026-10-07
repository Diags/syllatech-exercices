---
name: exporter-rapport
description: Produit le rapport mensuel de recrutement au format CSV
version: 0.9.0
platforms: [linux, darwin]
requires_toolsets: [code_execution]
---

# Exporter le rapport mensuel

⚠️ Cette skill declare `platforms: [linux, darwin]`. Sur Windows, Hermes ne
la proposera pas — sans rien dire. Le chapitre 3 le mesure.

## Les etapes

1. Agreger les candidatures du mois par offre et par statut.
2. Ecrire `rapports/<annee>-<mois>.csv`.
