package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;

import fr.portail.jeton.ServiceDeJetons;
import fr.portail.securite.ConvertisseurDeRoles;
import fr.portail.web.Controleurs;
import fr.portail.web.Decouverte;
import fr.portail.web.Proprietaire;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.List;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.security.oauth2.jwt.JwtDecoder;

/** Chapitres 5 et 6 — les deux jetons, le pont des rôles, la méthode. */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class RolesTest {

    @LocalServerPort
    int port;

    @Autowired
    ServiceDeJetons jetons;

    @Autowired
    JwtDecoder decodeur;

    @Autowired
    ConvertisseurDeRoles convertisseur;

    private final HttpClient client = HttpClient.newHttpClient();

    @BeforeEach
    void repartirDeZero() {
        convertisseur.actif(true);
        Controleurs.remettreAZero();
        Proprietaire.remettreAZero();
        Decouverte.remettreAZero();
    }

    @AfterEach
    void remettreLePont() {
        convertisseur.actif(true);
    }

    @Nested
    @DisplayName("le pont entre KeyCloak et Spring")
    class Pont {

        @Test
        @DisplayName("le jeton porte les roles sans prefixe, dans un claim imbrique")
        void leFormatKeycloak() {
            var decode = decodeur.decode(jetons.acces("awa", List.of("RH")));
            assertThat(ConvertisseurDeRoles.rolesDu(decode)).containsExactly("RH");
            // Le claim est une CARTE, pas une chaine ni une liste : c'est ce
            // qui met en echec `setAuthoritiesClaimName`. `getClaimAsString`
            // rend d'ailleurs le `toString` de la carte, ce qui ressemble a
            // une valeur exploitable et n'en est pas une.
            assertThat(decode.getClaimAsMap("realm_access"))
                    .containsKey("roles");
            // ⚠️ `getClaimAsStringList` ne rend pas null : il rend
            // `["{roles=[RH]}"]`, le `toString` de la carte range dans une
            // liste d'un element. Une valeur qui a l'air exploitable et qui
            // ne l'est pas — c'est pire qu'une erreur.
            assertThat(decode.getClaimAsStringList("realm_access"))
                    .doesNotContain("RH")
                    .hasSize(1);
        }

        @Test
        @DisplayName("le convertisseur ajoute le prefixe ROLE_")
        void lePrefixe() {
            var decode = decodeur.decode(jetons.acces("awa", List.of("RH", "USER")));
            assertThat(convertisseur.autorites(decode).stream()
                    .map(Object::toString).toList())
                    .containsExactlyInAnyOrder("ROLE_RH", "ROLE_USER");
        }

        @Test
        @DisplayName("sans lui, aucune autorite n'est tiree du jeton")
        void sansLePont() {
            convertisseur.actif(false);
            var decode = decodeur.decode(jetons.acces("awa", List.of("RH")));
            assertThat(convertisseur.autorites(decode)).isEmpty();
        }

        @Test
        @DisplayName("JwtGrantedAuthoritiesConverter ne lit pas un claim imbrique")
        void leConvertisseurStandardNeSuffitPas() {
            var standard = new org.springframework.security.oauth2.server.resource
                    .authentication.JwtGrantedAuthoritiesConverter();
            standard.setAuthoritiesClaimName("realm_access.roles");
            standard.setAuthorityPrefix("ROLE_");
            var decode = decodeur.decode(jetons.acces("awa", List.of("RH")));
            assertThat(standard.convert(decode))
                    .as("il cherche un claim NOMME `realm_access.roles`, pas "
                        + "`roles` a l'interieur de `realm_access` — c'est "
                        + "l'exemple qui circule le plus, et il ne marche pas")
                    .isEmpty();
        }

        @Test
        @DisplayName("le meme jeton : 403 sans le pont, 200 avec")
        void leMemeJetonDeuxReponses() {
            String jeton = jetons.acces("awa", List.of("RH"));
            convertisseur.actif(false);
            assertThat(code("/api/rh/candidatures", jeton)).isEqualTo(403);
            convertisseur.actif(true);
            assertThat(code("/api/rh/candidatures", jeton)).isEqualTo(200);
        }

        @Test
        @DisplayName("sans le pont, l'identite reste etablie : 200 sur /api/moi")
        void lIdentiteResteEtablie() {
            String jeton = jetons.acces("awa", List.of("RH"));
            convertisseur.actif(false);
            assertThat(code("/api/moi", jeton))
                    .as("c'est ce qui rend le bug long a trouver : tout marche, "
                        + "sauf les droits")
                    .isEqualTo(200);
        }
    }

    @Nested
    @DisplayName("access token et ID token")
    class DeuxJetons {

        @Test
        @DisplayName("l'access token ouvre la route RH")
        void lAccessToken() {
            assertThat(code("/api/rh/candidatures",
                    jetons.acces("awa", List.of("RH")))).isEqualTo(200);
        }

        @Test
        @DisplayName("l'ID token ne l'ouvre pas")
        void lIdToken() {
            assertThat(code("/api/rh/candidatures",
                    jetons.identite("awa", "awa@exemple.test", "Awa Diallo")))
                    .as("signature valide, identite etablie, aucun role : 403")
                    .isEqualTo(403);
        }

        @Test
        @DisplayName("les deux visent des destinataires differents")
        void lesAudiences() {
            assertThat(decodeur.decode(jetons.acces("awa", List.of()))
                    .getAudience()).containsExactly("portail-api");
            assertThat(decodeur.decode(jetons.identite("awa", "a@b", "A"))
                    .getAudience()).containsExactly("portail-spa");
        }
    }

    @Nested
    @DisplayName("la decouverte OIDC")
    class Decouvrir {

        @Test
        @DisplayName("le document nomme l'emetteur et le JWKS")
        void leDocument() {
            var reponse = obtenir("/.well-known/openid-configuration");
            assertThat(reponse.statusCode()).isEqualTo(200);
            assertThat(reponse.body())
                    .contains("\"issuer\"")
                    .contains("\"jwks_uri\"")
                    .contains(ServiceDeJetons.EMETTEUR);
        }

        @Test
        @DisplayName("il n'annonce que S256 pour PKCE")
        void pkce() {
            assertThat(obtenir("/.well-known/openid-configuration").body())
                    .contains("S256")
                    .as("`plain` envoie le secret en clair : le lister "
                        + "reviendrait a l'autoriser")
                    .doesNotContain("\"plain\"");
        }

        @Test
        @DisplayName("valider cent jetons ne telecharge aucune cle")
        void aucunTelechargement() {
            String jeton = jetons.acces("awa", List.of("USER"));
            for (int i = 0; i < 100; i++) {
                code("/api/moi", jeton);
            }
            assertThat(Decouverte.lecturesDuJwks())
                    .as("valider un JWT est un calcul local : il ne parle a "
                        + "personne")
                    .isZero();
        }

        @Test
        @DisplayName("le JWKS ne publie aucune cle privee")
        void aucuneClePrivee() {
            var document = obtenir("/oauth2/jwks").body();
            assertThat(document).contains("\"n\"", "\"e\"", "RSA");
            assertThat(document).doesNotContain("\"d\"");
        }
    }

    @Nested
    @DisplayName("la securite au niveau methode")
    class Methode {

        @Test
        @DisplayName("l'auteur lit son brouillon")
        void lAuteur() {
            assertThat(code("/api/offres/OFF-014/brouillon",
                    jetons.acces("awa", List.of("USER")))).isEqualTo(200);
        }

        @Test
        @DisplayName("un autre utilisateur, meme role, meme URL, ne le lit pas")
        void unAutre() {
            assertThat(code("/api/offres/OFF-014/brouillon",
                    jetons.acces("karim", List.of("USER"))))
                    .as("aucune regle d'URL ne peut exprimer « seulement si "
                        + "l'offre vous appartient »")
                    .isEqualTo(403);
        }

        @Test
        @DisplayName("la regle est evaluee AVANT le corps de la methode")
        void avantLeCorps() {
            code("/api/offres/OFF-014/brouillon",
                    jetons.acces("karim", List.of("USER")));
            assertThat(Proprietaire.consultations()).isEqualTo(1);
            assertThat(Controleurs.entrees())
                    .as("le corps de `brouillon` n'a jamais tourne")
                    .isZero();
        }

        @Test
        @DisplayName("@PreAuthorize(\"hasRole\") complete la regle d'URL")
        void surLaMethode() {
            assertThat(code("/api/rh/statistiques",
                    jetons.acces("awa", List.of("RH")))).isEqualTo(200);
            assertThat(code("/api/rh/statistiques",
                    jetons.acces("karim", List.of("USER")))).isEqualTo(403);
        }

        @Test
        @DisplayName("chaque offre a bien un auteur distinct")
        void lesAuteurs() {
            assertThat(Proprietaire.auteurDe("OFF-014")).isEqualTo("awa");
            assertThat(Proprietaire.auteurDe("OFF-021")).isEqualTo("karim");
        }
    }

    // ── la plomberie du test ─────────────────────────────────────────────

    private int code(String chemin, String jeton) {
        return obtenir(chemin, "Authorization", "Bearer " + jeton).statusCode();
    }

    private HttpResponse<String> obtenir(String chemin, String... entetes) {
        try {
            var construction = HttpRequest.newBuilder()
                    .uri(URI.create("http://localhost:" + port + chemin));
            for (int i = 0; i + 1 < entetes.length; i += 2) {
                construction.header(entetes[i], entetes[i + 1]);
            }
            return client.send(construction.GET().build(),
                    HttpResponse.BodyHandlers.ofString());
        } catch (java.io.IOException | InterruptedException erreur) {
            if (erreur instanceof InterruptedException) {
                Thread.currentThread().interrupt();
            }
            throw new IllegalStateException("requete impossible", erreur);
        }
    }
}
