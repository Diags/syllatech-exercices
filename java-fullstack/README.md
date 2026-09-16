# Java Fullstack — projet de départ du cours

Un **vrai portail Spring Boot 4** : trois couches, des DTO, Bean Validation,
Spring Data JPA sur H2, un schéma versionné par Flyway, et des JWT signés en
HMAC-SHA256 qu'un filtre valide à chaque requête. Tout cela démarre sur un
port libre et répond en HTTP.

Et la mesure d'ouverture, côté React — sans navigateur, sans Node :

```
   Une offre arrive en tete de liste. Les six autres n'ont pas bouge.

   APPARIEMENT              CREER     SUPPR.    DEPLACER    MAJ         TOTAL
   par POSITION (sans key)  1         0         0           6 ⚠️        7
   par CLE (avec key)       1         0         0           0           1
```

**Sept opérations contre une.** Et le pire n'est pas là : sans `key`, l'état
interne suit la *position*. Une case cochée sur `OFF-101` se retrouve sur
`OFF-107` — un bogue qu'aucun test d'affichage ne voit.

Côté back, la mesure qui fait mal :

```
   APPEL                                          STATUT
   GET /api/moi, avant la desactivation           200
   POST /api/auth/connexion, apres                401
   POST /api/auth/rafraichir, apres               401
   GET /api/moi avec l'ANCIEN access token        200   ⚠️
```

Le compte est désactivé, le refresh token révoqué — et l'access token
continue de fonctionner. **On ne peut pas révoquer ce qu'on ne stocke pas.**
Ce n'est pas un défaut : c'est la définition d'un jeton auto-porteur, et
c'est pour cela qu'on le fait vivre quelques minutes.

---

## Ce que ce projet est, et n'est pas

| | Réalité |
|---|---|
| le **back** | une vraie application Spring Boot 4, démarrée sur un port choisi par le système et interrogée avec le client HTTP du JDK. |
| la **base** | H2 en mémoire, schéma posé par **Flyway** et *validé* par Hibernate (`ddl-auto=validate`). Rien n'est deviné. |
| le **N+1** | compté par un `StatementInspector` d'Hibernate : ce n'est pas une histoire, c'est un nombre. |
| les **JWT** | signés et vérifiés à la main en HMAC-SHA256, pour que le chapitre 4 puisse en **ouvrir la charge utile** devant vous. Quatre attaques sont fabriquées et soumises au vérificateur. |
| **Stripe** | la vérification de signature est la **vraie** : `t=…,v1=…`, HMAC sur `t + "." + corps`, tolérance de 5 minutes, comparaison en temps constant. Un webhook rejoué est refusé pour de vrai. |
| le **Dockerfile** | audité, règle par règle, sur les deux fichiers livrés dans `deploiement/`. |

⚠️ **Le front n'est pas lancé, et ses mécanismes sont mesurés.** Un cours ne
peut pas exiger Node ni un navigateur. Ce que les chapitres 1 et 5
implantent en Java — la réconciliation d'une liste avec et sans `key`, la
sémantique des dépendances de `useEffect`, un magasin à la Redux — ce sont
les *algorithmes* que React et Redux appliquent, et ils se comptent. Ce
n'est ni React, ni Redux Toolkit : ni fibres, ni Immer, ni rendu concurrent.

⚠️ **Aucune clé d'API, aucun compte Stripe.** Les sessions de paiement sont
fabriquées localement ; ce qui est vérifié est le **schéma de signature**,
qui se calcule hors ligne.

## Démarrer

```bash
mvn test                      # 76 tests

mvn spring-boot:run           # le portail sur http://localhost:8080

mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre1React
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre2Api
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre3Jpa
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre4Jwt
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre5Redux
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre6Deploiement
```

À essayer à la main, sur le portail qui tourne :

