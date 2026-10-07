package fr.portail.securite;

import java.security.Principal;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * « Qui suis-je ? » — la route qui exige une identite, et rien d'autre.
 *
 * <p>⚠️ REGARDEZ LE PARAMETRE : Spring injecte l'`Authentication` que le
 * filtre a posee. Le controleur ne lit aucun en-tete, ne decode aucun jeton,
 * ne connait pas le mot « Bearer ». C'est ce que la chaine de filtres
 * apporte.
 *
 * <p>Elle sert aussi d'instrument au chapitre 4 : c'est sur elle qu'on
 * mesure qu'un access token survit a la desactivation du compte.
 */
@RestController
public class MoiControleur {

    @GetMapping("/api/moi")
    public Map<String, Object> moi(Authentication authentification) {
        Map<String, Object> reponse = new LinkedHashMap<>();
        reponse.put("identifiant", authentification.getName());
        reponse.put("roles", authentification.getAuthorities().stream()
                .map(Object::toString).toList());
        return reponse;
    }
}
