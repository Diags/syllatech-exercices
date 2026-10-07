package fr.portail.chapitres;

import fr.portail.commun.Banc;
import fr.portail.commun.Console;
import fr.portail.erreurs.PanneMetier;
import fr.portail.mesure.CompteurDeRequetes;
import fr.portail.offre.EntrepriseRepository;
import fr.portail.offre.OffreRepository;
import fr.portail.offre.OffreService;
import java.util.List;
import org.hibernate.LazyInitializationException;

/**
 * Chapitre 4 — JPA et transactions.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre4Jpa
 * </pre>
 *
 * <p>Le cours dit : « activez {@code show-sql} en dev ; si vous voyez la même
 * requête revenir en boucle, c'est un N+1 ». Ce chapitre ne lit pas un
 * journal — il <strong>compte</strong>, avec un {@code StatementInspector}
 * branché sur Hibernate. Un N+1 devient alors un nombre, donc un test.
 *
 * <p>Puis il mesure les deux pièges que le cours nomme : l'exception vérifiée
 * qui ne déclenche pas de rollback, et l'appel interne qui contourne le
 * proxy. Dans les deux cas la question est la même, et elle a une réponse
 * entière : combien de lignes restent en base ?
 */
public final class Chapitre4Jpa {

    private Chapitre4Jpa() {
    }

