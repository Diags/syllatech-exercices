# Spring Security — projet de départ du cours

Une vraie application Spring Boot 4, qui **émet ses propres jetons RS256** et
les valide avec le décodeur de Spring Security. Les attaques classiques contre
un JWT ne sont pas décrites : elles sont **fabriquées** et soumises au vrai
décodeur.

```
   jeton presente                        verdict     ce que dit le decodeur
   ────────────────────────────────────  ──────────  ────────────────────────
   le jeton, tel quel                    ACCEPTE     sujet awa, roles [RH, USER]
   un role change en Base64              refuse      signature verification failed
   `alg: none`, sans signature           refuse      Unsupported algorithm of none
   signe en HMAC avec la cle PUBLIQUE    refuse      Unsupported algorithm of HS256
   expire il y a cinq minutes            refuse      Jwt expired at …
```

Et la mesure qui fait mal :

```
   apres la revocation                   code    verdict
   GET /api/moi, avec l'access token     200     PASSE ENCORE
   POST /api/public/rafraichir           401     refuse
```

Le compte est supprimé, le refresh token est révoqué — et l'access token
continue de fonctionner jusqu'à son expiration. **On ne peut pas révoquer ce
qu'on ne stocke pas.**

---

## Ce que ce projet est, et n'est pas

| | Réalité |
|---|---|
| les **jetons** | de vrais JWT RS256, signés par `NimbusJwtEncoder` avec une paire RSA 2048 bits engendrée au démarrage. |
| les **refus** | prononcés par le vrai `NimbusJwtDecoder`, celui d'une API de production. Le message affiché est le sien. |
| la **chaîne de filtres** | lue dans le `FilterChainProxy` de l'application qui tourne. Deux chaînes cohabitent : session+CSRF et JWT sans état. |
| **CORS** | de vraies requêtes avec un en-tête `Origin`, et de vrais *preflight* `OPTIONS`, envoyés avec le client HTTP du JDK. |
| **OIDC** | le portail publie son propre `/.well-known/openid-configuration` et son propre JWKS — exactement ce que fait un KeyCloak. |

⚠️ **Aucun KeyCloak n'est démarré.** Le portail joue le rôle de l'émetteur
pour que tout tourne hors ligne. Ce qui est mesuré n'est pas KeyCloak, c'est
le **format de ses jetons** — `realm_access.roles`, sans préfixe — et ce que
Spring en fait.

⚠️ **La paire de clés est régénérée à chaque démarrage.** Une clé privée dans
un dépôt Git est une clé compromise, et il n'existe pas de façon pédagogique
d'en poser une. Conséquence : les jetons d'un démarrage ne valent rien au
suivant.

## Démarrer

```bash
mvn test                      # 82 tests

mvn spring-boot:run           # le portail sur http://localhost:8080

mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre1Chaine
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre2Authentification
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre3CorsCsrf
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre4Jwt
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre5Oauth2
mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre6Keycloak
```

À essayer à la main, sur le portail qui tourne :

```bash
# un jeton, puis une route reservee
JETON=$(curl -s -X POST localhost:8080/api/public/connexion \
  -H 'Content-Type: application/json' \
  -d '{"identifiant":"awa","motDePasse":"motdepasse"}' | jq -r .access_token)

curl -s localhost:8080/api/rh/candidatures -H "Authorization: Bearer $JETON"
curl -s localhost:8080/.well-known/openid-configuration | jq
curl -s localhost:8080/oauth2/jwks | jq        # la cle PUBLIQUE, et rien d'autre

# collez le jeton sur jwt.io : le payload se lit sans aucune cle
echo $JETON | cut -d. -f2 | base64 -d
```

## Ce que les six chapitres mesurent

