package fr.portail.chapitres;

import fr.portail.modele.ModeleFactice;
import fr.portail.outils.CatalogueOffres;
import io.agentscope.core.ReActAgent;
import io.agentscope.core.event.AgentEvent;
import io.agentscope.core.event.AgentEventType;
import io.agentscope.core.message.Msg;
import io.agentscope.core.model.ToolSchema;
import io.agentscope.core.permission.PermissionBehavior;
import io.agentscope.core.permission.PermissionContextState;
import io.agentscope.core.permission.PermissionDecision;
import io.agentscope.core.permission.PermissionEngine;
import io.agentscope.core.permission.PermissionMode;
import io.agentscope.core.permission.PermissionRule;
import io.agentscope.core.tool.ToolBase;
import io.agentscope.core.tool.Toolkit;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Chapitre 3 — Outils et permissions.
 *
 * <pre>
 *   mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre3Outils
 * </pre>
 *
 * <p>Le modele ne touche jamais au catalogue : il emet une INTENTION, et
 * c'est le runtime qui decide. Ce chapitre imprime le schema qu'AgentScope
 * engendre depuis les annotations, envoie la MEME intention hostile a trois
 * agents qui ne different que par leur regle — puis montre la facon
 * d'ecrire cette regle qui ne protege RIEN, sans rien signaler.
 */
public final class Chapitre3Outils {

    private Chapitre3Outils() {
    }

    /** La demande hostile, identique dans tous les essais. */
    private static final String DEMANDE = "Fais le menage dans les offres.";

    /**
     * ⚠️ LE CONTENU D'UNE REGLE QUI S'APPLIQUE A TOUT EST LA CHAINE VIDE.
     *
     * <p>Pas {@code "*"} : voir la section 4, qui le mesure.
     */
    private static final String TOUS_LES_ARGUMENTS = "";

