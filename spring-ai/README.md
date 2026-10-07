# Spring AI — projet de départ du cours

Une application Spring Boot 4 qui utilise Spring AI **sans aucun fournisseur**.
Pas de clé, pas de réseau, pas de facture : le `ChatModel` est écrit à la main
et **retient tout ce que `ChatClient` lui envoie**. Les six chapitres
n'expliquent donc pas ce que Spring AI fabrique — ils l'impriment.

```
   Le prompt complet, tel que le modele l'a recu :
      [USER] Analyse ce CV : Sept ans en Java, dont trois sur Spring Boot…
      Your response should be in JSON format.
      Do not include any explanations, only provide a RFC8259 compliant
      JSON response following this format without deviation.
      Here is the JSON Schema instance your output must adhere to:
      ```{ "type" : "object", "properties" : { "score" : { "type" :
      "integer", "format" : "int32" } … } }```

   votre message              Analyse ce CV : {cv}
   ce qui est parti           936 caracteres
```

Et la mesure qui fait mal, au chapitre 3 :

```
   document      similarite    verite terrain
   ────────────  ────────────  ────────────────────────
   OFF-033       0.2182        dit NON au teletravail
   OFF-021       0.1250        en propose vraiment
   OFF-047       0.1147        en propose vraiment
```

La question portait sur le télétravail. Le document le **mieux** classé est
celui qui annonce « Aucun télétravail ». Il part dans le prompt, le modèle le
cite, et la réponse est fausse — avec ses sources.

---

## Ce que ce projet est, et n'est pas

| | Réalité |
|---|---|
| `ChatClient`, les advisors, `entity()` | ceux de Spring AI 2.0.1, sans une ligne de contournement. Le prompt affiché est celui qu'un vrai fournisseur recevrait. |
| le **modèle** | écrit à la main (`ModeleFactice implements ChatModel`). Il répond selon des règles, et **retient chaque prompt**. |
| les **embeddings** | un sac de mots, 256 dimensions, déterministe et hors ligne. La similarité cosinus est réelle ; la sémantique, non. |
| la **base vectorielle** | le `SimpleVectorStore` de Spring AI — même interface `VectorStore` qu'un pgvector, même recherche. |
| les **outils** | de vraies méthodes `@Tool`, dont Spring AI déduit le schéma JSON, et qu'il **exécute** dans un aller-retour complet. |
| les **métriques** | un vrai `SimpleMeterRegistry` : `gen_ai.client.token.usage` avec ses étiquettes, produit par les gestionnaires d'observation de Spring AI. |

⚠️ **Ce projet ne mesure jamais la qualité d'une réponse.** Le modèle ne
comprend rien. Ce qui est vérifié, c'est ce que Spring AI **construit,
envoie et reconstruit** — ce qui est précisément ce qu'un cours sur Spring AI
enseigne. Juger une réponse demande un vrai fournisseur ; le chapitre 6 le dit
et montre pourquoi c'est une autre discipline.

⚠️ **Le modèle d'embeddings ne rapprochera jamais « salaire » de
« rémunération ».** C'est justement ce qu'on achète en payant des embeddings.
Tout le reste du chapitre 3 — la normalisation, le classement, le contexte
injecté, l'effet du découpage — reste vrai.

## Démarrer

```bash
mvn test                      # 61 tests

mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre1ChatClient
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre2Structure
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre3Rag
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre4Outils
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre5Multimodal
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre6Production
```

Aucune variable d'environnement, aucune clé, aucun conteneur. Si un chapitre
demande un réseau, c'est un bug.

Pour brancher un **vrai** fournisseur, il suffit d'ajouter son starter et une
propriété — le code des six chapitres ne change pas d'une ligne :

```xml
<dependency>
  <groupId>org.springframework.ai</groupId>
  <artifactId>spring-ai-starter-model-openai</artifactId>
</dependency>
```

```properties
spring.ai.openai.api-key=${OPENAI_API_KEY}
spring.ai.openai.chat.options.model=gpt-4.1-mini
```

…et le `ChatModel` du contexte devient celui d'OpenAI. C'est la démonstration
du chapitre 1, faite pour de bon.

## Ce que les six chapitres mesurent

