# Microservices événementiels — projet de départ du cours

Une application Axon Framework 4.13 qui tourne **sans la moindre
infrastructure** : ni Axon Server, ni Kafka, ni PostgreSQL. Les événements
vivent dans un `InMemoryEventStorageEngine` — une classe d'Axon, derrière la
même interface qu'un moteur JPA — et les six chapitres **impriment le
journal**. En event sourcing, la vérité est une liste ; une liste se lit.

```
   Le flux de la candidature c-awa :
     1. seq=0 CandidatureDeposee[candidatureId=c-awa, candidat=Awa, offre=OFF-014]
     2. seq=1 EntretienPlanifie[candidatureId=c-awa, creneau=mardi 14h]
```

Et la mesure qui rend le pattern Saga concret — trois candidatures, deux
créneaux :

```
   Ce que la saga a fait pour la troisieme :
     → saga demarree pour c-lea
     → -> ReserverCreneau
     → creneau REFUSE : plus aucun creneau disponible
     → -> AnnulerCandidature (compensation)
     → saga terminee (compensee) pour c-lea

   candidature         statut final
   ──────────────────  ──────────────────────
   c-awa               ENTRETIEN
   c-karim             ENTRETIEN
   c-lea               ANNULEE
```

---

## Ce que ce projet est, et n'est pas

| | Réalité |
|---|---|
| les **agrégats**, **commandes**, **événements** | ceux d'Axon 4.13 : `@CommandHandler`, `@EventSourcingHandler`, `AggregateLifecycle.apply`, `@AggregateIdentifier`. |
| le **magasin d'événements** | l'`InMemoryEventStorageEngine` d'Axon, derrière un `EmbeddedEventStore`. Même interface qu'un moteur JPA ou qu'Axon Server. |
| les **projections** | de vraies classes `@EventHandler`, alimentées par le bus, jetables et rejouables. |
| la **saga** | une vraie `@SagaEventHandler` avec `@StartSaga`, `@EndSaga` et compensation, coordonnant **deux** agrégats. |
| les **tests** | les `AggregateTestFixture` et `SagaTestFixture` d'Axon — le *given / when / expect* que le cours annonce. |

⚠️ **Aucune auto-configuration Spring Boot.** Le cours décrit un starter qui
assemble tout ; ce projet câble Axon **à la main** dans `commun/Banc.java`,
précisément pour que la plomberie soit lisible. Conséquence : les agrégats ne
portent pas `@Aggregate` et la saga ne porte pas `@Saga` — ces annotations
vivent dans `axon-spring` et ne font rien d'autre que déclencher
`configureAggregate(...)` et `registerSaga(...)`. Le code métier est
identique.

⚠️ **Les processeurs sont en mode _subscribing_, pas _tracking_.** Le défaut
d'Axon est le mode *tracking* : chaque groupe de handlers a son fil et son
jeton de position — c'est ce qu'on veut en production, et c'est ce qui crée la
fenêtre de cohérence à terme. En *subscribing*, les projections tournent dans
le fil qui publie : la fenêtre devient **nulle**, et les mesures de ces
chapitres deviennent reproductibles. Le chapitre 3 le dit au lieu de le
cacher.

## Démarrer

```bash
mvn test                      # 37 tests

mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre1Evenementiel
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre2Axon
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre3Cqrs
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre4EventSourcing
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre5Saga
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre6Projet
```

Aucune variable d'environnement, aucun conteneur. Si un chapitre demande un
réseau, c'est un bug.

## Ce que les six chapitres mesurent

| | Mesure |
|---|---|
| 1 | Une commande refusée laisse **0 événement** dans le journal ; une acceptée en laisse 1. L'invariant « pas de décision sans entretien », tenu par l'agrégat et impossible dans une projection. Et une livraison *at-least-once* fabriquée : le compteur naïf annonce **2** candidatures là où il y en a **1**, sans lever la moindre erreur. |
| 2 | La plomberie, imprimée : `SimpleCommandBus`, `EmbeddedEventStore`, `SubscribingEventProcessor` — et le fait que le bus d'événements et le magasin sont **le même objet**. Le routage, mesuré sur le `AnnotationCommandTargetResolver` : même champ, même valeur, l'annotation en moins → `IllegalArgumentException`. |
| 3 | Deux projections, un seul journal. La vue **jetée** puis reconstruite à l'identique, et une projection créée après coup qui connaît tout le passé. Le modèle d'écriture, lui, n'a pas bougé. |
| 4 | Le flux complet d'une candidature, numéros de séquence compris. Le rejeu qui s'allonge à chaque commande : 3, 4, 5, 6 événements relus. Puis un snapshot au rang 6 : **0 événement relu** là où il en fallait **7** — et les 7 sont toujours dans le journal. |
| 5 | La saga, étape par étape, sur les deux chemins. Trois candidatures pour deux créneaux : la troisième passe par DEPOSEE, reçoit un `CreneauRefuse` — un **événement**, pas une exception — et finit ANNULEE par compensation. |
| 6 | Les fixtures `given/when/expect` exécutées devant vous, erreur comprise. Un **seul `traceId`** pour 3 événements produits par 2 agrégats. Le retard d'un consommateur, mesuré. Et le pattern Outbox, testé en fabriquant la panne qu'il évite : sans lui, 1 ligne en base et **0 événement publié**. |

