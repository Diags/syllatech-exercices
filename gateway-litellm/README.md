# Passerelle IA — projet de départ du cours **LiteLLM + Spring Cloud Gateway**

Le proxy est le **vrai** `litellm.Router`, monté depuis un vrai `config.yaml`.
Routage, bascule, comptage de jetons et calcul du coût sont ceux de la
bibliothèque, pas d'une imitation.

```
   num_retries = 0          338 ms   a repondu : gpt-4o-mini   bascule : True
   num_retries = 1         2747 ms   a repondu : gpt-4o-mini   bascule : True
   num_retries = 2         5283 ms   a repondu : gpt-4o-mini   bascule : True
```

Le `config.yaml` du cours porte `num_retries: 2`. Voilà ce que ces deux
réessais coûtent avant que la bascule ne se produise — sur un appel
interactif, la différence entre une hésitation et un abandon.

---

## Ce qui est réel, et ce qui ne l'est pas

**Réel :** `litellm` 1.100, le `Router`, les `fallbacks`, `num_retries`, la
table de prix, le mécanisme de `success_callback`, la résolution de
`os.environ/…`.

**Substitué :** la réponse du fournisseur, par le champ `mock_response` — un
champ **de litellm**. Le proxy fait tout son travail et rend la réponse
annoncée au lieu d'appeler le réseau. Retirer ces deux lignes et poser de
vraies clés suffit pour brancher le projet sur de vrais fournisseurs ; rien
d'autre ne change.

⚠️ **Le code Spring n'est pas compilé ici.** `jobportal/passerelle.py` écrit
les *mêmes étapes* que le filtre Spring du cours — valider le JWT, retrouver
la clé virtuelle de l'équipe, la substituer — en Python, pour qu'elles soient
exécutables et testables. Le Java du cours reste la référence.

## Démarrer

```bash
uv sync --extra dev
uv run --extra dev pytest -q        # 40 tests

uv run python chapitres/chapitre_1_architecture.py    # N×M, et ce que l'étoile coûte
uv run python chapitres/chapitre_2_litellm.py         # alias, traduction, prix
uv run python chapitres/chapitre_3_gateway.py         # le JWT, démonté      (instantané)
uv run python chapitres/chapitre_4_budgets.py         # bascules et budgets, mesurés
uv run python chapitres/chapitre_5_securite.py        # la chaîne, maillon par maillon (instantané)
uv run python chapitres/chapitre_6_observabilite.py   # ce qu'on croit mesurer
```

Les deux outils s'utilisent seuls, sur **votre** `config.yaml` :

```bash
uv run python outils/verifier_config.py config/a-corriger.yaml
uv run python outils/mesurer_doublon.py
```

⚠️ **`import litellm` prend une trentaine de secondes.** C'est le paquet, pas
ce projet : il charge sa table de prix et ses cent intégrations. En production
c'est du démarrage de conteneur, payé une fois — mais c'est à savoir avant de
régler une sonde de vivacité à 10 secondes. Les chapitres 3 et 5 ne le
chargent pas et sont instantanés.

## La carte du projet

| Fichier | Ce qu'il contient | Chapitre |
| --- | --- | --- |
| `jobportal/proxy.py` | le vrai `Router`, monté depuis le YAML | 1, 2, 4 |
| `jobportal/jetons.py` | un JWT écrit à la main, et ses quatre refus | 3, 5 |
| `jobportal/passerelle.py` | le trajet complet et ses codes HTTP | 3, 4, 5 |
| `jobportal/budgets.py` | clés virtuelles, budgets, imputation | 4 |
| `jobportal/observabilite.py` | un `CustomLogger` réel + le tableau par équipe | 6 |
| `outils/verifier_config.py` | ce qui démarre et ne marche pas | 6 |
| `outils/mesurer_doublon.py` | la mesure qui exige un processus neuf | 6 |
| `tests/test_passerelle.py` | 40 tests, dont 8 sur le vrai Router | tous |

