package fr.portail.bac;

import fr.portail.langage.Interprete;
import fr.portail.langage.Politique;
import java.io.IOException;
import java.io.InputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;

/**
 * Le programme qui tourne DANS le bac a sable — et rien d'autre.
 *
 * <p>Il lit le script sur son entree standard, l'execute sous une politique
 * qui n'accorde rien, ecrit le resultat sur ses sorties, et se termine avec
 * le code du script.
 *
 * <p>⚠️ REGARDEZ CE QUE CETTE CLASSE N'IMPORTE PAS : ni Spring, ni le
 * contexte de l'application, ni le moindre service metier. Ce n'est pas de
 * la discipline, c'est structurel — ce processus a son propre tas, et le
 * {@code Environment} de l'application n'y existe tout simplement pas.
 * {@code secret "jobportal.cle-api"} n'a donc rien a lire, meme si la
 * politique l'autorisait.
 *
 * <p>C'est l'argument central du cours, et il tient en une phrase : on ne
 * protege pas un tas, on en change.
 */
public final class Executeur {

    private Executeur() {
    }

    public static void main(String[] args) throws IOException {
        String script = lireToutLEntree(System.in);

        PrintStream sortie = new PrintStream(System.out, true,
                                             StandardCharsets.UTF_8);
        PrintStream erreurs = new PrintStream(System.err, true,
                                              StandardCharsets.UTF_8);

        // ⚠️ `rienDuTout()` : ni fichiers, ni reseau, ni proprietes. C'est
        // la DERNIERE couche, posee derriere la frontiere de processus —
        // et c'est parce qu'elle est derriere qu'elle a du sens.
        Interprete interprete = new Interprete(Politique.rienDuTout());
        Interprete.Trace trace = interprete.executer(script);

        if (!trace.sortie().isEmpty()) {
            sortie.print(trace.sortie());
        }
        if (!trace.erreurs().isEmpty()) {
            erreurs.print(trace.erreurs());
        }
        sortie.flush();
        erreurs.flush();
        System.exit(trace.code());
    }

    private static String lireToutLEntree(InputStream entree)
            throws IOException {
        return new String(entree.readAllBytes(), StandardCharsets.UTF_8);
    }
}
