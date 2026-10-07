package fr.portail.chapitres;

import fr.portail.api.OffreService;
import fr.portail.domaine.CompteurDeRequetes;
import fr.portail.domaine.OffreRepository;
import java.util.List;

/**
 * Chapitre 3 — JPA et base de donnees.
 *
 * <pre>
 *   mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre3Jpa
 * </pre>
 *
 * <p>Le N+1 n'est pas une histoire qu'on raconte : ce chapitre COMPTE le SQL
 * reellement emis, par un {@code StatementInspector} d'Hibernate. Puis il
 * montre ce que Spring Data derive d'un nom de methode, et ce que Flyway
 * garantit qu'`ddl-auto=update` ne garantit jamais.
 */
public final class Chapitre3Jpa {

    private Chapitre3Jpa() {
    }

    public static void main(String[] args) {
        try (Banc banc = Banc.demarrer()) {
            CompteurDeRequetes compteur = banc.bean(CompteurDeRequetes.class);
            OffreService service = banc.bean(OffreService.class);
            OffreRepository repository = banc.bean(OffreRepository.class);

            System.out.println("""
                    1. LA MESURE QUI TRANCHE : LE N+1, COMPTE
                    """);
            System.out.println("""
                   Six offres au catalogue, chacune rattachee a une
                   entreprise. On demande la liste, et on lit le nom de
                   l'entreprise de chaque offre — ce que fait n'importe
                   quel affichage.
                """);

            compteur.demarrer();
            service.listerAvecUnNPlusUn();
            compteur.arreter();
            int avecNPlusUn = compteur.selects().size();
            List<String> requetesNPlusUn = compteur.selects();

            compteur.demarrer();
            service.lister();
            compteur.arreter();
            int avecJointure = compteur.selects().size();

            System.out.printf("   %-34s %-12s %s%n",
                              "FACON D'ECRIRE LA REQUETE", "SELECT", "POUR 6 OFFRES");
            System.out.printf("   %-34s %-12d %s%n", "findAll() puis .getNom()",
                              avecNPlusUn,
                              avecNPlusUn > 1
                                      ? "⚠️ 1 + " + (avecNPlusUn - 1)
                                        + " entreprises distinctes"
                                      : "");
            System.out.printf("   %-34s %-12d %s%n", "join fetch o.entreprise",
                              avecJointure, "une seule");

            System.out.println("\n   Les requetes du premier cas :\n");
            for (int rang = 0; rang < Math.min(3, requetesNPlusUn.size()); rang++) {
                System.out.printf("      %d. %s%n", rang + 1,
                                  couper(requetesNPlusUn.get(rang), 66));
            }
            if (requetesNPlusUn.size() > 3) {
                System.out.printf("      … et %d autres, identiques a la "
                                  + "deuxieme%n", requetesNPlusUn.size() - 3);
            }

            System.out.println("""

                   ⚠️ UNE REQUETE POUR LA LISTE, PUIS UNE PAR ENTREPRISE
                   DISTINCTE. Six offres, mais seulement trois requetes
                   supplementaires : le cache de premier niveau d'Hibernate
                   reconnait une entreprise deja chargee et ne la redemande
                   pas.

                   Cette deduplication est une bonne nouvelle, et c'est
                   aussi ce qui rend le N+1 si difficile a voir : sur un jeu
                   de test ou dix lignes partagent deux entreprises, l'ecart
                   est de deux requetes. Sur un catalogue reel ou chaque
                   offre a son entreprise, c'est une requete par ligne — et
                   la page met trente secondes, et l'on accuse la base.

                   ⚠️ ET LA BONNE CORRECTION N'EST PAS `FetchType.EAGER`.
                   Forcer EAGER paie la jointure a CHAQUE chargement d'offre,
                   y compris quand personne ne demande l'entreprise — on
                   deplace le cout, on ne le supprime pas. La reponse est un
                   `join fetch` CIBLE, la ou on a besoin de la relation.

                   ⚠️ Et souvenez-vous de la dissymetrie : `@ManyToOne` et
                   `@OneToOne` sont EAGER par defaut, `@OneToMany` et
                   `@ManyToMany` sont LAZY. C'est elle qui fabrique le N+1
                   sans qu'on ait rien demande.
                """);

            System.out.println("""
                    2. LE NOM DE LA METHODE EST LA REQUETE
                    """);
            compteur.demarrer();
            var java = repository.findByTitreContainingIgnoreCase("java");
            compteur.arreter();
            System.out.printf("   findByTitreContainingIgnoreCase(\"java\") → %d offre(s)%n",
                              java.size());
            System.out.printf("   %s%n%n", couper(
                    compteur.selects().isEmpty() ? "(aucune)"
                            : compteur.selects().getFirst(), 74));

            compteur.demarrer();
            var devops = repository.findByPile("devops");
            compteur.arreter();
            System.out.printf("   findByPile(\"devops\")                    → %d offre(s)%n",
                              devops.size());

            System.out.println("""

                   Zero ligne d'implantation, zero chaine SQL — et le
                   compilateur verifie le type de retour. Renommer le champ
                   `titre` dans l'entite fait echouer le DEMARRAGE, parce
                   que `findByTitre…` ne correspond plus a rien. L'erreur
                   arrive avant le premier utilisateur, et c'est tout
                   l'interet.

                   ⚠️ La limite est la lisibilite : au-dela de trois
                   criteres, un nom de methode devient illisible
                   (`findByPileAndVilleAndSalaireGreaterThanOrderByTitreAsc`).
                   C'est le moment de reprendre la main avec `@Query`, pas de
                   continuer a empiler.
                """);

            System.out.println("""
                    3. CE QUE FLYWAY GARANTIT, ET QUE `ddl-auto=update` NE GARANTIT PAS
                    """);
            System.out.printf("   %-30s %s%n", "spring.jpa.hibernate.ddl-auto",
                              "validate");
            System.out.printf("   %-30s %s%n", "migrations appliquees",
                              "V1__schema_initial, V2__donnees_du_portail");
            System.out.println("""

                   Le schema appartient a Flyway ; Hibernate se contente de
                   VERIFIER que les entites lui correspondent. Une entite qui
                   derive fait echouer le demarrage — ce qui est exactement
                   ce qu'on veut.

                   ⚠️ `ddl-auto=update`, le reglage qu'on trouve partout, fait
                   l'inverse : il modifie la base pour la faire ressembler aux
                   entites. En developpement c'est commode ; en production,
                   personne ne sait plus quel est le schema reel, et
                   `update` ne SUPPRIME jamais rien — les colonnes mortes
                   s'accumulent, et un renommage laisse les deux.

                   ⚠️ Et il y a un piege de reglage juste a cote :
                   `spring.jpa.open-in-view` vaut `true` PAR DEFAUT. La
                   session JPA reste alors ouverte pendant le rendu de la
                   reponse, donc un N+1 parti de la couche web ne leve
                   aucune erreur — il ralentit, simplement. Ce projet le met
                   a `false`, et c'est pour cela que la conversion en DTO a
                   lieu DANS le service.
                """);

            System.out.println("""
                    4. LE COMPTEUR EST UN OUTIL DE PRODUCTION, PAS UNE CURIOSITE
                    """);
            System.out.println("""
                   `spring.jpa.show-sql=true` affiche le SQL en
                   developpement, et c'est deja beaucoup. Mais un journal ne
                   fait jamais echouer une integration continue.

                   Le `StatementInspector` de ce projet, lui, COMPTE — et un
                   test peut donc dire :

                      assertThat(compteur.selects()).hasSize(1);

                   C'est ce qui empeche le N+1 de revenir six mois plus tard,
                   quand quelqu'un remplacera le `join fetch` par un
                   `findAll()` « plus simple ».
                """);
        }
    }

    private static String couper(String texte, int largeur) {
        String propre = texte.replaceAll("\\s+", " ").strip();
        return propre.length() <= largeur ? propre
                : propre.substring(0, largeur - 1) + "…";
    }
}