| | Mesure |
|---|---|
| 1 | Les **deux** messages que `defaultSystem()` envoie contre **un** sans lui. Le même code d'appel sur deux modèles. Et le flux : 33 morceaux, recollés à l'identique — après avoir dû **écrire** `stream()`, car `ChatModel` ne se rabat pas sur `call()`, il lève `UnsupportedOperationException`. |
| 2 | Ce que `entity()` colle au prompt : **936 caractères** pour une phrase de 19, dont un schéma JSON complet. Un modèle qui n'obéit pas → `StreamReadException`. Le piège à accolades : deux formes passent, la troisième **échoue**, parce qu'un seul `param()` suffit à rendre le texte comme un template. Et `ChatMemory` : 1 → 3 → 5 messages, 35 → 107 → 190 caractères. |
| 3 | Un vecteur de norme 1. Le classement qui remonte **l'offre sans télétravail** en tête. Le prompt enrichi, en entier : **×16** la question. Un seuil trop haut → la question est **remplacée** par un refus poli, sans une erreur. Et le découpage : cinq morceaux battent un gros document. |
| 4 | Le **schéma JSON** déduit de chaque `@Tool`, imprimé. Les outils qui ne sont **pas dans le prompt** (15 caractères avec ou sans). L'aller-retour complet : **2 appels au modèle pour 1 appel d'outil**. Un outil d'écriture qui refuse. Un outil inventé → `IllegalStateException`. Le plafond `maxTotalToolCalls` : 3 appels d'outil, mais **9 appels au modèle**. |
| 5 | Une image qui n'apparaît **pas** dans le texte du prompt. Le poids réel, et le **+33 %** du base64. Un modèle qui ne sait pas voir : réponse identique, **aucune erreur**. Et la transcription, dont le compilateur **prouve** qu'elle n'est pas un `ChatModel`. |
| 6 | `gen_ai.client.token.usage` avec `input`, `output`, `total`. Le prompt du **juge**, imprimé. `isPass()` qui refuse « Yes, absolument. ». Trois réessais que le compteur de jetons **ne voit pas**. Et l'absence de délai d'attente dans `ChatClient`. |

## Cinq pièges rencontrés en construisant ce projet

Chacun est documenté à l'endroit où il mord :

1. **`QuestionAnswerAdvisor` n'existe plus** en Spring AI 2 : l'API du RAG a
   été refondue en `RetrievalAugmentationAdvisor` + `DocumentRetriever`. Tout
   l'exemple de RAG que vous trouverez en ligne date d'avant ;
2. **`ChatModel` déclare `getOptions()` ET `getDefaultOptions()`** — et c'est
   la première que `ChatClient` appelle. Redéfinir l'autre, celle que toute la
   documentation 1.x nomme, fait **disparaître les outils** sans un mot ;
3. **des options qui n'implémentent pas `ToolCallingChatOptions`** perdent de
   la même façon tout ce qui passe par `.tools(...)` ;
4. **`stream()` n'a pas d'implémentation par défaut** : un `ChatModel` écrit à
   la main lève `UnsupportedOperationException` au premier `.stream()` ;
5. **un contexte RAG vide ne lève rien** : le `ContextualQueryAugmenter`
   remplace silencieusement votre question par « dis que tu ne sais pas ».

Aucun des cinq ne produit d'erreur au démarrage. C'est ce qui les rend longs à
trouver — et c'est pourquoi ils sont écrits ici.

## L'exercice

Six zones à compléter, réparties sur les chapitres qui les expliquent :

```
modele/ModeleFactice#stream        decouper la reponse mot a mot      (ch. 1)
rag/ModeleDEmbeddings#vecteur      normaliser le vecteur              (ch. 3)
rag/ModeleDEmbeddings#similarite   la similarite cosinus              (ch. 3)
rag/Corpus#baseVectorielle         indexer les documents              (ch. 3)
modele/ModeleFactice#getOptions    des options qui portent les outils (ch. 4)
outils/OutilsDOffres#postuler      verifier avant d'ecrire            (ch. 4)
```

Sur la branche `depart`, le squelette **compile et tourne** : le flux rend un
seul morceau, les vecteurs ne sont pas normalisés, la base est vide, les
outils sont perdus en silence et l'outil d'écriture accepte n'importe quelle
référence. Tout marche, et tout est faux — ce sont les tests qui le disent.

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

- **aucun fournisseur n'est appelé** : ce qui est mesuré est ce que Spring AI
  construit et envoie, jamais ce qu'un modèle répond ;
- **aucun serveur MCP n'est démarré** : le chapitre 4 montre que `@Tool` est
  la même annotation des deux côtés, et que MCP change le *transport* — et
  avec lui tout le calcul de sécurité ;
- **aucune image n'est lue, aucun son n'est transcrit** : le chapitre 5
  mesure la plomberie — les types, les octets, l'encodage — et le dit ;
- **les tailles d'image sont fabriquées** : deux PNG engendrés avec le grain
  d'un vrai scan. L'ordre de grandeur tient, le chiffre exact dépend du
  document ;
- **le coût est compté en jetons, jamais en euros** : le prix est chez le
  fournisseur, il change avec le modèle et avec le temps.
