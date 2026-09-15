/**
 * Les pièces à conviction : cinq classes <strong>volontairement fautives</strong>.
 *
 * <p><strong>Ne pas les réparer.</strong> Chacune porte un défaut précis que
 * les chapitres mesurent, et {@code src/test/java} vérifie que le défaut est
 * toujours là. Corriger l'une d'elles fait échouer un test — ce qui est le
 * comportement voulu : le défaut est le sujet.
 *
 * <table class="striped">
 *   <caption>Ce que chacune démontre</caption>
 *   <tr><th>classe</th><th>défaut</th><th>mesuré au</th></tr>
 *   <tr><td>{@link fr.portail.pieges.CandidatEcritMain}</td>
 *       <td>{@code equals} redéfini, {@code hashCode} oublié</td><td>chapitre 2</td></tr>
 *   <tr><td>{@link fr.portail.pieges.CleMuable}</td>
 *       <td>{@code hashCode} dépend d'un champ qui bouge</td><td>chapitre 3</td></tr>
 *   <tr><td>{@link fr.portail.pieges.SacCompteur}</td>
 *       <td>hérite de {@code HashSet} et compte double</td><td>chapitre 2</td></tr>
 *   <tr><td>{@link fr.portail.pieges.PanierSansCopie}</td>
 *       <td>un {@code record} sans copie défensive</td><td>chapitre 3</td></tr>
 *   <tr><td>{@link fr.portail.pieges.Guichet}</td>
 *       <td>un compteur partagé sans protection</td><td>chapitre 5</td></tr>
 * </table>
 */
package fr.portail.pieges;
