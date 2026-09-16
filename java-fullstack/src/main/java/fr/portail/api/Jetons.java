package fr.portail.api;

/**
 * Ce que l'API rend apres une connexion reussie.
 *
 * <p>⚠️ DEUX JETONS, ET DEUX DUREES. L'access token vit quelques minutes
 * parce qu'un JWT ne se revoque pas ; le refresh token vit longtemps parce
 * qu'il, lui, est stocke cote serveur et peut donc etre revoque. Le
 * chapitre 4 mesure ce que cette asymetrie coute quand on l'oublie.
 */
public record Jetons(String accessToken, String refreshToken,
                     long expireDansSecondes) {
}
