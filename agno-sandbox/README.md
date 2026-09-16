# Évaluateur de code — projet de départ du cours **Agno + Sandbox**

Un agent qui fait tourner le code d'un candidat, et les quatre problèmes
distincts que cela pose. La matrice du chapitre 3 :

```
   soumission                  famille     en local    sous-processus  bride
   lecture-de-fichier          machine     REUSSIE     REUSSIE         arretee
   variables-d-environnement   machine     REUSSIE     REUSSIE         arretee
   capacite-reseau             machine     REUSSIE     REUSSIE         REUSSIE
   consigne-dans-la-sortie     verdict     REUSSIE     REUSSIE         REUSSIE
```

Les deux dernières lignes sont le sujet du projet. **Aucun niveau
d'isolation ne change quoi que ce soit à la famille « verdict »** : ces
soumissions ne touchent à rien. Elles écrivent du texte sur leur sortie
standard — ce que fait tout programme honnête — et ce texte remonte jusqu'au
modèle qui note le candidat.

---

## Ce qui est réel, et ce qui ne l'est pas

**Réel** — `agno` 3.0.9, `agno.agent.Agent`, `output_schema`, la validation
Pydantic du verdict, `tool_call_limit`, les trois exécuteurs, et les mesures
de temps.

**Substitué** — le MODÈLE. `jobportal/modele.py` est un `agno.models.base.Model`
écrit à la main (six méthodes abstraites) qui applique une règle visible.

⚠️ **Ce projet ne mesure donc pas si un vrai LLM se laisserait prendre.** Un
modèle jouet qui obéit prouverait seulement qu'on l'a programmé pour. Ce qui
est mesuré est **ce qui entre dans son contexte** — une grandeur qui ne
dépend d'aucun modèle, et la seule qu'une garde puisse changer.

## Le paramètre s'appelle `output_schema`

```
>>> Agent(response_model=Verdict)
TypeError: Agent.__init__() got an unexpected keyword argument
'response_model'. Did you mean 'reasoning_model'?
```

La suggestion est le piège : `reasoning_model` **existe**. L'accepter donne un
agent qui démarre, ne type plus rien, et facture un modèle de raisonnement.
Une erreur qui propose une correction plausible et fausse coûte plus cher
qu'une erreur sèche. La page du cours a été corrigée.

## Démarrer

```bash
uv sync --extra dev
uv run --extra dev pytest -q        # 34 tests

uv run python chapitres/chapitre_1_agent.py         # ce que PythonTools fait vraiment
uv run python chapitres/chapitre_2_sortie_typee.py  # ce que le schéma accepte et refuse
uv run python chapitres/chapitre_3_sandbox.py       # la matrice : 13 soumissions × 3 niveaux
uv run python chapitres/chapitre_4_guardrails.py    # ce que le modèle lit, et combien
uv run python chapitres/chapitre_5_integration.py   # la frontière du job portal
uv run python chapitres/chapitre_6_production.py    # coûts, journaux, pannes
```

Les deux matrices s'obtiennent seules :

```bash
uv run python outils/mesurer.py            # corpus × niveaux d'exécution
uv run python outils/mesurer.py --gardes   # corpus × gardes de prompt
```

⚠️ **Le corpus est inoffensif par construction.** Les soumissions « machine »
lisent, comptent et impriment ; aucune n'efface, n'envoie rien à l'extérieur
ni ne modifie quoi que ce soit. La soumission « réseau » ouvre une socket
vers un port fermé de `127.0.0.1` — elle vérifie une capacité, elle n'appelle
personne.

## La carte du projet

| Fichier | Ce qu'il contient | Chapitre |
| --- | --- | --- |
| `jobportal/soumissions.py` | 13 soumissions, 4 familles, une preuve par attaque | 1 |
| `jobportal/verdict.py` | le schéma Pydantic et ses bornes | 2 |
| `jobportal/executeurs.py` | les trois niveaux d'exécution | 3 |
| `jobportal/gardes.py` | les trois gardes de prompt | 4 |
| `jobportal/modele.py` | un `Model` agno écrit à la main | 2, 4 |
| `jobportal/evaluateur.py` | le vrai `Agent`, avec `output_schema` | 2, 4 |
| `jobportal/service.py` | la frontière : plafond, file de revue, lot | 5 |
| `outils/mesurer.py` | les deux matrices | 3, 4 |
| `tests/test_evaluateur.py` | 34 tests, dont 5 sur le vrai `Agent` | tous |

