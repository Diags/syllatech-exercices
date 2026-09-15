# Microservices avec Spring Cloud — projet de départ du cours

Un **vrai** serveur Eureka, de **vrais** services qui s'y enregistrent, une
**vraie** Spring Cloud Gateway avec son disjoncteur Resilience4j — le tout
dans une seule JVM, sur des ports libres, interrogé en vrai HTTP. Aucun
conteneur n'est nécessaire pour les quatre premiers chapitres, et aucun
cluster pour les deux derniers.

```
   requete     code    qui a repondu   etat du circuit
   ──────────  ──────  ──────────────  ────────────────
   appel 1     500     service         CLOSED
   appel 2     500     service         CLOSED
   …
   appel 8     500     service         CLOSED

   replis servis              0
```

Huit erreurs 500 d'affilée, et le circuit **reste fermé**. C'est le
comportement par défaut d'un disjoncteur de passerelle, et c'est la mesure la
plus utile de ce projet : un 500 n'est pas une exception, c'est une réponse.
Une ligne de configuration plus loin, la même route ouvre son circuit au
quatrième appel.

---

## Ce que ce projet est, et n'est pas

| | Réalité |
|---|---|
| **Eureka** | le serveur Netflix complet, démarré par `@EnableEurekaServer`, interrogé par son API REST. |
| les **services** | de vraies applications Spring Boot, plusieurs instances du même nom, chacune sur son port. |
| la **passerelle** | une vraie Spring Cloud Gateway (`gateway-server-webmvc`) : routage, réécriture de chemin, `lb://`, circuit breaker, filtre d'authentification. |
| le **disjoncteur** | Resilience4j, avec ses vrais états `CLOSED` / `OPEN` / `HALF_OPEN`, lus dans l'actuator. |
| **Docker** et **Kubernetes** | de vrais fichiers, dans `deploiement/`, lus et vérifiés par du code — pas de démon, pas de cluster. |

⚠️ **Les intervalles d'Eureka sont raccourcis.** Par défaut, un service met
une trentaine de secondes à devenir visible et une instance morte reste
annoncée **quatre-vingt-dix secondes**. Ces valeurs sont raisonnables en
production et rendraient ces chapitres interminables : elles sont ramenées à
la seconde, et le chapitre 2 imprime les deux jeux côte à côte.

⚠️ **Spring Boot 4.0.8, pas 4.1.** Le train Spring Cloud 2025.1.3 déclare
`spring-boot.version` 4.0.8 : c'est la version contre laquelle il est compilé
et testé. Le train a toujours un temps de retard sur Boot, et suivre cette
matrice évite des incompatibilités qui n'apparaissent qu'à l'exécution.

## Démarrer

```bash
mvn test                      # 35 tests

mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre1Decoupage
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre2Annuaire
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre3Passerelle
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre4Docker
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre5Kubernetes
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre6Securite
```

Le port **8761** doit être libre : c'est celui de l'annuaire, et il est fixe
pour une raison expliquée dans `commun/Banc.java`. Tout le reste tourne sur
des ports attribués par le système.

## Ce que les six chapitres mesurent

| | Mesure |
|---|---|
| 1 | Le prix du réseau, chiffré : **0,005 ms** pour un appel en mémoire contre **4,8 ms** par HTTP — sur la boucle locale, sans TLS, sans sérialisation lourde. Soit un rapport de **×884**, qui est le plancher absolu. Puis une instance arrêtée pendant que l'autre continue de répondre. |
| 2 | Le contenu brut de l'annuaire, et le nom en MAJUSCULES sous lequel l'application est enregistrée. Les délais par défaut d'Eureka (30 s / 90 s / auto-préservation) face à ceux du banc. Et le temps réel d'oubli d'une instance morte. |
| 3 | La réécriture de chemin, l'équilibrage **10/10** entre deux instances via `lb://`, puis le disjoncteur : **8 × 500 ne l'ouvrent pas**, la même route avec `setStatusCodes` l'ouvre au 4ᵉ appel. Et le gain, chiffré : **7 ms** avec le repli contre **411 ms** sur un service lent. |
| 4 | Le Dockerfile du projet et sa version naïve, comparés ligne à ligne : étages, utilisateur, forme de l'`ENTRYPOINT`, ordre des couches. `latest` détecté comme tag mobile. Et `depends_on` qui n'attend la disponibilité que sous sa forme longue. |
| 5 | Deux manifestes Kubernetes qui démarrent tous les deux, dont un sans sondes, sans limites et sans stratégie. Puis l'arithmétique d'une mise à jour progressive, étape par étape — et le réglage `maxSurge: 0, maxUnavailable: 4` qui descend à **0 pod disponible**. |
| 6 | Trois requêtes à la passerelle : sans jeton (**401**), mal formé (**401**), valide (**200**). Puis la même requête **en direct sur le service** : **200**. Et un `X-Request-Id` différent à chaque requête, retrouvé côté service. |

