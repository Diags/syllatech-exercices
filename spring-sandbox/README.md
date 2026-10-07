# Java Spring + Sandbox — projet de départ du cours

Un vrai runner Spring Boot 4, interrogé en HTTP, dont on peut **commuter
l'implantation d'exécution**. La même soumission part des deux côtés de la
frontière, et on imprime ce qui revient.

La menace n'est pas décrite : elle est **exécutée**. Le code d'un candidat,
lancé dans la JVM de l'application, lit le secret de production — et le test
l'affirme.

```
   Soumission : « secret jobportal.cle-api »

      lecture d'une propriete    code=0  delai=false
      sortie  : sk-secret-de-production-a-ne-jamais-divulguer
      la valeur reelle de la propriete : sk-secret-de-production-a-ne-jamais-divulguer
```

Puis la même batterie contre un processus séparé :

```
   ATTAQUE                      dans la JVM            processus separe
   lire un fichier de l'hote    ⚠️ REUSSIE             bloquee (privilege)
   lire un secret de l'app      ⚠️ REUSSIE             bloquee (privilege)
   ouvrir une connexion         bloquee (code 2)       bloquee (privilege)
   boucler sans fin             ⚠️ JAMAIS RENDUE       bloquee (delai)
   devorer la memoire           ⚠️ REUSSIE             bloquee (code 3)
   inonder la sortie            ⚠️ REUSSIE             ⚠️ REUSSIE

   ATTAQUES NON BLOQUEES        5 sur 6                1 sur 6
   dont jamais rendues          1                      0
```

La ligne « **JAMAIS RENDUE** » est la mesure la plus dure du projet : dans la
JVM de l'application, la boucle n'a pas échoué — elle n'a jamais rendu la
main. `Thread.stop` est supprimé depuis Java 20, et il n'existe **aucune**
façon d'arrêter un fil qui ne coopère pas. Le chapitre ne peut se terminer
qu'en imposant une limite **de l'extérieur**, et c'est déjà la démonstration.

---

## Ce que ce projet est, et n'est pas

| | Réalité |
|---|---|
| le **runner** | une vraie application Spring Boot sur un port choisi par le système, appelée par un vrai `RestClient`. Validation `jakarta`, `@RestController`, records en entrée et en sortie. |
| la **frontière** | un vrai `ProcessBuilder`, un vrai `java` enfant, un vrai `waitFor` + `destroyForcibly`. Le `-Xmx` de l'enfant est réel, et il le tue. |
| le **langage du candidat** | un interpréteur de huit verbes écrit ici. Trois d'entre eux lisent vraiment le disque, ouvrent vraiment une connexion, lisent vraiment une propriété Spring. |
| les **métriques** | de vrais compteurs Micrometer dans un `SimpleMeterRegistry`, lus après coup. |
| l'**audit de durcissement** | il lit la ligne `docker run` que le projet construit, et le `Dockerfile` **livré dans ce dépôt**. Retirez-en `USER`, le chapitre 4 le dit. |

⚠️ **Docker n'est jamais lancé, et gVisor non plus.** Un cours ne peut pas
exiger un démon de conteneurs. Ce que le projet mesure est ce qu'une
**frontière de processus** apporte ; ce que le cours demande en plus —
`--runtime=runsc --network=none --read-only` — est **construit et audité**,
pas exécuté. La différence est écrite partout où elle compte.

⚠️ **Un processus séparé partage le NOYAU.** Une faille du noyau, un appel
système mal filtré, un montage oublié : cette frontière-là tombe. C'est
exactement pourquoi le chapitre 4 existe.

## Démarrer

```bash
mvn test                      # 113 tests

mvn spring-boot:run           # le runner sur http://localhost:8080

mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre1Menace
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre2Runner
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre3Piloter
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre4Durcir
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre5Integrer
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre6Evasion
```

À essayer à la main, sur le runner qui tourne :

```bash
# une solution honnete
curl -s localhost:8080/execute -H 'Content-Type: application/json' \
  -d '{"langage":"jobportal-script","code":"ecrire bonjour\nsomme 21 21"}'

# le meme appel, hostile : le bac a sable rend 77
curl -s localhost:8080/execute -H 'Content-Type: application/json' \
  -d '{"langage":"jobportal-script","code":"secret jobportal.cle-api"}'

# le contrat refuse AVANT d'executer : 400, en quelques millisecondes
curl -s -o /dev/null -w '%{http_code}\n' localhost:8080/execute \
  -H 'Content-Type: application/json' -d '{"langage":"","code":"ecrire x"}'

# et la boucle : le runner rend la main, le processus meurt
curl -s localhost:8080/execute -H 'Content-Type: application/json' \
  -d '{"langage":"jobportal-script","code":"boucle"}'
```

## Le petit langage du candidat

