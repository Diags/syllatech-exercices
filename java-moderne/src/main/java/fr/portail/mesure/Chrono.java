package fr.portail.mesure;

import java.util.function.Supplier;

/**
 * Mesurer un temps sur la JVM, avec les précautions qui rendent le chiffre
 * défendable.
 *
 * <p>Trois précautions, et une mise en garde :
 *
 * <ol>
 *   <li>un <strong>échauffement</strong> : les premières exécutions passent
 *       par l'interpréteur, le JIT ne compile qu'après quelques milliers
 *       d'appels. Mesurer sans échauffer, c'est mesurer l'interpréteur ;</li>
 *   <li>on rend le <strong>résultat</strong> du bloc mesuré, et les chapitres
 *       l'affichent : un calcul dont personne ne lit le résultat peut être
 *       supprimé par le JIT, et on mesure alors une boucle vide ;</li>
 *   <li>on prend la <strong>médiane</strong> de plusieurs tours, pas la
 *       moyenne : un ramasse-miettes pendant un tour décale la moyenne, pas
 *       la médiane.</li>
 * </ol>
 *
 * <p>⚠️ Ce n'est <strong>pas</strong> un banc d'essai sérieux. Pour cela il
 * existe JMH, qui isole la mesure dans un processus dédié et déjoue bien
 * d'autres optimisations. Ce que cette classe donne est un <em>ordre de
 * grandeur</em> — suffisant quand l'écart mesuré est d'un facteur 100, ce
 * qui est le cas de tout ce que ce projet mesure. Un écart de 10 % obtenu
 * ici ne vaudrait rien.
 */
public final class Chrono {

    private Chrono() {
    }

    /** Le temps d'un bloc, et ce que le bloc a produit. */
    public record Mesure(long nanos, Object resultat) {

        public double millis() {
            return nanos / 1_000_000.0;
        }

        /** Le temps, avec l'unité qui le rend lisible. */
        public String lisible() {
            if (nanos < 10_000) {
                return nanos + " ns";
            }
            if (nanos < 10_000_000) {
                return "%.2f ms".formatted(nanos / 1_000_000.0);
            }
            return "%.0f ms".formatted(nanos / 1_000_000.0);
        }
    }

    /** Une seule exécution, sans échauffement : pour ce qui ne se répète pas. */
    public static Mesure une(Supplier<?> bloc) {
        long debut = System.nanoTime();
        Object resultat = bloc.get();
        return new Mesure(System.nanoTime() - debut, resultat);
    }

    /**
     * Échauffe, puis prend la médiane de {@code tours} exécutions.
     *
     * @param echauffements nombre d'exécutions jetées avant de mesurer
     * @param tours         nombre d'exécutions mesurées (impair de préférence)
     */
    public static Mesure mediane(int echauffements, int tours, Supplier<?> bloc) {
        Object garde = null;
        for (int i = 0; i < echauffements; i++) {
            garde = bloc.get();
        }
        var temps = new long[tours];
        for (int i = 0; i < tours; i++) {
            long debut = System.nanoTime();
            garde = bloc.get();
            temps[i] = System.nanoTime() - debut;
        }
        java.util.Arrays.sort(temps);
        return new Mesure(temps[tours / 2], garde);
    }

    /** Les réglages courants de ce projet : 3 échauffements, 5 tours. */
    public static Mesure mediane(Supplier<?> bloc) {
        return mediane(3, 5, bloc);
    }

    /**
     * Le rapport entre deux temps, en texte.
     *
     * <p>Sous un facteur 2, on refuse de conclure : le bruit d'une JVM
     * dépasse largement cet écart, et annoncer « 1,3 fois plus rapide »
     * serait une affirmation que la mesure ne porte pas.
     */
    public static String rapport(Mesure lente, Mesure rapide) {
        if (rapide.nanos() == 0) {
            return "trop rapide pour etre mesure ici";
        }
        double facteur = (double) lente.nanos() / rapide.nanos();
        if (facteur < 2) {
            return "pas d'ecart mesurable (x%.1f — sous le bruit)".formatted(facteur);
        }
        return "x%.0f".formatted(facteur);
    }
}
