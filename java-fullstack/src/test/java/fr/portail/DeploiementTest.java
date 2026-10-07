package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;

import fr.portail.deploiement.AuditImage;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.ValueSource;

/**
 * L'audit du Dockerfile — un controle de configuration, comme un linter.
 *
 * <p>⚠️ Il lit un texte : il ne construit rien, ne lance rien, et ne mesure
 * aucune taille d'image. Il attrape l'oubli, jamais la vulnerabilite — et
 * l'oubli est de tres loin le cas le plus frequent.
 */
class DeploiementTest {

    @Test
    @DisplayName("⚠️ le Dockerfile LIVRE dans ce depot satisfait les six regles")
    void leDockerfileDuDepotEstConforme() {
        // Ce n'est pas une illustration : l'audit lit le fichier du depot.
        // Retirez-en `USER`, ce test tombe.
        String dockerfile = AuditImage.lire("Dockerfile");

        assertThat(AuditImage.conforme(dockerfile))
                .as(String.join("\n", AuditImage.rendre(dockerfile)))
                .isTrue();
    }

    @Test
    @DisplayName("⚠️ LA MESURE : celui qu'on ecrit sans y penser rate les SIX")
    void leDockerfileNaifEstUnePassoire() {
        String naif = AuditImage.lire("Dockerfile.naif");

        assertThat(AuditImage.manquantes(naif))
                .extracting(AuditImage.Regle::nom)
                .containsExactlyInAnyOrder("build multi-stage",
                                           "image finale minimale",
                                           "utilisateur non privilegie",
                                           "point d'entree en forme exec",
                                           "aucun secret dans l'image",
                                           "controle de sante");
        // ⚠️ Il FONCTIONNE pourtant : l'application demarre et repond. C'est
        // ce qui le rend dangereux — rien n'echoue, rien n'avertit.
    }

    @Test
    @DisplayName("retirer USER du Dockerfile rouvre exactement une regle")
    void retirerUserSeVoit() {
        String ampute = AuditImage.lire("Dockerfile").lines()
                .filter(ligne -> !ligne.strip().startsWith("USER "))
                .reduce("", (a, b) -> a + b + "\n");

        assertThat(AuditImage.manquantes(ampute))
                .extracting(AuditImage.Regle::nom)
                .containsExactly("utilisateur non privilegie");
    }

    @ParameterizedTest(name = "« {0} » est un secret dans l''image")
    @ValueSource(strings = {
        "ENV PORTAIL_JWT_CLE=cle-de-production",
        "ENV DB_PASSWORD=motdepasse",
        "ARG STRIPE_SECRET=sk_live_abcdef",
        "ENV API_KEY=abcdef"
    })
    @DisplayName("⚠️ un secret ecrit dans l'image est detecte, ENV comme ARG")
    void lesSecretsSontDetectes(String instruction) {
        // Un secret dans une image n'est pas « cache dedans » : il est dans
        // les metadonnees, et `docker history` le montre sans demarrer le
        // conteneur. Le retirer plus tard ne change rien — il faut faire
        // TOURNER la cle.
        assertThat(AuditImage.sentLeSecret(instruction)).isTrue();
    }

    @ParameterizedTest(name = "« {0} » est acceptable")
    @ValueSource(strings = {
        "ENV SPRING_PROFILES_ACTIVE=production",
        "ENV TZ=Europe/Paris",
        "ENV PORTAIL_JWT_CLE",
        "RUN mvn package",
        "COPY . /app"
    })
    @DisplayName("une variable sans valeur, ou sans secret, ne declenche rien")
    void lesInstructionsAcceptables(String instruction) {
        assertThat(AuditImage.sentLeSecret(instruction)).isFalse();
    }

    @Test
    @DisplayName("⚠️ un ENTRYPOINT sur cinq lignes doit etre recolle avant d'etre lu")
    void lesContinuationsSontRecollees() {
        // Sans recollage, cet ENTRYPOINT parfaitement correct passerait pour
        // absent — et l'audit dirait le contraire de la verite.
        String etale = """
                FROM node:22 AS front
                RUN npm run build
                FROM eclipse-temurin:25-jre-alpine
                USER 1000
                HEALTHCHECK CMD wget -q -O- http://localhost:8080/health
                ENTRYPOINT ["java", \\
                            "-jar", \\
                            "/app/app.jar"]
                """;

        assertThat(AuditImage.instructions(etale)).hasSize(6);
        assertThat(AuditImage.instructions(etale).getLast())
                .startsWith("ENTRYPOINT [").endsWith("\"/app/app.jar\"]");
        assertThat(AuditImage.conforme(etale)).isTrue();
    }

    @Test
    @DisplayName("les commentaires et les lignes vides ne sont pas des instructions")
    void lesCommentairesSontIgnores() {
        assertThat(AuditImage.instructions(AuditImage.lire("Dockerfile")))
                .noneMatch(ligne -> ligne.startsWith("#"))
                .noneMatch(String::isBlank);
    }

    @ParameterizedTest(name = "derniere base « {0} » : minimale = {1}")
    @CsvSource({"eclipse-temurin:25-jre-alpine,true",
                "eclipse-temurin:25-jre,true",
                "python:3.12-slim,true",
                "gcr.io/distroless/java,true",
                "maven:3-eclipse-temurin-25,false",
                "eclipse-temurin:25-jdk,false"})
    @DisplayName("la derniere etape decide, pas la premiere")
    void laDerniereEtapeDecide(String base, boolean minimale) {
        String dockerfile = """
                FROM maven:3-eclipse-temurin-25 AS build
                RUN mvn package
                FROM %s
                USER 1000
                HEALTHCHECK CMD true
                ENTRYPOINT ["java", "-jar", "/app.jar"]
                """.formatted(base);

        assertThat(AuditImage.manquantes(dockerfile)
                .stream().map(AuditImage.Regle::nom).toList()
                .contains("image finale minimale")).isNotEqualTo(minimale);
    }

    @Test
    @DisplayName("chaque regle dit ce qu'on risque sans elle")
    void chaqueRegleExpliqueSonRisque() {
        assertThat(AuditImage.REGLES).hasSize(6);
        for (AuditImage.Regle regle : AuditImage.REGLES) {
            assertThat(regle.nom()).isNotBlank();
            assertThat(regle.attendu()).isNotBlank();
            assertThat(regle.siAbsente()).isNotBlank().hasSizeGreaterThan(30);
        }
    }

    @Test
    @DisplayName("le rendu nomme les regles manquantes, pas seulement leur nombre")
    void leRenduEstLisible() {
        List<String> rendu = AuditImage.rendre(AuditImage.lire("Dockerfile.naif"));
        String texte = String.join("\n", rendu);

        assertThat(texte).contains("⚠️ 6 regle(s) non satisfaite(s) sur 6");
        assertThat(texte).contains("tourne en root DANS le conteneur");
        assertThat(texte).contains("docker history");
    }
}
