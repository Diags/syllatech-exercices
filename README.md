# Projets de départ — formations [syllatech](https://syllatech.pages.dev)

Un projet par cours. Chacun **tourne après un clone**, sans clé d'API.

## Deux branches

| Branche | Ce qu'elle contient | Pour quoi faire |
| --- | --- | --- |
| **`depart`** | Le squelette, avec des `# TODO` | **Commencez ici.** Les tests échouent : faites-les passer. |
| **`final`** | La solution complète | Pour vous débloquer, ou pour comparer une fois terminé. |

```bash
git clone -b depart https://github.com/Diags/syllatech-exercices.git
cd syllatech-exercices/mcp
uv sync --extra dev
uv run --extra dev pytest -q      # ça échoue : c'est l'énoncé
```

Une fois terminé, comparez :

```bash
git switch final
```

## Les projets

| Dossier | Cours | Ce qui est vérifié |
| --- | --- | --- |
| [`mcp/`](mcp) | [MCP : le Model Context Protocol](https://syllatech.pages.dev/cours/mcp) | 9 tests, serveur complet, 4 chapitres exécutables |
| [`langgraph/`](langgraph) | [LangGraph](https://syllatech.pages.dev/cours/langgraph) | 12 tests, 6 chapitres exécutables |
| [`cc-hooks/`](cc-hooks) | [Claude Code : les Hooks](https://syllatech.pages.dev/cours/cc-hooks) | 24 tests, hooks essayables sans session |
| [`prompt-engineering/`](prompt-engineering) | [Prompt & Context Engineering](https://syllatech.pages.dev/cours/prompt-engineering) | 13 tests, scores 17 → 83 % sur trois prompts |
| [`eval-llm/`](eval-llm) | [Évaluation & tests LLM](https://syllatech.pages.dev/cours/eval-llm) | 18 tests, ventilation par type de cas |
| [`rag-avance/`](rag-avance) | [RAG avancé](https://syllatech.pages.dev/cours/rag-avance) | 14 tests, BM25 et RRF écrits en entier |
| [`bases-vectorielles/`](bases-vectorielles) | [Bases vectorielles](https://syllatech.pages.dev/cours/bases-vectorielles) | 13 tests, index HNSW à la main, Qdrant en mémoire |
| [`cc-skills/`](cc-skills) | [Claude Code : les Skills](https://syllatech.pages.dev/cours/cc-skills) | 22 tests, coût de contexte mesuré, 3 skills à réparer |
| [`cc-agents/`](cc-agents) | [Claude Code : Sous-agents](https://syllatech.pages.dev/cours/cc-agents) | 30 tests, 6 chapitres, contexte divisé par 111 |
| [`cc-mcp/`](cc-mcp) | [Claude Code : MCP en pratique](https://syllatech.pages.dev/cours/cc-mcp) | 32 tests, serveur MCP réel + vérificateur de permissions |
| [`pydanticai/`](pydanticai) | [PydanticAI](https://syllatech.pages.dev/cours/pydanticai) | 27 tests, sortie validée, graphe à deux branches |
| [`agno/`](agno) | [Agno](https://syllatech.pages.dev/cours/agno) | 28 tests, mémoire, équipes, coût de contexte mesuré |
| [`securite-agents/`](securite-agents) | [Sécuriser les Agents IA](https://syllatech.pages.dev/cours/securite-agents) | 40 tests, 6 attaques OWASP rejouées contre 6 défenses |
| [`sandbox-securise/`](sandbox-securise) | [Sandboxing sécurisé](https://syllatech.pages.dev/cours/sandbox-securise) | 39 tests, 9 évasions contre 3 niveaux exécutés |
| [`crewai/`](crewai) | [CrewAI](https://syllatech.pages.dev/cours/crewai) | 28 tests, 5 équipages, un Flow à deux branches |
| [`autogen/`](autogen) | [Microsoft AutoGen](https://syllatech.pages.dev/cours/autogen) | 27 tests, 4 équipes, conditions d'arrêt mesurées |
| [`google-adk/`](google-adk) | [Google ADK](https://syllatech.pages.dev/cours/google-adk) | 27 tests, workflows et délégation mesurés |
| [`claude-code/`](claude-code) | [Claude Code Bootcamp](https://syllatech.pages.dev/cours/claude-code) | 33 tests, `.claude/` complet + vérificateur croisé |
| [`langfuse/`](langfuse) | [Langfuse](https://syllatech.pages.dev/cours/langfuse) | 21 tests, le vrai SDK branché sur un collecteur local |
| [`zep/`](zep) | [Zep](https://syllatech.pages.dev/cours/zep) | 20 tests, invalidation temporelle mesurée |
| [`cc-sandbox/`](cc-sandbox) | [Sandbox Claude Code](https://syllatech.pages.dev/cours/cc-sandbox) | 62 tests, 5 clés ignorées selon l'endroit du fichier |
| [`gateway-litellm/`](gateway-litellm) | [Passerelle IA](https://syllatech.pages.dev/cours/gateway-litellm) | 40 tests, bascules et coûts mesurés sur le vrai Router |
| [`agentcore/`](agentcore) | [Amazon Bedrock AgentCore](https://syllatech.pages.dev/cours/agentcore) | 34 tests, le contrat du runtime mesuré sans compte AWS |
| [`hermes-agent/`](hermes-agent) | [Hermes Agent](https://syllatech.pages.dev/cours/hermes-agent) | 36 tests, mémoire, skills et gardes du vrai paquet |
| [`agno-sandbox/`](agno-sandbox) | [Agno + Sandbox](https://syllatech.pages.dev/cours/agno-sandbox) | 34 tests, ce qu'un bac à sable n'arrête pas |
| [`n8n/`](n8n) | [n8n](https://syllatech.pages.dev/cours/n8n) | 23 tests, le signe « = » qui fait une expression |
| [`devcontainer/`](devcontainer) | [Dev Containers](https://syllatech.pages.dev/cours/devcontainer) | 195 tests, l'algorithme d'ordre des Features implanté d'après la spec |
| [`java-moderne/`](java-moderne) | [Java moderne](https://syllatech.pages.dev/cours/java-moderne) | 264 tests, `javac` appelé pendant l'exécution — le cours se compile lui-même |
| [`spring/`](spring) | [Spring & Spring Boot](https://syllatech.pages.dev/cours/spring) | 94 tests, une vraie application Spring Boot 4 démarrée et interrogée en HTTP |
| [`spring-security/`](spring-security) | [Spring Security](https://syllatech.pages.dev/cours/spring-security) | 82 tests, de vrais JWT RS256 et trois attaques soumises au décodeur |
| [`spring-ai/`](spring-ai) | [Spring AI](https://syllatech.pages.dev/cours/spring-ai) | 61 tests, aucun fournisseur — le `ChatModel` imprime ce que Spring AI construit |
| [`microservices-event/`](microservices-event) | [Microservices événementiels](https://syllatech.pages.dev/cours/microservices-event) | 37 tests, Axon sans infrastructure — CQRS, event sourcing et saga mesurés |
| [`microservices/`](microservices) | [Microservices avec Spring Cloud](https://syllatech.pages.dev/cours/microservices) | 35 tests, Eureka + Gateway + Resilience4j dans une JVM, Docker et k8s verifies |
| [`langchain4j/`](langchain4j) | [LangChain4j](https://syllatech.pages.dev/cours/langchain4j) | 59 tests, aucun fournisseur — et le schéma JSON change de place selon le modèle |
| [`terraform/`](terraform) | [Terraform](https://syllatech.pages.dev/cours/terraform) | 49 tests, un mini-Terraform en Python — `for_each` détruit 1 ressource, `count` en détruit 3 |
| [`docker-kubernetes/`](docker-kubernetes) | [Docker + Kubernetes](https://syllatech.pages.dev/cours/docker-kubernetes) | 113 tests, le cache de couches et la boucle de réconciliation écrits à la main |
| [`cloud/`](cloud) | [Architecture Cloud](https://syllatech.pages.dev/cours/cloud) | 92 tests, un moteur IAM, une composition de SLA et un modèle de coûts |
| [`kagent/`](kagent) | [kagent](https://syllatech.pages.dev/cours/kagent) | 61 tests, l'admission des CRD, la réconciliation, l'A2A et les traces |

Les autres arrivent. Un projet n'entre dans ce tableau qu'une fois **exécuté**,
pas une fois écrit.

## Ce que ces projets font, et que les vidéos ne peuvent pas faire

**Ils fournissent le chaînon manquant.** Un extrait de vidéo appelle
`db.query(...)` ou `llm.invoke(...)` sans jamais montrer ce qu'est `db` ou
`llm` — c'est normal dans un extrait, et c'est précisément ce qui empêche de
l'exécuter. Ici, ces pièces existent.

**Ils tournent sans clé d'API.** Les cours sur les agents enseignent une
*structure* — nœuds, outils, boucle — et elle s'observe très bien avec un
modèle factice. Poser une clé ne change qu'une ligne.

**Ils corrigent ce qui a vieilli.** Les bibliothèques bougent vite. Quand le
code d'une vidéo ne démarre plus, le projet utilise la forme actuelle **et
explique le changement** :

- `mcp` : le SDK Python est passé en 2.x, `FastMCP` s'appelle désormais `MCPServer` ;
- `cc-hooks` : la variable `$CLAUDE_FILE_PATHS`, qu'on lit dans beaucoup
  d'exemples, **n'existe pas** — le chemin du fichier arrive dans le JSON de
  l'entrée standard ;
- `langgraph` : `create_react_agent` est déprécié depuis la V1.

## ⚠️ Sous Windows : chemin court

Clonez dans un dossier à **chemin court** — `C:\dev\`, pas
`C:\Users\…\Documents\…\un\autre\niveau\`. Au-delà de 260 caractères,
l'installation échoue sur un fichier au nom à rallonge, avec un
`ModuleNotFoundError` qui ne dit rien de la vraie cause.

## Prérequis

- [uv](https://docs.astral.sh/uv/) et Python ≥ 3.11 pour les projets Python.
- **JDK 25 et Maven** pour les projets Java (`java-moderne`, `spring`,
  `spring-security`, `spring-ai`, `langchain4j`, `microservices-event`, `microservices`) :
  `mvn test` à la racine du dossier. Sans
  JDK 25 sous la main, `docker run --rm -v "$PWD:/w" -w /w
  maven:3-eclipse-temurin-25 mvn -B test` fait exactement la même chose —
  c'est ainsi qu'ils ont été vérifiés.

Les projets Java ont d'abord été livrés avec un avertissement : écrits avec
soin, mais **non compilés**, faute d'outillage sur la machine de rédaction.
Ce n'est plus le cas — chacun est compilé et testé dans
`maven:3-eclipse-temurin-25`, et le nombre de tests du tableau ci-dessus est
celui qui s'affiche.

---

Formations [syllatech](https://syllatech.pages.dev) — Diaguily SYLLA
