/**
 * Les expressions — autour du VRAI évaluateur de n8n.
 *
 *     new Expression(workflow).resolveSimpleParameterValue(valeur, donnees)
 *
 * C'est la méthode que n8n appelle pour chaque champ de chaque nœud. Ce
 * module l'enveloppe pour la rendre lisible, et pour mesurer deux choses que
 * l'éditeur ne montre pas.
 *
 * LE SIGNE « = » EST LA MOITIÉ DE L'HISTOIRE
 *
 * Dans le JSON d'un workflow, un champ qui contient une expression commence
 * par un signe égal :
 *
 *     "value": "={{ $json.titre }}"      →  évalué
 *     "value": "{{ $json.titre }}"       →  la chaîne, telle quelle
 *
 * L'éditeur pose ce signe tout seul quand on bascule un champ en mode
 * « Expression ». Un workflow écrit à la main, généré, ou recopié depuis une
 * page web ne l'a pas — et chaque champ contient alors le texte du gabarit.
 * Aucune erreur, aucun avertissement : `{{ $json.nom }}` part dans le
 * courriel du candidat.
 *
 * UN CHEMIN ABSENT NE LÈVE PAS
 *
 *     $json.absent          →  undefined
 *     $json.absent.profond  →  undefined   (et non une TypeError)
 *
 * n8n avale l'erreur d'accès. Une faute de frappe dans un nom de champ donne
 * donc `undefined`, qui descend ensuite dans tout le reste du workflow.
 */

'use strict';

const { Expression } = require('n8n-workflow');

const PREFIXE = '=';

/** Est-ce que n8n considérera cette valeur comme une expression ? */
function estUneExpression(valeur) {
  return typeof valeur === 'string' && valeur.startsWith(PREFIXE);
}

/** Est-ce que la valeur RESSEMBLE à une expression sans en être une ? */
function gabaritSansSigneEgal(valeur) {
  // TODO : rendre vrai quand une valeur RESSEMBLE a une expression sans en etre une : elle contient {{ … }} mais ne commence pas par « = ». C'est le defaut le plus silencieux de n8n — le gabarit part tel quel dans le courriel du candidat, sans erreur et sans avertissement. Trois tests le verifient.
  return false;
}

/**
 * Évalue une valeur de paramètre comme n8n le ferait.
 *
 * `contexte` porte `$json`, `$now`, `$itemIndex`… — exactement ce que n8n
 * met à disposition d'une expression.
 */
function evaluer(flux, valeur, contexte = {}) {
  const moteur = new Expression(flux);
  return moteur.resolveSimpleParameterValue(valeur, { ...contexte });
}

/**
 * Toutes les valeurs de paramètre d'un workflow, à plat.
 *
 * Rend `{ noeud, chemin, valeur }` pour chaque feuille — c'est ce qu'il faut
 * pour vérifier un workflow entier, plutôt que le champ qu'on a sous les yeux.
 */
function parametres(donnees) {
  const trouves = [];
  const descendre = (noeud, objet, chemin) => {
    if (typeof objet === 'string' || typeof objet === 'number'
        || typeof objet === 'boolean' || objet === null) {
      trouves.push({ noeud: noeud.name, chemin, valeur: objet });
      return;
    }
    if (Array.isArray(objet)) {
      objet.forEach((v, i) => descendre(noeud, v, `${chemin}[${i}]`));
      return;
    }
    if (objet && typeof objet === 'object') {
      for (const [cle, v] of Object.entries(objet)) {
        descendre(noeud, v, chemin ? `${chemin}.${cle}` : cle);
      }
    }
  };
  for (const noeud of donnees.nodes) descendre(noeud, noeud.parameters, '');
  return trouves;
}

/** Les références `$('Nom du nœud')` présentes dans une expression. */
const REFERENCE = /\$\(\s*['"]([^'"]+)['"]\s*\)/g;

function noeudsReferences(valeur) {
  if (typeof valeur !== 'string') return [];
  return [...valeur.matchAll(REFERENCE)].map((m) => m[1]);
}

/** Les champs `$json.xxx` lus par une expression. */
const CHAMP = /\$json\.([A-Za-z_$][\w$]*)/g;

function champsLus(valeur) {
  if (typeof valeur !== 'string') return [];
  return [...valeur.matchAll(CHAMP)].map((m) => m[1]);
}

module.exports = {
  PREFIXE, estUneExpression, gabaritSansSigneEgal, evaluer, parametres,
  noeudsReferences, champsLus,
};
