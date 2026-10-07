# Terraform — projet de départ du cours **Terraform**

Un **mini-Terraform écrit en Python** : analyseur HCL, moteur de plan,
fichier d'état, provider local. Les six chapitres n'expliquent pas ce que
Terraform ferait — ils impriment ce que **ce moteur-là** fait sur de vrais
fichiers `.tf`.

La mesure centrale du projet tient en deux plans. Même infrastructure,
même élément retiré **au milieu** de la liste :

```
for_each (par clé)      Plan: 0 to add, 0 to change, 1 to destroy.
count    (par position) Plan: 2 to add, 0 to change, 3 to destroy.
```

Une destruction contre trois. L'écart n'est pas une opinion sur le style :
c'est l'adresse qui change. `conteneur.app["prod"]` reste lui-même quoi
qu'il arrive à ses voisins ; `conteneur.app[2]` devient le contenu de
l'ancien rang 3.

Et, dans le fichier d'état écrit par l'`apply` :

```json
"attributes": {
  "nom": "jobportal-dev",
  "image": "jobportal:1.4.0",
  "mot_de_passe": "e0fe371ab316797e"
}
```

Ce mot de passe n'apparaît nulle part dans le code : le provider l'a
engendré, et l'état le stocke **en clair**. C'est la raison — mesurée, pas
récitée — pour laquelle un `terraform.tfstate` ne va jamais dans Git.

---

## Ce que ce projet est, et n'est pas

⚠️ **Le binaire `terraform` n'est pas installé, et n'est pas requis.** Un
cours ne peut pas exiger un compte AWS ni une clé d'API. Ce projet
**réimplémente le moteur** et le fait tourner sur des configurations HCL
réelles.

Ce qui est réel :

| | Réalité |
|---|---|
| le **HCL** | `jobportal/hcl.py` — lexeur + analyseur descendant. Blocs, étiquettes, blocs imbriqués, commentaires `#` et `//`, interpolations `${…}`, indexation `[…]`, appels de fonctions, expressions `for` en liste et en objet. Les fichiers `infra/*.tf` sont du HCL que Terraform accepterait tel quel. |
| l'**algorithme du plan** | `jobportal/plan.py` — `CREER` / `MODIFIER` / `REMPLACER` / `DETRUIRE`, calculé par comparaison entre les instances voulues et l'état, en excluant les attributs calculés. |
| le **fichier d'état** | `jobportal/etat.py` — format 4, `serial`, `lineage`, `resources[].instances[].index_key` : le vrai schéma d'un `terraform.tfstate`, écrit et relu. |
| le **verrou** | un fichier `.lock` à côté de l'état, pris par l'`apply`, qui fait échouer le second. |
| le **provider** | `jobportal/fournisseur.py` — un `realite.json` qui joue le monde extérieur. Ses schémas déclarent les attributs **calculés** (`id`, `mot_de_passe`) et ceux qui **forcent un remplacement** (`nom`). |

Ce que le moteur **refuse**, et qui est énuméré en tête de
`jobportal/hcl.py` : les `dynamic` blocks, les `provisioner`, les
conditionnelles ternaires, les heredocs, les `splat` (`a.*.b`) et
l'arithmétique. Une syntaxe non gérée lève `ErreurHcl` en nommant la ligne,
et une référence inconnue lève `ErreurEvaluation` — jamais une chaîne vide
qui produirait un conteneur nommé `jobportal-`.

## Démarrer

```bash
uv sync --extra dev
uv run --extra dev pytest -q        # 49 tests

uv run python chapitres/chapitre_1_declaratif.py      # le plan, et ce qui force un remplacement
uv run python chapitres/chapitre_2_hcl.py             # for_each contre count : 1 contre 3
uv run python chapitres/chapitre_3_etat.py            # le state, ses secrets, son verrou
uv run python chapitres/chapitre_4_modules.py         # un dossier, appelé deux fois
uv run python chapitres/chapitre_5_environnements.py  # un code, deux états, une isolation
uv run python chapitres/chapitre_6_production.py      # plan enregistré, dérive, prevent_destroy
```

