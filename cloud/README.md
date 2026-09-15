# Architecture Cloud — projet de départ du cours **Architecture Cloud**

« Architecture Cloud » est un cours où presque tout se raconte et où
presque rien ne se vérifie. Ce projet prend les six affirmations centrales
du cours et les **calcule** : un moteur d'évaluation IAM, une composition de
SLA, un planificateur d'adresses, un modèle de coûts, la matrice de
responsabilité partagée, et un moteur d'examen.

La mesure la plus dérangeante tient en trois lignes. Une politique IAM
nommée **`lecture-seule.json`** :

```
« lecture seule » accorde 6 action(s) sur 8 :
   s3:GetObject   s3:ListBucket   s3:PutObject
   s3:DeleteObject ⚠️   s3:DeleteBucket ⚠️   s3:PutBucketPolicy ⚠️
```

Elle s'appelle « lecture seule ». Elle accorde la suppression du bucket. La
cause est une seconde déclaration ajoutée « pour débloquer un incident » et
jamais retirée — et on ne le voit pas en **lisant**, seulement en
**essayant**, action par action.

Et la composition des SLA :

```
un seul service à 99,9 %        →  99,9000 %      8 h 45 min par an
trois en série, chacun à 99,9 % →  99,7003 %   1 j 2 h 16 min par an
```

---

## Ce que ce projet est, et n'est pas

⚠️ **Aucun compte cloud, aucune clé d'API, aucun appel réseau.** Ce projet
ne provisionne rien : il **implémente les règles** et les applique à de
vrais fichiers de politique et à des scénarios chiffrés.

Ce qui est réel :

| | Réalité |
|---|---|
| l'**évaluation IAM** | `jobportal/iam.py` — l'ordre exact : `Deny` explicite > `Allow` > refus implicite. `Action`/`NotAction`, `Resource`/`NotResource`, jokers `*` et `?`, conditions `StringEquals`, `StringLike`, `Bool`, `IpAddress`, `Null`, `ArnLike`, et le suffixe `...IfExists`. Les politiques de `politiques/` sont du JSON qu'une console accepterait. |
| la **composition des SLA** | `jobportal/disponibilite.py` — en série les disponibilités se multiplient, en parallèle ce sont les pannes. Plus le barème de remise, et l'écart entre la remise et la perte. |
| le **plan d'adressage** | `jobportal/reseau.py` — sur `ipaddress` de la bibliothèque standard. Découpage, chevauchements, appairage refusé, et les **cinq adresses réservées par sous-réseau**. |
| la **responsabilité partagée** | `jobportal/responsabilite.py` — onze couches × quatre modèles, et le calcul de ce qui reste à votre charge. |
| le **moteur d'examen** | `jobportal/examen.py` — il ne stocke **aucune** bonne réponse : chaque option est décrite sur quatre axes, et la meilleure est calculée pour le critère demandé. |

### Les entrées déclarées, et pourquoi elles le sont

Deux choses ne peuvent pas être mesurées hors ligne :

- `jobportal/tarifs.py` — les prix. Des ordres de grandeur relevés une fois
  sur des grilles publiques, arrondis, figés. Ils changent tous les
  trimestres et varient par région ;
- les **notes sur quatre axes** de `jobportal/questions.py` — un jugement
  d'architecte sur une échelle de 0 à 10, assumé comme tel.

**Ce que le projet mesure n'est aucun de ces chiffres.** Il mesure ce qu'il
en déduit : des **rapports** et des **ordres**. Un environnement allumé en
permanence coûte **4,21 fois** celui qu'on éteint le soir — et ce facteur
est `730 / 173`, où aucun prix n'entre. Changez toute la grille tarifaire :
le facteur ne bouge pas.

## Démarrer

```bash
uv sync --extra dev
uv run --extra dev pytest -q        # 92 tests

uv run python chapitres/chapitre_1_fondamentaux.py     # les SLA se multiplient
uv run python chapitres/chapitre_2_calcul_stockage.py  # la donnée refroidit
uv run python chapitres/chapitre_3_reseau_securite.py  # ce que la politique accorde
uv run python chapitres/chapitre_4_donnees.py          # managé, en euros et en couches
uv run python chapitres/chapitre_5_couts.py            # la dérive, chiffrée
uv run python chapitres/chapitre_6_certification.py    # le mot qui tranche
```

