# LangChain4j — projet de départ du cours

Une application Spring Boot 4 qui utilise LangChain4j 1.20 **sans aucun
fournisseur**. Pas de clé, pas de réseau, pas de facture : le `ChatModel` est
écrit à la main et **retient chaque `ChatRequest`** que le proxy d'`AiServices`
fabrique. Les six chapitres n'expliquent donc pas ce que LangChain4j
construit — ils l'impriment.

C'est d'ailleurs exactement ce que le chapitre 6 du cours recommande pour les
tests. Ici, on en a fait la base de tout le projet.

```
   Le prompt complet, tel que le modele l'a recu :
      [SYSTEM] Tu analyses des CV pour un portail d'emploi.
      [USER] Analyse ce CV pour le poste developpeuse Java senior :
      Sept ans en Java, dont trois sur Spring Boot…
      You must answer strictly in the following JSON format: {
      "competences": (type: array of string),
      "score": (type: integer),
      "resume": (type: string)
      }
```

Et la mesure qui surprend le plus — le **même** code Java, le **même** record,
deux prompts différents :

```
   ce que le modele declare      prompt envoye     schema
   ────────────────────────────  ────────────────  ──────────────
   rien                          418 caracteres    dans le texte
   RESPONSE_FORMAT_JSON_SCHEMA   268 caracteres    dans la requete
```

---

## Ce que ce projet est, et n'est pas

| | Réalité |
|---|---|
| `AiServices`, les annotations, le RAG, les outils | ceux de LangChain4j 1.20.0, sans une ligne de contournement. Le prompt affiché est celui qu'un vrai fournisseur recevrait. |
| le **modèle** | écrit à la main (`ModeleFactice implements ChatModel`). Il répond selon des règles, et **retient chaque requête**. |
| les **embeddings** | un sac de mots, 256 dimensions, déterministe et hors ligne. La similarité cosinus est réelle ; la sémantique, non. |
| le **magasin vectoriel** | l'`InMemoryEmbeddingStore` de LangChain4j — même interface `EmbeddingStore` qu'un pgvector, même recherche. |
| les **outils** | de vraies méthodes `@Tool`, dont LangChain4j déduit la `ToolSpecification`, et qu'il **exécute** dans un aller-retour complet. |
| le **streaming** | un vrai `StreamingChatModel` et un vrai `TokenStream`, avec un temps jusqu'au premier jeton mesuré. |
| l'**observabilité** | un vrai `ChatModelListener` : requêtes, réponses, erreurs, jetons, latence. |

⚠️ **Ce projet ne mesure jamais la qualité d'une réponse.** Le modèle ne
comprend rien. Ce qui est vérifié, c'est ce que LangChain4j **construit,
envoie et reconstruit** — ce qui est précisément ce qu'un cours sur
LangChain4j enseigne. Juger une réponse demande un vrai fournisseur ; le
chapitre 6 le dit et montre pourquoi c'est une autre discipline.

⚠️ **Pas de `langchain4j-spring-boot-starter` non plus.** À ce jour il reste
publié en `-betaNN` et il est compilé contre Spring Boot 3.5, alors que ce
projet tourne sur Spring Boot 4. Rien n'en dépend ici : `AiServices.create(…)`
et `AiServices.builder(…)` font tout ce que montre le cours, et l'annotation
`@AiService` n'ajoute que le câblage Spring.

## Démarrer

```bash
mvn test                      # 59 tests

mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre1Demarrer
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre2AiServices
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre3Rag
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre4Outils
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre5Memoire
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre6Production
```

Aucune variable d'environnement, aucune clé, aucun conteneur. Si un chapitre
demande un réseau, c'est un bug.

Pour brancher un **vrai** fournisseur, il suffit d'ajouter son module et de
construire le modèle — le code des six chapitres ne change pas d'une ligne :

```xml
<dependency>
  <groupId>dev.langchain4j</groupId>
  <artifactId>langchain4j-open-ai</artifactId>
  <version>1.20.0</version>
</dependency>
```

```java
ChatModel modele = OpenAiChatModel.builder()
        .apiKey(System.getenv("OPENAI_API_KEY"))
        .modelName("gpt-4.1-mini")
        .build();
```

…et `AiServices.create(AssistantCarriere.class, modele)` devient un assistant
réel. C'est la démonstration du chapitre 1, faite pour de bon.

## Ce que les six chapitres mesurent

