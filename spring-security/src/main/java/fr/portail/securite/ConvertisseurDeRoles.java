package fr.portail.securite;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import org.springframework.core.convert.converter.Converter;
import org.springframework.security.authentication.AbstractAuthenticationToken;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.stereotype.Component;

/**
 * Le pont entre les rôles d'un jeton KeyCloak et les autorités de Spring.
 *
 * <p>C'est le détail qui fait trébucher tout le monde, et le chapitre 6 le
 * mesure : KeyCloak range les rôles dans un claim <strong>imbriqué</strong>,
 * {@code realm_access.roles}, et <strong>sans</strong> le préfixe
 * {@code ROLE_} que {@code hasRole(...)} exige.
 *
 * <pre>
 * le jeton dit            : realm_access = { roles: ["RH", "USER"] }
 * Spring attend           : ROLE_RH, ROLE_USER
 * sans ce convertisseur   : aucune autorite → 403, avec un jeton parfaitement valide
 * </pre>
 *
 * <p>Et {@code JwtGrantedAuthoritiesConverter} ne suffit pas : son
 * {@code setAuthoritiesClaimName("realm_access.roles")} lit un claim
 * <em>nommé ainsi</em>, avec un point dans son nom — pas un claim imbriqué.
 * Il faut donc descendre à la main dans la carte, comme ci-dessous. Le
 * chapitre 6 mesure les deux.
 */
@Component
public class ConvertisseurDeRoles
        implements Converter<Jwt, AbstractAuthenticationToken> {

    public static final String CLAIM = "realm_access";

    public static final String PREFIXE = "ROLE_";

    /** Vrai si le pont est posé. Le chapitre 6 le coupe, puis le remet. */
    private volatile boolean actif = true;

    public void actif(boolean actif) {
        this.actif = actif;
    }

    public boolean actif() {
        return actif;
    }

    @Override
    public AbstractAuthenticationToken convert(Jwt jeton) {
        return new JwtAuthenticationToken(jeton, autorites(jeton),
                jeton.getSubject());
    }

    /** Les autorités Spring que ce jeton donne, une fois traduites. */
    public Collection<GrantedAuthority> autorites(Jwt jeton) {
        var autorites = new ArrayList<GrantedAuthority>();
        if (!actif) {
            // Le comportement par defaut de Spring : il ne connait pas
            // `realm_access`, et n'en tire donc aucune autorite.
            return autorites;
        }
        // >>> depart: transformer chaque role du jeton en autorite Spring, prefixee par PREFIXE
        //     return autorites;
        for (var role : rolesDu(jeton)) {
            autorites.add(new SimpleGrantedAuthority(PREFIXE + role));
        }
        return autorites;
        // <<<
    }

    /** Les rôles bruts du jeton, tels que KeyCloak les écrit. */
    @SuppressWarnings("unchecked")
    public static List<String> rolesDu(Jwt jeton) {
        Object brut = jeton.getClaim(CLAIM);
        if (!(brut instanceof Map<?, ?> carte)) {
            return List.of();
        }
        // >>> depart: descendre dans la carte pour y lire la liste `roles`
        //     return List.of();
        Object roles = carte.get("roles");
        return roles instanceof Collection<?> liste
                ? List.copyOf((Collection<String>) liste)
                : List.of();
        // <<<
    }
}
