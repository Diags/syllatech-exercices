# Workflows n8n — projet de départ du cours **n8n : l'automatisation low-code**

Le graphe et les expressions sont ceux de n8n : ce projet utilise
**`n8n-workflow`**, la bibliothèque que n8n utilise pour lui-même.

```
   ={{ $json.poste }}     →  "devops"
   {{ $json.poste }}      →  "{{ $json.poste }}"
```

Le signe `=` en tête est ce qui fait une expression. L'éditeur le pose tout
seul quand on bascule un champ en mode « Expression » ; un workflow écrit à
la main, généré, ou recopié depuis une page web ne l'a pas. Le candidat reçoit
alors un courriel qui commence par « Bonjour {{ $json.nom }} » — sans erreur,
sans avertissement, et avec un historique entièrement vert.

---

## Ce qui est réel, et ce qui ne l'est pas

**Réel** — `n8n-workflow` 2.16 : la classe `Workflow` (graphe, parents,
enfants, déclencheurs) et la classe `Expression` (le moteur qui évalue chaque
champ de chaque nœud). Les fichiers de `flux/` sont au format d'export de
l'éditeur : on peut les y importer tels quels.

**Substitué** — le COMPORTEMENT des nœuds. Un « Postgres » d'ici n'écrit rien,
un « Send Email » n'envoie rien : cela vit dans `n8n-nodes-base`, qui pèse des
centaines de Mo. Le registre de `jobportal/typesDeNoeuds.js` déclare juste
assez pour que le vrai `Workflow` se construise.

⚠️ **L'entrée ESM de `n8n-workflow` 2.16.0 est cassée** —
`ERR_MODULE_NOT_FOUND … dist/esm/logger-proxy`, un import sans extension dans
le build publié. C'est pourquoi ce projet est en CommonJS : `require`
fonctionne. Ce n'est pas un choix de style.

## Démarrer

```bash
npm install
npm test                                    # 23 tests

node chapitres/chapitre_1_demarrer.js       # le JSON, le graphe, le tapis
node chapitres/chapitre_2_expressions.js    # le vrai moteur d'expressions
node chapitres/chapitre_3_declencheurs.js   # 50 items, 250 expressions
node chapitres/chapitre_4_logique.js        # une branche inversée
node chapitres/chapitre_5_ia.js             # ce qu'un nœud IA coûte
node chapitres/chapitre_6_production.js     # auto-hébergement, et la clé
```

Le vérificateur s'utilise sur **vos** workflows, avant de les importer :

```bash
node outils/verifier-flux.js flux/a-corriger.json   # 4 erreurs, 2 avertissements
node outils/verifier-flux.js flux/candidature.json  # 0 / 0
node outils/verifier-flux.js ~/telecharge.json
```

## La carte du projet

| Fichier | Ce qu'il contient | Chapitre |
| --- | --- | --- |
| `flux/candidature.json` | un workflow correct, importable dans n8n | tous |
| `flux/a-corriger.json` | le même, avec cinq défauts silencieux | 2, 4, 6 |
| `jobportal/flux.js` | le vrai `Workflow`, et la lecture du graphe | 1, 4 |
| `jobportal/expressions.js` | le vrai `Expression`, et ce qu'il rend | 2 |
| `jobportal/execution.js` | le tapis roulant d'items, compté | 3, 4, 5 |
| `jobportal/typesDeNoeuds.js` | le registre minimal de types | 1, 3 |
| `outils/verifier-flux.js` | sept contrôles avant import | 4, 6 |
| `tests/flux.test.js` | 23 tests (`node --test`) | tous |

## Six choses que le code enseigne

**Le signe `=` fait l'expression.** Voir l'encadré du haut. Le vérificateur
l'attrape ; une relecture humaine, non — dans l'éditeur, un champ littéral et
un champ en mode Expression se ressemblent.

**Un chemin absent rend `undefined`, sans lever.** `{{ $json.post }}` (au lieu
de `poste`) → `undefined`. Et `{{ $json.a.b.c }}`, qui déréférencerait
`undefined` en JavaScript ordinaire, rend `undefined` aussi : n8n avale la
`TypeError`. Un champ vide descend alors dans tout le reste du workflow.

