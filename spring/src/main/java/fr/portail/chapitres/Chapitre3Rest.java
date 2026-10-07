package fr.portail.chapitres;

import fr.portail.commun.Banc;
import fr.portail.commun.Console;
import fr.portail.offre.OffreService;
import java.util.List;

/**
 * Chapitre 3 — API REST et validation.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre3Rest
 * </pre>
 *
 * <p>Deux affirmations du cours, mesurées sur de vraies requêtes HTTP :
 * « ne jamais exposer ses entités » — on compare les deux JSON, et on
 * cherche dedans ce qui n'aurait jamais dû sortir ; et « la validation
 * contrôle à l'entrée, <em>avant</em> qu'elle n'atteigne votre logique
 * métier » — un compteur dans le service dit si elle l'a atteinte.
 */
public final class Chapitre3Rest {

    private Chapitre3Rest() {
    }

    public static void main(String[] args) {
        Console.utf8();

        try (var banc = Banc.demarrer()) {
            var client = banc.anonyme();
            var service = banc.bean(OffreService.class);

            Console.titre(1, "CE QU'UNE ENTITE LAISSE FUIR");
            var parDto = Banc.obtenir(client, "/api/public/offres");
            var parEntite = Banc.obtenir(client, "/api/public/offres/entites-brutes");
            Console.sousTitre("GET /api/public/offres — la reponse construite "
                    + "avec un DTO :");
            Console.texte(premierObjet(parDto.corps()), 6);
            Console.sousTitre("GET /api/public/offres/entites-brutes — l'entite "
                    + "telle quelle :");
            Console.texte(premierObjet(parEntite.corps()), 6);
            System.out.println();
            Console.tableau(List.of("ce qu'on cherche dans la reponse",
                    "avec le DTO", "avec l'entite"), List.of(
                    ligne("salaireReel", parDto, parEntite),
                    ligne("noteInterne", parDto, parEntite),
                    ligne("contactEmail", parDto, parEntite),
                    ligne("\"id\"", parDto, parEntite)),
                    List.of(36, 14, 16));
            System.out.println();
            Console.texte("`salaireReel` est ce que l'entreprise est prete a "
                    + "payer ; `noteInterne` dit « rachat en cours, ne pas "
                    + "diffuser ». Aucune de ces deux colonnes n'a ete "
                    + "exposee volontairement : elles sont sorties parce "
                    + "qu'elles sont dans la table, et que la route a rendu "
                    + "la table.");
            System.out.println();
            Console.texte("Le DTO n'est pas une couche de plus par gout de "
                    + "l'architecture. C'est la seule facon de repondre a la "
                    + "question « que publie cette route ? » en lisant un "
                    + "fichier de vingt lignes plutot qu'un schema de base.");

            Console.titre(2, "UNE DONNEE INVALIDE N'ATTEINT PAS LE SERVICE");
            service.remettreAZeroLesEntrees();
            var invalide = Banc.poster(client, "/api/public/offres", """
                    {"titre": "", "salaireMin": -5,
                     "contactEmail": "pas-un-courriel", "entreprise": "Nordeau"}
                    """);
            Console.ligne("POST avec trois champs fautifs",
                    String.valueOf(invalide.valeur()), 38);
            Console.ligne("entrees dans OffreService.creer",
                    String.valueOf(service.entrees()), 38);
            Console.ligne("Content-Type de la reponse",
                    invalide.entetes().getOrDefault("Content-Type", "(aucun)"), 38);
            System.out.println();
            Console.sousTitre("Le corps :");
            for (var ligne : joliJson(invalide.corps())) {
                Console.texte(ligne, 6);
            }
            System.out.println();
            Console.texte("Le compteur du service vaut zero. La validation "
                    + "n'est pas un controle poli en debut de methode : elle "
                    + "est AVANT la methode, dans la chaine de traitement de "
                    + "Spring MVC. Le code metier n'a jamais vu ces donnees.");

            Console.titre(3, "CE QUE « SPRING LE FAIT TOUT SEUL » NE COUVRE PAS");
            Console.texte("Le meme POST, sur la MEME application, demarree "
                    + "sans `spring.mvc.problemdetails.enabled` :");
            System.out.println();
            String sansLaPropriete;
            String typeSansLaPropriete;
            try (var brut = Banc.demarrer("dev",
                    "spring.mvc.problemdetails.enabled=false")) {
                var reponse = Banc.poster(brut.anonyme(), "/api/public/offres", """
                        {"titre": "", "salaireMin": -5,
                         "contactEmail": "pas-un-courriel", "entreprise": "Nordeau"}
                        """);
                sansLaPropriete = reponse.valeur() + ", corps de "
                        + (reponse.corps() == null ? 0 : reponse.corps().length())
                        + " caractere(s)";
                typeSansLaPropriete = reponse.entetes()
                        .getOrDefault("Content-Type", "(aucun)");
            }
            Console.ligne("problemdetails.enabled = false",
                    sansLaPropriete, 38);
            Console.ligne("   Content-Type", typeSansLaPropriete, 38);
            Console.ligne("problemdetails.enabled = true",
                    invalide.valeur() + ", corps de " + invalide.corps().length()
                    + " caractere(s)", 38);
            Console.ligne("   Content-Type",
                    invalide.entetes().getOrDefault("Content-Type", "(aucun)"), 38);
            System.out.println();
            Console.texte("⚠️ La propriete vaut `false` PAR DEFAUT, y compris "
                    + "en Spring Boot 4. « Spring renvoie automatiquement un "
                    + "ProblemDetail » est donc vrai a une ligne de "
                    + "configuration pres — et sans elle, le client recoit un "
                    + "400 vide, qui ne lui dit rien.");
            System.out.println();
            Console.texte("Et une fois la propriete posee, le document que "
                    + "Spring produit seul dit « Invalid request content. » "
                    + "sans nommer un seul champ. Le `champs` du JSON "
                    + "ci-dessus vient de `GestionnaireErreurs`, qui enrichit "
                    + "le document plutot que de le remplacer — sinon on "
                    + "perdrait `instance` et la coherence avec les autres "
                    + "erreurs de Spring.");

            Console.titre(4, "CE QUE LE CLIENT N'A PAS LE DROIT DE CHOISIR");
            service.remettreAZeroLesEntrees();
            var tentative = Banc.poster(client, "/api/public/offres", """
                    {"titre": "Developpeuse Java (2)", "salaireMin": 50000,
                     "contactEmail": "rh@nordeau.test", "entreprise": "Nordeau",
                     "id": 9999, "salaireReel": 1}
                    """);
            Console.ligne("POST avec `id` et `salaireReel` en plus",
                    String.valueOf(tentative.valeur()), 38);
            Console.ligne("Location", tentative.entetes()
                    .getOrDefault("Location", "(aucun)"), 38);
            Console.sousTitre("La ressource creee :");
            Console.texte(tentative.apercu(140), 6);
            System.out.println();
            Console.texte("Les deux champs en trop ont ete ignores en silence "
                    + "— c'est le reglage par defaut de Spring Boot. Ce n'est "
                    + "pas ce qui protege : ce qui protege, c'est que "
                    + "`CreerOffreDto` ne les declare pas. Un DTO qui les "
                    + "aurait declares les aurait acceptes, et le silence de "
                    + "Jackson n'y aurait rien change.");
            System.out.println();
            Console.ligne("201 plutot que 200",
                    "l'adresse de la ressource est dans `Location`", 30);

            Console.titre(5, "UNE FORME D'ERREUR, POUR TOUTE L'API");
            var inconnue = Banc.poster(client, "/api/public/offres", """
                    {"titre": "Developpeur Go", "salaireMin": 50000,
                     "contactEmail": "rh@nulle-part.test",
                     "entreprise": "Entreprise Fantome"}
                    """);
            Console.ligne("POST citant une entreprise inconnue",
                    String.valueOf(inconnue.valeur()), 38);
            Console.sousTitre("Le corps, produit par notre "
                    + "@RestControllerAdvice :");
            for (var ligne : joliJson(inconnue.corps())) {
                Console.texte(ligne, 6);
            }
            System.out.println();
            Console.tableau(List.of("champ de ProblemDetail",
                    "echec de validation", "erreur metier"), List.of(
                    comparer("type", invalide.corps(), inconnue.corps()),
                    comparer("title", invalide.corps(), inconnue.corps()),
                    comparer("status", invalide.corps(), inconnue.corps()),
                    comparer("detail", invalide.corps(), inconnue.corps())),
                    List.of(26, 26, 26));
            System.out.println();
            Console.texte("Les deux erreurs n'ont rien a voir : l'une vient de "
                    + "Spring, l'autre de notre code metier. Elles ont la "
                    + "meme forme, les memes champs, le meme type de contenu. "
                    + "Un client ecrit UN lecteur d'erreurs, pas deux — et "
                    + "c'est ce que le `@RestControllerAdvice` achete.");
            System.out.println();
            Console.texte("Sans lui, `EntrepriseInconnue` serait remontee en "
                    + "500 avec une trace : le client aurait appris le nom de "
                    + "nos classes et rien d'utile, et notre journal se "
                    + "serait rempli d'une erreur qui n'en est pas une.");

            Console.titre(6, "CE QUE LE CHAPITRE SUIVANT MESURE");
            Console.texte("Le nombre exact de requetes SQL que la liste "
                    + "ci-dessus a coute — et ce qu'un `join fetch` en fait. "
                    + "Puis deux facons de croire qu'on a une transaction "
                    + "quand on n'en a pas.");
            System.out.println();
        }
    }

