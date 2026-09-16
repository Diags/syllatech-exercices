package fr.portail.chapitres;

import fr.portail.front.Magasin;
import fr.portail.paiement.ServicePaiement;
import fr.portail.paiement.SignatureStripe;
import java.time.Duration;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Chapitre 5 — Redux, Stripe et Tailwind.
 *
 * <pre>
 *   mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre5Redux
 * </pre>
 *
 * <p>Trois sujets, trois natures. Le magasin et l'echelle de Tailwind sont
 * des MECANIQUES, ecrites en Java parce qu'un cours ne peut pas exiger Node.
 * La verification de signature de Stripe, elle, est REELLE : c'est du
 * HMAC-SHA256, et un webhook rejoue est refuse pour de vrai.
 */
public final class Chapitre5Redux {

    private Chapitre5Redux() {
    }

    /** L'etat partage : la liste des offres, et son statut. */
    private record EtatOffres(List<String> items, String statut) {
    }

    /** Le reducteur : une fonction PURE, etat + action → nouvel etat. */
    @SuppressWarnings("unchecked")
    private static EtatOffres reduire(EtatOffres etat, Magasin.Action action) {
        return switch (action.type()) {
            case "offresChargees" ->
                    new EtatOffres((List<String>) action.charge(), "ok");
            case "chargementDemarre" -> new EtatOffres(etat.items(), "chargement");
            case "offreAjoutee" -> {
                // ⚠️ ON RECONSTRUIT, ON NE MUTE PAS. `etat.items().add(...)`
                // leverait ici (la liste est immuable) — et dans une
                // application React, cela ne leverait RIEN : la liste
                // changerait sans que sa reference change, donc sans qu'un
                // seul composant se re-rende. Le bogue « les donnees sont la
                // mais l'ecran ne bouge pas » vient de la.
                List<String> augmentee = new java.util.ArrayList<>(etat.items());
                augmentee.add(String.valueOf(action.charge()));
                yield new EtatOffres(List.copyOf(augmentee), etat.statut());
            }
            default -> etat;
        };
    }

