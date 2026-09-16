package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import fr.portail.cles.Cles;
import fr.portail.jeton.Forge;
import fr.portail.jeton.ServiceDeJetons;
import fr.portail.securite.ConvertisseurDeRoles;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtException;

/** Chapitre 4 — ce qu'un JWT garantit, et ce qu'il ne garantit pas. */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class JetonTest {

    @Autowired
    ServiceDeJetons jetons;

    @Autowired
    JwtDecoder decodeur;

    @Autowired
    Cles cles;

    @Nested
    @DisplayName("signe, pas chiffre")
    class LisibleParTous {

        @Test
        @DisplayName("la charge utile se lit sans aucune cle")
        void laChargeEstLisible() {
            String jeton = jetons.acces("awa", List.of("RH"));
            assertThat(Forge.lireLaCharge(jeton))
                    .contains("\"sub\":\"awa\"")
                    .contains("RH");
        }

        @Test
        @DisplayName("l'en-tete nomme l'algorithme et la cle")
        void lEnteteEstLisible() {
            String entete = Forge.lireLEntete(jetons.acces("awa", List.of("RH")));
            assertThat(entete).contains("RS256").contains(Cles.IDENTIFIANT);
        }

        @Test
        @DisplayName("un jeton a exactement trois parties")
        void troisParties() {
            assertThat(jetons.acces("awa", List.of()).split("\\.")).hasSize(3);
        }
    }

    @Nested
    @DisplayName("ce que le decodeur refuse")
    class Attaques {

        @Test
        @DisplayName("le jeton intact est accepte")
        void leJetonIntact() {
            var decode = decodeur.decode(jetons.acces("awa", List.of("RH", "USER")));
            assertThat(decode.getSubject()).isEqualTo("awa");
            assertThat(ConvertisseurDeRoles.rolesDu(decode))
                    .containsExactlyInAnyOrder("RH", "USER");
        }

        @Test
        @DisplayName("un role change en Base64 casse la signature")
        void laChargeAlteree() {
            String altere = Forge.chargeUtileAlteree(
                    jetons.acces("awa", List.of("USER")), "\"USER\"", "\"ADMIN\"");
            assertThatThrownBy(() -> decodeur.decode(altere))
                    .isInstanceOf(JwtException.class);
        }

        @Test
        @DisplayName("changer le sujet la casse aussi")
        void leSujetAltere() {
            String altere = Forge.chargeUtileAlteree(
                    jetons.acces("awa", List.of("USER")), "\"awa\"", "\"lea\"");
            assertThatThrownBy(() -> decodeur.decode(altere))
                    .isInstanceOf(JwtException.class);
        }

        @Test
        @DisplayName("`alg: none` est refuse")
        void algNone() {
            String sansSignature = Forge.sansSignature(
                    jetons.acces("awa", List.of("USER")));
            assertThatThrownBy(() -> decodeur.decode(sansSignature))
                    .isInstanceOf(JwtException.class);
        }

        @Test
        @DisplayName("un jeton signe en HMAC avec la cle publique est refuse")
        void substitutionDAlgorithme() throws Exception {
            String force = Forge.signeEnHmacAvecLaClePublique("lea", cles.publique());
            assertThatThrownBy(() -> decodeur.decode(force))
                    .as("la cle publique est PUBLIQUE : accepter HS256 la "
                        + "transformerait en secret partage avec le monde entier")
                    .isInstanceOf(JwtException.class);
        }

        @Test
        @DisplayName("un jeton expire est refuse")
        void leJetonExpire() {
            assertThatThrownBy(() ->
                    decodeur.decode(jetons.accesExpire("awa", List.of("RH"))))
                    .isInstanceOf(JwtException.class);
        }

        @Test
        @DisplayName("un jeton signe par une autre cle est refuse")
        void uneAutreCle() throws Exception {
            assertThatThrownBy(() -> decodeur.decode(jetonEtranger()))
                    .isInstanceOf(JwtException.class);
        }

        private String jetonEtranger() throws Exception {
            var generateur = java.security.KeyPairGenerator.getInstance("RSA");
            generateur.initialize(2048);
            var paire = generateur.generateKeyPair();
            var claims = new com.nimbusds.jwt.JWTClaimsSet.Builder()
                    .issuer(ServiceDeJetons.EMETTEUR).subject("lea")
                    .expirationTime(java.util.Date.from(
                            java.time.Instant.now().plusSeconds(600)))
                    .build();
            var jwt = new com.nimbusds.jwt.SignedJWT(
                    new com.nimbusds.jose.JWSHeader(
                            com.nimbusds.jose.JWSAlgorithm.RS256), claims);
            jwt.sign(new com.nimbusds.jose.crypto.RSASSASigner(paire.getPrivate()));
            return jwt.serialize();
        }
    }

    @Nested
    @DisplayName("les claims")
    class Claims {

        @Test
        @DisplayName("l'access token porte les roles et vise l'API")
        void lAccessToken() {
            var decode = decodeur.decode(jetons.acces("lea", List.of("ADMIN")));
            assertThat(decode.getAudience()).containsExactly("portail-api");
            assertThat(ConvertisseurDeRoles.rolesDu(decode)).containsExactly("ADMIN");
            assertThat(decode.getClaimAsString("typ")).isEqualTo("Bearer");
        }

        @Test
        @DisplayName("l'ID token porte l'identite et AUCUN role")
        void lIdToken() {
            var decode = decodeur.decode(
                    jetons.identite("lea", "lea.m@exemple.test", "Lea Marchand"));
            assertThat(decode.getAudience()).containsExactly("portail-spa");
            assertThat(ConvertisseurDeRoles.rolesDu(decode)).isEmpty();
            assertThat(decode.getClaimAsString("email"))
                    .isEqualTo("lea.m@exemple.test");
        }

        @Test
        @DisplayName("chaque jeton a un identifiant unique")
        void leJti() {
            var premier = decodeur.decode(jetons.acces("awa", List.of()));
            var second = decodeur.decode(jetons.acces("awa", List.of()));
            assertThat(premier.getId()).isNotEqualTo(second.getId());
        }

        @Test
        @DisplayName("l'access token dure cinq minutes")
        void laDuree() {
            var decode = decodeur.decode(jetons.acces("awa", List.of()));
            var duree = java.time.Duration.between(
                    decode.getIssuedAt(), decode.getExpiresAt());
            assertThat(duree).isEqualTo(ServiceDeJetons.DUREE_ACCES);
            assertThat(duree).isLessThanOrEqualTo(java.time.Duration.ofMinutes(15));
        }
    }

    @Nested
    @DisplayName("la revocation")
    class Revocation {

        @Test
        @DisplayName("un refresh token se revoque")
        void leRefreshSeRevoque() {
            String refresh = jetons.rafraichissement("karim");
            assertThat(jetons.porteurDu(refresh)).contains("karim");
            assertThat(jetons.revoquer(refresh)).isTrue();
            assertThat(jetons.porteurDu(refresh)).isEmpty();
        }

        @Test
        @DisplayName("un access token, lui, reste valide apres la revocation")
        void lAccessNeSeRevoquePas() {
            String acces = jetons.acces("karim", List.of("USER"));
            String refresh = jetons.rafraichissement("karim");
            jetons.revoquer(refresh);
            assertThat(decodeur.decode(acces).getSubject())
                    .as("on ne peut pas revoquer ce qu'on ne stocke pas")
                    .isEqualTo("karim");
        }

        @Test
        @DisplayName("revoquer deux fois le meme jeton ne fait rien de plus")
        void revoquerDeuxFois() {
            String refresh = jetons.rafraichissement("karim");
            assertThat(jetons.revoquer(refresh)).isTrue();
            assertThat(jetons.revoquer(refresh)).isFalse();
        }
    }

    @Nested
    @DisplayName("le JWKS")
    class Jwks {

        @Test
        @DisplayName("il ne publie que la partie publique")
        void aucuneCleePriveeNeSort() {
            // `toJSONString`, et non `toJSONObject().toString()` : le second
            // rend le `toString` d'une carte Java, qui ressemble a du JSON
            // sans en etre — et un test ecrit dessus mesure la mauvaise chose.
            String document = new com.nimbusds.jose.jwk.JWKSet(
                    cles.jwk().toPublicJWK()).toString();
            assertThat(document).contains("\"n\"").contains("\"e\"");
            assertThat(document)
                    .as("`d`, `p` et `q` sont la cle PRIVEE : les publier "
                        + "reviendrait a laisser n'importe qui emettre des jetons")
                    .doesNotContain("\"d\"")
                    .doesNotContain("\"p\"")
                    .doesNotContain("\"q\"");
        }

        @Test
        @DisplayName("la cle fait 2048 bits")
        void laTaille() {
            assertThat(cles.publique().getModulus().bitLength()).isEqualTo(2048);
        }
    }
}