    public static void main(String[] args) {
        Console.utf8();

        try (var banc = Banc.demarrer()) {
            var service = banc.bean(OffreService.class);
            var offres = banc.bean(OffreRepository.class);
            var entreprises = banc.bean(EntrepriseRepository.class);

            Console.titre(1, "LE JEU DE DONNEES");
            Console.ligne("entreprises", String.valueOf(entreprises.count()), 24);
            Console.ligne("offres", String.valueOf(offres.count()), 24);
            Console.ligne("l'instrument",
                    "hibernate.session_factory.statement_inspector", 24);
            System.out.println();
            Console.texte("Hibernate appelle cet inspecteur avec chaque "
                    + "instruction SQL, juste avant de l'envoyer. Ce qui suit "
                    + "n'est pas une estimation : c'est la liste exacte de ce "
                    + "qui est parti vers la base.");

            Console.titre(2, "LE N+1, COMPTE");
            var naives = CompteurDeRequetes.pendant(service::listerOffresNaivement);
            var jointes = CompteurDeRequetes.pendant(service::listerOffres);
            Console.tableau(List.of("la methode appelee", "instructions SQL",
                    "selects sur `entreprise`"), List.of(
                    List.of("findAll()", String.valueOf(naives.size()),
                            String.valueOf(CompteurDeRequetes.selectsSur(
                                    naives, "entreprise"))),
                    List.of("findAllAvecEntreprise()", String.valueOf(jointes.size()),
                            String.valueOf(CompteurDeRequetes.selectsSur(
                                    jointes, "entreprise")))),
                    List.of(26, 20, 26));
            System.out.println();
            Console.sousTitre("Ce que `findAll()` a reellement envoye :");
            for (int i = 0; i < Math.min(4, naives.size()); i++) {
                Console.texte((i + 1) + ". " + CompteurDeRequetes.resumer(naives.get(i)), 6);
            }
            if (naives.size() > 4) {
                Console.texte("... et " + (naives.size() - 4) + " autre(s), "
                        + "toutes de la meme forme", 6);
            }
            System.out.println();
            Console.sousTitre("Ce que `findAllAvecEntreprise()` a envoye :");
            for (var requete : jointes) {
                Console.texte(CompteurDeRequetes.resumer(requete), 6);
            }
            System.out.println();
            Console.texte("Une requete pour la liste, puis une par entreprise "
                    + "distincte : c'est le N+1. Il ne vient pas de "
                    + "`findAll()` — qui est innocent tant qu'on ne touche a "
                    + "rien — mais du moment ou le code lit "
                    + "`offre.getEntreprise()`. Hibernate honore alors la "
                    + "promesse `LAZY`, une entreprise a la fois.");
            System.out.println();
            Console.texte("Sur quatre entreprises, l'ecart parait modeste. Sur "
                    + "une page de deux cents lignes, ce sont deux cents "
                    + "aller-retours reseau la ou un seul suffisait — et "
                    + "c'est la panne de performance la plus repandue des "
                    + "applications JPA.");

            Console.titre(3, "`join fetch` N'EST PAS UNE JOINTURE ORDINAIRE");
            var sansFetch = CompteurDeRequetes.pendant(
                    () -> offres.findByEntrepriseVille("Lyon"));
            Console.ligne("findByEntrepriseVille(\"Lyon\")",
                    sansFetch.size() + " instruction(s)", 34);
            Console.texte(CompteurDeRequetes.resumer(sansFetch.getFirst()), 6);
            System.out.println();
            Console.texte("Cette requete derivee JOINT bien la table "
                    + "`entreprise` — pour filtrer sur la ville. Elle ne la "
                    + "CHARGE pas : le mot `fetch` est ce qui dit a Hibernate "
                    + "de remplir l'association au passage. Une jointure sans "
                    + "`fetch` filtre et laisse le N+1 intact.");

            Console.titre(4, "LIRE UNE ASSOCIATION HORS DE LA TRANSACTION");
            var detachee = offres.findAll().getFirst();
            String verdict;
            try {
                verdict = "lue sans erreur : " + detachee.getEntreprise().getNom();
            } catch (LazyInitializationException erreur) {
                verdict = "LazyInitializationException";
            }
            Console.ligne("offre.getEntreprise().getNom()", verdict, 36);
            System.out.println();
            Console.texte("L'entite a survecu a la transaction ; son "
                    + "association, non. C'est pourquoi ce projet convertit "
                    + "en DTO DANS le service, la ou la session est encore "
                    + "ouverte — et non dans le controleur, ou elle ne l'est "
                    + "plus.");
            System.out.println();
            Console.texte("⚠️ Cette ligne depend d'un reglage. "
                    + "`spring.jpa.open-in-view` est ACTIF par defaut : il "
                    + "garde la session ouverte jusqu'a la fin de la requete "
                    + "HTTP, et masque donc l'erreur — au prix d'une "
                    + "connexion retenue pendant toute la serialisation. Ce "
                    + "projet le coupe dans `application.yml`, et c'est ce "
                    + "qui rend l'echec visible ici.");
            System.out.println();
            Console.ligne("spring.jpa.open-in-view",
                    banc.environnement().getProperty(
                            "spring.jpa.open-in-view", "(defaut : true)"), 34);

            Console.titre(5, "QUATRE FACONS DE CROIRE QU'ON A UNE TRANSACTION");
            var lignes = new java.util.ArrayList<List<String>>();
            lignes.add(mesurer(service, "RuntimeException", "annule",
                    () -> {
                        try {
                            service.demoRollbackSurRuntime();
                        } catch (IllegalStateException attendue) {
                            // c'est le cas mesure
                        }
                    }));
            lignes.add(mesurer(service, "exception VERIFIEE", "annule",
                    () -> {
                        try {
                            service.demoPasDeRollbackSurExceptionVerifiee();
                        } catch (PanneMetier attendue) {
                            // c'est le cas mesure
                        }
                    }));
            lignes.add(mesurer(service, "la meme + rollbackFor", "annule",
                    () -> {
                        try {
                            service.demoRollbackForSurExceptionVerifiee();
                        } catch (PanneMetier attendue) {
                            // c'est le cas mesure
                        }
                    }));
            lignes.add(mesurer(service, "appel INTERNE a la 1re", "annule",
                    () -> service.demoAppelInterne()));
            Console.tableau(List.of("elle ecrit 2 lignes, puis echoue par",
                    "reste en base", "verdict"), lignes, List.of(40, 18, 14));
            System.out.println();
            Console.texte("Les lignes 2 et 4 sont les deux pieges du cours, et "
                    + "ils se ressemblent : dans les deux cas l'annotation "
                    + "`@Transactional` est bien ecrite, bien orthographiee, "
                    + "au bon endroit — et elle ne sert a rien.");
            System.out.println();
            Console.texte("Ligne 2 : Spring n'annule que sur une exception NON "
                    + "verifiee. Une exception verifiee est consideree comme "
                    + "un resultat metier attendu, pas comme une panne. "
                    + "`rollbackFor` corrige, a condition de savoir qu'il "
                    + "existe — c'est la ligne 3.");
            System.out.println();
            Console.texte("Ligne 4 : `this.methodeAnnotee()` ne passe pas par "
                    + "le proxy que Spring a place autour du bean. "
                    + "L'annotation n'est pas lue, et chaque `save` se valide "
                    + "dans sa propre petite transaction. Rien dans le code "
                    + "appelant ne le laisse voir.");

            Console.titre(6, "CE QUE LE CHAPITRE SUIVANT MESURE");
            Console.texte("La chaine de filtres, filtre par filtre, dans "
                    + "l'ordre ou Spring Security les execute — et la preuve "
                    + "qu'un refus n'atteint jamais le controleur.");
            System.out.println();
        }
    }

    private static List<String> mesurer(OffreService service, String quoi,
                                        String attendu, Runnable geste) {
        service.effacerLesEssais();
        long avant = service.combien();
        geste.run();
        long apres = service.combien();
        long ecrites = apres - avant;
        service.effacerLesEssais();
        return List.of(quoi, ecrites + " ligne(s) sur 2",
                ecrites == 0 ? "annule" : "VALIDE");
    }
}