Le moteur s'utilise aussi seul, sur **vos** fichiers `.tf` :

```python
from jobportal.terraform import Terraform

tf = Terraform("mon-infra", etat="mon.tfstate", realite="realite.json")
print(tf.plan().resume)
tf.apply()
print(tf.state_list())
```

`infra/`, `infra-modules/` et `infra-protegee/` sont les configurations sur
lesquelles les chapitres mesurent. Les chapitres écrivent leur état dans un
dossier temporaire : **relancer deux fois donne le même résultat**, et rien
ne traîne dans le dépôt.

## Ce que les six chapitres mesurent

| | Mesure |
|---|---|
| 1 | Un `for_each` déclaré **une** fois → **trois** instances déduites. Le second `plan` est vide (idempotence). Changer `version_image` donne 3 `~` ; changer `prefixe` donne 3 `-/+` — **le même fichier, un caractère de différence**. Et `variables.tf` est lu **après** `main.tf` qui s'en sert : l'ordre des lignes ne compte pas. |
| 2 | Le type refuse `memoire = "beaucoup"` ; la `validation` refuse `taille = "enorme"` avec **votre** message. Puis la mesure qui tranche : retirer `recette` au milieu → **1 destruction** avec `for_each`, **3 destructions et 2 créations** avec `count`. |
| 3 | `mot_de_passe` en clair dans l'état. Perdre l'état ne détruit rien et propose **3 créations** — les objets existent toujours, Terraform ne sait plus qu'ils sont à lui. `import` ajoute une entrée sans toucher au réel ; `state mv` renomme l'entrée, `state rm` l'oublie : **4 objets réels avant, 4 après**. Le verrou fait échouer le second `apply`. |
| 4 | Deux appels du même dossier → **4 ressources**, préfixées `module.<appel>.`. L'appelant reçoit `nom_du_reseau` sans jamais savoir que le module crée **aussi** une passerelle. Et l'état reste **unique** : un module n'est pas une frontière de déploiement. |
| 5 | Le même `infra/` appliqué deux fois avec deux jeux de variables et deux fichiers d'état. `destroy` sur dev → **dev 0 objets, prod 3 objets**. Puis le tableau workspaces / dossiers, ligne par ligne, avec ce que les workspaces **ne** séparent pas : le backend, donc les droits. |
| 6 | Un plan enregistré applique `jobportal-*` alors que le code, modifié entre-temps, créerait `autre-*`. Une dérive fabriquée à la main reste **invisible** au plan (il compare le code à l'**état**), puis apparaît attribut par attribut après rafraîchissement. `prevent_destroy` laisse le plan afficher le `-/+` et fait échouer l'`apply`. |

## Ce que le projet ne prouve pas

- **aucune ressource n'est créée nulle part** : le « monde extérieur » est
  `realite.json`. Ce qui est mesuré, c'est l'**algorithme**, pas un appel
  d'API ;
- **il n'y a pas de `terraform init`** : aucun provider n'est téléchargé,
  donc pas de `.terraform.lock.hcl`. Le verrouillage de versions est ce qui
  rend un `apply` reproductible six mois plus tard — le chapitre 6 le dit,
  il ne le démontre pas ;
- **il n'y a pas de graphe de dépendances explicite** : les références sont
  résolues, les ressources ne sont pas ordonnées par un tri topologique.
  Une dépendance `depends_on` n'est pas gérée ;
- **le typage est plus strict que celui de Terraform**, qui convertit quand
  il peut (`"512"` → `512`). Le choix est assumé et documenté dans
  `jobportal/configuration.py` ;
- **le rafraîchissement est écrit à la main dans le chapitre 6** (une
  boucle sur les instances) : il n'y a pas de commande `refresh`.

**Ne pas « corriger » `infra-protegee/main.tf`** : son `prevent_destroy` est
la pièce à conviction du chapitre 6, et `tests/test_etat.py` mesure dessus.
