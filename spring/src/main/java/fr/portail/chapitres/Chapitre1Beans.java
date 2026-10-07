package fr.portail.chapitres;

import fr.portail.coeur.Brouillon;
import fr.portail.coeur.CompteurDeVues;
import fr.portail.coeur.CompteurSur;
import fr.portail.coeur.CycleDeVie;
import fr.portail.commun.Banc;
import fr.portail.commun.Console;
import fr.portail.offre.OffreController;
import fr.portail.offre.OffreService;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;
import org.springframework.beans.factory.BeanCurrentlyInCreationException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;
import org.springframework.context.annotation.Bean;

/**
 * Chapitre 1 — Le cœur de Spring : IoC et beans.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre1Beans
 * </pre>
 *
 * <p>Le cours énonce une règle d'or : « un bean singleton doit être sans
 * état ». Ce chapitre ne la répète pas — il lance <strong>deux cents requêtes
 * concurrentes</strong> sur un singleton avec état et compte ce qui casse.
 * Deux choses cassent, et la seconde est bien pire que la première.
 */
public final class Chapitre1Beans {

    private Chapitre1Beans() {
    }

    public static void main(String[] args) throws Exception {
        Console.utf8();

        Console.titre(1, "LE CONTENEUR, ET CE QU'IL A CONSTRUIT");
        try (var banc = Banc.demarrer()) {
            var contexte = banc.contexte();
            Console.ligne("beans definis", String.valueOf(
                    contexte.getBeanDefinitionCount()), 34);
            Console.ligne("dont les notres",
                    String.valueOf(java.util.Arrays.stream(
                            contexte.getBeanDefinitionNames())
                            .filter(nom -> {
                                var type = contexte.getType(nom);
                                return type != null
                                        && type.getName().startsWith("fr.portail");
                            }).count()), 34);
            Console.ligne("le reste vient de",
                    "l'auto-configuration (chapitre 2)", 34);
            System.out.println();
            Console.texte("Nous en avons ecrit une quinzaine. Le conteneur en "
                    + "a construit dix fois plus : une source de donnees, un "
                    + "gestionnaire de transactions, un serialiseur JSON, une "
                    + "chaine de filtres. C'est le chapitre 2 qui explique "
                    + "d'ou ils sortent.");

            Console.titre(2, "SINGLETON, PROTOTYPE : DEUX FOIS LE MEME NOM");
            var premierService = banc.bean(OffreService.class);
            var secondService = banc.bean(OffreService.class);
            Console.ligne("le meme OffreService, deux fois",
                    premierService == secondService
                            ? "le MEME objet (singleton)" : "deux objets", 38);
            var premierBrouillon = banc.bean(Brouillon.class);
            var secondBrouillon = banc.bean(Brouillon.class);
            Console.ligne("le meme Brouillon, deux fois",
                    premierBrouillon == secondBrouillon
                            ? "le meme objet"
                            : "deux objets (prototype) — n° "
                              + premierBrouillon.numero() + " et n° "
                              + secondBrouillon.numero(), 38);
            System.out.println();
            Console.texte("Le singleton est le defaut, et c'est le bon defaut "
                    + ": un service sans etat n'a aucune raison d'exister en "
                    + "plusieurs exemplaires. Le prototype est l'exception — "
                    + "pour ce qui porte un etat qui appartient a un seul "
                    + "appelant.");

            Console.titre(3, "L'ORDRE DE CONSTRUCTION, TEL QUE SPRING L'A SUIVI");
            for (var etape : CycleDeVie.journal()) {
                Console.texte(etape, 5);
            }
            System.out.println();
            Console.texte("La premiere ligne est celle qui compte : au moment "
                    + "du constructeur, la dependance injectee PAR LE "
                    + "CONSTRUCTEUR est deja la. Le chapitre 5 du cours Java "
                    + "moderne dirait : l'objet est valide des sa creation. "
                    + "C'est ce que l'injection par champ ne permet pas — on "
                    + "y verra `null`, comme la section 5 le montre.");

            Console.titre(4, "DEUX CENTS REQUETES SUR UN SINGLETON AVEC ETAT");
            int requetes = 200;
            var client = banc.anonyme();
            var croisements = ConcurrentHashMap.<String>newKeySet();
            var envoyees = new AtomicInteger();
            try (var executeur = Executors.newVirtualThreadPerTaskExecutor()) {
                for (int i = 0; i < requetes; i++) {
                    String utilisateur = "client-" + i;
                    executeur.submit(() -> {
                        var reponse = Banc.obtenir(client,
                                "/api/public/offres/vue?utilisateur=" + utilisateur);
                        envoyees.incrementAndGet();
                        // Le JSON contient le nom demande et le nom que le
                        // singleton avec etat a retenu. S'ils different, la
                        // requete a lu la donnee de QUELQU'UN D'AUTRE.
                        if (!reponse.contient("\"vuParLeSingletonAvecEtat\":\""
                                + utilisateur + "\"")) {
                            croisements.add(utilisateur);
                        }
                        return null;
                    });
                }
            }
            var compteurs = Banc.obtenir(client, "/api/public/offres/compteurs");
            var avecEtat = banc.bean(CompteurDeVues.class);
            var sansEtat = banc.bean(CompteurSur.class);

            Console.tableau(List.of("compteur", "attendu", "obtenu", "perdu"),
                    List.of(
                        List.of("champ `long vues++`", String.valueOf(requetes),
                                String.valueOf(avecEtat.vues()),
                                String.valueOf(requetes - avecEtat.vues())),
                        List.of("champ `AtomicLong`", String.valueOf(requetes),
                                String.valueOf(sansEtat.vues()),
                                String.valueOf(requetes - sansEtat.vues()))),
                    List.of(24, 12, 12, 10));
            System.out.println();
            Console.ligne("requetes envoyees", String.valueOf(envoyees.get()), 40);
            Console.ligne("requetes ayant lu le nom d'UN AUTRE client",
                    croisements.size() + " sur " + requetes, 44);
            System.out.println();
            Console.texte("La seconde ligne est le vrai probleme. Un compteur "
                    + "faux se remarque ; une requete qui lit le nom d'un "
                    + "autre utilisateur ne se remarque pas — jusqu'au jour "
                    + "ou c'est son panier, son dossier medical ou son "
                    + "numero de carte.");
            System.out.println();
            Console.texte("Le bean fautif ne fait rien d'exotique : il retient "
                    + "`dernierUtilisateur` dans un champ. Un seul exemplaire "
                    + "pour toute l'application, et deux cents threads qui "
                    + "ecrivent dedans. La regle « un singleton doit etre sans "
                    + "etat » n'est pas une preference de style : c'est ce "
                    + "tableau.");
            System.out.println();
            Console.ligne("ce que la route repond maintenant",
                    compteurs.apercu(48), 40);

            Console.titre(5, "TROIS FACONS D'INJECTER, UNE SEULE QUI TIENT");
            var parChamp = new AnnotationConfigApplicationContext(
                    ParChamp.class, Dependance.class);
            var beanParChamp = parChamp.getBean(ParChamp.class);
            Console.ligne("par champ : vue au constructeur",
                    beanParChamp.vueAuConstructeur(), 40);
            Console.ligne("par champ : vue apres l'injection",
                    beanParChamp.dependance() == null ? "null" : "presente", 40);
            parChamp.close();
            System.out.println();
            Console.texte("`@Autowired` sur un champ injecte APRES la "
                    + "construction. Tout ce que le constructeur veut faire "
                    + "avec cette dependance trouve `null` — et un champ "
                    + "injecte ne peut pas etre `final`, donc rien ne garantit "
                    + "qu'il le restera.");
            System.out.println();
            Console.ligne("le controleur du portail",
                    OffreController.class.getDeclaredConstructors().length
                    + " constructeur(s), "
                    + java.util.Arrays.stream(
                            OffreController.class.getDeclaredFields())
                            .filter(c -> java.lang.reflect.Modifier
                                    .isFinal(c.getModifiers()))
                            .count()
                    + " champ(s) final", 40);

            Console.titre(6, "LA DEPENDANCE CIRCULAIRE, SELON LA FACON D'INJECTER");
            String parConstructeur;
            try (var cercle = new AnnotationConfigApplicationContext()) {
                cercle.register(CercleParConstructeur.class);
                cercle.refresh();
                parConstructeur = "demarre — la boucle n'a pas ete vue";
            } catch (RuntimeException erreur) {
                parConstructeur = racine(erreur) instanceof
                        BeanCurrentlyInCreationException
                        ? "REFUSE au demarrage : BeanCurrentlyInCreationException"
                        : "REFUSE : " + racine(erreur).getClass().getSimpleName();
            }
            Console.ligne("A et B s'injectent par CONSTRUCTEUR",
                    parConstructeur, 44);
            String parSetter;
            try (var cercle = new AnnotationConfigApplicationContext()) {
                cercle.register(CercleParSetter.class);
                cercle.refresh();
                parSetter = "demarre — la boucle passe inapercue";
            } catch (RuntimeException erreur) {
                parSetter = "REFUSE : " + racine(erreur).getClass().getSimpleName();
            }
            Console.ligne("les memes, injectes par CHAMP", parSetter, 44);
            System.out.println();
            Console.texte("L'injection par constructeur ne peut pas construire "
                    + "A sans B ni B sans A : elle echoue au demarrage, avec "
                    + "un message qui nomme le cycle. L'injection par champ "
                    + "construit les deux vides puis les remplit — "
                    + "l'application demarre, et la conception circulaire "
                    + "reste la, invisible, jusqu'a ce qu'elle produise un "
                    + "bug d'initialisation impossible a lire.");

            Console.titre(7, "CE QUE LE CHAPITRE SUIVANT MESURE");
            Console.texte("D'ou viennent les autres beans : le rapport "
                    + "d'auto-configuration, ligne par ligne — et ce qui se "
                    + "passe exactement quand on declare le sien.");
            System.out.println();
        }
    }

