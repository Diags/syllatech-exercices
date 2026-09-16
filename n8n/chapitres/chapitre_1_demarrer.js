/**
 * Chapitre 1 — Démarrer avec n8n.
 *
 *     node chapitres/chapitre_1_demarrer.js
 *
 * n8n lui-même est une application Node qu'on lance par Docker. Ce projet ne
 * la lance pas : il utilise `n8n-workflow`, **la bibliothèque que n8n utilise
 * pour lui-même** — le graphe, l'ordre, les expressions viennent d'elle.
 *
 * Ce qu'on peut donc vérifier ici : tout ce qui concerne le WORKFLOW. Ce
 * qu'on ne peut pas : ce que font les nœuds, qui vit dans `n8n-nodes-base`.
 */

'use strict';

const { titre, ligne, tableau } = require('../jobportal/commun');
const flux = require('../jobportal/flux');
const { TYPES } = require('../jobportal/typesDeNoeuds');

function principal() {
  titre(1, 'CE QUI EST INSTALLE, ET CE QUI NE L\'EST PAS');
  const version = require('n8n-workflow/package.json').version;
  ligne('n8n-workflow', version, 26);
  ligne('exports de la bibliotheque',
    String(Object.keys(require('n8n-workflow')).length), 26);
  ligne('n8n (l\'application)', 'absent — c\'est une image Docker', 26);
  ligne('n8n-nodes-base', 'absent — des centaines de Mo', 26);
  console.log();
  console.log('   La bibliotheque suffit pour tout ce que ce cours enseigne du');
  console.log('   WORKFLOW : le graphe, l\'ordre, les expressions. Elle ne');
  console.log('   contient pas le COMPORTEMENT des noeuds — un « Postgres »');
  console.log('   n\'ecrit rien ici.');

  titre(2, 'L\'ENTREE ESM DE LA BIBLIOTHEQUE EST CASSEE');
  console.log('   `import \'n8n-workflow\'` echoue sur la 2.16.0 :\n');
  console.log('      ERR_MODULE_NOT_FOUND … dist/esm/logger-proxy\n');
  console.log('   Le build ESM publie contient un import sans extension, ce');
  console.log('   que Node refuse. C\'est pourquoi ce projet est en CommonJS :');
  console.log('   `require` fonctionne. Ce n\'est pas un choix de style, c\'est');
  console.log('   la seule entree qui marche.');

  titre(3, 'UN WORKFLOW N8N, C\'EST DU JSON');
  const { donnees, flux: graphe } = flux.charger('candidature');
  ligne('nom', donnees.name, 20);
  ligne('noeuds', String(donnees.nodes.length), 20);
  ligne('connexions', String(Object.keys(donnees.connections).length), 20);
  ligne('executionOrder', donnees.settings.executionOrder, 20);
  console.log();
  console.log('   `flux/candidature.json` est un export de l\'editeur n8n. On');
  console.log('   peut l\'y importer tel quel — et c\'est la meme chose que ce');
  console.log('   projet analyse.');

  titre(4, 'LE TAPIS ROULANT, LU DANS LE GRAPHE');
  const depart = flux.declencheurs(graphe)[0];
  ligne('declencheur', depart || '(aucun — a completer)', 20);
  console.log();
  for (const nom of depart ? flux.ordreDeLecture(graphe, depart) : []) {
    const enfants = flux.enfantsDirects(graphe, nom, 'main');
    const erreurs = flux.enfantsDirects(graphe, nom, 'error');
    console.log(`      ${nom.padEnd(24)} → ${enfants.join(', ') || '(fin)'}`
      + (erreurs.length ? `   [erreur → ${erreurs.join(', ')}]` : ''));
  }
  console.log();
  console.log('   ⚠️ Cet ordre est celui de la LECTURE, pas de l\'execution.');
  console.log('   n8n applique en plus « executionOrder: v1 », qui range les');
  console.log('   branches de haut en bas selon leur position a l\'ecran. Un');
  console.log('   noeud deplace de 40 pixels peut donc changer l\'ordre.');

  titre(5, 'CE QU\'UN TYPE DE NŒUD DECLARE');
  tableau(['type', 'groupe', 'entrees', 'sorties'],
    Object.entries(TYPES).slice(0, 7).map(([nom, t]) => [
      nom.replace('n8n-nodes-base.', ''),
      t.description.group.join(','),
      String(t.description.inputs.length),
      String(t.description.outputs.length),
    ]), [22, 12, 10, 10]);
  console.log();
  console.log('   La ligne « if » a DEUX sorties : vrai (index 0) et faux');
  console.log('   (index 1). Une connexion posee sur la mauvaise inverse toute');
  console.log('   la logique — et rien ne le signale. Le chapitre 4 le mesure');
  console.log('   sur le workflow a corriger, ou les candidats QUALIFIES');
  console.log('   recoivent le courriel de refus.');

  titre(6, 'CE QUE LE PROJET VA MESURER');
  for (const [quoi, ou] of [
    ['le signe « = » qui fait une expression', 'chapitre 2'],
    ['un champ absent qui rend undefined sans lever', 'chapitre 2'],
    ['50 items → 50 executions, comptees', 'chapitre 3'],
    ['une branche IF inversee', 'chapitre 4'],
    ['un noeud orphelin, visible et inerte', 'chapitre 4'],
    ['ce qu\'un agent IA ajoute, et ce qu\'il coute', 'chapitre 5'],
    ['ce qui manque pour auto-heberger', 'chapitre 6'],
  ]) console.log(`   ${quoi.padEnd(48)}${ou}`);

  console.log('\n   Au chapitre suivant : les items et les expressions.\n');
}

if (require.main === module) principal();
module.exports = { principal };
