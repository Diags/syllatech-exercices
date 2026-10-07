# Docker + Kubernetes — projet de départ du cours **Docker + Kubernetes**

Le **cache de couches** d'un `docker build`, le **système de fichiers empilé**
d'une image, l'**ordre de démarrage** d'un Compose et la **boucle de
réconciliation** d'un cluster Kubernetes — écrits en Python, et appliqués à de
vrais `Dockerfile`, `compose.yaml`, manifestes et chart Helm.

La mesure centrale tient en un caractère. On ajoute un retour à la ligne à un
`README.md` qui n'a aucune influence sur le binaire produit :

```
                      1er build     sans rien   +1 car. README   +1 ligne de code
Dockerfile.naif      6 c / 145s      0 c / 0s      5 c / 114s        5 c / 114s
Dockerfile           8 c / 153s      0 c / 0s        0 c / 0s          3 c /  39s
```

Cinq couches reconstruites contre zéro, et **114 secondes contre zéro** — le
téléchargement complet des dépendances Maven, pour une ligne de documentation.
La seule différence entre les deux fichiers est l'ordre des instructions.

Et les deux images que ces fichiers produisent :

```
somme des calques (ce qui est transféré) :  842,2 Mo   contre  233,0 Mo
vue fusionnée (ce que `ls` montre)       :  583,2 Mo
écart                                    :  259,0 Mo
```

Ces 259 Mo sont ce que deux `RUN rm` ont cru supprimer. Ils partent sur chaque
nœud, à chaque déploiement. Le `.env` effacé de la même façon est toujours
là — le chapitre 1 l'extrait de son calque et **imprime le mot de passe**.

---

## Ce que ce projet est, et n'est pas

⚠️ **Aucun démon Docker, aucun cluster.** Un cours ne peut pas les exiger. Ce
projet **réimplémente les algorithmes** et les fait tourner sur des artefacts
réels.

Ce qui est réel :

| | Réalité |
|---|---|
| le **Dockerfile** | `jobportal/dockerfile.py` — lexeur + arbre. Continuations `\`, commentaires intercalés, `ARG` avant `FROM`, multi-stage, `COPY --from=`, formes *exec* et *shell*. `contexte/Dockerfile` est du Dockerfile que Docker accepterait tel quel. |
| le **`.dockerignore`** | les règles de Go, pas celles de `.gitignore` : `*` ne traverse pas un `/`, `**` le traverse, et c'est le **dernier** motif qui correspond qui l'emporte. |
| le **cache de couches** | `jobportal/construction.py` — clé = (clé parente, texte de l'instruction, empreinte des fichiers copiés). C'est l'algorithme de Docker, et il est exact. |
| l'**image** | `jobportal/image.py` — calques, marques de suppression, vue fusionnée. `fouiller()` fait ce que `docker save` + `tar -x` feraient. |
| le **YAML** | `jobportal/yaml_minimal.py` — écrit à la main pour pouvoir montrer ce qu'une bibliothèque escamote : l'indentation est la syntaxe, et `yes` n'est pas un booléen ici. |
| **Kubernetes** | `jobportal/kubernetes.py` — quatre contrôleurs qui tournent en boucle : Deployment, ReplicaSet, ordonnanceur, kubelet. `requests` place, `limits` tue, la readiness décide du trafic. |
| **Helm** | `jobportal/helm.py` — fusion profonde des valeurs, `{{ }}` avec `if`/`range`/`include`/`required`, et un historique de manifestes **rendus**. |

### Les entrées déclarées, et pourquoi elles le sont

Trois choses ne peuvent pas être mesurées hors ligne, et sont donc **déclarées
en un seul endroit**, en clair :

- `jobportal/effets.py` — ce que coûte chaque `RUN` (secondes, fichiers
  produits). Relevé une fois sur une construction réelle ;
- `contexte/poids.json` — le poids réel des fichiers qu'un dépôt Git ne peut
  pas transporter (un jar de 47 Mo, un `.git` de 184 Mo) ;
- `REGISTRE` dans `jobportal/kubernetes.py` et `x-simulation` dans les
  `compose.yaml` — en combien de temps une image devient prête, et combien de
  mémoire elle consomme vraiment.

**Ce que le projet mesure n'est aucun de ces chiffres.** Il mesure ce qu'il
en *déduit* : quelles couches sont reconstruites, combien de pods restent
prêts, quelles connexions sont refusées. Changez une durée dans `effets.py` et
les secondes affichées changent ; **le nombre de couches, lui, ne bouge pas**.

## Démarrer

```bash
uv sync --extra dev
uv run --extra dev pytest -q        # 113 tests

