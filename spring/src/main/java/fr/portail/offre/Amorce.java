package fr.portail.offre;

import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * Le jeu de données du portail, posé au démarrage.
 *
 * <p>Quatre entreprises, dix offres. Les nombres comptent : le chapitre 4
 * mesure un N+1 et annonce « 1 + 4 requêtes » — il faut donc que quatre
 * entreprises distinctes portent ces dix offres, sans quoi le cache de
 * premier niveau d'Hibernate masquerait une partie du problème et le chiffre
 * mesuré ne correspondrait plus à ce que le chapitre explique.
 *
 * <p>Un {@link ApplicationRunner} plutôt qu'un {@code data.sql} : l'ordre
 * entre la création du schéma par Hibernate et l'exécution du script SQL
 * demande {@code spring.jpa.defer-datasource-initialization}, un réglage que
 * l'on découvre en général par une erreur. Ici, le code s'exécute après que
 * tout est prêt, et il n'y a rien à savoir.
 */
@Component
public class Amorce implements ApplicationRunner {

    private final EntrepriseRepository entreprises;

    Amorce(EntrepriseRepository entreprises) {
        this.entreprises = entreprises;
    }

    @Override
    @Transactional
    public void run(ApplicationArguments args) {
        if (entreprises.count() > 0) {
            return;
        }
        poser("Nordeau", "Lyon", "paie mal, mais forme bien", new String[][]{
            {"Developpeuse Java", "48000", "55000"},
            {"Developpeur Java senior", "62000", "70000"},
            {"Architecte logiciel", "75000", "82000"},
        });
        poser("Belleville Data", "Paris", "rachat en cours, ne pas diffuser",
            new String[][]{
                {"Ingenieure donnees", "52000", "58000"},
                {"Analyste BI", "44000", "47000"},
                {"Data engineer", "56000", "61000"},
            });
        poser("Grand Sud Cloud", "Toulouse", "budget gele au T3", new String[][]{
            {"Ingenieur plateforme", "54000", "59000"},
            {"Ingenieure SRE", "58000", "64000"},
        });
        poser("Atelier Mobile", "Nantes", "client unique, risque eleve",
            new String[][]{
                {"Developpeuse mobile", "46000", "51000"},
                {"Developpeur mobile", "46000", "50000"},
            });
    }

    private void poser(String nom, String ville, String note,
                       String[][] descriptions) {
        var entreprise = new Entreprise(nom, ville, note);
        for (var description : descriptions) {
            entreprise.ajouter(new Offre(description[0],
                    Integer.parseInt(description[1]),
                    Integer.parseInt(description[2]),
                    "recrutement@" + nom.toLowerCase(java.util.Locale.ROOT)
                            .replace(' ', '-') + ".test"));
        }
        entreprises.save(entreprise);
    }
}
