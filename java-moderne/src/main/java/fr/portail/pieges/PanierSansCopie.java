package fr.portail.pieges;

import java.util.List;

/**
 * Un {@code record} qui garde la liste qu'on lui a donnée, telle quelle.
 *
 * <p>⚠️ <strong>Pièce à conviction : ne pas réparer.</strong> Un record est
 * souvent présenté comme « immuable ». C'est vrai de ses <em>références</em> :
 * on ne peut pas réaffecter {@code articles}. Ce n'est pas vrai de ce qu'elles
 * désignent — si la liste passée au constructeur est modifiable, l'appelant
 * garde le moyen de la changer <em>après</em> la construction.
 *
 * <p>Conséquence mesurée au chapitre 3 : le {@code hashCode} du record change
 * tout seul, et l'objet devient introuvable dans l'ensemble où il se trouve
 * pourtant. C'est exactement le défaut de {@link CleMuable}, atteint par un
 * chemin qu'on croyait fermé.
 *
 * <p>Le correctif tient en une ligne dans le bloc compact —
 * {@code articles = List.copyOf(articles);} — et c'est ce que fait
 * {@link fr.portail.domaine.Candidat}.
 */
public record PanierSansCopie(String nom, List<String> articles) {
}