uv run python chapitres/chapitre_1_docker.py       # ce qu'une image transporte
uv run python chapitres/chapitre_2_dockerfile.py   # 0 couche contre 5
uv run python chapitres/chapitre_3_compose.py      # la connexion refusée
uv run python chapitres/chapitre_4_kubernetes.py   # la boucle, tick par tick
uv run python chapitres/chapitre_5_avance.py       # 3 pods prêts contre 0
uv run python chapitres/chapitre_6_production.py   # `latest` ne déploie rien
```

Les modules s'utilisent aussi seuls, sur **vos** fichiers :

```python
from jobportal import construction, contexte, dockerfile

ctx = contexte.charger("mon-projet")
resultat = construction.construire(
    dockerfile.analyser_fichier("mon-projet/Dockerfile"), ctx)
print("\n".join(construction.rendre(resultat)))
```

## Ce que les six chapitres mesurent

| | Mesure |
|---|---|
| 1 | Une image de 3 calques, et une de 842 Mo dont **259 Mo de poids mort**. Le `.env` invisible dans le conteneur, **extrait et imprimé** depuis son calque. `FROM openjdk` vaut `openjdk:latest`. Forme *shell* → **le PID 1 est `/bin/sh`**, qui ne transmet pas le SIGTERM. Et `EXPOSE` ne publie rien : seul `ports:` ouvre 5432 sur la machine. |
| 2 | Le contexte : **13 fichiers et 231 Mo** sans `.dockerignore`, **10 fichiers et 5 ko** avec. Puis la mesure phare — 1 caractère dans le README → **5 couches et 114 s** contre **0 et 0 s**. Enfin, 6 contrôles sur les deux fichiers, **6 écarts**. |
| 3 | `depends_on: [db]` → l'application se connecte à **t=4,2 s**, la base n'accepte qu'à **t=9,0 s** : **1 connexion refusée**. Avec `condition: service_healthy` : **0**. Et le healthcheck passe au vert **un intervalle après** la disponibilité réelle, jamais à l'instant même. |
| 4 | `kubectl apply` → **0 pod créé**. Les contrôleurs en créent 3 en 7 ticks. Un pod supprimé revient — sous un **autre nom**. Un Service au sélecteur `jobporta` : **0 endpoint, aucune erreur**. Et un second `apply` : **0 pod recréé**. |
| 5 | 4 répliques à 2 Gi sur 2 nœuds de 3,6 Gi allouables → **2 `Pending` pour toujours**. Une image qui dépasse sa limite → **OOMKilled**, pod `Running`, compteur de redémarrages. Sans readiness, les pods entrent dans le Service **dès le premier tick**. `maxSurge 1/maxUnavailable 0` → **minimum 3 pods prêts** ; `0/3` → **minimum 0**. Et une image cassée : **`ProgressDeadlineExceeded`, et le service n'a jamais cessé de répondre**. |
| 6 | La fusion des valeurs sur trois couches. `required` fait échouer le **rendu** ; sans lui, `image: registry/jobportal:` part vers le cluster. Puis : deux `helm upgrade` avec `latest` → **manifestes identiques, 1 ReplicaSet, aucun pod redémarré** ; avec le SHA → **2 ReplicaSets**. Et `rollback` rejoue les manifestes **rendus**, pas le chart. |

## Les pièces à conviction

```
contexte/Dockerfile.naif                    six défauts, et il construit
pile/compose.naif.yaml                      quatre défauts, et elle démarre
manifestes/deployment-sans-sondes.yaml      trois absences, et 3/3 pods « prêts »
manifestes/service-mauvais-selecteur.yaml   une lettre, et zéro endpoint
manifestes/deployment-gourmand.yaml         des requests que le cluster ne peut pas tenir
```

**Ne pas les réparer** : `tests/test_a_corriger.py` vérifie que chaque défaut
est toujours là, et les chapitres mesurent dessus. Un vérificateur qui n'a
jamais vu de fichier incorrect ne prouve rien.

## Ce que le projet ne prouve pas

- **aucune image n'est construite, aucun conteneur ne démarre** : ce qui est
  vérifié est l'**algorithme du cache**, pas un `docker build` ;
- **le constructeur modélisé est le classique**, pas BuildKit : les étapes
  s'exécutent dans l'ordre, toutes, y compris celles dont l'image finale ne
  dépend pas. BuildKit les parallélise et saute les inutiles — l'algorithme du
  cache, lui, est le même ;
- **il n'y a ni réseau, ni registre, ni volumes persistants, ni `kube-proxy`** :
  les *endpoints* d'un Service sont les pods prêts dont les étiquettes
  correspondent, et rien de plus ;
- **ni `StatefulSet`, ni `Ingress`, ni HPA, ni éviction** : les classes de
  qualité de service sont calculées et affichées, l'éviction n'est pas
  simulée ;
- **le moteur de gabarits n'est pas celui de Helm** (Go `text/template` +
  Sprig) : il couvre ce que le cours utilise, et les écarts de rendu sur les
  cas limites ne sont pas mesurés ;
- **le lecteur YAML est un sous-ensemble** : ni ancres, ni références, ni
  étiquettes. Chacune lève en nommant la ligne plutôt que de produire un
  document faux.
