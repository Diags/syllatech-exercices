# Registre d'artefacts — projet de départ du cours **AgentRegistry**

Onze manifestes, aucune faute de YAML, et trois contrôles qui ne trouvent pas
les mêmes fautes :

```
catalogue/a-corriger.yaml     schéma publié        2 erreurs
catalogue/a-corriger.yaml     validateur           7 erreurs
catalogue/a-corriger.yaml     résolution des refs  2 erreurs
                              ────────────────────────────────
                              8 documents refusés sur 11
                              3 que personne n'attrape
```

Les deux premières colonnes tournent **hors ligne**. La troisième a besoin du
catalogue — et c'est le découpage de l'amont lui-même, pas un choix de ce
projet : `Validate()` porte le commentaire *« No network I/O; ref existence
is covered by ResolveRefs »*.

---

## Ce que ce projet est, et n'est pas

⚠️ **Ce n'est pas AgentRegistry.** Le vrai est un service Go devant une base
PostgreSQL, qu'on lève avec Docker Compose, piloté par un CLI qui s'installe
en `curl | bash`. Rien de tout cela ne tourne ici.

Ce qui tourne : **les règles**, appliquées à des manifestes. Trois couches,
et elles ne sont pas fiables au même degré — ce projet le dit plutôt que de
faire semblant :

| Couche | Ce qu'elle lit | Fidélité |
|---|---|---|
| **A** — schéma publié | `amont/openapi.yaml`, copié verbatim | **totale** — OpenAPI 3.1 *est* du JSON Schema 2020-12, rien n'est transcrit |
| **B** — validateur | `pkg/api/v1alpha1/*_validate.go` | **transcrite**, règle par règle, chacune avec sa citation |
| **C** — références | le catalogue | **modélisée** : la résolution, pas la base |

Le garde-fou de la couche B est `tests/test_amont.py` : les **dix manifestes
d'exemple du dépôt**, livrés dans `amont/exemples/`, doivent passer. S'ils
cessent de passer, c'est la transcription qui a tort.

Voir [`amont/PROVENANCE.md`](amont/PROVENANCE.md) : dépôt, commit, licence,
et la commande pour tout remettre à jour.

## Démarrer

```bash
uv sync --extra dev
uv run --extra dev pytest -q        # 199 tests

uv run python chapitres/chapitre_1_demarrer.py      # ce qui manque pour lever le registre
uv run python chapitres/chapitre_2_artefacts.py     # quatre artefacts, ou neuf ?
uv run python chapitres/chapitre_3_publier.py       # trois couches, trois trous
uv run python chapitres/chapitre_4_consommer.py     # ce qu'« épingler » veut dire
uv run python chapitres/chapitre_5_passerelle.py    # le champ qui ne sait pas porter un secret
uv run python chapitres/chapitre_6_gouvernance.py   # la curation, cherchée dans le contrat
```

Les deux outils s'utilisent aussi seuls, sur **vos** manifestes :

```bash
uv run python outils/verifier_manifeste.py MON.yaml --registre catalogue/portail
uv run python outils/fiches.py catalogue/portail
```

`verifier_manifeste.py` sort avec le nombre de documents refusés — il se met
dans une CI tel quel. Sans `--registre`, il affiche **« références NON
VÉRIFIÉES »** au lieu d'un OK : un contrôle qui confond « je n'ai pas trouvé
d'erreur » et « il n'y en a pas » ment à celui qui le lit.

## Le catalogue

Le Portail de l'emploi publie sept artefacts :

```
catalogue/portail/
  mcp-offres.yaml         MCPServer  image OCI, transport stdio
  mcp-scoring.yaml        MCPServer  paquet PyPI, transport http + port
  mcp-annuaire.yaml       MCPServer  remote streamable-http — jamais déployé
  skill-tri.yaml          Skill      un dépôt git, un sous-dossier
  prompt-entretien.yaml   Prompt     des instructions versionnées
  agent-recruteur.yaml    Agent      une image + cinq références épinglées
  modele-defaut.yaml      Model      Model/default@latest, la dépendance implicite
```

Et `catalogue/a-corriger.yaml` en casse onze de onze façons différentes.
**Ne pas le réparer** : les chapitres et les tests mesurent dessus.

## Ce que les six chapitres mesurent

| | Mesure |
|---|---|
| 1 | La procédure d'installation publiée compte **trois** étapes, dont un `docker compose up`. Aucun des dix exemples amont n'écrit son espace de noms ; sept n'écrivent pas leur étiquette. |
| 2 | Le registre enregistre **neuf** types, dont **six** étiquetés. `npx` et `uvx` ne sont pas des origines : ce sont des commandes **dérivées**. Déclarer `launch` soi-même retire l'injection de l'identifiant. |
| 3 | Les deux contrats se contredisent : une référence sans `kind` est **refusée** par le schéma publié et **acceptée** par le validateur ; un manifeste sans `namespace`, l'inverse. Trois manifestes passent les trois couches et ne désignent rien. |
| 4 | Il n'existe **ni commande `arctl search`, ni route de recherche**. Le seul filtre de contenu est `?labels=`. Republier sous la même étiquette est accepté, silencieux, et ne casse aucune référence. |
| 5 | Trois champs du schéma renvoient vers un `Secret` ; celui d'un en-tête de serveur distant est une **chaîne**. L'URL de l'icône doit être en `https` ; celle du serveur MCP, non. |
| 6 | Aucun champ d'approbation, aucune route d'approbation dans le contrat publié. La version publiée d'une fiche vient d'une **cascade à trois étages**, dont le dernier est `0.0.0`. Zéro artefact du portail est épinglé sur un contenu adressable. |

## Ce que le projet ne prouve pas

- le registre ne tourne pas : ni service, ni base, ni interface web, ni `arctl` ;
- la couche B est une transcription — son garde-fou est `tests/test_amont.py` ;
- la couche C modélise la résolution, pas la base : ni transactions, ni
  suppression différée, ni concurrence ;
- rien n'est déployé, donc rien de ce qui suit l'`apply` n'est mesuré — ni le
  résolveur de déploiement, ni la passerelle, ni le cluster.

Ce qui **est** réel : `amont/openapi.yaml` est le document que le registre
publie, copié sans retouche, et la couche A valide contre lui sans une ligne
de transcription.