    public static void main(String[] args) {
        System.out.println("""
                1. REDUX : EN AVEZ-VOUS BESOIN ? LA QUESTION SE CHIFFRE
                """);
        System.out.printf("   %-36s %-16s %s%n", "PROFONDEUR DE L'ARBRE",
                          "SANS MAGASIN", "AVEC MAGASIN");
        for (int profondeur : new int[] {1, 3, 6, 10}) {
            System.out.printf("   %-36s %-16d %d%n",
                    profondeur + " niveau(x) entre source et usage",
                    Magasin.composantsTraverses(profondeur, false),
                    Magasin.composantsTraverses(profondeur, true));
        }

        System.out.println("""

                   Sans magasin, chaque niveau intermediaire declare un
                   parametre dont il ne fait rien, et se re-rend quand la
                   donnee change. C'est le « prop drilling », et il se compte
                   en composants qui n'auraient jamais du connaitre la
                   donnee.

                   ⚠️ MAIS LA PREMIERE LIGNE DIT L'ESSENTIEL : a un niveau,
                   le magasin ne fait rien gagner — il ajoute une
                   indirection. La plupart de l'etat d'une application est
                   LOCAL (le contenu d'un champ, l'ouverture d'un menu) et
                   n'a rien a faire dans un magasin global. Redux repond au
                   probleme de l'etat PARTAGE entre composants ELOIGNES : le
                   panier, l'utilisateur connecte, un cache.
                """);

        System.out.println("""
                2. UN REDUCTEUR EST PUR, ET L'ETAT RESTE IMMUABLE
                """);
        Magasin<EtatOffres> magasin = new Magasin<>(
                new EtatOffres(List.of(), "idle"), Chapitre5Redux::reduire);

        int[] notifications = {0};
        magasin.abonner(etat -> notifications[0]++);

        EtatOffres initial = magasin.etat();
        magasin.envoyer(new Magasin.Action("chargementDemarre", null));
        magasin.envoyer(new Magasin.Action("offresChargees",
                List.of("OFF-101", "OFF-102")));
        magasin.envoyer(new Magasin.Action("offreAjoutee", "OFF-107"));
        magasin.envoyer(new Magasin.Action("actionInconnue", "peu importe"));

        System.out.printf("   %-34s %s%n", "etat courant", magasin.etat());
        System.out.printf("   %-34s %s%n", "etat initial, toujours intact",
                          initial);
        System.out.printf("   %-34s %d%n", "etats dans l'historique",
                          magasin.historique().size());
        System.out.printf("   %-34s %d%n", "notifications aux abonnes",
                          notifications[0]);

        System.out.println("""

                   Quatre actions envoyees, et seulement TROIS notifications :
                   l'action inconnue rend l'etat tel quel, donc aucun rendu
                   n'est declenche. C'est ce qui evite qu'une action non
                   geree repeigne toute l'interface.

                   L'historique, lui, en compte quatre : l'etat initial, plus
                   un par changement.

                   ⚠️ Et l'etat initial est toujours la, inchange. C'est ce
                   qui permet aux outils de developpement de REJOUER
                   l'historique — et c'est impossible des qu'un reducteur
                   mute son entree.

                   ⚠️ Redux Toolkit autorise `state.items = …` grace a Immer,
                   qui enregistre les mutations et fabrique un nouvel objet.
                   La mutation est APPARENTE ; l'immuabilite reste garantie.
                   Ecrire la meme ligne dans un reducteur ecrit a la main
                   casse tout, en silence.
                """);

        System.out.println("""
                3. STRIPE : LA MESURE QUI TRANCHE, ET ELLE EST REELLE
                """);
        ServicePaiement paiement = new ServicePaiement("whsec_du_portail");
        Map<String, String> session = paiement.creerUneSession("CMD-42", 4900);
        System.out.printf("   Session creee cote SERVEUR : %s%n",
                          session.get("sessionId"));
        System.out.printf("   L'utilisateur est redirige vers : %s%n%n",
                          session.get("url"));

        String corps = """
                {"type":"checkout.session.completed","data":{"object":                {"id":"%s","amount_total":4900,"payment_status":"paid"}}}"""
                .formatted(session.get("sessionId"));
        Instant maintenant = Instant.now();
        SignatureStripe signature = paiement.signature();

        System.out.printf("   %-44s %-11s %s%n",
                          "WEBHOOK PRESENTE", "VERDICT", "MOTIF");

        String enTeteValide = signature.enTete(corps, maintenant);
        verdict(paiement, corps, enTeteValide, maintenant,
                "le webhook de Stripe, tel quel");

        // ⚠️ Le montant passe de 4 900 a 1 centime, l'en-tete ne bouge pas.
        String corpsTrafique = corps.replace("\"amount_total\":4900",
                                             "\"amount_total\":1");
        verdict(paiement, corpsTrafique, enTeteValide, maintenant,
                "le MEME en-tete, montant passe a 1 centime");

        verdict(paiement, corps, "t=" + maintenant.getEpochSecond() + ",v1=deadbeef",
                maintenant, "une signature inventee");

        Instant vieux = maintenant.minus(Duration.ofMinutes(30));
        verdict(paiement, corps, signature.enTete(corps, vieux), maintenant,
                "un webhook VALIDE, rejoue 30 min apres");

        verdict(paiement, corps, null, maintenant, "aucun en-tete");

        System.out.printf("%n      etat de la commande CMD-42 : %s%n",
                          paiement.etat("CMD-42"));
        System.out.printf("      webhooks acceptes : %d, refuses : %d%n",
                          paiement.webhooksAcceptes(), paiement.webhooksRefuses());

        System.out.println("""

                   ⚠️ TROIS CONTROLES, ET AUCUN NE REMPLACE LES AUTRES. La
                   signature couvre l'horodatage ET le corps — recopier une
                   signature valide sur un autre corps echoue. L'horodatage
                   est borne a cinq minutes — sans cela, un webhook capte une
                   fois serait rejouable indefiniment, puisque sa signature
                   reste valide pour toujours. Et la comparaison se fait en
                   TEMPS CONSTANT.

                   ⚠️ ET CE QUI COMPTE VRAIMENT : c'est le WEBHOOK qui a fait
                   passer la commande a PAYEE, pas le retour du navigateur.
                """);

        System.out.println("""
                4. LE RETOUR DU NAVIGATEUR N'EST PAS UNE PREUVE
                """);
        ServicePaiement naif = new ServicePaiement("whsec_du_portail");
        Map<String, String> commande = naif.creerUneSession("CMD-99", 129000);
        ServicePaiement.Etat avant = naif.etat("CMD-99");
        ServicePaiement.Etat apres =
                naif.confirmerDepuisLeNavigateur(commande.get("sessionId"));

        System.out.printf("   %-52s %s%n", "etat avant", avant);
        System.out.printf("   %-52s %s   ⚠️%n",
                          "apres un simple GET sur l'URL de retour", apres);
        System.out.printf("   %-52s %d centimes%n",
                          "montant jamais encaisse", 129000);

        System.out.println("""

                   ⚠️ L'URL DE RETOUR EST TAPABLE A LA MAIN. Marquer une
                   commande payee sur ce retour — la ligne qu'on ecrit pour
                   « aller vite » — suffit a se faire livrer sans payer. Ici,
                   1 290 € pour une requete GET.

                   La source de verite est le webhook signe, et lui seul. Le
                   retour du navigateur sert a AFFICHER « merci », rien de
                   plus.

                   ⚠️ Et le corps du webhook se lit BRUT, en chaine. Laisser
                   Spring le desserialiser puis le reserialiser change les
                   espaces et l'ordre des cles — et la signature, qui porte
                   sur les octets exacts, ne correspond plus. C'est une
                   heure de debogage pour un `@RequestBody String`.
                """);

        System.out.println("""
                5. TAILWIND : L'ECHELLE, ET CE QU'ELLE EMPECHE
                """);
        Map<String, String> echelle = new LinkedHashMap<>();
        echelle.put("p-1", "0.25rem  (4 px)");
        echelle.put("p-2", "0.5rem   (8 px)");
        echelle.put("p-4", "1rem     (16 px)");
        echelle.put("p-6", "1.5rem   (24 px)");
        echelle.put("p-8", "2rem     (32 px)");

        System.out.printf("   %-10s %s%n", "CLASSE", "VALEUR");
        echelle.forEach((classe, valeur) ->
                System.out.printf("   %-10s %s%n", classe, valeur));

        System.out.println("""

                   Il n'y a pas de `p-3.5` ni de `p-13` : l'echelle est
                   FERMEE. C'est tout l'interet, et ce n'est pas une
                   contrainte esthetique — c'est ce qui empeche les « 13 px »
                   et les gris legerement differents d'une page a l'autre.

                   ⚠️ Le vrai argument de Tailwind n'est donc pas d'ecrire
                   moins de CSS : c'est de rendre le SYSTEME DE DESIGN
                   obligatoire. Un `style={{padding: 13}}` reste possible —
                   et c'est exactement la ligne qu'une revue doit attraper.

                   ⚠️ Et le CSS mort disparait au build : Tailwind ne garde
                   que les classes REELLEMENT rencontrees dans les sources.
                   Corollaire a connaitre : une classe construite
                   dynamiquement (`\\"p-\\" + taille`) n'est pas vue par
                   l'analyseur, et elle manque a l'execution. Il faut ecrire
                   les classes en toutes lettres.
                """);
    }

    private static void verdict(ServicePaiement paiement, String corps,
                                String enTete, Instant maintenant,
                                String libelle) {
        SignatureStripe.Verdict verdict =
                paiement.traiterLeWebhook(corps, enTete, maintenant);
        System.out.printf("   %-44s %-11s %s%n", libelle,
                verdict.valide() ? "ACCEPTE" : "⚠️ refuse", verdict.motif());
    }
}
