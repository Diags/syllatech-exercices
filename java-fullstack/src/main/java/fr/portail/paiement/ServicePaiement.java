package fr.portail.paiement;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

/**
 * Le paiement : une session creee cote SERVEUR, un webhook comme verite.
 *
 * <p>⚠️ AUCUN NUMERO DE CARTE NE TRAVERSE CE CODE, ET C'EST TOUT LE SUJET.
 * Le back cree une session avec sa cle secrete, rend une URL, et React y
 * redirige. Les donnees de carte sont saisies chez Stripe. Les faire passer
 * par votre serveur — meme « juste pour valider le format » — vous fait
 * heriter de la conformite PCI-DSS.
 *
 * <p>⚠️ ET LA COMMANDE N'EST PAYEE QUE SUR LE WEBHOOK. Le retour du
 * navigateur est une URL que l'utilisateur peut taper.
 */
@Service
public class ServicePaiement {

    /** L'etat d'une commande. */
    public enum Etat { EN_ATTENTE, PAYEE }

    private final SignatureStripe signature;
    private final Map<String, Etat> commandes = new ConcurrentHashMap<>();
    private final Map<String, String> sessions = new ConcurrentHashMap<>();
    private final AtomicInteger webhooksRefuses = new AtomicInteger();
    private final AtomicInteger webhooksAcceptes = new AtomicInteger();

    public ServicePaiement(
            @Value("${portail.stripe.secret-webhook}") String secret) {
        this.signature = new SignatureStripe(secret);
    }

    /**
     * Cree une session de paiement. En production, cet appel part chez
     * Stripe avec la cle secrete ; ici il rend une URL de la meme forme.
     */
    public Map<String, String> creerUneSession(String commande, int montantEnCentimes) {
        String session = "cs_test_" + Integer.toHexString(
                (commande + montantEnCentimes).hashCode());
        sessions.put(session, commande);
        commandes.put(commande, Etat.EN_ATTENTE);

        Map<String, String> reponse = new LinkedHashMap<>();
        reponse.put("sessionId", session);
        reponse.put("url", "https://checkout.stripe.com/c/pay/" + session);
        return reponse;
    }

    /**
     * ⚠️ PIECE A CONVICTION — NE PAS « REPARER ».
     *
     * <p>Marquer la commande payee sur le retour du navigateur. C'est la
     * ligne qu'on ecrit quand on veut « aller vite », et elle suffit a se
     * faire livrer sans payer : l'URL de retour est tapable a la main.
     */
    public Etat confirmerDepuisLeNavigateur(String sessionId) {
        String commande = sessions.get(sessionId);
        if (commande != null) {
            commandes.put(commande, Etat.PAYEE);
        }
        return commande == null ? null : commandes.get(commande);
    }

    /** La SEULE confirmation qui vaille : le webhook signe. */
    public SignatureStripe.Verdict traiterLeWebhook(String corps, String enTete,
                                                    Instant maintenant) {
        SignatureStripe.Verdict verdict =
                signature.verifier(corps, enTete, maintenant);
        if (!verdict.valide()) {
            webhooksRefuses.incrementAndGet();
            return verdict;
        }
        webhooksAcceptes.incrementAndGet();
        // Le corps est du JSON Stripe ; on n'en lit ici que la session.
        String session = extraireLaSession(corps);
        String commande = sessions.get(session);
        if (commande != null) {
            commandes.put(commande, Etat.PAYEE);
        }
        return verdict;
    }

    private static String extraireLaSession(String corps) {
        int debut = corps.indexOf("cs_test_");
        if (debut < 0) {
            return "";
        }
        int fin = debut;
        while (fin < corps.length()
                && (Character.isLetterOrDigit(corps.charAt(fin))
                    || corps.charAt(fin) == '_')) {
            fin++;
        }
        return corps.substring(debut, fin);
    }

    public Etat etat(String commande) {
        return commandes.get(commande);
    }

    public SignatureStripe signature() {
        return signature;
    }

    public int webhooksRefuses() {
        return webhooksRefuses.get();
    }

    public int webhooksAcceptes() {
        return webhooksAcceptes.get();
    }
}