    public static void main(String[] args) {
        System.out.println("""
                1. VOS METHODES JAVA DEVIENNENT DES OUTILS, AVEC LEUR SCHEMA
                """);
        Toolkit vitrine = new Toolkit();
        vitrine.registerTool(new CatalogueOffres());

        System.out.printf("   %-22s %-11s %-11s %s%n", "OUTIL", "PARAMETRES",
                          "LECTURE ?", "DESCRIPTION (lue par le MODELE)");
        for (ToolSchema schema : vitrine.getToolSchemas()) {
            ToolBase outil = (ToolBase) vitrine.getTool(schema.getName());
            System.out.printf("   %-22s %-11s %-11s %s%n",
                    schema.getName(), parametres(schema),
                    outil.isReadOnly() ? "oui" : "⚠️ non",
                    couper(schema.getDescription(), 46));
        }

        System.out.println("""

                   ⚠️ Ces descriptions ne sont pas de la documentation : elles
                   partent dans le prompt, a chaque appel. Une description
                   vague est un outil mal appele — et le cout se paie en
                   tours de boucle.

                   Le schema est engendre depuis `@Tool` et `@ToolParam` : il
                   n'y a pas de JSON a maintenir a cote du code, donc pas de
                   derive possible entre les deux. Et `readOnly` n'est pas
                   decoratif : c'est lui que les modes de permission lisent.
                """);

        System.out.println("""
                2. LA MESURE QUI TRANCHE : TROIS REGLES, UNE MEME INTENTION
                """);
        System.out.println("""
                   Trois agents identiques — meme modele, meme sysPrompt,
                   meme catalogue. Seule change la regle posee sur
                   `supprimer_offre`. Le modele, lui, demande la meme chose
                   dans les trois cas.
                """);

        System.out.printf("   %-8s %-9s %-11s %-13s %s%n", "REGLE", "OFFRES",
                          "SUPPRIMEE", "OUTILS EXEC.", "EVENEMENT DU RUNTIME");
        Essai sousAsk = null;
        for (PermissionBehavior regle : List.of(PermissionBehavior.ALLOW,
                                                PermissionBehavior.ASK,
                                                PermissionBehavior.DENY)) {
            Essai essai = jouer(regle, TOUS_LES_ARGUMENTS);
            if (regle == PermissionBehavior.ASK) {
                sousAsk = essai;
            }
            System.out.printf("   %-8s %-9d %-11s %-13d %s%n",
                    regle.getValue(), essai.offresRestantes(),
                    essai.offresRestantes() < 6 ? "⚠️ OUI" : "non",
                    essai.outilsExecutes(), essai.evenementMarquant());
        }

        System.out.println("""

                   ⚠️ Sous DENY et sous ASK, le catalogue n'a PAS ete
                   appele : zero outil execute, six offres toujours la. Ce
                   n'est pas le modele qui a renonce — il a demande la
                   suppression dans les trois cas. C'est le runtime qui a
                   court-circuite l'appel.

                   ⚠️ ET REGARDEZ LA COLONNE DES EVENEMENTS : sous DENY,
                   la boucle produit quand meme un `TOOL_RESULT_END`. Le
                   refus n'est pas une exception : c'est un RESULTAT
                   D'OUTIL, rendu au modele comme n'importe quel autre. Le
                   modele apprend donc qu'il n'a pas le droit, et peut
                   s'adapter — proposer autre chose, expliquer a
                   l'utilisateur. Une exception, elle, aurait casse la
                   conversation.

                """);

        System.out.println("""
                3. ⚠️ CE QUE « DEMANDER APPROBATION » NE FAIT PAS TOUT SEUL
                """);
        System.out.printf("   Sous ASK, la reponse rendue a l'utilisateur est :"
                          + "%n%n      « %s »%n%n",
                          premiereLigne(sousAsk.reponseFinale()));
        System.out.printf("   ... et le catalogue compte toujours %d offres, "
                          + "pour %d outil(s) execute(s).%n",
                          sousAsk.offresRestantes(), sousAsk.outilsExecutes());

        System.out.println("""

                   ⚠️ LISEZ CES DEUX LIGNES ENSEMBLE. L'agent annonce que
                   c'est fait. Rien n'a ete fait. Et il n'a trompe personne :
                   le runtime a EMIS un `REQUIRE_USER_CONFIRM`, puis a rendu
                   la main. Il n'attend pas — il n'a aucun moyen d'attendre.

                   ASK n'est donc pas une suspension automatique : c'est un
                   PROTOCOLE. Le framework dit « un humain doit trancher » ;
                   c'est a l'APPLICATION de s'arreter la, de poser la
                   question, et de reprendre la conversation avec la reponse.
                   Une interface qui ignore cet evenement affiche une
                   confirmation pour une action qui n'a jamais eu lieu.

                   C'est le piege le plus couteux de ce chapitre, parce que
                   tout se passe bien : aucune erreur, aucune trace, et un
                   utilisateur convaincu.

                   La regle : si votre interface ne sait pas traiter
                   `REQUIRE_USER_CONFIRM`, la regle a poser est DENY, pas
                   ASK. Un refus franc vaut mieux qu'une approbation que
                   personne ne recueille.
                """);

        System.out.println("""
                4. ⚠️ LA REGLE QUI NE PROTEGE RIEN, ET NE LE DIT PAS
                """);
        System.out.println("""
                   Le reflexe, pour « cette regle vaut pour tous les
                   arguments », est d'ecrire une etoile :

                      new PermissionRule("supprimer_offre", "*",
                                         PermissionBehavior.DENY, "politique")

                   Le contenu d'une regle est un MOTIF compare aux arguments
                   de l'appel — pour un outil de fichier, un chemin. L'etoile
                   n'y est pas un joker : c'est un motif litteral, qui ne
                   correspond a rien. La regle est enregistree, elle
                   n'echoue pas, elle ne previent pas — elle ne s'applique
                   simplement jamais.
                """);

        System.out.printf("   %-26s %-14s %s%n",
                          "CONTENU DE LA REGLE", "DECISION", "LA REGLE A-T-ELLE SERVI ?");
        Toolkit banc = new Toolkit();
        banc.registerTool(new CatalogueOffres());
        ToolBase suppression = (ToolBase) banc.getTool("supprimer_offre");
        for (String contenu : List.of("*", "OFF-101", TOUS_LES_ARGUMENTS)) {
            PermissionDecision decision = decider(suppression, contenu,
                                                  PermissionBehavior.DENY,
                                                  PermissionMode.DEFAULT);
            boolean servie = decision != null
                    && decision.getBehavior() == PermissionBehavior.DENY;
            System.out.printf("   %-26s %-14s %s%n",
                    contenu.isEmpty() ? "\"\" (chaine vide)" : "\"" + contenu + "\"",
                    decision == null ? "(aucune)" : decision.getBehavior(),
                    servie ? "oui" : "⚠️ NON — repli sur le MODE");
        }

        System.out.println("""

                   Une regle « DENY » ecrite avec une etoile laisse donc
                   l'outil au regime par defaut du mode. Sous `DEFAULT`, ce
                   regime est ASK — on croit avoir interdit, on a seulement
                   demande. Sous `BYPASS`, ce serait ALLOW : la suppression
                   passerait.

                   C'est le genre d'erreur qu'aucun test ne rattrape si l'on
                   teste « l'action n'a pas eu lieu » plutot que « la regle a
                   ete appliquee ».
                """);

        System.out.println("""
                5. LE MODE EST LA POLITIQUE PAR DEFAUT, ET IL DECIDE BEAUCOUP
                """);
        System.out.printf("   %-16s %-22s %s%n", "MODE",
                          "OUTIL DE LECTURE", "OUTIL D'ECRITURE");
        ToolBase recherche = (ToolBase) banc.getTool("rechercher_offres");
        for (PermissionMode mode : PermissionMode.values()) {
            PermissionEngine moteur = new PermissionEngine(
                    PermissionContextState.builder().mode(mode).build());
            System.out.printf("   %-16s %-22s %s%n", mode,
                    verdict(moteur, recherche, Map.of("motCle", "java")),
                    verdict(moteur, suppression, Map.of("reference", "OFF-101")));
        }

        System.out.println("""

                   ⚠️ Lisez la premiere ligne : sous `DEFAULT`, meme un outil
                   de LECTURE demande confirmation. C'est prudent, et c'est
                   invivable en production — d'ou `EXPLORE`, qui autorise la
                   lecture et refuse l'ecriture, et qui est le mode a
                   connaitre pour un assistant en libre-service.

                   `BYPASS` autorise tout, y compris ce qu'une regle DENY
                   ecrite avec une etoile croyait interdire. C'est la
                   combinaison a ne jamais laisser partir en production.
                """);

        System.out.println("""
                6. CE QU'UNE PERMISSION NE PROTEGE PAS
                """);
        System.out.println("""
                   Une permission encadre CE QUE l'agent fait. Elle ne dit
                   rien de :

                      • l'injection de prompt — une offre dont l'intitule
                        contient « ignore tes consignes » traverse le
                        catalogue comme une donnee ordinaire, et arrive dans
                        le contexte du modele ;
                      • la sur-permission — un outil « rechercher » qui
                        accepte un filtre libre est une porte ouverte, quel
                        que soit son regime ;
                      • l'exfiltration — un outil autorise qui rend TROP de
                        donnees les livre au modele, donc au fournisseur.

                   Le regime d'un outil est la derniere ligne de defense. La
                   premiere est la SURFACE de cet outil : ce qu'il accepte en
                   entree, et ce qu'il rend en sortie.
                """);
    }