| | Mesure |
|---|---|
| 1 | Les **deux** chaînes, filtre par filtre : le jeton est lu au rang 8, les droits vérifiés au rang 14. L'API ne pose **aucun cookie** ; la chaîne de session en pose un. Le contexte est un `ThreadLocal` : un autre thread ne voit **aucune identité**. 40 requêtes refusées, **0 entrée** dans le code. |
| 2 | Le même message pour « compte inconnu » et « mot de passe faux » — et une **fuite par le temps** : instantané contre 74 ms sur une authentification écrite à la main, 78 contre 75 ms sur celle de Spring. Puis BCrypt aux coûts 4, 8, 10 et 12, chronométré. |
| 3 | Sans en-tête `Origin`, l'API rend **tout**. Depuis une origine interdite, le `CorsFilter` de Spring **refuse** (403) — plus strict que la spécification. Le *preflight* répond `Max-Age: 3600` à la SPA et 403 au pirate. Puis CSRF : **403** sans le jeton, **200** avec. |
| 4 | Le payload lu **sans aucune clé**. Trois attaques fabriquées et soumises au décodeur. Et le talon d'Achille : compte supprimé, refresh révoqué, access token **encore valide**. |
| 5 | L'access token et l'ID token côte à côte, claim par claim — et ce que l'API répond quand on lui présente le mauvais (**403**, pas 401). Le document de découverte, le JWKS, et **0 téléchargement de clé** pour 100 requêtes authentifiées. |
| 6 | Le **même jeton** : 403 sans le convertisseur de rôles, 200 avec. Et `JwtGrantedAuthoritiesConverter` avec `setAuthoritiesClaimName("realm_access.roles")` ne marche **pas** — il cherche un claim nommé ainsi, pas un claim imbriqué. Puis `@PreAuthorize` : même URL, même rôle, deux réponses. |

## Quatre pièges rencontrés en construisant ce projet

Chacun est documenté à l'endroit où il mord, dans `SecurityConfig` :

1. **le bean CORS doit s'appeler `corsConfigurationSource`** — nommé
   autrement, il est ignoré en silence, sans un seul en-tête dans les
   réponses ;
2. **`httpBasic` ne range plus l'identité dans la session** depuis Spring
   Security 6 : le cookie sortait et n'authentifiait rien ;
3. **le gestionnaire CSRF par défaut masque le jeton** (protection BREACH) :
   une SPA qui renvoie le cookie tel quel se fait refuser ;
4. **le refus par défaut passe par `/error`**, qui retraverse les chaînes :
   un 403 revenait au client en **401 « Bearer »**.

Aucun des quatre ne produit d'erreur au démarrage. C'est ce qui les rend longs
à trouver — et c'est pourquoi ils sont écrits ici.

## L'exercice

Cinq zones à compléter, réparties sur les chapitres qui les expliquent :

```
securite/SecurityConfig       les regles d'autorisation de l'API      (ch. 1)
securite/SecurityConfig       la politique CORS                       (ch. 3)
securite/ConvertisseurDeRoles lire `realm_access.roles`               (ch. 6)
securite/ConvertisseurDeRoles prefixer chaque role par `ROLE_`        (ch. 6)
web/Controleurs               l'expression `@PreAuthorize`            (ch. 6)
```

Sur la branche `depart`, le squelette **compile et démarre** : les règles
ouvrent tout, la politique CORS autorise `*`, et le convertisseur ne rend
aucune autorité. Tout marche, et tout est faux — ce sont les tests qui le
disent.

## Les pièces à conviction

```
comptes/AuthentificationNaive   l'authentification qui fuit par le temps
jeton/Forge                     les trois attaques contre un JWT
web/Controleurs#panne           une route ouverte qui ressort en 401
```

**Ne pas les réparer** : des tests vérifient que les défauts sont toujours là.

## Ce que le projet ne prouve pas

- aucun KeyCloak n'est démarré : ce qui est mesuré est le **format** de ses
  jetons, pas son comportement ;
- aucun navigateur n'est lancé : CORS est mesuré **côté serveur**, ce qui est
  précisément le propos du chapitre 3 ;
- le flux Authorization Code + PKCE n'est pas implémenté — le portail échange
  directement des identifiants contre des jetons, ce que les chapitres 5 et 6
  déconseillent explicitement ;
- la fuite temporelle du chapitre 2 est une mesure sur **cette** machine :
  l'ordre de grandeur tient, les millisecondes non.
