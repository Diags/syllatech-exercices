package fr.portail.chapitres;

import fr.portail.commun.Banc;
import fr.portail.commun.Console;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.config.ConfigurableListableBeanFactory;
import org.springframework.boot.autoconfigure.condition.ConditionEvaluationReport;
import org.springframework.security.crypto.password.PasswordEncoder;

/**
 * Chapitre 2 — Spring Boot 4.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre2Boot
 * </pre>
 *
 * <p>« Spring Boot semble deviner votre configuration. Ce n'est pas de la
 * magie. » Ce chapitre ouvre le rapport que Boot tient lui-même :
 * {@link ConditionEvaluationReport} contient, pour chaque décision
 * d'auto-configuration, la condition évaluée et son verdict, en clair. Ce que
 * le cours appelle « conditionnel » s'y lit ligne par ligne.
 */
public final class Chapitre2Boot {

    private Chapitre2Boot() {
    }

    /** Ce que le profil dev donne, retenu pendant que son contexte est ouvert. */
    private static List<String> proprietesDev = List.of("?", "?");

    public static void main(String[] args) {
        Console.utf8();

        try (var banc = Banc.demarrer()) {
            var fabrique = (ConfigurableListableBeanFactory)
                    banc.contexte().getBeanFactory();
            var rapport = ConditionEvaluationReport.get(fabrique);
            var decisions = rapport.getConditionAndOutcomesBySource();

            long retenues = decisions.values().stream()
                    .filter(ConditionEvaluationReport.ConditionAndOutcomes::isFullMatch)
                    .count();
            long ecartees = decisions.size() - retenues;

            Console.titre(1, "LE RAPPORT QUE SPRING BOOT TIENT LUI-MEME");
            Console.ligne("decisions evaluees", String.valueOf(decisions.size()), 34);
            Console.ligne("   retenues", String.valueOf(retenues), 34);
            Console.ligne("   ecartees", String.valueOf(ecartees), 34);
            Console.ligne("classes exclues d'emblee",
                    String.valueOf(rapport.getExclusions().size()), 34);
            Console.ligne("classes non evaluees (absentes du classpath)",
                    String.valueOf(rapport.getUnconditionalClasses().size()), 46);
            System.out.println();
            Console.texte("Chacune de ces decisions est un `if` ecrit par "
                    + "l'equipe de Spring Boot, pas une devinette. La "
                    + "difference importe : un `if` se lit, se teste, et rend "
                    + "toujours le meme verdict pour un meme classpath.");

            Console.titre(2, "POURQUOI UNE SOURCE DE DONNEES EXISTE");
            montrer(decisions, "DataSourceAutoConfiguration", 3);
            montrer(decisions, "HibernateJpaConfiguration", 2);
            System.out.println();
            Console.texte("Aucune de ces lignes ne parle de notre code. Elles "
                    + "constatent ce qui est dans le classpath : `h2` est la, "
                    + "`spring-boot-starter-data-jpa` est la, donc une source "
                    + "de donnees et un gestionnaire de transactions sont "
                    + "construits. Retirez H2 du pom, et les memes lignes "
                    + "diront l'inverse.");

            Console.titre(3, "CE QUI SE PASSE QUAND ON DECLARE LE SIEN");
            Console.ligne("notre PasswordEncoder",
                    banc.bean(PasswordEncoder.class).getClass().getSimpleName(), 38);
            Console.ligne("declare dans",
                    "fr.portail.securite.SecurityConfig", 38);
            System.out.println();
            var recule = decisions.entrySet().stream()
                    .filter(e -> e.getKey().contains("PasswordEncoder")
                            || e.getKey().contains("UserDetailsService"))
                    .toList();
            if (recule.isEmpty()) {
                Console.texte("Spring Boot n'a meme pas eu a reculer : la "
                        + "condition `@ConditionalOnMissingBean` est evaluee "
                        + "AVANT de construire quoi que ce soit, et notre bean "
                        + "etait deja declare.");
            }
            for (var entree : recule) {
                Console.texte(courte(entree.getKey()), 5);
                for (var issue : entree.getValue()) {
                    Console.texte("→ " + issue.getOutcome().getMessage(), 8);
                }
            }
            System.out.println();
            Console.texte("C'est cela, « votre bean gagne toujours » : "
                    + "l'auto-configuration de Spring Security est annotee "
                    + "`@ConditionalOnMissingBean`. Elle regarde si un "
                    + "`PasswordEncoder` existe deja ; il existe, donc elle "
                    + "s'efface. On n'a rien desactive, rien surcharge — on a "
                    + "declare, et la condition a fait le reste.");

            Console.titre(4, "UN STARTER N'EST PAS UNE BIBLIOTHEQUE");
            var lignes = new java.util.ArrayList<List<String>>();
            for (var apport : APPORTS) {
                lignes.add(List.of(apport.starter(), apport.bibliotheque(),
                        chargeable(apport.classeTemoin()) ? "present" : "ABSENT"));
            }
            Console.tableau(List.of("le starter declare", "apporte", "verifie"),
                    lignes, List.of(22, 26, 10));
            System.out.println();
            Console.texte("Quatre lignes dans le pom, et tout ceci sur le "
                    + "classpath — avec, surtout, des versions choisies "
                    + "ensemble par l'equipe de Spring Boot. C'est ce que le "
                    + "cours appelle « un bouquet de dependances aux versions "
                    + "compatibles » : ce n'est pas du confort, c'est "
                    + "l'absence de conflits a resoudre soi-meme.");
            System.out.println();
            Console.ligne("jars sur le classpath de compilation",
                    "plus de 70 — pour 6 lignes de dependances", 42);

            proprietesDev = List.of(
                    String.valueOf(banc.environnement().getProperty(
                            "management.endpoint.health.show-details", "(defaut)")),
                    declare("dev", "ddl-auto"));

            Console.titre(5, "ACTUATOR : CE QUE L'ORCHESTRATEUR LIT");
            var client = banc.anonyme();
            var sante = Banc.obtenir(client, "/actuator/health");
            Console.ligne("GET /actuator/health (profil dev)",
                    sante.valeur() + " — " + sante.apercu(46), 38);
            var metriques = Banc.obtenir(client, "/actuator/metrics");
            Console.ligne("GET /actuator/metrics",
                    metriques.valeur() + (metriques.valeur() == 401
                            ? " — protege par la chaine de filtres" : ""), 38);
            var beans = Banc.obtenir(client, "/actuator/beans");
            Console.ligne("GET /actuator/beans",
                    beans.valeur() + " — non expose par defaut", 38);
            System.out.println();
            Console.texte("`health` est le seul point ouvert, et c'est "
                    + "deliberement le seul dont un orchestrateur a besoin. "
                    + "`beans`, `env` ou `heapdump` existent aussi et "
                    + "publieraient la configuration complete de "
                    + "l'application : il faut les demander, un par un, dans "
                    + "`management.endpoints.web.exposure.include`.");
        }
        Console.titre(6, "LE MEME CODE, DEUX PROFILS");
        try (var banc = Banc.demarrer("prod",
                "spring.jpa.hibernate.ddl-auto=create-drop")) {
            Console.tableau(List.of("profil actif", "health.show-details",
                    "jpa.hibernate.ddl-auto (declare)"), List.of(
                    List.of("dev", proprietesDev.get(0), proprietesDev.get(1)),
                    List.of("prod",
                            String.valueOf(banc.environnement().getProperty(
                                    "management.endpoint.health.show-details",
                                    "(defaut)")),
                            declare("prod", "ddl-auto"))),
                    List.of(16, 24, 34));
            System.out.println();
            Console.texte("Une seule classe, un seul jar, deux comportements. "
                    + "Le code n'a pas ete recompile entre les deux lignes — "
                    + "c'est `SPRING_PROFILES_ACTIVE` qui a change.");
            System.out.println();
            Console.sousTitre("Ce que `application.yml` declare pour prod :");
            for (var ligne : declarations("prod")) {
                Console.texte(ligne, 6);
            }
            System.out.println();
            Console.texte("`${DB_URL:...}` : la valeur vient de "
                    + "l'environnement, et le texte apres `:` n'est qu'un "
                    + "repli pour que ce chapitre demarre sans base. Le depot "
                    + "ne contient donc jamais l'adresse de la vraie base, ni "
                    + "son mot de passe — c'est la regle que le cours enonce, "
                    + "et elle se verifie en lisant le fichier.");
            System.out.println();
            var sante = Banc.obtenir(banc.anonyme(), "/actuator/health");
            Console.ligne("GET /actuator/health (profil prod)",
                    sante.valeur() + " — " + sante.apercu(46), 38);
            System.out.println();
            Console.texte("La meme route, le meme code, deux reponses. En "
                    + "prod, `show-details: never` : l'orchestrateur apprend "
                    + "que le service va bien, et personne n'apprend de quoi "
                    + "il depend. La liste des dependances d'un service est "
                    + "une information qu'on ne publie pas.");
            System.out.println();
            Console.texte("⚠️ Ce demarrage force `ddl-auto=create-drop` : le "
                    + "profil prod dit `validate`, et il a raison — mais il "
                    + "n'y a ici aucune base migree a valider. Le forcage est "
                    + "sur la ligne de commande, visible ; le fichier de "
                    + "configuration, lui, reste juste.");
        }

        Console.titre(7, "CE QUE LE CHAPITRE SUIVANT MESURE");
        Console.texte("Ce qu'une entite renvoyee telle quelle laisse fuir, et "
                + "le ProblemDetail que Spring produit tout seul quand une "
                + "donnee entrante est invalide.");
        System.out.println();
    }

