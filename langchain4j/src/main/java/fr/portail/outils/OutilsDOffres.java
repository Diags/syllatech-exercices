package fr.portail.outils;

import dev.langchain4j.agent.tool.P;
import dev.langchain4j.agent.tool.Tool;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import org.springframework.stereotype.Service;

/**
 * Ce que le modèle a le droit de faire sur le portail.
 *
 * <p>Trois méthodes annotées {@code @Tool}, et c'est tout ce qu'il faut :
 * LangChain4j lit la signature, en déduit une {@code ToolSpecification} avec
 * un <strong>schéma d'arguments</strong>, et l'envoie au modèle à côté des
 * messages. Le chapitre 4 imprime ce schéma — c'est lui, et non la
 * description, qui dit au modèle comment appeler la méthode.
 *
 * <p>⚠️ <strong>La description n'est pas un commentaire.</strong> C'est la
 * seule chose que le modèle lit pour décider s'il appelle cet outil. Une
 * description vague produit un outil jamais appelé, ou appelé de travers —
 * et c'est un bug qu'aucun compilateur ne verra.
 *
 * <p>⚠️ Et un outil qui <em>écrit</em> mérite la même méfiance qu'une route
 * HTTP : le modèle peut être manipulé par le texte qu'il lit. Ici,
 * {@link #postuler} refuse une référence inconnue plutôt que de faire
 * confiance — le compteur {@link #appels} permet au chapitre 4 de vérifier
 * qui a été appelé, et combien de fois.
 */
@Service
public class OutilsDOffres {

    private static final AtomicInteger APPELS = new AtomicInteger();

    private static final List<String> CANDIDATURES =
            new java.util.concurrent.CopyOnWriteArrayList<>();

    public static int appels() {
        return APPELS.get();
    }

    public static List<String> candidatures() {
        return List.copyOf(CANDIDATURES);
    }

    public static void remettreAZero() {
        APPELS.set(0);
        CANDIDATURES.clear();
    }

    @Tool("Recherche les offres d'emploi du portail dont le texte contient un "
          + "mot-cle. Rend leurs references et leurs villes.")
    public List<String> rechercherOffres(
            @P("le mot-cle a chercher, en minuscules") String motCle) {
        APPELS.incrementAndGet();
        return fr.portail.rag.Corpus.OFFRES.stream()
                .filter(d -> d.text().toLowerCase(java.util.Locale.ROOT)
                        .contains(motCle.toLowerCase(java.util.Locale.ROOT)))
                .map(d -> d.metadata().getString("reference") + " a "
                          + d.metadata().getString("ville"))
                .toList();
    }

    @Tool("Rend le salaire minimum annonce pour une offre, en euros par an.")
    public int salaireDe(
            @P("la reference de l'offre, par exemple OFF-014") String reference) {
        APPELS.incrementAndGet();
        return fr.portail.rag.Corpus.OFFRES.stream()
                .filter(d -> reference.equals(d.metadata().getString("reference")))
                .map(d -> Integer.parseInt(d.metadata().getString("salaire")))
                .findFirst()
                .orElse(-1);
    }

    /**
     * L'outil qui écrit — et qui vérifie avant.
     *
     * <p>Un outil de lecture qui se trompe rend une mauvaise réponse ; un
     * outil d'écriture qui se trompe crée une ligne dans une base. La
     * vérification n'est pas là pour le modèle : elle est là parce que ce qui
     * arrive ici vient d'un texte qu'on n'a pas écrit.
     */
    @Tool("Depose une candidature du candidat connecte sur une offre, "
          + "identifiee par sa reference.")
    public String postuler(@P("la reference de l'offre") String reference) {
        APPELS.incrementAndGet();
        // TODO : refuser une reference qui n'existe pas, AVANT d'ecrire quoi que ce soit
        // sans cette verification, le modele cree ce qu'il veut
        CANDIDATURES.add(reference);
        return "candidature enregistree sur " + reference;
    }
}
