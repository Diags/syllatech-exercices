# AgentScope Java — projet de départ du cours

Le **vrai framework**, résolu depuis Maven Central
(`io.agentscope:agentscope-core:2.0.3`) : la boucle ReAct, le catalogue
d'outils, le moteur de permissions, le flux d'événements typés et la
persistance d'état sont les siens. Ce qui est écrit ici est le **modèle** —
déterministe, sans clé d'API — et c'est ce qui rend la boucle mesurable.

La mesure d'ouverture, sur la même question :

```
                              un appel au modele     un agent ReAct
   appels au modele           1                      3
   outils EXECUTES            0                      2
   references reelles citees  0 (aucune)             3
```

À gauche, le modèle a répondu — vite, et à côté : villes inventées, nombre de
candidatures inventé. À droite, la boucle a alterné réflexion, appel d'outil
et observation. **Trois appels au lieu d'un : c'est le prix de l'exactitude.**

Et la mesure qui fait mal, au chapitre 3 :

```
   REGLE    OFFRES    SUPPRIMEE   OUTILS EXEC.  EVENEMENT DU RUNTIME
   allow    5         ⚠️ OUI      1             TOOL_RESULT_END
   ask      6         non         0             REQUIRE_USER_CONFIRM
   deny     6         non         0             TOOL_RESULT_END

   Sous ASK, la reponse rendue a l'utilisateur est :

      « C'est fait. »

   ... et le catalogue compte toujours 6 offres, pour 0 outil(s) execute(s).
```

**L'agent annonce que c'est fait. Rien n'a été fait.** Et il n'a trompé
personne : le runtime a émis un `REQUIRE_USER_CONFIRM` puis a rendu la main —
il n'attend pas, il n'a aucun moyen d'attendre. `ASK` n'est pas une
suspension automatique, c'est un **protocole** : c'est à l'application de
s'arrêter là. Si votre interface ne sait pas traiter cet événement, la règle
à poser est `DENY`, pas `ASK`.

---

## Ce que ce projet est, et n'est pas

| | Réalité |
|---|---|
| le **framework** | `io.agentscope:agentscope-core:2.0.3`, depuis Maven Central. `ReActAgent`, `Toolkit`, `PermissionEngine`, `MiddlewareBase`, `JsonFileAgentStateStore` : tout vient de là. |
| les **outils** | de vraies méthodes Java annotées `@Tool` / `@ToolParam` dans une classe ordinaire. Le schéma JSON est engendré depuis les annotations. |
| les **permissions** | le vrai moteur. Les décisions du tableau ci-dessus sont les siennes ; le catalogue n'est pas appelé quand il refuse. |
| les **événements** | de vrais `AgentEvent` typés — 16 pour une boucle à un outil — lus dans le `Flux` et mappés sur du SSE. |
| l'**application** | un vrai Spring Boot 4 WebFlux, démarré sur un port libre et interrogé en HTTP puis en Server-Sent Events. |

⚠️ **Aucune clé d'API, aucun réseau.** Le `Model` est écrit ici : il suit un
*scénario*, tour par tour. Ce n'est pas une simplification pédagogique, c'est
la condition de la mesure — on ne compte rien avec un modèle non déterministe.

⚠️ **Le cours parle de `HarnessAgent`, la bibliothèque publie `ReActAgent`.**
Et `agent.call(…)` rend un `Mono<Msg>`, pas un flux d'événements : le flux
s'obtient par `streamEvents(…)`. Les concepts de la vidéo sont exacts ; les
noms ont bougé.

## Démarrer

```bash
mvn test                      # 58 tests

mvn spring-boot:run           # le portail sur http://localhost:8080

mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre1Agent
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre2Modeles
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre3Outils
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre4Sandbox
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre5MultiAgents
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre6Integrer
```

À essayer à la main, sur le portail qui tourne :

```bash
# la reponse complete
curl -s 'localhost:8080/assistant?q=Quelles+offres+Java&session=awa'

# le MEME agent, en Server-Sent Events : chaque evenement porte son TYPE
curl -N 'localhost:8080/assistant/flux?q=Quelles+offres+Java&session=awa'
```

## Ce que les six chapitres mesurent

| | Mesure |
|---|---|
| 1 | Un appel au modèle contre un agent : **1 appel / 0 outil / 0 référence réelle** contre **3 / 2 / 3**. Puis configuration et contexte : le **même objet agent**, deux sessions — la deuxième question d'awa arrive avec 4 messages d'historique, le premier message de bilal avec 2, et il ne voit rien de la conversation d'awa. |
| 2 | Le même agent avec deux « fournisseurs » : seule la ligne `.model(…)` change, et la réponse est identique. Puis la conversation, bloc par bloc : `TextBlock` → `ToolUseBlock` → `ToolResultBlock` → `TextBlock`. Puis **16 événements typés** pour une boucle à un outil. |
| 3 | Trois règles, une même intention : **5 offres** contre **6** et **6**. Puis « c'est fait » pour zéro outil exécuté. Puis la règle écrite `"*"` qui **ne s'applique jamais** — silencieusement. Puis les cinq modes tabulés : sous `DEFAULT`, même une **lecture** demande confirmation. |
| 4 | Le validateur de commandes : **4 refusées sur 10** — et les deux qui passent sont `cat /etc/passwd` et `cat ../../../etc/shadow`. Le filtre lit l'**exécutable**, jamais ses arguments. Et le contrôle de chemin fourni attrape `..` mais **pas** le chemin absolu. |
| 5 | Un monolithe (consigne de 161 caractères, 3 outils) contre une équipe (consigne de 45, **2 outils qui sont des agents**). Coût mesuré : **2 appels au modèle contre 6**. Puis le piège : enchaîner deux `.subAgent(…)` **en perd un**, sans erreur. Puis le middleware, qui voit 3 appels au modèle et 2 phases d'action. |
| 6 | Une vraie application Spring Boot : l'agent est un bean, le contrôleur ne connaît qu'un `ReActAgent`, et le `Flux` se mappe sur du SSE sans passerelle. Puis la mesure qui décide du déploiement : **4 messages survivent sur disque, 0 en mémoire**. |

