# Java moderne — projet de départ du cours **Java moderne**

Ce projet **appelle le compilateur pendant l'exécution**.

```
   var reaffecte avec un autre type       REFUSE
      incompatible types: java.lang.String cannot be converted to int
   un cas manquant, sans default          REFUSE
      the switch expression does not cover all possible input values
   le meme, avec un default               compile
```

Un cours de langage affirme sans arrêt des choses sur la **compilation** :
« le switch ne compilera pas si vous oubliez un cas », « `var` n'est pas du
typage dynamique ». Ces phrases ne se vérifient pas en exécutant un
programme — elles se vérifient en essayant d'en compiler un.

Le JDK embarque son propre compilateur. `fr.portail.mesure.Compilateur` lui
donne une source en mémoire et rend ses diagnostics, mot pour mot. Chaque
« le compilateur refusera » de ces six chapitres est donc **une mesure**.

La troisième ligne ci-dessus est l'avertissement du projet : ajouter un
`default` fait compiler le `switch` incomplet. Une hiérarchie scellée ne
protège que les `switch` qui n'en ont pas.

---

## Ce que ce projet est, et n'est pas

| | Réalité |
|---|---|
| les **refus du compilateur** | `javax.tools.ToolProvider.getSystemJavaCompiler()`, en mémoire, aucun fichier écrit. **Zéro transcription.** |
| les **comportements d'exécution** | mesurés avec des compteurs et un chronomètre, sur cette machine, à chaque lancement. |
| la **concurrence** | 5 000 tâches réellement lancées, sur un pool de plateforme puis sur des threads virtuels. |
| ce que **Java 25 rend définitif** | un fichier source *compact* écrit, compilé, chargé et exécuté dans le processus. |

⚠️ Ce n'est **pas** un banc d'essai. `fr.portail.mesure.Chrono` échauffe et
prend la médiane, mais pour un chiffre défendable il existe JMH. Ce que ce
projet mesure sont des écarts d'un facteur 30 à 300 ; un écart de 10 % obtenu
ici ne vaudrait rien, et la classe le dit dans son en-tête.

**Aucune dépendance en dehors de JUnit.** Un cours de langage qui a besoin
d'une bibliothèque pour montrer le langage a raté quelque chose.

## Démarrer

Il faut un **JDK 25** (pas un JRE : sans compilateur, la moitié des mesures
s'annoncent indisponibles) et Maven.

```bash
mvn test                                  # 264 tests

mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre1Fondamentaux
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre2Objets
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre3Collections
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre4Streams
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre5Concurrence
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre6Java25
```

Sans JDK 25 sous la main, tout se joue dans un conteneur :

```bash
docker run --rm -v "$PWD:/w" -w /w maven:3-eclipse-temurin-25 mvn -q test
```

Le chapitre 5 prend une dizaine de secondes : il lance vraiment les tâches.

## Ce que les six chapitres mesurent

| | Mesure |
|---|---|
| 1 | Le cache d'`Integer` va de **-128 à 127** : `==` rend `true` puis `false` selon la valeur comparée. `Double` n'a aucun cache, ce qui rend le bug plus visible — c'est `Integer` qui est piégeux, parce qu'il fait marcher le mauvais code. Et `final` devant une variable change le résultat de `==` sur une concaténation. |
| 2 | Un `addAll` de 3 éléments, un compteur à **6**. La même classe écrite par composition compte 3. Puis : un `switch` à qui il manque un cas est **refusé** — et le même, avec un `default`, **compile**. |
| 3 | Une clé rangée dans un `HashMap` puis modifiée devient introuvable — alors que `size()` vaut toujours 1 et que l'itération la voit. Remettre l'ancienne valeur la fait réapparaître. Et un `record` « immuable » subit exactement le même sort quand sa liste n'a pas été copiée. |
| 4 | `stream().peek(...).count()` fait traverser le pipeline par **zéro** élément. Un `filter` ajouté devant, et les six passent. Un flux **infini** se termine en 7 éléments. `sorted` avant `limit(3)` en consomme 100. |
| 5 | 5 000 tâches bloquantes : un pool de 16 contre un thread virtuel par tâche. 2 000 threads virtuels portés par 16 porteurs. Un compteur `recues++` qui perd **plus de 80 %** de ses incrémentations. Et `StructuredTaskScope`, **toujours en preview** dans une LTS. |
| 6 | Le compilateur refuse un cas garde placé après le cas général. Un fichier source **compact** (`void main()`, sans classe ni paquet) est écrit, compilé, chargé et exécuté — la preuve que JEP 512 est définitif ne vient pas d'une note de version. |

## L'exercice

Cinq zones à compléter, dans `fr.portail.tri` :

```
Selection.retenus         filtrer et trier le vivier
Selection.score           pondérer compétences et expérience
Selection.classement      trier, limiter, projeter
Selection.parCompetence   aplatir et compter, dans une TreeMap
Journal.decrire           un switch exhaustif, avec des motifs de record
```

Sur la branche `depart`, `SelectionTest` et `DomaineTest` échouent. Les faire
passer **est** l'énoncé.

Un détail qui vaut le détour : `Lea Marchand` arrive **troisième au
classement** et figure pourtant dans les motifs de refus. Le classement et le
verdict répondent à deux questions différentes, et les confondre est l'erreur
classique d'un moteur de tri de CV. `SelectionTest.leClassementNEstPasLeVerdict`
la fixe.

## Ce que le projet ne prouve pas

- ce n'est **pas** un banc d'essai : les durées donnent un ordre de grandeur,
  pas un chiffre publiable ;
- les mesures de concurrence dépendent du nombre de processeurs — le chapitre
  5 l'affiche en premier, exprès ;
- la course du compteur `recues++` **n'est pas garantie** de se produire :
  c'est une course, pas un théorème. Le test l'admet dans son message ;
- rien n'est mesuré sur une autre version de Java. Les tests de `Java25Test`
  décrivent le JDK qui les exécute, et disent quoi faire si l'un d'eux
  échoue après une mise à jour : la fonctionnalité est peut-être devenue
  définitive.

**Ne pas « réparer » `fr.portail.pieges`** : ces cinq classes sont la pièce à
conviction, et les tests mesurent dessus. Leur `package-info.java` dit ce que
chacune démontre.