## Cinq pièges rencontrés en construisant ce projet

Chacun est documenté à l'endroit où il mord :

1. **une saga sans `@Inject` ne reçoit rien** — Axon n'injecte que les champs
   portant `jakarta.inject.Inject`, `javax.inject.Inject` ou l'`@Autowired` de
   Spring. Sans l'un d'eux, la passerelle reste `null` et la saga échoue au
   premier événement, **dans un autre fil** — donc avec une trace que
   l'appelant ne voit jamais ;
2. **un agrégat « registre » n'a pas de commande de création** — sans
   `@CreationPolicy(CREATE_IF_MISSING)`, la première réservation échoue en
   `AggregateNotFoundException` ;
3. **`eventStore().readEvents(id)` ne rend pas le journal complet** : il part
   du snapshot. Pour voir tous les événements, il faut interroger le moteur de
   stockage. Le snapshot n'efface rien, il court-circuite ;
4. **les processeurs *tracking* rendent toute mesure non déterministe** — à la
   ligne suivante, la projection n'est pas encore à jour, et le chiffre
   imprimé dépend de la machine ;
5. **`axon-test` ne compile pas sans Hamcrest** : la signature
   d'`expectEvents(...)` mentionne un `Matcher`, et l'erreur tombe à un
   endroit qui n'a rien à voir.

Aucun des cinq ne produit d'erreur au démarrage. C'est ce qui les rend longs à
trouver — et c'est pourquoi ils sont écrits ici.

## Sur les versions

Axon Framework existe en deux lignes. La **5.x** est sortie pour les modules
de cœur (`axon-messaging`, `axon-eventsourcing`, `axon-modelling`,
`axon-test`) et introduit un modèle de programmation différent ; son
intégration Spring, elle, en est encore à `5.0.0-preview`. La **4.13**,
utilisée ici, est la ligne dont le starter Spring Boot est publié et dont les
annotations sont exactement celles du cours. C'est donc elle qu'un projet qui
suit ce cours doit utiliser aujourd'hui — en sachant qu'une migration est à
prévoir.

Le chapitre 2 imprime la version réellement chargée : ne la croyez pas sur
parole.

## L'exercice

Six zones à compléter, réparties sur les chapitres qui les expliquent :

```
domaine/Candidature#Decider        l'invariant « pas de decision sans entretien »  (ch. 1)
domaine/Candidature#Annuler        rendre la compensation idempotente              (ch. 1)
domaine/Candidature#Planifier      refuser sur une candidature close               (ch. 2)
projection/CompteurParOffre        ignorer un fait deja traite                     (ch. 1)
projection/VueDesCandidatures      alimenter le modele de lecture                  (ch. 3)
domaine/Agenda#ReserverCreneau     publier un refus plutot que lever               (ch. 5)
saga/SagaDeCandidature#CreneauRefuse  compenser au lieu d'attendre                 (ch. 5)
```

Sur la branche `depart`, le squelette **compile et tourne** : les invariants
sont absents, le compteur compte deux fois, la vue reste vide et la saga
n'annule rien. Tout marche, et tout est faux — ce sont les tests qui le
disent.

## Ce que le projet ne prouve pas

- **aucune infrastructure n'est démarrée** : le débit, la latence, le
  partitionnement, la reprise d'un consommateur et le comportement d'un
  cluster ne sont pas mesurés ici ;
- **la fenêtre de cohérence à terme est nulle**, parce que les processeurs
  sont en mode *subscribing*. En production elle existe, et c'est côté
  interface qu'elle se gère ;
- **aucun upcaster n'est écrit** : le chapitre 4 montre pourquoi ils existent
  — un événement porte le nom de classe et la forme qu'il avait le jour de son
  écriture — sans en fabriquer un ;
- **le pattern Outbox est simulé**, avec deux listes et une panne forcée. Ce
  qui est mesuré est la propriété — on ne perd rien — pas la performance d'un
  relais réel.
