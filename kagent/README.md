# kagent — projet de départ du cours **kagent**

Les CRD, le contrôleur, le moteur d'exécution, la délégation A2A et les
traces OpenTelemetry de kagent — **écrits en clair**, et appliqués à de vrais
manifestes `kagent.dev/v1alpha2`.

La mesure centrale tient en deux « s » de trop. Ce manifeste est accepté :

```yaml
spec:
  type: Declarative
  declarative:
    systemMesssage: |          # ← trois s
      Tu diagnostiques les incidents du cluster.
      Verifie TOUJOURS les faits avec tes outils.
    maxIteration: 3            # ← sans s
```

```
Verdict de l'API  : admis, 2 champ(s) elague(s) en silence
Sortie de kubectl : « agent.kagent.dev/assistant-faute-de-frappe configured »

Ce que l'API a STOCKE :
   systemMessage    = ''
   maxIterations    = 10

NOM                        ACCEPTED   READY    RAISON
assistant-faute-de-frappe  True       True     Invocable
```

L'agent est `Accepted`, il est `Ready`, `kubectl apply` a répondu
« configured » — et il tourne **sans prompt système**. C'est le comportement
normal d'un schéma structurel : tout champ inconnu est **élagué** avant
stockage. La parade tient en une habitude : relire l'objet tel que l'API l'a
*stocké*, jamais le fichier qu'on a envoyé.

Et la mesure du grounding, sur la même question :

```
assistant-sans-outils   0 outil,  1 appel modèle,   76 jetons
   « une sonde de liveness trop stricte… »          ← plausible, et faux

assistant-sre           4 outils, 5 appels modèle, 1191 jetons
   « CrashLoopBackOff après 12 redémarrages ; son journal finit
     sur une OutOfMemoryError ; sa mémoire atteint 502 Mio »    ← observé
```

---

## Ce que ce projet est, et n'est pas

⚠️ **Aucun cluster, aucune clé d'API, aucun appel réseau.** Ce projet
**réimplémente ce que kagent fait** d'un manifeste, et le fait tourner sur
les fichiers de `manifestes/`.

Ce qui est réel :

| | Réalité |
|---|---|
| l'**admission** | `jobportal/crd.py` — un schéma structurel appliqué comme l'API le ferait : `type`, `required`, `enum`, `pattern`, bornes, **valeurs par défaut écrites**, **champs inconnus élagués**, et les règles transverses que Kubernetes écrit en CEL (`x-kubernetes-validations`). |
| la **réconciliation** | `jobportal/controleur.py` — le contrôleur ne crée rien, il constate : il résout les références et publie `Accepted` / `Ready` avec une raison. L'ordre d'application n'a aucune importance. |
| les **permissions** | `jobportal/outils.py` — chaque outil est d'un des deux côtés, **lecture** ou **action**. `toolNames` est nominative, et la vérification se fait à l'exécution, pas dans le prompt. |
| l'**A2A** | `jobportal/moteur.py` — un agent délégué est un outil comme un autre, avec détection de cycle et profondeur maximale. |
| les **traces** | `jobportal/traces.py` — `trace_id`, `parent`, attributs `gen_ai.*`. Le contexte se propage explicitement, et le chapitre 5 montre ce qui arrive quand il ne l'est pas. |
| le **contrat A2A / MCP** | `jobportal/integration.py` — les deux sens de circulation avec une application Spring, validés par le même moteur de schémas. |

### Les entrées déclarées, et pourquoi elles le sont

Quatre choses ne peuvent pas être mesurées hors ligne, et sont donc
**déclarées en un seul endroit**, en clair :

- `jobportal/schemas.py` — une transcription abrégée des CRD du cours. Un
  vrai `kubectl get crd agents.kagent.dev -o yaml` en rend plusieurs
  centaines de lignes ;
- `jobportal/outils.py` — le catalogue du `kagent-tool-server`, réduit aux
  outils dont le cours parle. Le classement lecture/action, lui, est une
  propriété de chaque outil ;
- `jobportal/cluster.py` — un cluster en panne, écrit comme un
  dictionnaire ;
- `ModeleFactice` dans `jobportal/moteur.py` — des règles de décision
  lisibles, et le coût déclaré d'un appel (jetons, millisecondes).

**Ce que le projet mesure n'est aucune de ces entrées.** Il mesure ce que le
mécanisme en fait : quels champs sont élagués, quelles conditions sont
publiées, quels outils sont refusés, combien d'appels une délégation coûte,
et combien de traces sortent d'une invocation.

## Démarrer

```bash
uv sync --extra dev
uv run --extra dev pytest -q        # 61 tests

uv run python chapitres/chapitre_1_demarrer.py       # apply ne démarre rien
uv run python chapitres/chapitre_2_crds.py           # ce que le schéma élague
uv run python chapitres/chapitre_3_outils.py         # le même agent, sans ses yeux
uv run python chapitres/chapitre_4_a2a.py            # ce que la délégation coûte
uv run python chapitres/chapitre_5_observabilite.py  # la trace qui se coupe en deux
uv run python chapitres/chapitre_6_spring.py         # un 200 qui rend du HTML
```