    private static void montrer(
            Map<String, ConditionEvaluationReport.ConditionAndOutcomes> decisions,
            String fragment, int combien) {
        var trouvee = decisions.entrySet().stream()
                .filter(e -> e.getKey().contains(fragment))
                .findFirst();
        if (trouvee.isEmpty()) {
            Console.ligne("  " + fragment, "non evaluee sur ce classpath", 40);
            return;
        }
        Console.sousTitre(courte(trouvee.get().getKey()) + " — "
                + (trouvee.get().getValue().isFullMatch() ? "RETENUE" : "ecartee"));
        int vues = 0;
        for (var issue : trouvee.get().getValue()) {
            if (vues++ >= combien) {
                break;
            }
            Console.texte("→ " + issue.getOutcome().getMessage(), 6);
        }
    }

    /** Le nom de la classe d'auto-configuration, sans son paquet. */
    private static String courte(String source) {
        int point = source.lastIndexOf('.');
        return point < 0 ? source : source.substring(point + 1);
    }

    /**
     * Ce que le fichier {@code application.yml} DECLARE pour un profil.
     *
     * <p>⚠️ Et non ce que l'environnement rend. Le banc d'essai force une
     * base par démarrage — sans quoi deux contextes ouverts en même temps se
     * détruiraient mutuellement leur schéma. Lire l'environnement afficherait
     * donc l'URL du banc, pas celle du fichier, et le chapitre montrerait le
     * contraire de ce qu'il affirme.
     */
    private static List<String> declarations(String profil) {
        var lignes = new java.util.ArrayList<String>();
        boolean dedans = false;
        for (var ligne : fichierDeConfiguration().lines().toList()) {
            if (ligne.strip().startsWith("on-profile:")) {
                dedans = ligne.contains(profil);
                continue;
            }
            if (ligne.startsWith("---")) {
                dedans = false;
            }
            if (dedans && !ligne.isBlank() && !ligne.strip().startsWith("#")) {
                lignes.add(ligne);
            }
        }
        return lignes;
    }

