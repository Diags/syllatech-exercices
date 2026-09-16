# Spring & Spring Boot — projet de départ du cours

Une **vraie** application Spring Boot 4, démarrée par chaque chapitre, qui
reçoit de vraies requêtes HTTP. Rien n'est simulé.

```
   compteur                attendu     obtenu      perdu
   ──────────────────────  ──────────  ──────────  ────────
   champ `long vues++`     200         198         2
   champ `AtomicLong`      200         200         0

   requetes ayant lu le nom d'UN AUTRE client   10 sur 200
```

Le cours énonce une règle d'or : « un bean singleton doit être sans état ».
Le chapitre 1 lance deux cents requêtes concurrentes sur un singleton qui
retient un champ, et compte. Le compteur faux est le moindre problème : **dix
requêtes ont lu le nom d'un autre client**.

---

## Ce que ce projet est, et n'est pas

| | Réalité |
|---|---|
| l'**application** | Spring Boot 4.1.1, Java 25, H2 en mémoire. Elle démarre, écoute, sert des routes protégées. |
| les **requêtes** | de vraies requêtes HTTP sur un port libre, avec un vrai `RestClient`. Un 401 mesuré ici est celui de la production. |
| le **N+1** | compté par un `StatementInspector` branché sur Hibernate : la liste exacte du SQL envoyé. |
| l'**auto-configuration** | le `ConditionEvaluationReport` que Spring Boot tient lui-même, lu décision par décision. |
| la **chaîne de filtres** | lue dans le `FilterChainProxy` de l'application qui tourne, filtre par filtre, dans l'ordre. |

⚠️ **Aucune image Docker n'est construite.** Le `Dockerfile` est livré et
vérifié par des tests (deux étapes, ordre des couches, `JarLauncher`, pas de
`root`), mais rien ne le construit ici — Docker n'est pas une dépendance d'un
projet de cours.

⚠️ **Aucune base réelle.** H2 en mémoire, recréée à chaque démarrage. Ce qui
est mesuré n'est pas la performance d'une base, c'est le **nombre de
requêtes** — et ce nombre est le même sur PostgreSQL.

## Démarrer

Il faut un **JDK 25** et Maven.

```bash
mvn test                      # 94 tests

mvn spring-boot:run           # le portail sur http://localhost:8080

mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre1Beans
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre2Boot
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre3Rest
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre4Jpa
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre5Securite
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre6Docker
```

Sans JDK 25 sous la main, tout se joue dans un conteneur :

```bash
docker run --rm -v "$PWD:/w" -w /w maven:3-eclipse-temurin-25 mvn -q test
```

Le portail qui tourne, à essayer à la main :

```bash
curl http://localhost:8080/api/public/offres                  # 200
curl http://localhost:8080/rapports/salaires                  # 401
curl -u awa:motdepasse http://localhost:8080/api/admin/tableau-de-bord
curl -u karim:motdepasse http://localhost:8080/api/admin/tableau-de-bord   # 403
```

## Ce que les six chapitres mesurent

| | Mesure |
|---|---|
| 1 | 200 requêtes concurrentes : le singleton avec état perd des incrémentations, et **rend à dix requêtes le nom d'un autre client**. Puis : l'injection par champ voit `null` au constructeur, et une dépendance circulaire **démarre sans rien dire** quand elle est injectée par champ — alors qu'elle est refusée au démarrage par constructeur. |
| 2 | Le rapport d'auto-configuration, décision par décision, avec le texte des conditions. Notre `PasswordEncoder` gagne — et le rapport dit pourquoi. Six lignes de `pom.xml` amènent plus de soixante-dix jars. Le même code, deux profils, deux comportements. |
| 3 | La route qui rend l'entité laisse sortir `salaireReel` et la `noteInterne` de l'entreprise. Une donnée invalide n'atteint **jamais** le service — un compteur le dit. Et les deux erreurs, celle de Spring et la nôtre, ont la même forme RFC 9457. |
| 4 | `findAll()` : **5 instructions SQL**. `findAllAvecEntreprise()` : **1**. Puis quatre façons de croire qu'on a une transaction : l'exception vérifiée laisse 2 lignes en base, et l'appel interne aussi. |
| 5 | La chaîne de filtres, imprimée dans l'ordre réel. Une route que la configuration ne mentionne nulle part répond **401** — c'est le refus par défaut. 60 requêtes refusées, **0 entrée** dans le contrôleur. BCrypt : deux empreintes pour le même mot de passe, et le temps que coûte une vérification. |
| 6 | Notre code pèse **moins de 1 %** de ce qui composerait l'image. Le `layers.idx` du jar, lu dans le jar. Et `-Djarmode=layertools` — le mode que citent tous les tutoriels — **a été retiré de Spring Boot 4**. |

## L'exercice

Cinq zones à compléter, réparties sur les quatre chapitres qui les expliquent :

```
offre/OffreRepository        la requete JPQL avec `join fetch`       (ch. 4)
offre/dto/OffreDto           construire le DTO depuis l'entite       (ch. 3)
offre/dto/CreerOffreDto      les contraintes de Bean Validation      (ch. 3)
erreurs/GestionnaireErreurs  le ProblemDetail d'une erreur metier    (ch. 3)
securite/SecurityConfig      les regles d'autorisation               (ch. 5)
```

Sur la branche `depart`, le squelette **compile et démarre** — c'est
volontaire : une application qui ne démarre pas ne dit rien. Ce sont les
tests qui échouent, et chacun nomme ce qui manque. Le squelette de
`SecurityConfig` ouvre tout (`anyRequest().permitAll()`), celui du
repository fait un `select` sans jointure : les deux marchent, et les deux
sont faux.

## Les pièces à conviction

Cinq classes sont **volontairement fautives**, et des tests vérifient qu'elles
le sont toujours. **Ne pas les réparer** :

```
coeur/CompteurDeVues       un singleton qui retient un champ par requête
offre/OffreController      la route `/entites-brutes`, qui publie l'entité
offre/OffreService         demoPasDeRollback… et demoAppelInterne
securite/RouteOubliee      `/rapports/salaires`, citée nulle part dans la config
offre/Offre                `salaireReel`, qui ne doit jamais sortir
```

## Ce que le projet ne prouve pas

- aucune image n'est construite : le `Dockerfile` est **lu et vérifié**, pas
  exécuté ;
- aucun déploiement AWS : ECS et EKS consomment une image, et c'est l'image
  que le chapitre 6 décrit ;
- la course du chapitre 1 **n'est pas garantie** de se produire : c'est une
  course, pas un théorème. Le test l'admet dans son message ;
- les nombres de requêtes SQL dépendent du jeu de données — quatre
  entreprises, dix offres. `Amorce` explique pourquoi ces nombres-là.
