# AgentCore — projet de départ du cours **Amazon Bedrock AgentCore**

Le Runtime est **réel**. `BedrockAgentCoreApp` est une application Starlette :
on l'appelle en direct, sans port, sans compte AWS, et les réponses sont
celles que le runtime renverrait.

```
   force_ping_status("HealthyBusy")   Healthy
   force_ping_status(PingStatus.…)    HealthyBusy
```

La chaîne a la bonne valeur. `/ping` continue pourtant de répondre
« Healthy » : le handler lève un `AttributeError` qu'il journalise et avale.
L'orchestrateur n'apprend jamais que l'instance est saturée, et continue de
lui envoyer du trafic. Une panne de charge, causée par une annotation de type.

---

## Ce qui est réel, et ce qui ne l'est pas

**Réel** — `bedrock-agentcore` 1.23, `BedrockAgentCoreApp`, `@app.entrypoint`,
les routes `/invocations`, `/ping` et `/ws`, le format des réponses, le
streaming SSE, le `RequestContextFormatter` des journaux, et les signatures
de `code_session`, `browser_session` et `MemoryClient`, affichées telles
quelles par les chapitres.

**Substitué** — tout ce qui appelle AWS : les sandboxes, la Gateway et Memory
sont des doubles locaux qui gardent la forme de l'API. Le modèle aussi : le
cours écrit `Agent(model="…")`, ici `repondre()` est une fonction. Ce
qu'AgentCore emballe n'est pas le modèle, c'est **l'entrypoint**.

## Démarrer

```bash
uv sync --extra dev
uv run --extra dev pytest -q        # 34 tests

uv run python chapitres/chapitre_1_runtime.py        # le contrat, sept comportements
uv run python chapitres/chapitre_2_sandbox.py        # session, état, résultat seul
uv run python chapitres/chapitre_3_navigateur.py     # l'entrée non fiable
uv run python chapitres/chapitre_4_gateway.py        # 42 outils, et ce qu'ils coûtent
uv run python chapitres/chapitre_5_memoire.py        # session contre acteur
uv run python chapitres/chapitre_6_production.py     # journaux, fuites, vérificateur
```

Le vérificateur s'utilise sur **votre** agent :

```bash
uv run python outils/verifier_agent.py jobportal.agent              # 0 / 0
uv run python outils/verifier_agent.py jobportal.agent_a_corriger   # 3 erreurs
```

Et l'agent se sert pour de vrai : `uv run python -m jobportal.agent`
écoute sur `http://localhost:8080`, avec les mêmes routes qu'en production.

## La carte du projet

| Fichier | Ce qu'il contient | Chapitre |
| --- | --- | --- |
| `jobportal/agent.py` | le vrai `BedrockAgentCoreApp` et son entrypoint | 1, 6 |
| `jobportal/agent_a_corriger.py` | le même, avec cinq défauts qui se déploient | 6 |
| `jobportal/contrat.py` | exercer `/invocations` sans port ni AWS | tous |
| `jobportal/sandbox.py` | Code Interpreter : cycle, état, flux vers le modèle | 2 |
| `jobportal/navigateur.py` | Browser, et la page piégée | 3 |
| `jobportal/passerelle.py` | OpenAPI → outils MCP, et leur coût | 4 |
| `jobportal/memoire.py` | Memory par acteur, Identity par jeton | 5 |
| `outils/verifier_agent.py` | ce qui se déploie et ne marche pas | 6 |
| `tests/test_agentcore.py` | 34 tests, dont 9 sur le contrat du SDK | tous |

## Sept choses que le code enseigne

**Un entrypoint qui lève renvoie SON MESSAGE au client.** `{"error":
"connexion refusee vers postgres-prod.interne:5432"}`, avec un 500. Un nom
d'hôte interne, un chemin de fichier ou un fragment de requête SQL sort donc
du système. Attrapez vos exceptions dans l'entrypoint.

**Un retour non sérialisable est `str()`-ifié, sans erreur.** 200, et une
*chaîne* contenant un repr Python : `"{'quand': datetime.datetime(…)}"`. Le
consommateur qui lit `reponse["quand"]` reçoit un texte, et rien nulle part
ne signale la conversion.

**Deux `@app.entrypoint` : le second gagne, en silence.** Le SDK ne garde
qu'un handler, sous la clé `main`. Le premier décorateur n'a servi à rien.

**Un générateur change le transport.** Même décorateur, même route : rendre
un générateur fait passer le runtime en `text/event-stream`. Un `yield`
ajouté par mégarde change le contrat de votre API.

**La session vient d'un en-tête, pas du payload.**
`X-Amzn-Bedrock-AgentCore-Runtime-Session-Id`, posé par le runtime. En local
il est absent — d'où l'impression que l'isolation « ne marche pas ».

**Sans corps JSON, `/invocations` rend 400.** Le runtime exige un corps, même
vide (`{}`), et il en envoie lors de ses vérifications : votre entrypoint doit
rendre une erreur *métier*, pas lever.

**`force_ping_status` n'accepte pas la chaîne.** Voir l'encadré en haut.

## Le test qui ne s'est jamais déclenché

La première version du contrôle « l'entrypoint attrape-t-il ses exceptions ? »
était :

```python
if "try" not in inspect.getsource(fonction): …
```

Elle n'a **jamais** rien signalé. `getsource` inclut la ligne du décorateur,
et `@app.en`**`try`**`point` contient la sous-chaîne. Le test passait sur tous
les agents, y compris ceux sans le moindre bloc `try`.

Un test qui passe toujours vaut exactement un test absent, et il est plus
difficile à voir. La version livrée lit l'arbre syntaxique, où un `try` est un
nœud et pas trois lettres — et un test vérifie la distinction.

## Ce que ce projet ne prouve pas

- **Aucun appel AWS n'est fait.** Le Runtime est réel et exerçable ; les
  sandboxes, la Gateway et Memory sont des doubles locaux.
- **L'isolation d'AgentCore n'est pas mesurée** : un dictionnaire Python
  sépare des variables, pas des privilèges. Le cours *Sandboxing sécurisé*
  mesure, lui, ce qu'une vraie isolation arrête.
- La recherche de la Gateway utilise des **plongements vectoriels** ; celle
  d'ici compte les mots partagés, et rate donc les synonymes — le chapitre 4
  le montre sur « postes disponibles » contre « offres ».
- L'extraction de Memory utilise un **modèle** ; celle d'ici, des expressions
  régulières. Et elle n'invalide pas un fait qui change : le cours *Zep*
  traite exactement ce problème.
- La liste de motifs d'injection du chapitre 3 est là pour **montrer** le
  problème, pas pour le résoudre : deux reformulations sur quatre la passent.

## Pour aller plus loin

- Ajoutez un `yield` dans `invoke` et regardez le contrat de l'API changer.
- Enlevez le `try` de `jobportal/agent.py` et relancez `verifier_agent.py`.
- Écrivez un `operationId` sur `/stats/offres` et le doublon disparaît.
- Branchez un vrai modèle dans `jobportal/metier.py` : rien d'autre ne bouge.
- Sur un compte AWS : `agentcore configure && agentcore launch`, puis
  comparez le comportement de `/ping` et `/invocations` à celui d'ici.

---

Cours associé : [Amazon Bedrock AgentCore](https://syllatech.pages.dev/cours/agentcore)
· Formation syllatech — Diaguily SYLLA