Le validateur s'utilise aussi seul, sur **vos** manifestes :

```python
from jobportal import crd, schemas, yaml_minimal

manifeste = yaml_minimal.charger_fichier("mon-agent.yaml")
verdict = crd.admettre(schemas.AGENT, manifeste)
print(verdict)                 # refusé ? élagué ? combien de champs ?
print(verdict.elagues)
```

## Ce que les six chapitres mesurent

| | Mesure |
|---|---|
| 1 | Après `apply` : l'objet existe et n'a **aucune condition**. Le contrôleur en pose deux. Puis l'agent appliqué **avant** son `ModelConfig` converge quand celui-ci arrive — sans qu'aucune commande soit rejouée. Et la mesure : un agent qui référence un `ModelConfig` inexistant est **créé sans erreur**, jamais `Ready`, et la seule trace est dans `status.conditions`. |
| 2 | Un manifeste hors `enum` est **refusé bruyamment** ; une faute de frappe est **élaguée en silence**. Mesuré : 2 champs retirés, `systemMessage = ''`, agent `Ready`. Et le schéma **ajoute** aussi — `maxIterations: 10`, `stream: false`, `namespace: kagent` — des valeurs qui appartiennent à la version de la CRD, pas à vos fichiers. |
| 3 | 5 outils de lecture, 4 d'action. Puis la mesure du grounding : **1 appel modèle et 76 jetons** pour une réponse inventée, **5 appels et 1 191 jetons** pour une réponse qui cite trois observations — un facteur 16 pour une réponse vérifiable. Puis : le prompt dit « ne supprime JAMAIS », le trousseau autorise, **le pod est supprimé**. Et un outil nommé qui n'existe pas ne fait échouer personne. |
| 4 | `type: Agent` met un agent dans le trousseau d'un autre, préfixé `a2a:`. Mesuré : **8 appels au modèle contre 5** — déléguer ne divise pas le travail, il l'ajoute. Ce qu'on achète : des permissions séparées. Puis le cycle `ping → pong → ping`, invisible dans les manifestes, **détecté à l'exécution**. |
| 5 | L'arbre des spans d'une invocation, avec les jetons d'entrée qui **croissent à chaque tour**. Puis la mesure : sans propagation du contexte, **mêmes spans, même réponse, même coût — et 3 traces au lieu d'1**. Rien n'échoue. Enfin, ce qui se teste sur un agent (les outils appelés) et ce qui ne se teste pas (la formulation). |
| 6 | Le contrat A2A dans les deux sens. Un champ ajouté côté Spring est **élagué** — la même leçon qu'au chapitre 2, de l'autre côté du fil. Puis le cas qui coûte une matinée : un **200 qui rend du HTML**, et l'exception qui parle de JSON. Enfin, l'agent appelle l'API Spring exposée en MCP, et la trace traverse les deux. |

## Les pièces à conviction

```
manifestes/agent-faute-de-frappe.yaml   deux « s » de trop, agent sans prompt
manifestes/agent-invalide.yaml          refusé — et c'est le contraste qui compte
manifestes/agent-sans-modele.yaml       créé sans erreur, jamais Ready
manifestes/agent-sans-outils.yaml       répond de mémoire, et se trompe
manifestes/agent-outil-fantome.yaml     un outil nommé que le serveur n'expose pas
manifestes/a2a-cyclique.yaml            deux manifestes valides, un cycle
```

**Ne pas les réparer** : `tests/test_crd.py` et `tests/test_moteur.py`
vérifient que chaque défaut est toujours là, et les chapitres mesurent
dessus.

## Ce que le projet ne prouve pas

- **aucun agent ne parle à un modèle** : `ModeleFactice` décide selon des
  règles déclarées, lisibles dans `jobportal/moteur.py`. Ce qui est mesuré
  est le comportement du MOTEUR autour de ces décisions, pas la qualité
  d'un LLM ;
- **le validateur est un sous-ensemble** : ni `oneOf`/`anyOf`/`allOf`, ni
  `$ref`, ni CEL dans sa généralité. Chacun **lève** plutôt que d'être
  ignoré ;
- **il n'y a ni RBAC, ni `Secret`, ni webhook d'admission, ni `finalizer`,
  ni `ownerReferences`** : le contrôleur publie un statut et rien d'autre ;
- **aucun HTTP n'est fait** : les deux sens de l'intégration Spring
  s'appellent en mémoire. Ce qui est mesuré est le **contrat**, pas le
  transport ;
- **les spans ne sont pas exportés** : il n'y a pas de collecteur OTLP. Le
  modèle de données (`trace_id`, `parent`, attributs `gen_ai.*`) est celui
  d'OpenTelemetry, la sérialisation ne l'est pas ;
- **les durées sont déclarées** (620 ms par appel de modèle, 45 ms par
  appel d'outil) : elles rendent les traces lisibles, elles ne mesurent
  rien.