| | Mesure |
|---|---|
| 1 | Le proxy, prouvé : `java.lang.reflect.Proxy.isProxyClass(...)` rend **vrai**, et aucune classe n'a été écrite. Les **deux** messages que `@SystemMessage` produit. Et la méthode à redéfinir : `doChat`, jamais `chat`. |
| 2 | Ce qu'un type de retour `record` ajoute : **418 caractères** de prompt contre 268 selon ce que le modèle déclare savoir faire. Sans capacité, le schéma est écrit en toutes lettres ; avec `RESPONSE_FORMAT_JSON_SCHEMA`, il voyage dans la requête. Un modèle qui n'obéit pas → `OutputParsingException`. |
| 3 | `recursive(300, 30)` : 8 morceaux, et un chevauchement **de zéro**. Il faut 120 caractères pour en obtenir 92. L'ingestion vectorise 8 textes une fois, une question en vectorise **un**. Le prompt enrichi fait **×16** la question. Et `minScore(0.9)` rend le RAG muet, sans une erreur. |
| 4 | Les trois `ToolSpecification` déduites, imprimées. Le prompt **inchangé** (141 caractères avec ou sans outils). Un aller-retour = **2 appels au modèle pour 1 appel d'outil**. Un outil inventé → exception. Et le plafond par défaut : **100 appels d'outils, 101 appels au modèle** pour une question. |
| 5 | La mémoire : 2 → 4 → 6 messages en trois tours. Une fenêtre de 4 contre 20 : 2 736 contre 4 128 caractères cumulés. `@MemoryId` : deux conversations, **zéro fuite**. Le streaming : **126 ms** jusqu'au premier jeton contre 261 ms au total. Et une image de 628 ko qui en pèse 837 une fois encodée. |
| 6 | L'écouteur voit 3 requêtes sur 3 — et **0 sur 3** quand le modèle redéfinit `chat` au lieu de `doChat`. Trois réessais dont le compteur de jetons n'en voit qu'un. Et l'absence totale de délai d'attente dans `AiServices`. |

## Six pièges rencontrés en construisant ce projet

Chacun est documenté à l'endroit où il mord :

1. **`chat` contre `doChat`** — `chat(ChatRequest)` est l'enveloppe qui
   prévient les `ChatModelListener`. La redéfinir, comme le fait l'exemple de
   modèle bouchonné du chapitre 6 du cours, **désactive toute
   l'observabilité**, sans erreur et sans message ;
2. **`recursive(300, 30)` ne chevauche rien** — le chevauchement est rempli
   avec des phrases entières, et aucune phrase de vraie prose ne tient en 30
   caractères. La ligne que tout le monde recopie produit donc zéro ;
3. **`maxSequentialToolsInvocations` vaut 100 par défaut** — un modèle qui
   boucle exécute cent fois votre outil avant que LangChain4j ne s'arrête ;
4. **`supportedCapabilities()` réécrit le prompt** — une seule capacité
   déclarée déplace le schéma JSON du texte vers la requête. Changer de modèle
   change donc le prompt sans qu'on ait touché à une ligne ;
5. **`UserMessage.singleText()` lève** dès qu'un message porte une image : un
   message utilisateur est une **liste** de contenus, pas une chaîne ;
6. **un seul `@MemoryId` rend le `ChatMemoryProvider` obligatoire** pour tout
   le service — et l'échec arrive à la construction du proxy, pas au premier
   appel. C'est le bon comportement, mais il contamine les méthodes voisines.

Aucun des six ne produit d'erreur au démarrage. C'est ce qui les rend longs à
trouver — et c'est pourquoi ils sont écrits ici.

## L'exercice

Six zones à compléter, réparties sur les chapitres qui les expliquent :

```
service/AssistantCarriere          le @SystemMessage qui pose le cadre  (ch. 1)
rag/ModeleDEmbeddings#vecteur      normaliser le vecteur                (ch. 3)
rag/ModeleDEmbeddings#similarite   la similarite cosinus                (ch. 3)
rag/Corpus#magasin                 decouper, vectoriser, ranger         (ch. 3)
outils/OutilsDOffres#postuler      verifier avant d'ecrire              (ch. 4)
modele/ModeleFacticeEnFlux#doChat  diffuser mot a mot                   (ch. 5)
```

Sur la branche `depart`, le squelette **compile et tourne** : l'assistant n'a
plus de personnalité, les vecteurs ne sont pas normalisés, le magasin est
vide, l'outil d'écriture accepte n'importe quelle référence et le flux rend un
seul morceau. Tout marche, et tout est faux — ce sont les tests qui le disent.

## Les pièces à conviction

```
rag/ModeleDEmbeddings           le sac de mots qui classe l'offre SANS teletravail en tete
rag/Corpus                      OFF-033, « Aucun teletravail », et son voisinage trompeur
modele/ModeleFactice#conseils   une reponse ecrite d'avance, qui ne comprend rien
```

**Ne pas les réparer** : des tests vérifient que les défauts sont toujours là.
Le classement trompeur du chapitre 3 n'est pas un bug de ce projet — c'est la
limite du procédé, et un vrai modèle d'embeddings place lui aussi « avec
télétravail » et « sans télétravail » côte à côte.

## Ce que le projet ne prouve pas

- **aucun fournisseur n'est appelé** : ce qui est mesuré est ce que
  LangChain4j construit et envoie, jamais ce qu'un modèle répond ;
- **aucune image n'est lue** : le chapitre 5 mesure la plomberie — les types,
  les octets, l'encodage — et le dit ;
- **la taille d'image est fabriquée** : un PNG engendré avec le grain d'un
  vrai scan. L'ordre de grandeur tient, le chiffre exact dépend du document ;
- **les durées du streaming sont celles de cette machine** : le rapport entre
  premier jeton et réponse complète tient, les millisecondes non ;
- **le coût est compté en jetons, jamais en euros** : le prix est chez le
  fournisseur, il change avec le modèle et avec le temps.