**50 items, 250 expressions.** Chaque expression est réévaluée une fois par
item — rapport mesuré : exactement ×50. Le nombre d'*exécutions de nœud*, lui,
n'est pas proportionnel : il dépend de la répartition du IF, donc **des
données**. Deux lots de 50 candidatures ne coûtent pas la même chose.

**Le JSON ne dit pas « vrai » et « faux » : il dit 0 et 1.** Inverser deux
lignes du tableau `connections` inverse la logique, et le JSON reste
parfaitement valide. Dans `a-corriger.json`, les 20 candidats qui ont **trois
ans d'expérience ou plus** reçoivent le courriel de refus.

**Un nœud IA est un nœud, et il tourne une fois par item.** Le déplacer après
le filtre au lieu d'avant fait passer 50 appels à 20 — sans changer de modèle
ni raccourcir un prompt.

**Un export ne contient aucun secret.** `"credentials": {"id": "2", "name":
"SMTP sortant"}` — une référence, pas un mot de passe. Bonne nouvelle pour
git, piège à l'import : sur une autre installation, l'identifiant « 2 » ne
désigne rien, et le workflow échoue au premier passage.

## Le défaut que le vérificateur ne voit pas

La branche inversée. Les deux branchements sont **syntaxiquement identiques** :
seule l'intention du concepteur les sépare. Aucune vérification statique ne
peut la trouver.

Elle se révèle en faisant circuler des items connus — trois lignes de test :

```js
assert.equal(a.get('Enregistrer').itemsEntres, 20);   // workflow correct
assert.equal(b.get('Enregistrer').itemsEntres, 30);   // workflow inversé
```

C'est la seule bonne pratique qui compte vraiment ici : un workflow de
production mérite un jeu de données de référence et une assertion sur ce qui
en sort.

## Le piège trouvé en écrivant le projet

`new Workflow({ nodes })` **mute les nœuds qu'on lui passe** : n8n normalise
chaque `parameters` contre les `properties` déclarées par le type de nœud, et
jette tout ce qui n'y figure pas. Avec un registre minimal, il ne reste rien.

Ce n'est pas un défaut du registre, c'est le comportement de n8n — et il
explique un vrai incident : un workflow exporté depuis une version où un champ
existait, réimporté dans une version où il a été renommé, **perd ce champ sans
erreur**. L'éditeur affiche un nœud aux paramètres vides.

`jobportal/flux.js` travaille donc sur une copie, et un test le vérifie.

## Ce que ce projet ne prouve pas

- **n8n lui-même ne tourne pas.** Pas d'éditeur, pas de serveur, pas de
  Docker : seulement la bibliothèque.
- Les nœuds n'exécutent rien. Le registre de types est minimal.
- L'ordre d'exécution réel (`executionOrder: v1`, position des nœuds à
  l'écran) n'est pas reproduit : le projet parle d'ordre de **lecture**, et le
  dit à chaque fois.
- Les coûts du chapitre 5 sont des ordres de grandeur annoncés comme tels ;
  ce qui est mesuré est le **nombre d'appels**, qui vient du graphe.
- `$('Autre nœud')` n'est pas résolu : cela demande le proxy de données
  complet de n8n, qui n'existe qu'au cours d'une vraie exécution. Ces
  expressions sont comptées à part, jamais comme « vides ».

## Pour aller plus loin

- Importez `flux/candidature.json` dans un vrai n8n (`docker run …`) et
  comparez.
- Retirez le `=` d'un champ de `candidature.json` : le vérificateur passe de
  0 à 1 erreur, et le chapitre 2 le montre.
- Ajoutez un nœud et oubliez de le brancher : `orphelins()` le trouve.
- Mettez `outils/verifier-flux.js` dans votre CI, sur le dossier de workflows
  versionnés — c'est le seul contrôle qui tienne entre deux relectures.

---

Cours associé : [n8n : l'automatisation low-code](https://syllatech.pages.dev/cours/n8n)
· Formation syllatech — Diaguily SYLLA
