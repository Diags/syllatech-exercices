# Job portal — projet de départ du cours **Langfuse : l'observabilité de vos LLM**

Le **vrai SDK Langfuse**, sans serveur, sans clé, sans réseau — et 21 tests.

```
   verification-eligibilite  span
     repondre                  span
       rechercher_contexte       span
       generer                   generation
```

Le span du haut n'a **aucun décorateur Langfuse** : c'est de l'OpenTelemetry
ordinaire. Il apparaît pourtant dans la trace, avec les autres en dessous.

---

## Ce projet n'est pas une simulation

Langfuse 3.x est bâti sur OpenTelemetry. `@observe()` ouvre un span OTEL, et ce
qui part vers le serveur, ce sont **ces spans tels quels**. Le SDK accepte un
`tracer_provider` :

```python
Langfuse(..., tracer_provider=le_notre)
```

On en fournit donc un avec un exportateur **local**, et l'on reçoit exactement
ce que Langfuse recevrait : noms, attributs, durées, parenté. Le SDK est réel.
Seule la destination change.

**Ce qui ne marche pas sans serveur :** `get_prompt()`, `get_dataset()`,
`create_score()` interrogent l'API. Les chapitres 4 et 5 montrent la forme
exacte **et** implémentent l'équivalent local, en le disant à chaque fois.

## Démarrer

```bash
uv sync --extra dev
uv run --extra dev pytest -q        # 21 tests

uv run python chapitres/chapitre_1_demarrer.py      # le premier trace
uv run python chapitres/chapitre_2_traces.py        # le défaut qui coûte un mois
uv run python chapitres/chapitre_3_integrations.py  # trois chemins, un format
uv run python chapitres/chapitre_4_prompts.py       # déplacer un label
uv run python chapitres/chapitre_5_evaluation.py    # 80 % → 100 %
uv run python chapitres/chapitre_6_production.py    # ce que ça coûte vraiment
```

## La carte du projet

| Fichier | Ce qu'il contient | Chapitre |
| --- | --- | --- |
| `jobportal/collecteur.py` | Le vrai SDK, branché sur un exportateur local | 1, 2, 3 |
| `jobportal/assistant.py` | Un assistant observé de bout en bout | 1, 2 |
| `jobportal/prompts.py` | Versions, labels, compilation — l'équivalent local | 4 |
| `jobportal/evaluation.py` | Trois sortes de score, et un dataset | 5 |
| `tests/test_observabilite.py` | 21 tests, sans réseau | tous |

## Cinq choses que le code enseigne

**Oublier `as_type="generation"` ne se voit pas dans la trace.** L'étape
apparaît bien — au même endroit, avec la même durée. Elle n'entre simplement
pas dans le tableau de bord des coûts : ni modèle, ni tokens, ni euros. On
s'en aperçoit en comparant la facture du fournisseur au total affiché par
Langfuse, souvent un mois plus tard. Un test le démontre.

**`user_id` et `session_id` ne servent pas à la trace : ils servent à la
retrouver.** Sans eux, un tableau de bord montre des traces sans savoir de qui
elles viennent — et l'on ne peut pas répondre à *« qu'est-il arrivé à cet
utilisateur hier ? »*, qui est la question la plus fréquente.

**Un seul `TracerProvider` par processus, et ce n'est pas un détail.** OTEL
refuse de remplacer celui qui est déjà posé : il journalise *« Overriding of
current TracerProvider is not allowed »* et garde le premier. Un second
collecteur ne reçoit alors **rien**, pendant que les spans continuent d'aller
vers le premier. Le symptôme — « aucune trace » — n'a aucun rapport avec la
cause. C'est exactement ce qui arrive dans une suite de tests naïve, et le
fichier le documente là où ça s'est produit.

**Déplacer un label ne redéploie rien — et c'est aussi le danger.** Un prompt
qui change sans passer par la revue de code change le comportement de la
production sans aucune trace dans git. Ce qui doit rester dans git : le nom du
prompt, les variables attendues, un prompt de repli, et le label utilisé.

**Une variable oubliée dans un prompt reste littérale.** `compile()` sans
argument laisse `{{portail}}` tel quel, et c'est ce texte qui part au modèle.
Aucune erreur — juste un prompt qui parle d'une variable au lieu de sa valeur.

## Sur le juge LLM, une précaution

`score_juge()` est **simulé par des heuristiques vérifiables**, et le fichier
le dit en toutes lettres. Un vrai juge est un modèle : il coûte, il varie d'une
exécution à l'autre, et il faut le **calibrer contre des notes humaines** avant
de lui faire confiance. Un juge non calibré donne un chiffre rassurant et faux
— et un chiffre faux est pire que pas de chiffre.

Les heuristiques tiennent sa place pour que la mécanique — échantillonnage,
moyenne, seuil d'alerte — soit mesurable sans clé. Elles ne sont pas un juge.

## Pour aller plus loin

- Retirez `as_type="generation"` de `generer` : la trace ne change pas, deux tests tombent.
- Appelez `brancher()` deux fois : le second collecteur reste vide, et rien ne vous le dit.
- Ajoutez un cas au jeu de `JEU_METIER` et regardez la moyenne bouger.
- Branchez un vrai Langfuse (`LANGFUSE_HOST` + clés) : seul `brancher()` change.

---

Cours associé : [Langfuse : l'observabilité de vos LLM](https://syllatech.pages.dev/cours/langfuse)
· Formation syllatech — Diaguily SYLLA
