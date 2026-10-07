package fr.portail.chapitres;

import fr.portail.domaine.Offre;
import fr.portail.domaine.OffreRepository;
import java.lang.reflect.Field;
import java.util.List;

/**
 * Chapitre 2 — Spring Boot : l'API REST.
 *
 * <pre>
 *   mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre2Api
 * </pre>
 *
 * <p>Une VRAIE application demarre ici, sur un port libre, et on l'interroge
 * avec le client HTTP du JDK. Ce chapitre mesure trois choses : ce qu'un
 * contrat rend vraiment, ce qu'un DTO cache que l'entite exposerait, et ce
 * que la validation refuse AVANT d'atteindre le metier.
 */
public final class Chapitre2Api {

    private Chapitre2Api() {
    }

    public static void main(String[] args) {
        try (Banc banc = Banc.demarrer()) {
            System.out.println("""
                    1. LE CONTRAT : UNE URL, UN VERBE, UN CODE DE STATUT
                    """);
            System.out.printf("   Le portail ecoute sur %s%n%n", banc.url());

            String jetonRh = banc.connecter("awa", "motdepasse");

            System.out.printf("   %-42s %-8s %s%n",
                              "APPEL", "STATUT", "CE QUE LE STATUT DIT");
            ligne(banc.get("/api/offres", null),
                  "GET    /api/offres", "la liste, publique");
            ligne(banc.get("/api/offres/1", null),
                  "GET    /api/offres/1", "une ressource");
            ligne(banc.get("/api/offres/999", null),
                  "GET    /api/offres/999", "⚠️ introuvable, pas 200 + null");
            ligne(banc.post("/api/offres", """
                    {"titre":"Developpeur Go","pile":"devops",
                     "salaireEnKiloEuros":55,"entrepriseId":1}
                    """, jetonRh),
                  "POST   /api/offres  (avec ROLE_RH)", "cree, + en-tete Location");
            ligne(banc.post("/api/offres", """
                    {"titre":"Developpeur Go","pile":"devops",
                     "salaireEnKiloEuros":55,"entrepriseId":1}
                    """, null),
                  "POST   /api/offres  (sans jeton)", "⚠️ 401 : connecte-toi");
            String jetonSimple = banc.connecter("bilal", "motdepasse");
            ligne(banc.post("/api/offres", """
                    {"titre":"Developpeur Go","pile":"devops",
                     "salaireEnKiloEuros":55,"entrepriseId":1}
                    """, jetonSimple),
                  "POST   /api/offres  (sans ROLE_RH)", "⚠️ 403 : pas le droit");

            System.out.println("""

                   ⚠️ LE CODE DE STATUT FAIT PARTIE DU CONTRAT, autant que le
                   JSON. Rendre 200 partout oblige React a lire le corps pour
                   savoir ce qui s'est passe — et a inventer sa propre
                   convention, differente de celle du voisin.

                   Et le 404 n'est pas une erreur du serveur : c'est une
                   reponse. Le distinguer d'un 500 est ce qui permet a une
                   interface d'afficher « offre supprimee » plutot que
                   « une erreur est survenue ».

                   ⚠️ LISEZ LES DEUX DERNIERES LIGNES ENSEMBLE : 401 et
                   403 ne disent pas la meme chose. 401 : « je ne sais pas
                   qui tu es » — React redirige vers la connexion. 403 :
                   « je sais qui tu es, et tu n'as pas le droit » — React
                   affiche un refus. Les confondre envoie un utilisateur
                   deja connecte sur un formulaire de connexion, en boucle.

                   Et le defaut de Spring Security est de rendre 403 dans
                   les DEUX cas : il faut poser un `authenticationEntryPoint`
                   pour obtenir le 401. C'est trois lignes, et c'est ce que
                   fait `ConfigurationSecurite`.
                """);

            System.out.println("""
                    2. LA MESURE QUI TRANCHE : CE QUE L'ENTITE EXPOSERAIT
                    """);
            OffreRepository repository = banc.bean(OffreRepository.class);

            System.out.printf("   %-26s %s%n", "CHAMPS DE L'ENTITE JPA",
                              champs(Offre.class));
            System.out.printf("   %-26s %s%n", "CHAMPS DU DTO PUBLIC",
                              champs(fr.portail.api.OffreDto.class));
            System.out.println();
            System.out.printf("   Le JSON que l'API rend :%n%n      %s%n",
                    banc.get("/api/offres/1", null).corps());

            System.out.println("""

                   ⚠️ Les deux listes ne se ressemblent pas, et c'est le
                   point. L'entite porte `entreprise`, un OBJET : serialisee
                   telle quelle, elle entraine toute la jointure — et, sur
                   une relation bidirectionnelle, une recursion infinie que
                   Jackson signale par une pile de mille lignes.

                   Le DTO, lui, expose un nom et une ville. Renommer la
                   colonne `salaire_ke` devient une migration Flyway, pas un
                   deploiement du front.

                   ⚠️ Et il y a pire que la structure : les CHAMPS. Une
                   entite `Compte` serialisee expose son empreinte de mot de
                   passe. Ce n'est pas theorique — c'est la fuite la plus
                   banale d'une API ecrite vite.
                """);

            System.out.println("""
                    3. LA VALIDATION EST A LA FRONTIERE, PAS DANS LE METIER
                    """);
            System.out.printf("   %-46s %-8s %s%n",
                              "CORPS ENVOYE", "STATUT", "CHAMP FAUTIF");
            validation(banc, jetonRh, """
                    {"titre":"","pile":"java","salaireEnKiloEuros":48,"entrepriseId":1}
                    """, "titre vide");
            validation(banc, jetonRh, """
                    {"titre":"Dev","pile":"cobol","salaireEnKiloEuros":48,"entrepriseId":1}
                    """, "pile inconnue");
            validation(banc, jetonRh, """
                    {"titre":"Dev","pile":"java","salaireEnKiloEuros":5,"entrepriseId":1}
                    """, "salaire hors bornes");
            validation(banc, jetonRh, """
                    {"titre":"Dev","pile":"java","salaireEnKiloEuros":48,"entrepriseId":999}
                    """, "entreprise inexistante");

            System.out.println("""

                   Les trois premieres n'ont jamais atteint le service :
                   elles sont refusees par `@Valid`, a la frontiere. La
                   quatrieme, si — parce qu'« cette entreprise existe-t-elle »
                   est une regle METIER, pas une contrainte de format.

                   ⚠️ C'est la ligne de partage, et elle se trace une fois
                   pour toutes : la validation verifie la FORME, le service
                   verifie la COHERENCE. Mettre la seconde dans une annotation
                   demanderait a la couche web d'ouvrir la base.

                   ⚠️ Et les erreurs sont NORMALISEES en `problem+json`
                   (RFC 9457), champ par champ. Sans cela, une API rend trois
                   formats d'erreur differents — celui de Spring, celui de la
                   validation, le message brut d'une exception — et React
                   doit traiter les trois.
                """);

            System.out.println("""
                    4. LE CONTROLEUR EST MINCE, ET CELA SE VERIFIE
                    """);
            System.out.printf("      lignes du controleur   : %d%n",
                              lignesDe("OffreControleur"));
            System.out.printf("      lignes du service      : %d%n",
                              lignesDe("OffreService"));
            System.out.println("""

                   Le controleur ne contient ni `if` metier, ni SQL, ni
                   `@Transactional`. Il lit la requete, delegue, choisit un
                   statut. C'est cette maigreur qui rend le service testable
                   SANS serveur — et qui fait qu'un changement d'API ne
                   touche pas au metier.

                   ⚠️ La transaction vit dans le SERVICE, et ce n'est pas un
                   detail de rangement : une transaction delimite une
                   operation METIER, pas une requete HTTP. Au-dessus, on en
                   ouvrirait une pour servir une page d'erreur.
                """);
        }
    }