Le moteur IAM s'utilise sur **vos** politiques :

```python
from jobportal import iam

politique = iam.charger_fichier("ma-politique.json")
verdict = iam.evaluer(politique, iam.Demande(
    "s3:DeleteBucket", "arn:aws:s3:::mon-bucket"))
print("\n".join(iam.expliquer(verdict, iam.Demande(
    "s3:DeleteBucket", "arn:aws:s3:::mon-bucket"))))
```

## Ce que les six chapitres mesurent

| | Mesure |
|---|---|
| 1 | La matrice de responsabilité : **11 → 7 → 4 → 3** couches à votre charge. Trois d'entre elles — données, identités, configuration — **ne bougent jamais**. Puis trois 99,9 % en série font **99,7003 %**, doubler un composant fait passer sa panne de 8 h 46 min à **32 s** par an, et une panne de 4 h rend **420 €** de remise pour **36 000 €** de perte. |
| 2 | Trois façons d'héberger la même API : un rapport de **1 à 18** — qui s'inverse passé 50 millions d'appels par mois, et le chapitre imprime le point de bascule. Puis un cycle de vie sur 3 ans : **3 312 € → 518 €, soit 84 %**. Et le piège : il faut **1,1 mois sans relecture** pour que la descente au froid soit rentable. |
| 3 | Un `/28` donne **11 adresses sur 16**. Deux VPC en `10.0.0.0/16` ne s'appairent pas. Puis la politique « lecture seule » qui accorde 6 actions sur 8, le `NotAction` qui en accorde 7, le `Deny` sur le MFA qui **autorise** un appel n'annonçant rien, et le `Deny` d'organisation qui bat un administrateur. |
| 4 | Le supplément managé (**×1,85**) achète 1 heure d'ingénierie par mois — et déplace **3 couches** de responsabilité. Puis l'analyse sur la production : **10 h 35 min de service dégradé par mois** de plus que sur un entrepôt. |
| 5 | Une facture de mois ordinaire dont **48 %** est inutilisée et non attribuable. Le facteur **×4,21**. Le right-sizing qui **change de verdict selon la marge** — une décision, pas un détail. Les engagements, du ×1 au ×0,28. Et la ligne réseau : sortie payante, entrée gratuite, réplication facturée **des deux côtés**. |
| 6 | La même question, les mêmes options, **3 réponses différentes sur 4 critères**. Un énoncé sans mot qui tranche **lève** au lieu de deviner. Et le cas qui fait réfléchir : sur « le moins cher », la bonne réponse est *rendre le stockage public*. |

## Les pièces à conviction

```
politiques/lecture-seule.json     s'appelle « lecture seule », accorde la suppression
politiques/tout-sauf-iam.json     un NotAction dont le périmètre grandit tout seul
politiques/sans-mfa.json          un Deny qui ne refuse rien
```

**Ne pas les réparer** : `tests/test_iam.py` vérifie que chaque défaut est
toujours là, et les chapitres mesurent dessus. Leurs versions corrigées sont
à côté, en `-corrigee.json`.

## Ce que le projet ne prouve pas

- **aucune ressource n'est créée, aucune facture n'est émise** : les euros
  affichés viennent de `tarifs.py`, qui le dit en toutes lettres ;
- **le moteur IAM est un sous-ensemble** : ni politiques de ressource et
  leurs `Principal`, ni frontières de permissions, ni SCP d'organisation, ni
  rôles assumables, ni variables de contexte (`${aws:username}`). Chacun
  **lève** plutôt que d'être ignoré. Et il applique le JSON, pas
  l'intention — là où AWS restreint `s3:ListBucket` à l'ARN du bucket, ce
  moteur l'accorde sur ce que la politique nomme ;
- **la composition des SLA suppose des pannes indépendantes**, ce qui est
  faux : deux répliques partagent un plan de contrôle, une configuration et
  une équipe. Le chiffre obtenu est un **plafond théorique** ;
- **les cinq adresses réservées sont celles d'AWS** — Azure en réserve cinq,
  GCP quatre. Le nombre est déclaré en un endroit ;
- **le moteur d'examen juge sur quatre axes**, et rien d'autre. Il ne sait
  pas que la sécurité est un prérequis et non un critère parmi d'autres :
  le chapitre 6 le montre justement en le laissant se tromper.