    /** La valeur déclarée pour une clé, dans le document de ce profil. */
    private static String declare(String profil, String cle) {
        for (var ligne : declarations(profil)) {
            if (ligne.strip().startsWith(cle + ":")) {
                return ligne.strip().substring(cle.length() + 1).strip();
            }
        }
        return "(non declare)";
    }

    private static String fichierDeConfiguration() {
        try (var flux = Chapitre2Boot.class.getResourceAsStream(
                "/application.yml")) {
            return flux == null ? "" : new String(flux.readAllBytes(),
                    java.nio.charset.StandardCharsets.UTF_8);
        } catch (java.io.IOException erreur) {
            return "";
        }
    }

    /**
     * Cette bibliothèque est-elle réellement là ?
     *
     * <p>⚠️ On interroge le <strong>chargeur de classes</strong>, et non
     * {@code java.class.path}. La première version lisait cette propriété et
     * annonçait « ABSENT » des bibliothèques pourtant présentes : sous
     * {@code exec:java}, le programme tourne dans la JVM de Maven avec un
     * chargeur dédié, et {@code java.class.path} décrit Maven, pas nous.
     */
    private static boolean chargeable(String classe) {
        try {
            Class.forName(classe, false, Chapitre2Boot.class.getClassLoader());
            return true;
        } catch (ClassNotFoundException | LinkageError absente) {
            return false;
        }
    }

    /** Ce que chaque starter apporte, et la classe qui le prouve. */
    private record Apport(String starter, String bibliotheque,
                          String classeTemoin) {
    }

    private static final List<Apport> APPORTS = List.of(
            new Apport("starter-web", "spring-webmvc",
                    "org.springframework.web.servlet.DispatcherServlet"),
            new Apport("starter-web", "tomcat-embed-core",
                    "org.apache.catalina.startup.Tomcat"),
            new Apport("starter-web", "jackson-databind",
                    "tools.jackson.databind.ObjectMapper"),
            new Apport("starter-validation", "jakarta.validation-api",
                    "jakarta.validation.Valid"),
            new Apport("starter-validation", "hibernate-validator",
                    "org.hibernate.validator.HibernateValidator"),
            new Apport("starter-data-jpa", "hibernate-core",
                    "org.hibernate.SessionFactory"),
            new Apport("starter-data-jpa", "spring-data-jpa",
                    "org.springframework.data.jpa.repository.JpaRepository"),
            new Apport("starter-data-jpa", "HikariCP",
                    "com.zaxxer.hikari.HikariDataSource"),
            new Apport("starter-security", "spring-security-web",
                    "org.springframework.security.web.FilterChainProxy"),
            new Apport("starter-security", "spring-security-config",
                    "org.springframework.security.config.annotation.web."
                    + "builders.HttpSecurity"),
            new Apport("starter-actuator", "micrometer-core",
                    "io.micrometer.core.instrument.MeterRegistry"));
}
