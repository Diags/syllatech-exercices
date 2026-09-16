package fr.portail.chapitres;

import fr.portail.commun.Banc;
import fr.portail.commun.Console;
import fr.portail.passerelle.Passerelle;
import fr.portail.services.OffresService;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;

/**
 * Chapitre 3 — Gateway et résilience.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre3Passerelle
 * </pre>
 *
 * <p>« Passé un seuil, il ouvre le circuit — les appels échouent
 * immédiatement vers un fallback. » Ce chapitre fait tomber le service pour
 * de bon, envoie des requêtes, et <strong>regarde l'état du disjoncteur</strong>
 * changer : CLOSED, puis OPEN, puis HALF_OPEN, puis CLOSED à nouveau.
 *
 * <p>Il chronomètre aussi la différence qui justifie tout le mécanisme :
 * le temps d'une réponse quand le circuit est fermé, et quand il est ouvert.
 */
public final class Chapitre3Passerelle {

    private Chapitre3Passerelle() {
    }

    public static void main(String[] args) {
        Console.utf8();

        try (var banc = Banc.complet(2)) {
            String parLaPasserelle = banc.urlPasserelle() + "/api/offres";
            Banc.attendre(() -> Banc.get(parLaPasserelle).code() == 200,
                    Duration.ofSeconds(60));

            Console.titre(1, "UNE SEULE PORTE D'ENTREE");
            var directe = Banc.get("http://localhost:"
                    + banc.portsDesInstances().getFirst() + "/offres");
            var routee = Banc.get(parLaPasserelle);
            Console.tableau(List.of("comment on appelle", "code", "reponse"),
                    List.of(
                    List.of("le service directement", String.valueOf(directe.code()),
                            court(directe.corps())),
                    List.of("par la passerelle", String.valueOf(routee.code()),
                            court(routee.corps()))),
                    List.of(24, 8, 34));
            System.out.println();
            Console.ligne("le client appelle", "/api/offres", 26);
            Console.ligne("le service expose", "/offres", 26);
            Console.ligne("qui a reecrit le chemin", "la passerelle", 28);
            System.out.println();
            Console.texte("Le client ne connait qu'une adresse et un prefixe "
                    + "public. La passerelle reecrit le chemin, demande une "
                    + "instance vivante a l'annuaire, et relaie. Le service, "
                    + "lui, ignore tout du prefixe `/api` — et c'est tant "
                    + "mieux : il peut etre appele par d'autres chemins "
                    + "demain sans changer une ligne.");
            System.out.println();
            Console.texte("⚠️ Une nuance de version, et elle coute cher : la "
                    + "passerelle a ete SCINDEE. Le "
                    + "`spring-cloud-starter-gateway` que l'on trouve dans "
                    + "tous les tutoriels ne suit plus le train ; ce sont "
                    + "`gateway-server-webmvc` et `gateway-server-webflux` "
                    + "qui le font, et les proprietes de configuration ont "
                    + "change de prefixe avec eux. Un `spring.cloud.gateway."
                    + "routes` recopie d'un article ancien est ignore en "
                    + "silence — la passerelle demarre, et aucune route "
                    + "n'existe.");

            Console.titre(2, "L'EQUILIBRAGE, VU DE LA PASSERELLE");
            OffresService.remettreAZero();
            for (int appel = 0; appel < 20; appel++) {
                Banc.get(parLaPasserelle);
            }
            var lignes = new ArrayList<List<String>>();
            OffresService.servies().forEach((port, compteur) ->
                    lignes.add(List.of("instance " + port,
                            String.valueOf(compteur.get()))));
            lignes.sort((a, b) -> a.get(0).compareTo(b.get(0)));
            Console.tableau(List.of("qui a repondu", "requetes servies"),
                    lignes, List.of(24, 20));
            Console.ligne("instances sollicitees",
                    String.valueOf(lignes.size()), 26);
            Console.ligne("total servi",
                    String.valueOf(OffresService.total()), 26);
            System.out.println();
            Console.texte("Vingt requetes envoyees a UNE adresse — celle de la "
                    + "passerelle — et deux instances qui repondent. "
                    + "Personne n'a ecrit d'adresse IP nulle part : "
                    + "`lb://offres-service` a demande la liste a l'annuaire, "
                    + "et l'equilibrage cote client a choisi.");
            System.out.println();
            Console.texte("C'est ce que le cours appelle le « load balancing "
                    + "cote client », par opposition a un repartiteur place "
                    + "devant les services. Il n'y a pas de machine "
                    + "supplementaire : c'est l'APPELANT qui choisit, a "
                    + "partir de la liste qu'il connait.");

            Console.titre(3, "UN 500 N'OUVRE PAS LE CIRCUIT");
            Passerelle.remettreAZero();
            OffresService.remettreAZero();
            Console.ligne("etat au depart", etat(banc, "offresCB"), 26);
            // On casse le service pour de bon : il repond 500.
            for (var port : banc.portsDesInstances()) {
                Banc.post("http://localhost:" + port + "/panne?active=true");
            }
            var suivi = new ArrayList<List<String>>();
            for (int appel = 1; appel <= 8; appel++) {
                var reponse = Banc.get(parLaPasserelle);
                suivi.add(List.of("appel " + appel,
                        String.valueOf(reponse.code()),
                        reponse.corps().contains("repli") ? "repli" : "service",
                        etat(banc, "offresCB")));
            }
            Console.tableau(List.of("requete", "code", "qui a repondu",
                    "etat du circuit"), suivi, List.of(12, 8, 16, 18));
            System.out.println();
            Console.ligne("replis servis",
                    String.valueOf(Passerelle.replis()), 26);
            System.out.println();
            Console.texte("Huit erreurs 500 d'affilee, et le circuit reste "
                    + "FERME. Le repli n'a jamais ete appele, et le client a "
                    + "recu huit fois l'erreur du service.");
            System.out.println();
            Console.texte("⚠️ Ce n'est pas un bug : c'est le comportement par "
                    + "defaut, et il faut le savoir. Un disjoncteur de "
                    + "passerelle compte les EXCEPTIONS — connexion refusee, "
                    + "delai depasse, aucune instance disponible. Un service "
                    + "qui repond proprement 500 a, de son point de vue, "
                    + "repondu. C'est la reponse qui est mauvaise, pas "
                    + "l'appel.");
            System.out.println();
            Console.texte("Le nombre de systemes en production qui croient "
                    + "avoir un disjoncteur et n'en ont pas tient "
                    + "entierement dans ce paragraphe.");

            Console.titre(4, "LA MEME ROUTE, QUI COMPTE LES 500");
            Passerelle.remettreAZero();
            String stricte = banc.urlPasserelle() + "/api/strict/offres";
            var suiviStrict = new ArrayList<List<String>>();
            for (int appel = 1; appel <= 8; appel++) {
                var reponse = Banc.get(stricte);
                suiviStrict.add(List.of("appel " + appel,
                        String.valueOf(reponse.code()),
                        reponse.corps().contains("repli") ? "repli" : "service",
                        etat(banc, "offresStrictCB")));
            }
            Console.tableau(List.of("requete", "code", "qui a repondu",
                    "etat du circuit"), suiviStrict, List.of(12, 8, 16, 18));
            System.out.println();
            Console.ligne("replis servis",
                    String.valueOf(Passerelle.replis()), 26);
            System.out.println();
            Console.texte("Une seule ligne de configuration les separe : "
                    + "`setStatusCodes(\"500\", \"502\", \"503\")`. Les "
                    + "premiers appels partent vers le service, echouent, et "
                    + "basculent sur le repli ; passe le seuil — quatre "
                    + "appels, la moitie en echec — le circuit s'OUVRE, et "
                    + "les suivants ne touchent meme plus le service.");
            System.out.println();
            Console.texte("C'est exactement le but : laisser respirer un "
                    + "service en difficulte. Continuer a le marteler pendant "
                    + "qu'il suffoque est la meilleure facon de transformer "
                    + "une panne locale en panne generale.");

            Console.titre(5, "CE QUE L'OUVERTURE FAIT GAGNER");
            // Le circuit est encore OUVERT : on mesure le repli.
            long avecRepli = chronometrer(stricte, 6);
            // On remet le service debout, mais LENT — le cas qui fait le plus
            // de degats en production.
            for (var port : banc.portsDesInstances()) {
                Banc.post("http://localhost:" + port + "/panne?active=false");
                Banc.post("http://localhost:" + port + "/lenteur?millisecondes=400");
            }
            // ⚠️ Un circuit ne se referme pas tout seul dans son coin : il
            // passe en HALF_OPEN apres le delai, puis attend des appels
            // d'ESSAI. Sans trafic, il reste a moitie ouvert indefiniment.
            boolean referme = Banc.attendre(() -> {
                Banc.get(stricte);
                return "CLOSED".equals(etat(banc, "offresStrictCB"));
            }, Duration.ofSeconds(30));
            long sansRepli = chronometrer(stricte, 6);
            Console.tableau(List.of("ce qui repond", "appels", "temps moyen"),
                    List.of(
                    List.of("le repli, circuit OUVERT", "6",
                            "%.1f ms".formatted(avecRepli / 1e6 / 6)),
                    List.of("le service lent, circuit FERME", "6",
                            "%.1f ms".formatted(sansRepli / 1e6 / 6))),
                    List.of(32, 10, 16));
            Console.ligne("lenteur imposee au service", "400 ms", 32);
            Console.ligne("le circuit s'est-il referme",
                    referme ? "oui" : "NON", 32);
            Console.ligne("etat final", etat(banc, "offresStrictCB"), 32);
            System.out.println();
            Console.texte("Voila le gain, et il se lit dans le rapport entre "
                    + "les deux lignes. Un circuit ouvert repond SANS "
                    + "APPELER PERSONNE : le temps mesure est celui de "
                    + "l'aller-retour vers la passerelle, et rien de plus. "
                    + "Attendre un service lent coute 400 millisecondes de "
                    + "plus ET un thread bloque, multiplie par le nombre de "
                    + "requetes en vol.");
            System.out.println();
            Console.texte("C'est ainsi qu'une panne se propage : l'appelant "
                    + "epuise ses threads a attendre, cesse de repondre a ses "
                    + "propres clients, qui epuisent les leurs. Le "
                    + "disjoncteur casse cette chaine — et c'est pour cela "
                    + "qu'on l'appelle un disjoncteur.");
            System.out.println();
            Console.texte("⚠️ La fermeture, elle, a demande du TRAFIC. Apres "
                    + "le delai d'attente, Resilience4j passe en HALF_OPEN : "
                    + "il laisse passer quelques appels d'essai. Tant que "
                    + "personne n'appelle, rien ne se ferme. Un circuit ne se "
                    + "repare pas dans le silence.");
            System.out.println();
            Console.texte("⚠️ Les seuils de ce banc sont VOLONTAIREMENT bas — "
                    + "quatre appels, 50 % d'echecs, deux secondes d'attente "
                    + "— pour que le chapitre tienne en quelques secondes. En "
                    + "production, une fenetre de quatre appels ouvrirait le "
                    + "circuit au premier hoquet. On regle ces valeurs sur le "
                    + "trafic reel, et on les surveille.");

            Console.titre(6, "CE QUE LE DISJONCTEUR NE FAIT PAS");
            Console.texte("Il ne remplace pas un DELAI D'ATTENTE. Un service "
                    + "qui repond en trente secondes n'est pas « en "
                    + "echec » : il est lent, et sans timeout, le "
                    + "disjoncteur ne le verra jamais. On pose donc les "
                    + "deux, et le timeout doit etre plus court que la "
                    + "patience de l'appelant.");
            System.out.println();
            Console.texte("Il ne remplace pas non plus les REESSAIS — mais "
                    + "attention a l'ordre : reessayer trois fois un service "
                    + "en difficulte triple la charge qu'il subit. Le "
                    + "reglage sain est « peu de reessais, et seulement sur "
                    + "des operations idempotentes ». Rejouer un GET est "
                    + "sur ; rejouer un paiement, non.");
            System.out.println();
            Console.texte("Enfin, il ne protege pas VOS services d'un afflux "
                    + "de clients : c'est le role de la limitation de debit, "
                    + "posee elle aussi a la passerelle, et pour la meme "
                    + "raison — un seul endroit a regler.");

            Console.titre(7, "CE QUE LE CHAPITRE SUIVANT MESURE");
            Console.texte("Les images : ce qu'un Dockerfile multi-etapes "
                    + "embarque vraiment, et ce que `depends_on` ne garantit "
                    + "pas.");
            System.out.println();
        }
    }

    /** L'état du disjoncteur, lu dans l'actuator de la passerelle. */
    private static String etat(Banc banc, String nom) {
        var reponse = Banc.get(banc.urlPasserelle()
                + "/actuator/circuitbreakers");
        if (reponse.code() != 200) {
            return "(actuator indisponible)";
        }
        int position = reponse.corps().indexOf(nom);
        position = position < 0 ? -1 : reponse.corps().indexOf("\"state\":\"", position);
        if (position < 0) {
            return "(inconnu)";
        }
        int debut = position + 9;
        return reponse.corps().substring(debut,
                reponse.corps().indexOf('"', debut));
    }

    private static long chronometrer(String url, int appels) {
        long debut = System.nanoTime();
        for (int appel = 0; appel < appels; appel++) {
            Banc.get(url);
        }
        return System.nanoTime() - debut;
    }

    private static String court(String texte) {
        String plat = texte.replaceAll("\\s+", " ").strip();
        return plat.length() <= 32 ? plat : plat.substring(0, 29) + "...";
    }
}
