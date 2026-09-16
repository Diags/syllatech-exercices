package fr.portail.chapitres;

import fr.portail.observabilite.Disjoncteur;
import fr.portail.observabilite.Mesures;
import fr.portail.runner.DemandeExecution;
import fr.portail.runner.ExecutionDansLaJvm;
import fr.portail.runner.ExecutionEnBacASable;
import fr.portail.runner.Resultat;
import fr.portail.runner.ServiceExecution;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.util.List;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

/**
 * Chapitre 6 — Tests d'evasion, observabilite et production.
 *
 * <pre>
 *   mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre6Evasion
 * </pre>
 *
 * <p>On n'affirme pas qu'une cage tient : on l'attaque. Ce chapitre rejoue
 * six soumissions hostiles contre les DEUX implantations et imprime le
 * tableau — puis il lit les metriques et fait ouvrir un disjoncteur.
 */
public final class Chapitre6Evasion {

    private Chapitre6Evasion() {
    }

    /** Les soumissions hostiles, et ce qu'elles cherchent. */
    private record Attaque(String nom, String code, String cherche) {
    }

    private static final List<Attaque> ATTAQUES = List.of(
            new Attaque("lire un fichier de l'hote",
                        "lire_fichier \"pom.xml\"",
                        "exfiltrer un fichier du serveur"),
            new Attaque("lire un secret de l'app",
                        "secret jobportal.cle-api",
                        "lire la configuration de l'application"),
            new Attaque("ouvrir une connexion",
                        "connexion \"127.0.0.1\" 80",
                        "sortir vers le reseau interne"),
            new Attaque("boucler sans fin",
                        "boucle",
                        "immobiliser le service"),
            new Attaque("devorer la memoire",
                        "memoire 400",
                        "saturer le noeud"),
            new Attaque("inonder la sortie",
                        ("ecrire " + "X".repeat(500) + "\n").repeat(80),
                        "saturer la memoire du runner"));

    public static void main(String[] args) {
        ServiceExecution dansLaJvm =
                new ExecutionDansLaJvm(nom -> "sk-secret-de-production");
        ServiceExecution bacASable = new ExecutionEnBacASable(3, 48);

        System.out.println("""
                1. LA MESURE QUI TRANCHE : ON ATTAQUE SA PROPRE CAGE
                """);
        System.out.printf("   %-28s %-22s %s%n",
                          "ATTAQUE", "dans la JVM", "processus separe");

        int passeesDansLaJvm = 0;
        int passeesEnBac = 0;
        int abandonnees = 0;
        for (Attaque attaque : ATTAQUES) {
            // ⚠️ L'appel « dans la JVM » est lui-meme borne DE L'EXTERIEUR,
            // parce qu'il n'a aucune borne interne : sans cela, la
            // soumission « boucle » ne rendrait jamais la main et ce
            // chapitre ne se terminerait pas. C'est deja la demonstration.
            Resultat gauche = avecUnDelai(dansLaJvm, attaque.code(), 4);
            Resultat droite = bacASable.lancer(
                    DemandeExecution.script(attaque.code()));
            boolean passeGauche = gauche == null || reussie(gauche);
            boolean passeDroite = reussie(droite);
            passeesDansLaJvm += passeGauche ? 1 : 0;
            passeesEnBac += passeDroite ? 1 : 0;
            abandonnees += gauche == null ? 1 : 0;
            System.out.printf("   %-28s %-22s %s%n", attaque.nom(),
                    gauche == null ? "⚠️ JAMAIS RENDUE"
                            : verdict(passeGauche, gauche),
                    verdict(passeDroite, droite));
        }

        System.out.printf("%n   %-28s %-22s %s%n", "ATTAQUES NON BLOQUEES",
                passeesDansLaJvm + " sur " + ATTAQUES.size(),
                passeesEnBac + " sur " + ATTAQUES.size());
        System.out.printf("   %-28s %-22s %s%n", "dont jamais rendues",
                abandonnees + "", "0");

        System.out.println("""

                   ⚠️ Un test d'evasion n'affirme pas qu'une attaque
                   ECHOUE : il affirme qu'elle n'aboutit pas a un SUCCES.
                   Le predicat est toujours le meme —

                      assertThat(r.codeSortie() != 0 || r.delaiDepasse())
                          .isTrue();

                   — parce qu'on ne sait pas d'avance COMMENT la cage
                   tiendra. Un refus de privilege, une erreur, un delai
                   depasse : les trois sont des succes du bac a sable. Un
                   code 0 avec une sortie utile est le seul echec.

                   Ces tests tournent en integration continue a chaque
                   changement du bac a sable, de son image ou de sa version
                   de runtime. Une evasion qui reussit est un ticket
                   bloquant — pas une regression a trier plus tard.
                """);

        System.out.println("""
                2. LES METRIQUES QU'ON REGARDE VRAIMENT
                """);
        Mesures mesures = new Mesures(new SimpleMeterRegistry());
        for (Attaque attaque : ATTAQUES) {
            mesures.enregistrer(bacASable.lancer(
                    DemandeExecution.script(attaque.code())));
        }
        for (int i = 0; i < 4; i++) {
            mesures.enregistrer(bacASable.lancer(
                    DemandeExecution.script("ecrire bonjour")));
        }

        System.out.printf("      executions             : %d%n",
                          mesures.executions());
        System.out.printf("      duree moyenne          : %.0f ms%n",
                          mesures.dureeMoyenneEnMillisecondes());
        System.out.printf("      delais depasses        : %d (%.0f %%)%n",
                          mesures.delaisDepasses(),
                          mesures.tauxDeDelaiDepasse() * 100);
        System.out.printf("      refus de privilege     : %d%n",
                          mesures.refusDePrivilege());
        System.out.printf("      echecs de demarrage    : %d%n",
                          mesures.echecsDeDemarrage());

        System.out.println("""

                   Le compteur qui compte est le troisieme. Zero est la
                   normale ; un pic de refus de privilege est une serie
                   temporelle sur laquelle on met une ALERTE, et c'est la
                   seule facon de transformer « quelqu'un a peut-etre
                   essaye » en un signal.

                   ⚠️ Et distinguez bien les deux derniers : un refus de
                   privilege est un incident de SECURITE ; un echec de
                   demarrage est un incident d'EXPLOITATION — le demon ne
                   repond pas, l'image a disparu, le noeud est plein. Les
                   confondre fait reveiller la mauvaise equipe.
                """);

        System.out.println("""
                3. LE DISJONCTEUR, ET CE QU'IL NE DOIT PAS COMPTER
                """);
        Disjoncteur disjoncteur = new Disjoncteur(3);
        ServiceExecution enPanne = new ServiceExecution() {
            @Override
            public Resultat lancer(DemandeExecution demande) {
                return new Resultat("", "le bac a sable n'a pas demarre", -2,
                                    false, 12);
            }

            @Override
            public String nom() {
                return "bac a sable en panne";
            }
        };

        System.out.printf("   %-8s %-16s %s%n", "APPEL", "ETAT", "REPONSE");
        for (int appel = 1; appel <= 5; appel++) {
            Resultat resultat = disjoncteur.appeler(
                    () -> enPanne.lancer(DemandeExecution.script("ecrire x")),
                    () -> new Resultat("", "bac a sable indisponible", -9,
                                       false, 0),
                    r -> r.codeSortie() == -2);
            System.out.printf("   %-8d %-16s %s%n", appel, disjoncteur.etat(),
                              resultat.erreurs());
        }

        System.out.println("""

                   Au troisieme echec de DEMARRAGE, le circuit s'ouvre : les
                   appels suivants echouent en 0 ms au lieu d'attendre le
                   delai complet. Sans lui, une panne du bac a sable
                   immobilise un fil d'execution par soumission, et la panne
                   du runner devient la panne de l'application.

                   ⚠️ Ce disjoncteur ne compte QUE les echecs de demarrage.
                   Un candidat dont la solution plante, boucle ou tente une
                   evasion est un evenement NORMAL : le compter comme une
                   panne ouvrirait le circuit sur du trafic parfaitement
                   sain — et c'est l'erreur de reglage la plus frequente.
                """);

        System.out.println("""
                4. CE QU'IL RESTE A FAIRE, ET QUE CE PROJET NE FAIT PAS
                """);
        System.out.println("""
                      • lancer VRAIMENT `docker run --runtime=runsc` : le
                        chapitre 4 construit et audite la ligne, il ne
                        l'execute pas. Un processus separe partage le noyau ;
                        gVisor est ce qui le remplace par un noyau en espace
                        utilisateur ;
                      • tenir le runtime d'isolation A JOUR. Un bac a sable
                        n'est sur que patche — les evasions publiees de
                        gVisor, de runc et des hyperviseurs se corrigent par
                        des mises a jour, pas par des reglages ;
                      • surveiller le NOEUD, pas seulement le service :
                        charge, memoire, nombre de processus. Une fork bomb
                        contenue par `--pids-limit` reste visible la ;
                      • et refaire l'exercice a chaque nouveau langage
                        accepte. Chaque runtime ajoute sa propre surface —
                        un `import os` en Python, un `Runtime.exec` en Java,
                        un `child_process` en Node.
                """);
    }