## Cinq pièges rencontrés en construisant ce projet

Chacun est documenté à l'endroit où il mord :

1. **un 500 n'ouvre pas le circuit** — un disjoncteur de passerelle compte les
   *exceptions*, pas les codes d'erreur. Sans `setStatusCodes(...)`, le
   disjoncteur que vous croyez avoir n'existe pas ;
2. **`spring-cloud-starter-gateway` ne suit plus le train** — la passerelle a
   été scindée en `gateway-server-webmvc` et `gateway-server-webflux`, et le
   préfixe des propriétés a changé avec elle. Un `spring.cloud.gateway.routes`
   recopié d'un article ancien est ignoré **en silence** ;
3. **le client Eureka choisit Jersey s'il le trouve** — et le starter du
   *serveur* Eureka l'amène. Dans une JVM qui héberge les deux, le client part
   sur un transport dont les fabriques manquent, et l'erreur parle d'un bean
   `TransportClientFactories` introuvable : rien qui oriente vers Jersey.
   `eureka.client.jersey.enabled=false` règle tout ;
4. **deux instances sur une même machine se déclarent identiquement** — sans
   `eureka.instance.instance-id` unique, l'annuaire n'en voit qu'une, et
   l'équilibrage n'a rien à équilibrer ;
5. **un serveur Eureka est aussi un client de lui-même** — il tente de se
   répliquer vers les pairs de `defaultZone`, réglage qui doit être connu
   *avant* le démarrage. D'où le port fixe 8761, quand tout le reste est
   aléatoire.

Aucun des cinq ne produit d'erreur au démarrage. C'est ce qui les rend longs à
trouver — et c'est pourquoi ils sont écrits ici.

## L'exercice

Six zones à compléter, réparties sur les chapitres qui les expliquent :

```
commun/Banc#communes                  un instance-id unique par instance   (ch. 2)
passerelle/Passerelle#routeDesOffres  reecrire /api/offres vers /offres    (ch. 3)
passerelle/Passerelle#routeStricte    compter les 5xx comme des echecs     (ch. 3)
plateforme/LectureDockerfile#nonRoot  lire la derniere instruction USER    (ch. 4)
plateforme/MiseAJourProgressive       respecter maxUnavailable             (ch. 5)
passerelle/Passerelle#routeProtegee   refuser en 401 sans jeton            (ch. 6)
```

Sur la branche `depart`, le squelette **compile et tourne** : l'annuaire ne
voit qu'une instance, la passerelle rend des 404, le disjoncteur ne s'ouvre
jamais, le vérificateur de Dockerfile dit toujours oui, la mise à jour descend
à zéro pod et la route « protégée » ne protège rien. Tout démarre, et tout est
faux — ce sont les tests qui le disent.

## Les pièces à conviction

```
deploiement/Dockerfile.naif           un etage, root, forme shell, cache invalide
deploiement/k8s/deployment-sans-sondes.yaml   ni sondes, ni limites, ni strategie
passerelle/Passerelle#routeDesOffres  le disjoncteur qui ne compte pas les 500
```

**Ne pas les réparer** : des tests vérifient que ces fichiers sont toujours
mauvais. Ils servent de contre-exemples — un vérificateur qui n'a jamais vu de
fichier incorrect ne prouve rien.

## Ce que le projet ne prouve pas

- **tout tourne dans une JVM** : le débit, la latence réseau réelle, la
  tolérance aux partitions et le comportement d'un cluster Eureka à plusieurs
  nœuds ne sont pas mesurés ;
- **aucune image n'est construite, aucun manifeste n'est appliqué** : les
  chapitres 4 et 5 lisent et calculent. Ce qui est vérifié est ce que les
  fichiers *décident*, pas ce que Docker ou Kubernetes en font ;
- **la mise à jour progressive est une simulation** : le vrai contrôleur
  attend les sondes et respecte `minReadySeconds`. Ce qui est calculé ici est
  l'enveloppe — le plancher de disponibilité et le pic de pods — et c'est
  précisément ce que les deux réglages garantissent ;
- **le jeton du chapitre 6 n'est pas un JWT** : la vérification est
  rudimentaire, parce que ce qui est mesuré est l'*emplacement* du contrôle.
  La validation d'un vrai jeton signé est l'objet du cours Spring Security ;
- **il n'y a pas de Config Server** : le chapitre 2 le décrit, le projet ne le
  démarre pas. Ce qui compte pour la suite — que
  `spring.application.name` soit la clef de tout — est mesuré sur Eureka.
