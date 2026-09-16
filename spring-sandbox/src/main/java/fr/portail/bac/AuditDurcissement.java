package fr.portail.bac;

import java.util.List;
import java.util.function.Predicate;

/**
 * L'audit d'une ligne {@code docker run} : quelle porte chaque drapeau ferme.
 *
 * <p>⚠️ CE QUE CET AUDIT EST, ET N'EST PAS. Il lit une ligne de commande et
 * verifie la presence de drapeaux. Il ne teste pas qu'ils FONCTIONNENT — une
 * faille de gVisor ou un demon mal configure lui echapperaient entierement.
 * C'est un controle de CONFIGURATION, comme un linter : il attrape l'oubli,
 * pas la vulnerabilite.
 *
 * <p>Ce qui le rend utile malgre cela : l'oubli est de loin le cas le plus
 * frequent. Un drapeau retire « juste pour deboguer » un vendredi soir se
 * retrouve en production le lundi, et rien ne le signale — sauf cet audit,
 * dans l'integration continue.
 */
public final class AuditDurcissement {

    /** Une porte, ce qui la ferme, et ce qui arrive si elle reste ouverte. */
    public record Porte(String nom, String drapeau, String siOuverte,
                        Predicate<List<String>> fermee) {

        public boolean estFermee(List<String> drapeaux) {
            return fermee.test(drapeaux);
        }
    }

    private static Predicate<List<String>> commence(String prefixe) {
        return drapeaux -> drapeaux.stream().anyMatch(d -> d.startsWith(prefixe));
    }

    private static Predicate<List<String>> contient(String exact) {
        return drapeaux -> drapeaux.contains(exact);
    }

    /**
     * ⚠️ ENTREE DECLAREE, et c'est la liste qui compte. Chaque ligne dit
     * pourquoi le drapeau existe — ce qu'aucune documentation d'option ne
     * fait vraiment.
     */
    public static final List<Porte> PORTES = List.of(
            new Porte("isolation du noyau", "--runtime=runsc",
                      "une faille du noyau franchit le conteneur",
                      contient("--runtime=runsc")),
            new Porte("exfiltration", "--network=none",
                      "le code appelle un serveur distant et envoie ce qu'il a lu",
                      contient("--network=none")),
            new Porte("porte derobee", "--read-only",
                      "le code ecrit un fichier qui survivra au conteneur",
                      contient("--read-only")),
            new Porte("privileges", "--cap-drop=ALL",
                      "le code garde des capacites qu'il n'utilise jamais legitimement",
                      contient("--cap-drop=ALL")),
            new Porte("escalade", "--security-opt no-new-privileges",
                      "un binaire setuid peut regagner des droits",
                      drapeaux -> drapeaux.contains("no-new-privileges")),
            new Porte("racine", "--user",
                      "le code tourne en root DANS le conteneur",
                      commence("--user")),
            new Porte("fork bomb", "--pids-limit",
                      "quelques lignes suffisent a saturer la machine",
                      commence("--pids-limit")),
            new Porte("saturation memoire", "--memory",
                      "une allocation sans fin tue le noeud, pas le conteneur",
                      commence("--memory")),
            new Porte("saturation CPU", "--cpus",
                      "une boucle occupe tous les cœurs du noeud",
                      commence("--cpus")),
            new Porte("script en clair", "--interactive",
                      "le script voyage alors dans la ligne de commande, donc "
                      + "dans `ps`, dans `docker inspect` et dans les journaux "
                      + "du demon",
                      contient("--interactive")),
            new Porte("fuite d'etat", "--rm",
                      "le conteneur survit, et le suivant herite de ses fichiers",
                      contient("--rm")));

    private AuditDurcissement() {
    }

    public record Constat(Porte porte, boolean fermee) {
    }

    public static List<Constat> auditer(CommandeDocker commande) {
        List<String> drapeaux = commande.drapeaux();
        return PORTES.stream()
                .map(porte -> new Constat(porte, porte.estFermee(drapeaux)))
                .toList();
    }

    public static List<Porte> ouvertes(CommandeDocker commande) {
        return auditer(commande).stream()
                .filter(constat -> !constat.fermee())
                .map(Constat::porte)
                .toList();
    }

    public static boolean conforme(CommandeDocker commande) {
        return ouvertes(commande).isEmpty();
    }

    /** Le compte-rendu, tel qu'une CI l'afficherait. */
    public static List<String> rendre(CommandeDocker commande) {
        List<String> lignes = new java.util.ArrayList<>();
        lignes.add(String.format("%-22s %-34s %s", "PORTE", "DRAPEAU", "ETAT"));
        for (Constat constat : auditer(commande)) {
            lignes.add(String.format("%-22s %-34s %s",
                    constat.porte().nom(), constat.porte().drapeau(),
                    constat.fermee() ? "fermee" : "⚠️ OUVERTE"));
        }
        List<Porte> ouvertes = ouvertes(commande);
        lignes.add("");
        lignes.add(ouvertes.isEmpty()
                ? "conforme : les " + PORTES.size() + " portes sont fermees"
                : "⚠️ " + ouvertes.size() + " porte(s) ouverte(s) sur "
                  + PORTES.size());
        for (Porte porte : ouvertes) {
            lignes.add("   " + porte.nom() + " → " + porte.siOuverte());
        }
        return lignes;
    }
}