## Quatre pièges rencontrés en construisant ce projet

Chacun est mesuré par un test, parce qu'aucun ne produit d'erreur :

1. **une règle de permission écrite `"*"` ne s'applique jamais.** Le contenu
   d'une règle est un *motif* comparé aux arguments de l'appel ; l'étoile n'y
   est pas un joker. La chaîne **vide** s'applique à tout. Une règle `DENY`
   écrite avec une étoile laisse l'outil au régime par défaut du mode — `ASK`
   sous `DEFAULT`, **`ALLOW` sous `BYPASS`** ;
2. **enchaîner deux `.subAgent(…)` sur une même `registration()` n'en garde
   qu'un.** Aucune exception, aucun log : l'orchestrateur démarre, il lui
   manque un spécialiste, et il répondra moins bien sans que rien ne le dise.
   Un `registration()…apply()` **par** sous-agent ;
3. **un `ToolUseBlock` doit porter ses arguments en JSON dans `content`,
   pas seulement dans `input`.** Un vrai fournisseur envoie les arguments
   d'outil en fragments de *texte*, que l'accumulateur recolle puis analyse.
   Sans cette chaîne, la validation refuse l'appel — « required property not
   found » — alors même que la `Map` est remplie ;
4. **le résultat d'un outil traverse la boucle sérialisé.** Une méthode qui
   rend une `String` arrive entre guillemets, retours à la ligne échappés.
   C'est logique — un bloc doit pouvoir porter un objet — mais cela se voit
   dans la réponse finale si on ne le décode pas.

## L'exercice

Sept zones à compléter, réparties sur les chapitres qui les expliquent :

```
outils/CatalogueOffres          declarer les outils et leur schema      (ch. 3)
modele/ModeleFactice            emettre un appel d'outil exploitable    (ch. 2)
securite/PolitiqueDuPortail     les regles de permission du portail     (ch. 3)
securite/PolitiqueDuPortail     le controle de chemin qui manque        (ch. 4)
observabilite/JournalDeMiddleware  intercepter la boucle sans fuite     (ch. 5)
web/ApplicationPortail          l'agent comme bean, avec son etat       (ch. 6)
web/AssistantControleur         le flux d'evenements en SSE             (ch. 6)
```

Sur la branche `depart`, le squelette **compile et démarre** : l'agent
répond, mais il n'a aucun outil, aucune règle, aucun journal, et son état
meurt avec le processus. Tout marche, et tout est faux — ce sont les tests
qui le disent.

## Les pièces à conviction

```
PermissionsTest#leJokerNeProtegeRien          la regle qui ne protege rien
PermissionsTest#sousAskLAgentRepondQuandMeme  « c'est fait » pour rien
MultiAgentsTest#enchainerLesSousAgentsEnPerdUn  le specialiste disparu
OutilsEtSandboxTest#leFiltreNeLitPasLesArguments  `cat /etc/passwd` passe
```

**Ne pas les « réparer »** : ces tests affirment ce que le framework
*laisse passer*. Ce ne sont pas des défauts à corriger dans ce projet — ce
sont les limites à connaître pour poser la couche suivante au bon endroit.

## Ce que le projet ne prouve pas

- **aucun fournisseur n'est appelé.** Ce qui est mesuré est la BOUCLE, pas la
  qualité d'un modèle. Basculer de fournisseur se fait en une ligne ; le
  **revalider** est un travail à part entière, et c'est lui qui coûte ;
- **le gain de latence du streaming n'est pas mesurable ici.** Le modèle de ce
  projet rend sa réponse d'un coup : ce que les chapitres prouvent est la
  *structure* du flux, pas le confort qu'il procure avec un vrai fournisseur ;
- **ni Docker ni Kubernetes ne sont lancés.** Le chapitre 4 mesure la couche
  la plus proche du code — le filtre de commandes et le cloisonnement des
  workspaces. Ce qu'une frontière de *processus* apporte par-dessus est mesuré
  dans le projet du cours « Java Spring + Sandbox » ;
- **l'état est persisté en fichiers JSON, pas en base.** La propriété
  démontrée est la bonne — l'état est *externe* au processus — mais
  PostgreSQL ou Redis apportent en plus la concurrence, les transactions et
  une durée de vie de session ;
- les **durées** sont mesurées sur *cette* machine : les ordres de grandeur
  tiennent, les millisecondes non.