    private static void ligne(Banc.Reponse reponse, String appel, String sens) {
        System.out.printf("   %-42s %-8d %s%n", appel, reponse.statut(), sens);
    }

    private static void validation(Banc banc, String jeton, String corps,
                                   String attendu) {
        Banc.Reponse reponse = banc.post("/api/offres", corps, jeton);
        String champ = reponse.corps().contains("champs")
                ? Banc.entre(reponse.corps(), "\"champs\":{\"", "\"")
                : "(refus du service)";
        System.out.printf("   %-46s %-8d %s%n",
                          attendu, reponse.statut(), champ);
    }

    /**
     * Les champs, AVEC LEUR TYPE. C'est le type qui fait la difference :
     * l'entite porte un objet `Entreprise`, le DTO porte deux `String`.
     */
    private static String champs(Class<?> type) {
        List<String> noms = java.util.Arrays.stream(type.getDeclaredFields())
                .filter(champ -> !champ.isSynthetic())
                .map(champ -> champ.getName() + " : "
                              + champ.getType().getSimpleName())
                .toList();
        return String.join(", ", noms);
    }

    private static long lignesDe(String classe) {
        java.nio.file.Path chemin = java.nio.file.Path.of(
                "src/main/java/fr/portail/api/" + classe + ".java");
        if (!java.nio.file.Files.isReadable(chemin)) {
            chemin = java.nio.file.Path.of(
                    "../src/main/java/fr/portail/api/" + classe + ".java");
        }
        try (var lignes = java.nio.file.Files.lines(chemin)) {
            // On compte le CODE : ni les lignes vides, ni les commentaires.
            return lignes.map(String::strip)
                    .filter(ligne -> !ligne.isEmpty())
                    .filter(ligne -> !ligne.startsWith("//")
                                     && !ligne.startsWith("*")
                                     && !ligne.startsWith("/*"))
                    .count();
        } catch (java.io.IOException erreur) {
            return -1;
        }
    }
}