Huit verbes, et les trois marqués sont la menace :

```
   ecrire <texte>            ecrit sur la sortie standard
   somme <a> <b>             ecrit la somme
   sortie <n>                termine avec ce code
   lire_fichier <chemin>     ⚠️ LIT LE DISQUE DE L'HOTE
   connexion <hote> <port>   ⚠️ OUVRE UNE CONNEXION SORTANTE
   secret <nom>              ⚠️ LIT UNE PROPRIETE DE L'APPLICATION
   boucle                    boucle sans fin
   memoire <mo>              alloue jusqu'a saturation
```

Pourquoi un langage inventé plutôt que Python : parce que le cours n'enseigne
pas Python. Il enseigne **où** le code d'un inconnu s'exécute, et ce qu'il
peut y faire. Huit verbes suffisent à poser la question, et ils ont une
propriété qu'aucun vrai langage n'a — on peut les faire tourner **des deux
côtés de la frontière** et comparer.

## Ce que les six chapitres mesurent

| | Mesure |
|---|---|
| 1 | Le code du candidat, dans la JVM de l'application, **lit le secret** (chaîne identique à `application.properties`), **lit `pom.xml`**, et **ouvre une connexion** avec l'identité du serveur. Puis pourquoi aucun réglage ne rattrape cela — demandé à la JVM qui tourne, pas affirmé : `System.setSecurityManager(…)` lève **`UnsupportedOperationException`** et `getSecurityManager()` rend `null`. Le `SecurityManager` n'est pas *supprimé*, il est **désactivé** (JEP 486, Java 24), et c'est l'aveu qu'une politique interne au processus ne résiste pas à du code qui s'exécute dans ce processus. |
| 2 | Le contrat étroit : `400 BAD_REQUEST` sur code vide, langage vide, code de 27 000 caractères — **avant** qu'une ligne ne s'exécute. Et la sortie hostile du candidat (`<script>alert('vole')</script>`) qui revient telle quelle, puis échappée. |
| 3 | La ligne de commande réelle du bac à sable, drapeau par drapeau. Le délai **dur** : `boucle` → tuée à 3 017 ms, code −1. La mémoire bornée : `memoire 400` sous `-Xmx48m` → **code 3, et zéro message** (`-XX:+ExitOnOutOfMemoryError` ne laisse rien sortir). La sortie plafonnée à 10 000 caractères. |
| 4 | Le même audit sur deux lignes `docker run` : **11 portes fermées** contre **10 ouvertes sur 11**. Puis le `Dockerfile` **du dépôt**, lu sur le disque : 5 règles satisfaites, contre 0 sur 5 pour celui des tutoriels. Et la sortie du bac à sable, hostile elle aussi. |
| 5 | Quatre soumissions notées de bout en bout à travers HTTP. La solution qui boucle coûte **4 014 ms** ; la mise en file rend la main en **2 ms** — un rapport de **×2 007**. Et la solution curieuse est **écartée, pas notée** : une décision métier, pas un score. |
| 6 | La batterie d'évasion des deux côtés : **5 attaques non bloquées sur 6** dans la JVM, **1 sur 6** en processus séparé. Puis les quatre compteurs, et un disjoncteur qui s'ouvre au troisième échec de **démarrage** — jamais sur un code candidat fautif. |

## Quatre décisions que ce projet prend, et pourquoi

1. **Le script ne voyage pas dans `argv`.** La ligne `docker run` durcie porte
   `--interactive` et s'arrête à l'image : le code arrive sur l'**entrée
   standard**. Passé en argument, il serait lisible dans `ps`, dans
   `docker inspect` et dans les journaux du démon — c'est-à-dire archivé, sur
   un nœud partagé. `CommandeDocker.argvAvecLeScriptEnClair` garde l'autre
   forme comme pièce à conviction.

2. **L'environnement de l'enfant est vidé** (`environment().clear()`). Une
   ligne, et un jeton d'API cesse de traverser sans qu'on y pense.

3. **Le délai dur est une entrée déclarée**, lue dans
   `jobportal.sandbox.delai-en-secondes`. Son *principe* n'est pas
   négociable — sans lui, une seule soumission fige le runner — mais sa
   *valeur* est une décision : cinq secondes pour un test technique,
   davantage pour une compilation, et plus encore sur un nœud froid, où le
   seul démarrage d'une JVM enfant peut coûter plusieurs secondes. Codée en
   dur, elle oblige à redéployer pour la changer — et c'est ainsi qu'on
   finit par la retirer.

4. **Le chemin de classes de l'enfant est minimal** : le seul répertoire qui
   contient `Executeur` et le langage. Ni Spring, ni pilote de base, ni
   bibliothèque métier — moins il y a de classes dans un bac à sable, moins
   il y a de *gadgets* à enchaîner. C'est aussi ce qui rend le lancement
   fiable sous Maven, où `java.class.path` pointe sur un jar d'amorçage.