## Six choses que le code enseigne

**Un fallback vers un alias non déclaré est accepté — et muet.** Le `Router`
ne dit rien à la construction. Au premier appel, la bascule échoue et
l'erreur rendue au client est celle du **modèle principal**. On cherche donc
la panne du mauvais côté, parfois longtemps.

**Le même alias déclaré deux fois n'écrase rien.** On croit remplacer la
première entrée ; LiteLLM y voit deux *déploiements* et répartit la charge
entre eux (`simple-shuffle` par défaut). Une part des requêtes part vers
l'autre modèle, avec l'autre prix et l'autre qualité.

**Un modèle absent de la table de prix coûte 0,00 $, pour toujours.** Rien
n'est levé, rien n'est journalisé : le modèle disparaît du tableau de bord des
coûts. Et il y a **deux** façons de coûter zéro — `ollama/llama3` est dans la
table *avec des zéros explicites*, ce qui est exact pour un modèle
auto-hébergé. Seule l'absence est un défaut.

**Tester `modele in model_cost` est juste au démarrage et faux ensuite.**
Après un seul appel vers un modèle inconnu, litellm **insère** sa clé dans
`model_cost` — avec un dictionnaire **vide**. Le vérificateur exige donc un
champ de tarif, jamais la seule présence de la clé. C'est un test.

**Réassigner `litellm.callbacks` n'est pas un remplacement.** litellm en
dérive des listes internes qu'il ne reconstruit pas. Mesuré dans un processus
neuf : la première sonde reçoit **2** mesures, la seconde **0**. Selon le
moment, l'autre cas se produit aussi — les deux sondes reçoivent tout, et le
coût affiché double. `brancher()` purge les listes dérivées.

**Le budget se vérifie avant l'appel et s'impute après.** Entre les deux, le
coût n'est pas connu : le dernier appel autorisé peut donc dépasser le plafond
de son propre coût. C'est un choix — refuser sur une estimation refuserait des
appels légitimes — mais il impose une marge, et `depassement_possible()` la
chiffre.

## Le piège d'observabilité le plus discret

```python
async def async_log_success_event(self, kwargs, response_obj,
                                  start_time, end_time)   # les 4 noms exacts
```

litellm appelle ces quatre paramètres **par mot-clé**. Une signature qui les
nomme autrement lève un `TypeError`… que litellm rattrape et journalise en
`[Non-Blocking] Exception occurred while success logging`. L'application
répond 200 à tout, et le tableau de bord reste à zéro. Rencontré en écrivant
ce projet.

## Ce que ce projet ne prouve pas

- **Aucun appel réseau n'est fait.** Les latences mesurées sont celles du
  routage, de la bascule et des réessais — pas celles d'un fournisseur.
- Le code **Spring** du cours n'est pas compilé : cette machine n'a pas de
  JDK, et `jobportal/passerelle.py` en écrit les étapes, pas le framework.
- Ni PostgreSQL, ni Redis, ni Prometheus, ni Langfuse ne tournent. Les budgets
  sont en mémoire, et la sonde garde ses mesures dans une liste.
- La `master_key`, les clés virtuelles et la rotation par coffre-fort sont
  **modélisées**, pas fournies par un vrai proxy LiteLLM.

## Pour aller plus loin

- Retirez les `mock_response`, posez vos clés, et tout le reste marche tel quel.
- Passez `num_retries` à 5 dans `config/passerelle.yaml` et relancez le
  chapitre 4 : la bascule devient plus lente que la panne.
- Ajoutez un modèle maison sans `model_info` et regardez son coût disparaître.
- Cassez volontairement la signature d'`async_log_success_event` : tout
  continue de marcher, et plus rien ne se mesure.

---

Cours associé : [Passerelle IA : LiteLLM + Spring Cloud Gateway](https://syllatech.pages.dev/cours/gateway-litellm)
· Formation syllatech — Diaguily SYLLA
