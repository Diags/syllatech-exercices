package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;

import fr.portail.plateforme.LectureDockerfile;
import fr.portail.plateforme.LectureYaml;
import fr.portail.plateforme.MiseAJourProgressive;
import java.nio.file.Path;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

/**
 * Les artefacts de déploiement, vérifiés par une machine.
 *
 * <p>Ces tests ne démarrent rien : ils lisent les fichiers du dossier
 * {@code deploiement/} et vérifient ce qu'ils déclarent. C'est exactement ce
 * qu'une CI devrait faire — et c'est infiniment plus fiable qu'une relecture,
 * qui oublie toujours la même chose.
 */
class PlateformeTest {

    private static final Path DEPLOIEMENT = Path.of("deploiement");

    @Test
    @DisplayName("le Dockerfile a deux etages, et le final est leger")
    void deuxEtages() throws Exception {
        var dockerfile = new LectureDockerfile(DEPLOIEMENT.resolve("Dockerfile"));

        assertThat(dockerfile.etages()).hasSize(2);
        assertThat(dockerfile.etages().getFirst().base()).contains("maven");
        assertThat(dockerfile.etageFinal().base())
                .as("l'etage final ne doit pas embarquer Maven")
                .contains("jre")
                .doesNotContain("maven");
        assertThat(dockerfile.copiesDepuisUnAutreEtage())
                .as("une seule chose franchit la frontiere : le jar")
                .hasSize(1);
    }

    /**
     * ⚠️ Trois réglages facultatifs pour Docker, indispensables en production.
     */
    @Test
    @DisplayName("le Dockerfile ne tourne pas en root, et coupe proprement")
    void lesTroisDecisions() throws Exception {
        var dockerfile = new LectureDockerfile(DEPLOIEMENT.resolve("Dockerfile"));

        assertThat(dockerfile.nonRoot())
                .as("une evasion de conteneur donnerait root sur l'hote")
                .isTrue();
        assertThat(dockerfile.entreeEnFormeExec())
                .as("en forme shell, la JVM ne recoit jamais SIGTERM")
                .isTrue();
        assertThat(dockerfile.cacheDesDependancesOptimise())
                .as("le pom doit etre copie AVANT les sources")
                .isTrue();
    }

    /**
     * ⚠️ Le contre-exemple, sans lequel le vérificateur ne prouve rien.
     *
     * <p>Un contrôle qui répond toujours « c'est bon » passe tous les tests
     * écrits sur un fichier correct. Il faut donc un fichier <em>incorrect</em>
     * pour vérifier que le contrôle sait dire non — et c'est exactement ce que
     * {@code Dockerfile.naif} est là pour faire.
     */
    @Test
    @DisplayName("le Dockerfile naif est reconnu comme tel")
    void leDockerfileNaif() throws Exception {
        var naif = new LectureDockerfile(DEPLOIEMENT.resolve("Dockerfile.naif"));

        assertThat(naif.etages())
                .as("un seul etage : le JDK et les sources partent en production")
                .hasSize(1);
        assertThat(naif.nonRoot())
                .as("aucune instruction USER : le conteneur tourne en root")
                .isFalse();
        assertThat(naif.entreeEnFormeExec())
                .as("forme shell : la JVM ne recevra pas SIGTERM")
                .isFalse();
        assertThat(naif.cacheDesDependancesOptimise())
                .as("`COPY . .` en premier : le cache est invalide a chaque ligne")
                .isFalse();
        assertThat(naif.copiesDepuisUnAutreEtage())
                .as("rien ne franchit de frontiere : il n'y en a pas")
                .isEmpty();
    }

    @ParameterizedTest(name = "« {0} » est une version precise : {1}")
    @CsvSource({
        "portail/offres:1.4.0, true",
        "portail/offres:latest, false",
        "portail/offres, false",
    })
    @DisplayName("`latest` n'est pas une version")
    void lesVersionsDImage(String image, boolean precise) {
        assertThat(LectureDockerfile.versionPrecise(image)).isEqualTo(precise);
    }