## Six choses que le code enseigne

**Quatre problèmes, pas un.** Le code touche la machine (bac à sable) ; le
code ne rend pas la main (délai, donc processus) ; le code parle au modèle
(garde de prompt) ; le modèle répond n'importe quoi (sortie typée). Les quatre
sont indépendants, et une solution parfaite à l'un ne fait rien pour les
autres.

**`PythonTools` fait `exec(code, self.safe_globals, self.safe_locals)`.**
« safe » ne qualifie que le dictionnaire de noms. Le code s'exécute dans votre
processus : 8 attaques sur 8 réussissent, et les deux soumissions qui ne
rendent pas la main ne sont même pas testables — elles bloqueraient le
processus de mesure.

**Ce qu'on peut écrire en Python portable arrête 4 attaques sur 10.** Ni le
réseau, ni le lancement de processus, ni l'évasion par `__subclasses__` ne se
ferment depuis Python. La suite est un conteneur, et le chapitre 3 le dit au
lieu de prétendre le contraire.

**Délimiter ne réduit PAS la surface.** Mesuré : 324 signes hostiles
atteignent le modèle sans garde, et **324 avec la délimitation**. Délimiter
agit sur une autre grandeur — la probabilité qu'un modèle s'y laisse prendre —
qui ne se mesure pas ici. Seul le résumé ramène la surface à zéro.

**Une délimitation qu'on peut refermer soi-même n'en est pas une.** Si le
candidat écrit le délimiteur de fin, il sort du cadre. `Delimitee` le retire
de la sortie avant d'encadrer ; sans cette ligne, la garde rassure sans
protéger, ce qui est pire que pas de garde.

**Le résumé est la seule garde dont la taille ne dépend pas du candidat.**
Sur 5 000 lignes de sortie : ~13 500 jetons pour les deux premières gardes,
46 pour la troisième. Un facteur 293, décidé par l'attaquant ou par vous.

## Le détail qui a résisté

`Bride` vide l'environnement. Mesuré dans le sous-processus : `PATH`,
`SYSTEMROOT`… et `PYTHONUSERBASE`, qu'aucune ligne du projet n'a mise — c'est
`uv run` qui la remet. **Vider l'environnement ne vaut que ce que le lanceur y
remet ensuite.** Le test vérifie donc la propriété qui compte (aucune variable
sensible) plutôt qu'un compte exact, qui dépendrait de qui lance le projet.

## Ce que ce projet ne prouve pas

- **Aucun vrai modèle n'est appelé.** Les scores rendus n'ont de sens que les
  uns par rapport aux autres.
- La question « un vrai LLM obéirait-il à la consigne cachée ? » n'est donc
  **pas** tranchée ici.
- `Bride` n'est pas un bac à sable : c'est ce qu'on peut écrire en Python
  portable, et le chapitre 3 mesure son insuffisance.
- Les coûts en jetons sont des ordres de grandeur (quatre signes par jeton),
  pas des factures.
- Le service du chapitre 5 n'écoute sur aucun port : il exerce les étapes,
  et la section 6 liste ce qui manque pour en faire un vrai service.

## Pour aller plus loin

- Ajoutez une soumission au corpus avec sa `PREUVE`, relancez
  `outils/mesurer.py` : la matrice s'étend toute seule.
- Écrivez un quatrième exécuteur qui lance Docker, et regardez les trois
  lignes restantes du chapitre 3 passer à « arretee ».
- Retirez le `retire les délimiteurs` de `Delimitee` : un test tombe, et
  l'évasion redevient possible.
- Branchez un vrai modèle dans `jobportal/modele.py` : rien d'autre ne bouge,
  et la colonne « signes hostiles » garde exactement le même sens.

---

Cours associé : [Agno + Sandbox : agent qui exécute du code](https://syllatech.pages.dev/cours/agno-sandbox)
· Formation syllatech — Diaguily SYLLA
