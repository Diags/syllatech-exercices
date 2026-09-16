package fr.portail.outils;

import io.agentscope.core.tool.Tool;
import io.agentscope.core.tool.ToolParam;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * Les outils du portail : de VRAIES methodes Java, annotees.
 *
 * <p>C'est le point du chapitre 3 : l'agent ne touche jamais au catalogue.
 * Le modele emet une INTENTION (« appelle rechercher_offres avec ce
 * mot-cle ») ; c'est le runtime AgentScope qui decide d'invoquer, ou non, la
 * methode ci-dessous. Cette indirection est le fondement de la securite —
 * rien ne s'execute sans passer par votre code.
 *
 * <p>⚠️ REGARDEZ LES DESCRIPTIONS : elles sont lues par le MODELE, pas par
 * un humain. Une description vague est un outil mal appele. Elles font
 * partie du prompt au meme titre que le {@code sysPrompt}, et se relisent
 * avec la meme attention.
 *
 * <p>⚠️ ENTREE DECLAREE. Les six offres ci-dessous sont les donnees du
 * projet. Ce que les chapitres mesurent — combien d'offres un mot-cle rend,
 * ce qu'une suppression coute — s'en DEDUIT.
 */
public class CatalogueOffres {

    /** Une offre du portail. */
    public record Offre(String reference, String intitule, String pile,
                        String ville, int salaireEnKiloEuros) {
    }

    private final List<Offre> offres = new CopyOnWriteArrayList<>(List.of(
            new Offre("OFF-101", "Developpeur Java Spring", "java",
                      "Lyon", 48),
            new Offre("OFF-102", "Ingenieur plateforme Kubernetes", "devops",
                      "Paris", 62),
            new Offre("OFF-103", "Developpeur Java / Kafka", "java",
                      "Nantes", 52),
            new Offre("OFF-104", "SRE astreinte", "devops",
                      "Paris", 58),
            new Offre("OFF-105", "Developpeur front React", "front",
                      "Lyon", 44),
            new Offre("OFF-106", "Architecte cloud", "devops",
                      "Bordeaux", 78)));

    private final List<String> journal = new CopyOnWriteArrayList<>();

    // >>> depart: declarer cette methode comme un outil — un nom, une description LUE PAR LE MODELE (donc precise), `readOnly` selon qu'elle lit ou ecrit, et un @ToolParam par argument
    //     public String rechercherOffres(String motCle) {
    @Tool(name = "rechercher_offres",
          description = "Recherche les offres d'emploi du portail par "
                        + "mot-cle. Le mot-cle est compare a l'intitule et a "
                        + "la pile technique (java, devops, front). Rend la "
                        + "reference, l'intitule et la ville de chaque offre.",
          readOnly = true)
    public String rechercherOffres(
            @ToolParam(name = "motCle", required = true,
                       description = "le mot-cle recherche, par exemple "
                                     + "« java » ou « kubernetes »")
            String motCle) {
    // <<<
        journal.add("rechercher_offres(" + motCle + ")");
        String recherche = motCle == null ? "" : motCle.toLowerCase();
        List<String> trouvees = new ArrayList<>();
        for (Offre offre : offres) {
            if (offre.intitule().toLowerCase().contains(recherche)
                    || offre.pile().equals(recherche)) {
                trouvees.add(offre.reference() + " — " + offre.intitule()
                             + " (" + offre.ville() + ")");
            }
        }
        return trouvees.isEmpty()
                ? "aucune offre pour « " + motCle + " »"
                : String.join("\n", trouvees);
    }

    @Tool(name = "compter_candidatures",
          description = "Rend le nombre de candidatures recues pour une "
                        + "offre, identifiee par sa reference (OFF-xxx).",
          readOnly = true)
    public String compterCandidatures(
            @ToolParam(name = "reference", required = true,
                       description = "la reference de l'offre, par exemple OFF-101")
            String reference) {
        journal.add("compter_candidatures(" + reference + ")");
        Map<String, Integer> candidatures = new LinkedHashMap<>();
        candidatures.put("OFF-101", 37);
        candidatures.put("OFF-102", 12);
        candidatures.put("OFF-103", 24);
        candidatures.put("OFF-104", 8);
        candidatures.put("OFF-105", 51);
        candidatures.put("OFF-106", 3);
        Integer compte = candidatures.get(reference);
        return compte == null
                ? "reference inconnue : " + reference
                : compte + " candidature(s) pour " + reference;
    }

    /**
     * ⚠️ L'OUTIL QUI JUSTIFIE LES PERMISSIONS. Lire un catalogue est anodin ;
     * supprimer une offre ne l'est pas. {@code readOnly = false} le declare,
     * et le chapitre 3 pose la regle qui l'encadre.
     */
    @Tool(name = "supprimer_offre",
          description = "Supprime definitivement une offre du portail. "
                        + "Action irreversible.",
          readOnly = false)
    public String supprimerOffre(
            @ToolParam(name = "reference", required = true,
                       description = "la reference de l'offre a supprimer")
            String reference) {
        journal.add("supprimer_offre(" + reference + ")");
        boolean retiree = offres.removeIf(
                offre -> offre.reference().equals(reference));
        return retiree
                ? "offre " + reference + " supprimee"
                : "reference inconnue : " + reference;
    }

    // -- l'instrument ------------------------------------------------------

    /** Ce que le catalogue a REELLEMENT execute, dans l'ordre. */
    public List<String> journal() {
        return List.copyOf(journal);
    }

    public List<Offre> offres() {
        return List.copyOf(offres);
    }

    public int nombreDOffres() {
        return offres.size();
    }
}