    private static List<String> ligne(String cherche, Banc.Reponse dto,
                                      Banc.Reponse entite) {
        return List.of(cherche,
                dto.contient(cherche) ? "PRESENT" : "absent",
                entite.contient(cherche) ? "PRESENT" : "absent");
    }

    private static List<String> comparer(String champ, String premier,
                                         String second) {
        return List.of(champ, valeur(premier, champ), valeur(second, champ));
    }

    /** Extrait la valeur d'un champ du JSON, sans bibliothèque. */
    private static String valeur(String json, String champ) {
        if (json == null) {
            return "-";
        }
        var motif = java.util.regex.Pattern.compile(
                "\"" + champ + "\"\\s*:\\s*(\"[^\"]*\"|[^,}\\s]+)");
        var trouve = motif.matcher(json);
        if (!trouve.find()) {
            return "(absent)";
        }
        String brut = trouve.group(1).replace("\"", "");
        return brut.length() <= 24 ? brut : brut.substring(0, 21) + "...";
    }

    /** Le premier objet d'un tableau JSON, sur une ligne lisible. */
    private static String premierObjet(String json) {
        if (json == null || json.isBlank()) {
            return "(vide)";
        }
        int debut = json.indexOf('{');
        int fin = json.indexOf("},");
        String morceau = fin > debut ? json.substring(debut, fin + 1)
                : json.substring(debut, Math.min(json.length(), debut + 400));
        return morceau.replaceAll("\\s+", " ");
    }

    /** Un JSON plat coupé en lignes courtes, sans bibliothèque de mise en forme. */
    private static List<String> joliJson(String json) {
        if (json == null || json.isBlank()) {
            return List.of("(vide)");
        }
        return java.util.Arrays.stream(
                        json.replace("{", "{\n ")
                            .replace(",\"", ",\n \"")
                            .replace("}", "\n}")
                            .split("\n"))
                .map(String::strip)
                .filter(l -> !l.isEmpty())
                .toList();
    }
}