## Cinq pièges rencontrés en construisant ce projet

1. **le chapitre 6 ne se terminait pas.** `ExecutionDansLaJvm` n'a aucune
   borne : la soumission `boucle` n'a jamais rendu la main, et le chapitre
   tournait indéfiniment. La correction n'est pas de borner cette classe —
   ce serait effacer la démonstration — mais de lui imposer une limite **de
   l'extérieur**, sur un fil démon, et d'imprimer « JAMAIS RENDUE » ;
2. **`java.class.path` est un jar d'amorçage sous surefire.** Le bac à sable
   lancé depuis un test ne trouvait pas `Executeur`. Il faut passer par
   `getProtectionDomain().getCodeSource()` ;
3. **`TestRestTemplate` et `@LocalServerPort` ont changé de module** en Spring
   Boot 4 : ni l'un ni l'autre n'est dans `spring-boot-starter-test`. Le port
   se lit dans l'`Environment` (`local.server.port`), ce que fait déjà le banc
   d'essai des chapitres ;
4. **un refus de privilège ressortait en « délai dépassé »** au premier
   appel, une fois sur deux : le tout premier démarrage d'une JVM enfant,
   caches froids, dépassait les 5 s du délai. Le correctif n'est pas de
   desserrer une assertion — c'est de sortir le délai du code et d'en faire
   une propriété, puis de payer le démarrage à froid une fois, hors
   assertion ;
5. **un `ENTRYPOINT` sur six lignes passait pour absent** à l'audit d'image :
   il faut recoller les continuations `\` avant de lire un Dockerfile, sinon
   l'audit dit le contraire de la vérité.

## L'exercice

Neuf zones à compléter, réparties sur les chapitres qui les expliquent :

```
runner/DemandeExecution        borner le contrat d'entree              (ch. 2)
runner/ExecutionEnBacASable    les drapeaux qui bornent l'enfant       (ch. 3)
runner/ExecutionEnBacASable    le delai DUR, et le tueur               (ch. 3)
runner/ExecutionEnBacASable    vider l'environnement de l'enfant       (ch. 3)
bac/CommandeDocker             fermer les onze portes                  (ch. 4)
securite/Sortie                l'echappement, esperluette en premier   (ch. 4)
application/ServiceEvaluation  comparer des chaines, et rien d'autre   (ch. 5)
observabilite/Mesures          les trois compteurs d'incident          (ch. 6)
observabilite/Disjoncteur      ouvrir le circuit, et sur quoi          (ch. 6)
```

Sur la branche `depart`, le squelette **compile et démarre** : le contrat
accepte tout, le bac à sable ne tue plus, l'échappement rend le texte tel
quel, et le disjoncteur appelle toujours. Tout marche, et tout est faux —
**38 tests le disent**, et `LangageTest` reste vert, parce que le langage,
lui, n'est pas l'exercice.

## Les pièces à conviction

```
runner/ExecutionDansLaJvm      l'execution qui lit vos secrets
langage/Politique#toutPermis   ce qu'un moteur de script accorde : tout
bac/CommandeDocker#naive       la ligne des tutoriels, 10 portes sur 11
CommandeDocker#argvAvecLeScriptEnClair   le script publie dans `ps`
```

**Ne pas les réparer** : des tests vérifient que les défauts sont toujours là.
`EvasionTest#laMemeBatterieDansLaJvm` affirme que trois attaques **passent**
dans la JVM de l'application ; le jour où il échouerait, le cours aurait perdu
sa démonstration.

## Ce que le projet ne prouve pas

- **aucun conteneur n'est lancé.** Ce qui est audité est une *configuration* —
  une ligne de commande et un Dockerfile — pas un comportement. C'est un
  contrôle de type *linter* : il attrape l'**oubli**, jamais la vulnérabilité.
  L'oubli reste, de très loin, le cas le plus fréquent ;
- **gVisor n'est pas mesuré.** Un processus séparé partage le noyau ; le noyau
  en espace utilisateur de gVisor est précisément ce que ce projet ne peut pas
  démontrer hors ligne ;
- **un bac à sable n'est sûr que patché.** Les évasions publiées de gVisor, de
  `runc` et des hyperviseurs se corrigent par des mises à jour, pas par des
  réglages. Rien ici ne le remplace ;
- les **durées** (3 017 ms, 4 014 ms, ×2 007) sont mesurées sur *cette*
  machine : l'ordre de grandeur tient, les millisecondes non ;
- le langage du candidat est **minuscule**. Chaque vrai runtime ajoute sa
  propre surface — un `import os` en Python, un `Runtime.exec` en Java, un
  `child_process` en Node — et l'exercice est à refaire à chaque langage
  accepté.