    private static boolean reussie(Resultat resultat) {
        return resultat.codeSortie() == 0 && !resultat.delaiDepasse();
    }

    /**
     * Appelle un service qui n'a AUCUNE borne, en lui en imposant une de
     * l'exterieur.
     *
     * <p>⚠️ Et le fil abandonne continue de tourner. `Future.cancel(true)`
     * pose un drapeau d'interruption que la boucle du script ne regarde
     * pas — `Thread.stop` est supprime depuis Java 20, et il n'existe
     * AUCUNE facon d'arreter un fil qui ne coopere pas. Le pool est en
     * mode « demon » pour que ce chapitre puisse au moins se terminer ;
     * dans un vrai serveur, ce fil reste occupe jusqu'au redemarrage.
     *
     * @return null quand l'appel n'a jamais rendu la main
     */
    private static Resultat avecUnDelai(ServiceExecution service, String code,
                                        long secondes) {
        ExecutorService pool = Executors.newSingleThreadExecutor(tache -> {
            Thread fil = new Thread(tache, "candidat-non-borne");
            fil.setDaemon(true);
            return fil;
        });
        try {
            Future<Resultat> promesse = pool.submit(
                    () -> service.lancer(DemandeExecution.script(code)));
            return promesse.get(secondes, TimeUnit.SECONDS);
        } catch (TimeoutException abandon) {
            return null;
        } catch (InterruptedException interruption) {
            Thread.currentThread().interrupt();
            return null;
        } catch (ExecutionException erreur) {
            return new Resultat("", String.valueOf(erreur.getCause()), 1,
                                false, 0);
        } finally {
            pool.shutdownNow();
        }
    }

    private static String verdict(boolean passee, Resultat resultat) {
        if (passee) {
            return "⚠️ REUSSIE";
        }
        if (resultat.delaiDepasse()) {
            return "bloquee (delai)";
        }
        if (resultat.codeSortie() == Mesures.CODE_REFUS) {
            return "bloquee (privilege)";
        }
        return "bloquee (code " + resultat.codeSortie() + ")";
    }
}
