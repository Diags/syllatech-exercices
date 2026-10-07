package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Timeout;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

/**
 * Les six chapitres tournent, et disent toujours la meme chose.
 *
 * <p>Quatre d'entre eux demarrent une vraie application Spring Boot : ce sont
 * les tests les plus lents du projet, et les seuls qui verifient ce que
 * l'apprenant verra a l'ecran.
 */
class ChapitresTest {

    private static final Map<String, String> SORTIES = new ConcurrentHashMap<>();

    @ParameterizedTest(name = "{0} s'execute et affiche ses mesures")
    @CsvSource(delimiter = '|', textBlock = """
        Chapitre1React        | par CLE (avec key)
        Chapitre2Api          | CE QUE L'ENTITE EXPOSERAIT
        Chapitre3Jpa          | join fetch o.entreprise
        Chapitre4Jwt          | CE QU'ON NE PEUT PAS REVOQUER
        Chapitre5Redux        | LE RETOUR DU NAVIGATEUR N'EST PAS UNE PREUVE
        Chapitre6Deploiement  | conforme : les 6 regles sont satisfaites
        """)
    @Timeout(600)
    @DisplayName("chaque chapitre tourne de bout en bout")
    void chaqueChapitreTourne(String classe, String attendu) throws Exception {
        String sortie = executer("fr.portail.chapitres." + classe);
        assertThat(sortie)
                .as(classe + " n'a pas affiche « " + attendu.strip() + " »\n"
                    + apercu(sortie))
                .contains(attendu.strip());
    }

    @Test
    @Timeout(600)
    @DisplayName("le chapitre 1 oppose 7 operations a 1")
    void leChapitre1CompteLesOperations() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre1React");

        assertThat(sortie).contains("par POSITION (sans key)  1         0         0           6 ⚠️");
        assertThat(sortie).contains("par CLE (avec key)       1         0         0           0           1");
        assertThat(sortie)
                .as("l'etat migre vers une autre offre sans key")
                .contains("OFF-107   ⚠️ ce n'est plus la meme offre");
        assertThat(sortie)
                .as("les trois formes de dependances sont comptees")
                .contains("useEffect(fn, [])");
    }

    @Test
    @Timeout(600)
    @DisplayName("le chapitre 2 distingue 401 et 403")
    void leChapitre2DistingueLesRefus() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre2Api");

        assertThat(sortie).contains("401      ⚠️ 401 : connecte-toi");
        assertThat(sortie).contains("403      ⚠️ 403 : pas le droit");
        assertThat(sortie)
                .as("le DTO ne porte pas d'objet Entreprise")
                .contains("entreprise : Entreprise")
                .contains("entreprise : String");
    }

    @Test
    @Timeout(600)
    @DisplayName("le chapitre 3 compte 4 requetes contre 1")
    void leChapitre3CompteLeNPlusUn() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre3Jpa");

        assertThat(sortie).contains("⚠️ 1 + 3 entreprises distinctes");
        assertThat(sortie).contains("join fetch o.entreprise            1");
        assertThat(sortie)
                .as("`ddl-auto=update` est explicitement deconseille")
                .contains("ddl-auto=update");
    }

    @Test
    @Timeout(600)
    @DisplayName("le chapitre 4 ouvre la charge utile et montre ce qui survit")
    void leChapitre4OuvreLeJeton() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre4Jwt");

        assertThat(sortie).contains("\"sub\":\"awa\"");
        assertThat(sortie).contains("un role change en Base64");
        assertThat(sortie).contains("un REFRESH token comme access");
        assertThat(sortie)
                .as("l'ancien access token fonctionne encore")
                .containsPattern("GET /api/moi avec l'ANCIEN access token\s+200");
    }

    @Test
    @Timeout(600)
    @DisplayName("le chapitre 5 refuse le rejeu et montre le paiement fantome")
    void leChapitre5RefuseLeRejeu() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre5Redux");

        assertThat(sortie).contains("horodatage hors tolerance (30 min)");
        assertThat(sortie).contains("le MEME en-tete, montant passe a 1 centime");
        assertThat(sortie)
                .as("1 290 € pour un GET")
                .contains("apres un simple GET sur l'URL de retour              PAYEE");
    }

    @Test
    @Timeout(600)
    @DisplayName("le chapitre 6 oppose 6 regles satisfaites a 6 manquantes")
    void leChapitre6AuditeLesDeuxImages() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre6Deploiement");

        assertThat(sortie).contains("conforme : les 6 regles sont satisfaites");
        assertThat(sortie).contains("⚠️ 6 regle(s) non satisfaite(s) sur 6");
        assertThat(sortie).contains("⚠️ SECRET DANS L'IMAGE");
    }

    @Test
    @DisplayName("les six classes de chapitre sont la")
    void lesSixChapitres() {
        for (String nom : List.of("Chapitre1React", "Chapitre2Api",
                "Chapitre3Jpa", "Chapitre4Jwt", "Chapitre5Redux",
                "Chapitre6Deploiement")) {
            org.junit.jupiter.api.Assertions.assertDoesNotThrow(
                    () -> Class.forName("fr.portail.chapitres." + nom),
                    nom + " est introuvable");
        }
    }

    private static String executer(String classe) throws Exception {
        String retenue = SORTIES.get(classe);
        if (retenue != null) {
            return retenue;
        }
        ByteArrayOutputStream capture = new ByteArrayOutputStream();
        PrintStream originale = System.out;
        try {
            System.setOut(new PrintStream(capture, true, StandardCharsets.UTF_8));
            Class.forName(classe).getDeclaredMethod("main", String[].class)
                    .invoke(null, (Object) new String[0]);
        } finally {
            System.setOut(originale);
        }
        String sortie = capture.toString(StandardCharsets.UTF_8);
        SORTIES.put(classe, sortie);
        return sortie;
    }

    private static String apercu(String sortie) {
        List<String> lignes = sortie.lines().toList();
        return "--- sortie (" + lignes.size() + " lignes) ---\n"
                + String.join("\n", lignes.subList(0, Math.min(30, lignes.size())));
    }
}