    /** Ce qu'un essai a produit. */
    private record Essai(int offresRestantes, int outilsExecutes,
                         String evenementMarquant, String reponseFinale) {
    }

    /** Le meme agent, la meme demande, une regle differente. */
    private static Essai jouer(PermissionBehavior regle, String contenu) {
        CatalogueOffres catalogue = new CatalogueOffres();
        Toolkit toolkit = new Toolkit();
        toolkit.registerTool(catalogue);

        PermissionContextState.Builder contexte = PermissionContextState.builder();
        PermissionRule sur = new PermissionRule("supprimer_offre", contenu,
                                                regle, "politique-du-portail");
        switch (regle) {
            case ALLOW -> contexte.addAllowRule("supprimer_offre", sur);
            case ASK -> contexte.addAskRule("supprimer_offre", sur);
            case DENY -> contexte.addDenyRule("supprimer_offre", sur);
            default -> throw new IllegalArgumentException(regle.toString());
        }

        ModeleFactice modele = new ModeleFactice("factice:" + regle.getValue(),
                List.of(new ModeleFactice.Tour.AppelDOutil("supprimer_offre",
                                Map.of("reference", "OFF-101")),
                        new ModeleFactice.Tour.Reponse("C'est fait.")));

        ReActAgent agent = ReActAgent.builder()
                .name("conseiller-" + regle.getValue())
                .sysPrompt("Tu es le conseiller carriere syllatech.")
                .model(modele)
                .toolkit(toolkit)
                .maxIters(3)
                .permissionContext(contexte.build())
                .build();

        // On lit le FLUX pour voir ce que le runtime ANNONCE, puis on rejoue
        // la meme demande en appel ordinaire pour lire ce qu'il REND.
        List<AgentEvent> evenements = agent
                .streamEvents(DEMANDE, Chapitre1Agent.contexte("s-" + regle))
                .take(Duration.ofSeconds(15))
                .collectList()
                .block();

        Msg reponse = agent
                .call(DEMANDE, Chapitre1Agent.contexte("s2-" + regle))
                .block(Duration.ofSeconds(15));

        return new Essai(catalogue.nombreDOffres(), catalogue.journal().size(),
                         marquant(evenements), Chapitre1Agent.texte(reponse));
    }