    private static Throwable racine(Throwable erreur) {
        var courante = erreur;
        while (courante.getCause() != null && courante.getCause() != courante) {
            courante = courante.getCause();
        }
        return courante;
    }

    // ── les contextes jetables des sections 5 et 6 ───────────────────────
    //
    // ⚠️ AUCUNE de ces classes ne porte @Component ni @Configuration. Elles
    // vivent dans `fr.portail.chapitres`, que PortailApplication balaie :
    // annotees, elles deviendraient des beans de l'application elle-meme —
    // et les deux `@Bean a()` ci-dessous se sont effectivement percutes au
    // demarrage avant qu'on retire les annotations. Elles sont donc
    // enregistrees a la main, dans un contexte jetable.
    //
    // Spring accepte une classe non annotee porteuse de @Bean : c'est le
    // mode « lite ». La seule difference avec @Configuration : sans lui, un
    // appel d'une methode @Bean a une autre construirait un objet neuf au
    // lieu de rendre le bean. Ici, aucune n'en appelle une autre.

    static class Dependance {
        String nom() {
            return "la dependance";
        }
    }

    static class ParChamp {

        @Autowired
        private Dependance dependance;

        private final String vueAuConstructeur;

        ParChamp() {
            // Spring n'a pas encore pu remplir le champ : il construit
            // l'objet d'abord, et l'injecte ensuite.
            this.vueAuConstructeur = dependance == null ? "null" : "presente";
        }

        String vueAuConstructeur() {
            return vueAuConstructeur;
        }

        Dependance dependance() {
            return dependance;
        }
    }

    static class CercleParConstructeur {

        static class A {
            A(B b) {
            }
        }

        static class B {
            B(A a) {
            }
        }

        @Bean
        A a(B b) {
            return new A(b);
        }

        @Bean
        B b(A a) {
            return new B(a);
        }
    }

    static class CercleParSetter {

        static class A {
            @Autowired
            B b;
        }

        static class B {
            @Autowired
            A a;
        }

        @Bean
        A a() {
            return new A();
        }

        @Bean
        B b() {
            return new B();
        }
    }
}
