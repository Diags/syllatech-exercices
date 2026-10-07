# Bac à sable — projet de départ du cours **Sandbox Claude Code**

Une configuration de bac à sable ne se relit pas : elle **s'interroge**.

```
configs/a-corriger.json     portee « projet »        7 erreurs
configs/a-corriger.json     portee « utilisateur »   4 erreurs
```

Le même fichier. Aucune faute de syntaxe. Ce n'est pas le contenu qui change
la politique de sécurité — c'est **l'endroit où le fichier est posé**, et cet
endroit ne se relit pas dans une revue de code.

---

## Ce que ce projet est, et n'est pas

⚠️ **Ce n'est pas le bac à sable.** Le vrai tourne sur macOS, Linux et WSL2 —
la documentation exclut Windows natif. Ce projet **modélise ses règles** et
rend le raisonnement exécutable : chaque règle du résolveur cite la phrase de
la documentation dont elle sort, pour qu'on puisse la contredire.

Un modèle qui se trompe se trompe en silence, exactement comme les défauts
qu'il traque. D'où les 62 tests, et les citations.

## Démarrer

```bash
uv sync --extra dev
uv run --extra dev pytest -q        # 62 tests

uv run python chapitres/chapitre_1_pourquoi.py       # ce qu'il résout, et ce qu'il n'est pas
uv run python chapitres/chapitre_2_fichiers.py       # la spécificité, mesurée sur 720 ordres
uv run python chapitres/chapitre_3_proteges.py       # 10 allowWrite nommés, 10 refus
uv run python chapitres/chapitre_4_reseau.py         # trois issues, deux jokers
uv run python chapitres/chapitre_5_identifiants.py   # deny, mask, et le masque qui fuit
uv run python chapitres/chapitre_6_limites.py        # les couches ensemble
```

Les deux outils s'utilisent aussi seuls, sur **votre** configuration :

```bash
uv run python outils/verifier.py configs/a-corriger.json --portee projet
uv run python outils/resolveur.py configs/depot.json --ecrire .mcp.json
uv run python outils/resolveur.py configs/depot.json --joindre gist.github.com
```

## Les trois configurations livrées

| Fichier | Où il va | Ce qu'il montre |
| --- | --- | --- |
| `configs/depot.json` | `.claude/settings.json` du dépôt | ne contient **que** des clés honorées là — 0 erreur |
| `configs/utilisateur.json` | `~/.claude/settings.json` | les cinq clés privilégiées — 0 erreur |
| `configs/a-corriger.json` | nulle part | huit clés qui n'ont pas l'effet qu'on croit |

## La carte du projet

| Fichier | Ce qu'il contient | Chapitre |
| --- | --- | --- |
| `outils/resolveur.py` → `appliquee()` | la configuration **telle qu'elle s'applique** | 1, 4, 5, 6 |
| `outils/resolveur.py` → `_plus_specifique()` | la règle la plus longue gagne | 2 |
| `outils/resolveur.py` → `protege()` | les quatre groupes de chemins protégés | 3 |
| `outils/resolveur.py` → `identifiants()` | ce qu'une commande voit de chaque variable | 5 |
| `outils/verifier.py` | les défauts qui ne lèvent aucune erreur | 6 |
| `tests/test_sandbox.py` | 62 tests, dont 25 sur les chemins protégés | tous |

## Cinq choses que le code enseigne

**La portée n'est pas dans le JSON.** Cinq clés — `filesystem.disabled`,
`network.strictAllowlist`, `network.tlsTerminate`,
`credentials.allowPlaintextInject`, et toute entrée `credentials` en mode
`mask` — ne sont honorées que depuis les réglages utilisateur, administrés ou
`--settings`. Dans le `.claude/settings.json` d'un dépôt, elles sont
**ignorées**. Pas refusées : ignorées. Elles ont toutes la même forme — elles
*élargissent* ce qu'une commande peut faire — et un fichier qu'un `git pull`
modifie ne peut pas les porter. La règle est cohérente ; elle n'est
simplement visible nulle part.

**Un `mask` ignoré ne devient pas un `deny`.** L'entrée disparaît. La
variable garde sa valeur, les commandes la lisent en entier, et la
configuration qu'on relit dit toujours `mask`. Des trois façons de rater un
masque, c'est la seule où **rien ne dysfonctionne** — les deux autres
(`tlsTerminate` absent, `injectHosts` hors de `allowedDomains`) cassent
l'authentification, donc se corrigent dans l'heure.

**La spécificité tranche, donc l'ordre ne compte pas.** Un `denyRead` tient
dans un `allowRead` plus large, et un `allowRead` plus étroit rouvre une
partie d'un `denyRead` : c'est la règle **la plus longue** qui gagne. Le
chapitre 2 le vérifie sur les 720 permutations de six règles — un seul
résultat. Ce n'est pas une évidence : une ACL, un pare-feu ou un `.gitignore`
répondraient différemment selon l'ordre, et c'est ce qui permet ici à
plusieurs fichiers de réglages de fusionner leurs listes sans que la fusion
décide du résultat.

**La couche réseau ne marche pas comme la couche fichiers.** Là, `deny`
l'emporte, point : on ne rouvre pas un sous-domaine d'un `deniedDomains`
comme on rouvre un sous-dossier d'un `denyRead`. Et elle a **trois** issues,
pas deux — un hôte hors liste est *demandé*, ce qui est précisément ce qui
rend le bac à sable tenable au quotidien.

**Couper une couche ne dégrade pas la sécurité uniformément.**
`filesystem.disabled` emporte les `denyRead`, les chemins protégés et les
`credentials.files` en mode `deny` — mais laisse intacts les `envVars` et les
masques de fichiers, qui appartiennent au proxy. Savoir à quelle couche
appartient une protection dit exactement ce qui reste quand on coupe l'autre.

## Ce que ce projet ne prouve pas

- **Aucune commande n'a été exécutée sous un vrai bac à sable.** Tout est le
  comportement *documenté*, rendu interrogeable. Sur macOS, Linux ou WSL2, la
  vérification finale est `/sandbox`, onglet **Config**.
- Les différences entre Seatbelt et seccomp ne sont pas modélisées —
  notamment qu'un `mask` de **fichier** s'applique comme un `deny` sur macOS
  tant que l'isolation des fichiers est active.
- Ni le repli d'un `mask` vers `deny` (dossier, glob, fichier > 8 Mio,
  non-UTF-8), ni `extract` / `decode` / `maskClaims`, ni les règles
  `WebFetch(domain:…)`, ni les formes ambiguës d'adresse IPv6.

`outils/resolveur.py` garde cette liste à jour dans sa constante `LIMITES`,
et le chapitre 6 l'affiche.

## Pour aller plus loin

- Posez `configs/utilisateur.json` en portée `projet` et regardez le
  vérificateur perdre la moitié de ses reproches — puis les retrouver.
- Ajoutez une sixième clé privilégiée à `CLES_PRIVILEGIEES` : le vérificateur,
  les six chapitres et les tests la prennent en compte sans rien d'autre.
- Mutez `_sous()` en un simple `startswith` : trois tests tombent, et c'est un
  vrai trou de sécurité — `/tmp/build` ouvrirait `/tmp/build-autre`.
- Sur une machine Linux, macOS ou WSL2 : comparez `protege()` à la liste
  **Denied within allowed** de `/sandbox`, onglet Config.

---

Cours associé : [Sandbox Claude Code](https://syllatech.pages.dev/cours/cc-sandbox)
· Formation syllatech — Diaguily SYLLA