```bash
# la liste, publique
curl -s localhost:8080/api/offres | jq

# un jeton, puis une route qui exige une identite
JETON=$(curl -s -X POST localhost:8080/api/auth/connexion \
  -H 'Content-Type: application/json' \
  -d '{"identifiant":"awa","motDePasse":"motdepasse"}' | jq -r .accessToken)

curl -s localhost:8080/api/moi -H "Authorization: Bearer $JETON" | jq

# 401 sans jeton, 403 avec un jeton sans ROLE_RH
curl -s -o /dev/null -w '%{http_code}\n' -X POST localhost:8080/api/offres \
  -H 'Content-Type: application/json' -d '{"titre":"x","pile":"java","salaireEnKiloEuros":40,"entrepriseId":1}'

# la charge utile du jeton se lit SANS aucune cle
echo $JETON | cut -d. -f2 | base64 -d
```

## Ce que les six chapitres mesurent

| | Mesure |
|---|---|
| 1 | Une insertion en tête de liste : **7 opérations du DOM sans `key`, 1 avec** — dont **6 réécritures** de lignes qui n'ont pas changé. Et l'état qui migre : la coche d'`OFF-101` se retrouve sur `OFF-107`. Puis `useEffect` compté sur quatre rendus : **4 effets sans tableau, 1 avec `[]`, 2 avec `[motCle]`** — et les nettoyages qui vont avec. |
| 2 | Les codes de statut du contrat : 200, 404, 201, **401** (personne n'est identifié) et **403** (identifié, pas le droit). L'entité porte `entreprise : Entreprise`, le DTO `entreprise : String` — c'est ce qui sépare le cycle de vie de la base de celui du front. Et la validation refuse à la frontière, champ par champ, en `problem+json`. |
| 3 | Le N+1, **compté** : `findAll()` puis `.getNom()` émet **4 requêtes** (1 + 3 entreprises distinctes — le cache de premier niveau déduplique), `join fetch` en émet **1**. Et les deux rendent exactement le même résultat, ce qui est précisément ce qui rend le N+1 invisible. |
| 4 | La charge utile du jeton, **lue sans aucune clé**. Quatre attaques soumises au vérificateur : rôle changé en Base64, `alg: none`, signature d'une autre clé, refresh token présenté comme access token. Puis le talon d'Achille : compte désactivé, refresh révoqué, **access token toujours valide**. |
| 5 | Le *prop drilling* chiffré (à 10 niveaux : 11 composants contre 2), un réducteur pur dont l'état initial reste intact, et **la vraie vérification Stripe** : montant modifié → refusé, signature inventée → refusée, webhook valide **rejoué 30 min plus tard → refusé**. Puis le paiement fantôme : **1 290 € encaissés pour une requête GET**. |
| 6 | Les deux Dockerfile du dépôt, audités : **6 règles satisfaites** contre **6 manquantes**. Et la détection d'un secret écrit dans l'image — `ENV` comme `ARG`, valeur présente ou non. |

## Six pièges rencontrés en construisant ce projet

Chacun est fixé par un test, parce qu'aucun ne produit d'erreur claire :

1. **un 403 ressort en 401.** Quand une requête est refusée, Tomcat la
   réachemine vers `/error` — et ce réacheminement **retraverse la chaîne de
   filtres**, cette fois en anonyme. Les journaux disent « Responding with
   403 », le client lit 401, et le front redirige vers la connexion un
   utilisateur déjà connecté. Il faut
   `.dispatcherTypeMatchers(ERROR).permitAll()` ;
2. **sans `authenticationEntryPoint`, Spring Security rend 403 dans les deux
   cas** — pour un anonyme comme pour un identifié sans droit. Or les deux
   appellent des réactions opposées côté React ;
3. **`flyway-core` seul ne migre rien.** Depuis Spring Boot 4, la
   configuration automatique vit dans `spring-boot-flyway`. Sans lui, tout
   se résout, aucune migration ne s'exécute, rien n'est journalisé — et
   Hibernate échoue plus loin sur « missing table » ;
4. **un `StatementInspector` déclaré par son NOM n'est pas votre bean.**
   Hibernate instancie le sien, et le compteur reste à zéro sans la moindre
   erreur. Il faut passer l'instance par un `HibernatePropertiesCustomizer` ;
5. **une base H2 en mémoire est partagée par tous les contextes du même
   processus** qui portent le même nom. Deux applications Spring lancées
   dans la même JVM — ce que font les tests de chapitres — se retrouvent sur
   les mêmes tables, et un chapitre qui désactive un compte fait échouer le
   suivant. Le nom porte donc un `${random.uuid}` ;
6. **Spring Boot 4 embarque Jackson 3** (`tools.jackson`), pas Jackson 2
   (`com.fasterxml.jackson.databind`). Le paquet a changé et les exceptions
   ne sont plus vérifiées : un `import` recopié d'un tutoriel de 2024 ne
   compile pas.

## L'exercice

Neuf zones à compléter, réparties sur les chapitres qui les expliquent :

```
front/Reconciliation        apparier une liste par CLE                (ch. 1)
front/Composant             les trois formes de dependances           (ch. 1)
api/OffreDto                le contrat public, pas l'entite           (ch. 2)
api/CreationOffre           la validation a la frontiere              (ch. 2)
domaine/OffreRepository     le `join fetch` qui tue le N+1            (ch. 3)
securite/Jeton              verifier signature, expiration, usage     (ch. 4)
securite/ConfigurationSecurite  les regles, et le refus par defaut    (ch. 4)
paiement/SignatureStripe    les trois controles d'un webhook          (ch. 5)
deploiement/AuditImage      detecter un secret dans l'image           (ch. 6)
```

Sur la branche `depart`, le squelette **compile et démarre** : le portail
répond, la liste s'affiche, la connexion fonctionne. Mais la réconciliation
ne fait rien, la validation accepte tout, le N+1 est là, le JWT accepte
n'importe quoi et le webhook aussi. Tout marche, et tout est faux —
**31 tests le disent**.

## Les pièces à conviction

```
front/Reconciliation#parPosition        l'appariement qui reecrit tout
api/OffreService#listerAvecUnNPlusUn    la liste qui emet 4 requetes
paiement/ServicePaiement#confirmerDepuisLeNavigateur   le paiement fantome
deploiement/Dockerfile.naif             l'image qui marche et n'isole rien
```

**Ne pas les « réparer »** : des tests vérifient que les défauts sont
toujours là. `SecuriteTest#leRetourDuNavigateurNeProuveRien` affirme qu'une
commande de 1 290 € passe à PAYÉE sur un simple GET — le jour où il
échouerait, le cours perdrait sa démonstration.

## Ce que le projet ne prouve pas

- **aucun navigateur n'est lancé, aucun Node n'est requis.** Les chapitres 1
  et 5 mesurent des *algorithmes* — l'appariement d'une liste, la sémantique
  d'un effet, l'immuabilité d'un réducteur — pas React ni Redux Toolkit ;
- **aucun compte Stripe n'est utilisé.** Ce qui est vérifié est le schéma de
  signature, qui se calcule hors ligne. Le tunnel de paiement réel, les
  moyens de paiement locaux et la conformité PCI-DSS ne le sont pas ;
- **la base est H2, pas PostgreSQL.** Les requêtes dérivées et le `join
  fetch` se comportent de la même façon, mais les types, les index, les
  verrous et les plans d'exécution diffèrent — c'est précisément pourquoi on
  teste sur la base de production, ou au moins sur la même en conteneur ;
- **aucune image n'est construite.** L'audit lit un texte : c'est un
  contrôle de configuration, comme un linter. Il attrape l'oubli, jamais la
  vulnérabilité — un scanner de CVE (Trivy, Grype) se branche au même
  endroit du pipeline ;
- **les refresh tokens sont stockés en mémoire.** La propriété démontrée est
  la bonne — on ne révoque que ce qu'on stocke — mais deux instances
  derrière un répartiteur ne révoqueraient pas les mêmes jetons. En
  production, c'est Redis ou la base.