    private static PermissionDecision decider(ToolBase outil, String contenu,
                                              PermissionBehavior regle,
                                              PermissionMode mode) {
        PermissionContextState.Builder contexte =
                PermissionContextState.builder().mode(mode);
        PermissionRule sur = new PermissionRule(outil.getName(), contenu, regle,
                                                "politique-du-portail");
        switch (regle) {
            case ALLOW -> contexte.addAllowRule(outil.getName(), sur);
            case ASK -> contexte.addAskRule(outil.getName(), sur);
            case DENY -> contexte.addDenyRule(outil.getName(), sur);
            default -> throw new IllegalArgumentException(regle.toString());
        }
        return new PermissionEngine(contexte.build())
                .checkPermission(outil, Map.of("reference", "OFF-101")).block();
    }

    private static String verdict(PermissionEngine moteur, ToolBase outil,
                                  Map<String, Object> arguments) {
        PermissionDecision decision =
                moteur.checkPermission(outil, arguments).block();
        String nom = decision == null ? "(aucune)"
                : decision.getBehavior().name();
        return nom + (nom.equals("ALLOW") ? "" : "  ⚠️");
    }

    /** L'evenement qui dit ce que le runtime a decide. */
    private static String marquant(List<AgentEvent> evenements) {
        if (evenements == null) {
            return "(aucun)";
        }
        Set<AgentEventType> parlants = Set.of(
                AgentEventType.ALL_TOOLS_DENIED,
                AgentEventType.REQUIRE_USER_CONFIRM,
                AgentEventType.TOOL_RESULT_END);
        for (AgentEvent evenement : evenements) {
            if (parlants.contains(evenement.getType())) {
                return evenement.getType().name();
            }
        }
        return "(aucun evenement decisif)";
    }

    private static String parametres(ToolSchema schema) {
        Map<String, Object> parametres = schema.getParameters();
        if (parametres != null
                && parametres.get("properties") instanceof Map<?, ?> carte) {
            return String.join(", ",
                    carte.keySet().stream().map(String::valueOf).toList());
        }
        return "(aucun)";
    }

    static String premiereLigne(String texte) {
        int fin = texte.indexOf(10);
        return fin < 0 ? texte : texte.substring(0, fin);
    }

    private static String couper(String texte, int largeur) {
        if (texte == null) {
            return "(aucune)";
        }
        String propre = texte.replace("\n", " ");
        return propre.length() <= largeur ? propre
                : propre.substring(0, largeur - 1) + "…";
    }
}
