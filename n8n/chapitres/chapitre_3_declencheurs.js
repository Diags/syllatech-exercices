/**
 * Chapitre 3 — Déclencheurs et intégrations.
 *
 *     node chapitres/chapitre_3_declencheurs.js
 *
 * Un déclencheur démarre une exécution, et c'est tout ce qu'il fait. Ce qui
 * compte ensuite est ce qu'il MET sur le tapis : un item, ou cinquante.
 * Ce chapitre le compte.
 */

'use strict';

const { titre, ligne, tableau } = require('../jobportal/commun');
const flux = require('../jobportal/flux');
const { candidatures, faireCirculer: circuler } = require('../jobportal/execution');

// Sur la branche « depart », il peut n'y avoir aucun point de depart : le
// tapis leve alors, et un chapitre qui plante n'enseigne rien. On rend une
// table vide et le chapitre le dit.
function faireCirculer(...arguments_) {
  try {
    return circuler(...arguments_);
  } catch (erreur) {
    console.log(`   (rien ne circule : ${erreur.message})`);
    return new Map();
  }
}
const { TYPES } = require('../jobportal/typesDeNoeuds');

function colonnes(passages) {
  return [...passages].map(([nom, p]) => [
    nom, String(p.itemsEntres), String(p.itemsSortis), String(p.executions),
    String(p.expressionsEvaluees), String(p.videsRendus),
  ]);
}

function principal() {
  const { donnees, flux: graphe } = flux.charger('candidature');

  titre(1, 'CE QUI FAIT D\'UN NŒUD UN DECLENCHEUR');
  console.log('   Ce n\'est pas son groupe : c\'est la presence d\'une methode');
  console.log('   `trigger` sur son type. Un noeud range dans « trigger » qui');
  console.log('   ne l\'a pas n\'en est pas un — et `getTriggerNodes()` ne le');
  console.log('   rendra pas.\n');
  tableau(['type', 'groupe', 'declencheur ?'],
    Object.entries(TYPES).slice(0, 6).map(([nom, t]) => [
      nom.replace('n8n-nodes-base.', ''),
      t.description.group.join(','),
      t.trigger ? 'oui' : 'non',
    ]), [22, 14, 14]);
  console.log();
  ligne('declencheurs de ce workflow',
    flux.declencheurs(graphe).join(', ') || '(aucun)', 30);

  titre(2, 'UN ITEM, OU CINQUANTE');
  console.log('   Le meme workflow, avec un item puis avec cinquante :\n');
  const mesures = {};
  for (const combien of [1, 50]) {
    const passages = faireCirculer(donnees, graphe, candidatures(combien));
    mesures[combien] = {
      executions: [...passages.values()].reduce((s, p) => s + p.executions, 0),
      expressions: [...passages.values()]
        .reduce((s, p) => s + p.expressionsEvaluees, 0),
    };
    ligne(`${combien} candidature(s)`,
      `${mesures[combien].executions} executions de noeud, `
      + `${mesures[combien].expressions} expressions evaluees`, 20);
  }
  console.log();
  const rapportExpr = mesures[50].expressions / mesures[1].expressions;
  const rapportExec = mesures[50].executions / mesures[1].executions;
  ligne('rapport sur les expressions', `×${rapportExpr}`, 30);
  ligne('rapport sur les executions', `×${rapportExec.toFixed(1)}`, 30);
  console.log();
  console.log('   Le premier rapport est EXACTEMENT 50 : chaque expression est');
  console.log('   reevaluee une fois par item, sans exception.');
  console.log();
  console.log('   Le second ne l\'est pas, et c\'est instructif : le IF repartit');
  console.log('   les 50 items entre deux branches qui n\'ont pas le meme');
  console.log('   nombre de noeuds. Le total depend donc des DONNEES, pas');
  console.log('   seulement de leur nombre — deux lots de 50 candidatures ne');
  console.log('   coutent pas la meme chose.');

  titre(3, 'LE DETAIL PAR NŒUD');
  const passages = faireCirculer(donnees, graphe, candidatures(50));
  tableau(['noeud', 'entres', 'sortis', 'exec.', 'expr.', 'vides'],
    colonnes(passages), [26, 9, 9, 8, 8, 8]);
  console.log();
  console.log('   La colonne « expr. » est celle qui surprend : `Normaliser`');
  console.log('   evalue 200 expressions pour 50 items, parce qu\'il a quatre');
  console.log('   champs. Un noeud « Set » a dix champs en evaluerait 500.');
  console.log();
  console.log('   C\'est sans importance a 50 items. A 50 000 — une');
  console.log('   synchronisation nocturne — cela devient la moitie du temps');
  console.log('   d\'execution, et cela ne se voit nulle part dans l\'editeur.');

  titre(4, 'OU LES ITEMS SE SEPARENT');
  const separation = [...passages].find(([nom]) => nom.includes('experience'));
  if (separation) {
    const [nom, p] = separation;
    ligne(`${nom} — entres`, String(p.itemsEntres), 30);
    for (const [cible, q] of passages) {
      if (['Enregistrer', 'Refus poli'].includes(cible)) {
        ligne(`  → ${cible}`, `${q.itemsEntres} items`, 30);
      }
    }
  }
  console.log();
  console.log('   Le IF ne filtre pas : il AIGUILLE. Les deux branches');
  console.log('   recoivent chacune leurs items, et la somme est conservee.');
  console.log('   Un IF dont la branche « faux » n\'est pas branchee perd donc');
  console.log('   silencieusement ses items — ils ne vont nulle part, et');
  console.log('   l\'execution est « verte ».');

  titre(5, 'LE DECLENCHEUR DECIDE DU VOLUME, PAS LE WORKFLOW');
  tableau(['declencheur', 'ce qu\'il met sur le tapis'], [
    ['Webhook', '1 item par appel HTTP'],
    ['Schedule Trigger', '1 item par tic — le reste vient des noeuds'],
    ['Postgres (select)', 'autant d\'items que de lignes'],
    ['Gmail / IMAP', '1 item par message non lu'],
  ], [24, 46]);
  console.log();
  console.log('   La troisieme ligne est celle qui casse les workflows du');
  console.log('   dimanche : un « SELECT * » sur une table qui a grossi met');
  console.log('   80 000 items sur le tapis, et chaque noeud suivant tourne');
  console.log('   80 000 fois. Le workflow n\'a pas change ; la table, si.');

  console.log('\n   Au chapitre suivant : les branches, et ce qui se perd.\n');
}

if (require.main === module) principal();
module.exports = { principal };