    @Test
    @DisplayName("le manifeste soigne declare sondes, limites et strategie")
    void leManifesteSoigne() throws Exception {
        var manifeste = new LectureYaml(
                DEPLOIEMENT.resolve("k8s/deployment.yaml"));

        assertThat(manifeste.entier("spec.replicas")).isEqualTo(4);
        assertThat(manifeste.premierConteneur())
                .containsKeys("livenessProbe", "readinessProbe", "resources");
        assertThat(manifeste.entier("spec.strategy.rollingUpdate.maxSurge"))
                .isEqualTo(1);
        assertThat(manifeste.entier(
                "spec.strategy.rollingUpdate.maxUnavailable")).isEqualTo(1);
        assertThat(LectureDockerfile.versionPrecise(
                String.valueOf(manifeste.premierConteneur().get("image"))))
                .isTrue();
    }

    @Test
    @DisplayName("le manifeste courant demarre, et n'a rien de tout cela")
    void leManifesteCourant() throws Exception {
        var manifeste = new LectureYaml(
                DEPLOIEMENT.resolve("k8s/deployment-sans-sondes.yaml"));

        assertThat(manifeste.entier("spec.replicas")).isEqualTo(4);
        assertThat(manifeste.premierConteneur())
                .as("ni sondes ni limites : c'est valide, et c'est le probleme")
                .doesNotContainKeys("livenessProbe", "readinessProbe",
                        "resources");
        assertThat(manifeste.existe("spec.strategy")).isFalse();
        assertThat(LectureDockerfile.versionPrecise(
                String.valueOf(manifeste.premierConteneur().get("image"))))
                .isFalse();
    }

    @Test
    @DisplayName("les deux sondes visent des chemins differents")
    void lesDeuxSondes() throws Exception {
        var manifeste = new LectureYaml(
                DEPLOIEMENT.resolve("k8s/deployment.yaml"));

        assertThat(String.valueOf(manifeste.premierConteneur()
                .get("livenessProbe"))).contains("liveness");
        assertThat(String.valueOf(manifeste.premierConteneur()
                .get("readinessProbe"))).contains("readiness");
    }

    /**
     * ⚠️ L'invariant que {@code maxUnavailable} garantit — et qui disparaît
     * dès qu'on le règle à la valeur du nombre de répliques.
     */
    @ParameterizedTest(name = "surge={0} indispo={1} : plancher {2}, pic {3}")
    @CsvSource({
        "1, 1, 3, 5",
        "1, 0, 4, 5",
        "2, 0, 4, 6",
        "0, 4, 0, 4",
    })
    @DisplayName("la mise a jour progressive respecte ses deux bornes")
    void lesBornesDeLaMiseAJour(int surge, int indispo, int plancher, int pic) {
        var etapes = MiseAJourProgressive.derouler(4, surge, indispo);

        assertThat(MiseAJourProgressive.creuxDeDisponibilite(etapes))
                .isEqualTo(plancher);
        assertThat(MiseAJourProgressive.picDePods(etapes)).isEqualTo(pic);
    }

    @Test
    @DisplayName("la mise a jour finit toujours sur la nouvelle version")
    void laMiseAJourAboutit() {
        var etapes = MiseAJourProgressive.derouler(4, 1, 1);
        var derniere = etapes.getLast();

        assertThat(derniere.anciens()).isZero();
        assertThat(derniere.nouveaux()).isEqualTo(4);
    }

    @Test
    @DisplayName("les valeurs Helm de production ne redefinissent que l'utile")
    void lesValeursHelm() throws Exception {
        var recette = new LectureYaml(DEPLOIEMENT.resolve("helm/values.yaml"));
        var production = new LectureYaml(
                DEPLOIEMENT.resolve("helm/values-production.yaml"));

        assertThat(recette.entier("replicaCount")).isEqualTo(2);
        assertThat(production.entier("replicaCount")).isEqualTo(6);
        assertThat(production.texte("image.tag"))
                .as("la version d'image est heritee, pas redefinie")
                .isNull();
        assertThat(recette.texte("image.tag")).isEqualTo("1.4.0");
    }

    @Test
    @DisplayName("`depends_on` n'attend la disponibilite que sous sa forme longue")
    void dependsOn() throws Exception {
        var compose = new LectureYaml(DEPLOIEMENT.resolve("compose.yaml"));
        String tout = String.valueOf(compose.racine());

        assertThat(tout).contains("service_healthy");
        assertThat(tout)
                .as("la passerelle, elle, n'attend que le demarrage")
                .contains("passerelle");
    }
}
