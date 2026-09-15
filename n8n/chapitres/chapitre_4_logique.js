/**
 * Chapitre 4 — Logique avancée et gestion d'erreurs.
 *
 *     node chapitres/chapitre_4_logique.js
 *
 * Les deux workflows de `flux/` ont le même dessin. L'un envoie le refus aux
 * candidats refusés ; l'autre l'envoie aux candidats retenus. La différence
 * tient à l'index d'une connexion, et rien dans l'éditeur ne la signale.
 */

'use strict';

const { titre, ligne, plier, tableau } = require('../jobportal/commun');
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
const { verifier } = require('../outils/verifier-flux');

function branchesDuIf(donnees, nomDuIf) {
  const sorties = (donnees.connections[nomDuIf] || {}).main || [];
  return sorties.map((b) => b.map((l) => l.node).join(', ') || '(rien)');
}

function principal() {
  const propre = flux.charger('candidature');
  const fautif = flux.charger('a-corriger');

  titre(1, 'DEUX SORTIES, ET AUCUNE ETIQUETTE DANS LE JSON');
  for (const [etiquette, paquet, nomDuIf] of [
    ['candidature.json', propre, "Assez d'experience ?"],
    ['a-corriger.json', fautif, 'Decision'],
  ]) {
    const [vrai, faux] = branchesDuIf(paquet.donnees, nomDuIf);
    console.log(`   ${etiquette}`);
    ligne('  sortie 0 (vrai)', vrai, 22);
    ligne('  sortie 1 (faux)', faux, 22);
  }
  console.log();
  console.log('   Le JSON ne dit pas « vrai » et « faux » : il dit 0 et 1.');
  console.log('   L\'ordre du tableau EST la semantique. Inverser deux lignes');
  console.log('   inverse la logique, et le JSON reste parfaitement valide.');

  titre(2, 'CE QUE CELA DONNE SUR CINQUANTE CANDIDATURES');
  for (const [etiquette, paquet] of [
    ['candidature.json', propre], ['a-corriger.json', fautif],
  ]) {
    const passages = faireCirculer(paquet.donnees, paquet.flux,
      candidatures(50));
    const enregistres = passages.get('Enregistrer');
    const refuses = passages.get('Refus poli');
    console.log(`   ${etiquette}`);
    ligne('  enregistres en base', String(enregistres ? enregistres.itemsEntres : 0), 24);
    ligne('  courriels de refus', String(refuses ? refuses.itemsEntres : 0), 24);
  }
  console.log();
  console.log('   Les nombres sont echanges. Dans le second workflow, les 20');
  console.log('   candidats qui ont TROIS ANS D\'EXPERIENCE OU PLUS recoivent');
  console.log('   le courriel de refus, et les 30 autres sont enregistres en');
  console.log('   base comme retenus.');
  console.log();
  console.log('   Aucune erreur, aucune alerte, un historique entierement');
  console.log('   vert. Le defaut se decouvre par un candidat qui telephone.');

  titre(3, 'CE QU\'UN NŒUD SANS GESTION D\'ERREUR COUTE');
  for (const [etiquette, paquet] of [
    ['candidature.json', propre], ['a-corriger.json', fautif],
  ]) {
    const risques = flux.sansGestionDErreur(paquet.donnees);
    ligne(etiquette, risques.length
      ? `${risques.length} noeud(s) sans garde : ${risques.join(', ')}`
      : 'tous les noeuds risques ont une sortie d\'erreur', 22);
  }
  console.log();
  console.log('   Par defaut, un noeud qui echoue ARRETE l\'execution. Sur un');
  console.log('   lot de 50 candidatures, la 3e qui echoue empeche les 47');
  console.log('   suivantes — et ces 47 ne sont pas « en attente », elles');
  console.log('   n\'ont jamais existe.');
  console.log();
  console.log('   `onError: continueErrorOutput` change cela : l\'item fautif');
  console.log('   part sur la sortie d\'erreur, les autres continuent. C\'est');
  console.log('   ce que fait `candidature.json`, et c\'est pourquoi son nœud');
  console.log('   « Journaliser l\'echec » existe.');

  titre(4, 'LE NŒUD QUI NE S\'EXECUTE JAMAIS');
  for (const [etiquette, paquet] of [
    ['candidature.json', propre], ['a-corriger.json', fautif],
  ]) {
    const seuls = flux.orphelins(paquet.flux);
    ligne(etiquette, seuls.length ? seuls.join(', ') : 'aucun orphelin', 22);
  }
  console.log();
  console.log('   « Notes internes » est dans le fichier, s\'affiche dans');
  console.log('   l\'editeur, et n\'est relie a rien. n8n ne le signale pas :');
  console.log('   un noeud detache est une situation NORMALE pendant qu\'on');
  console.log('   construit. Elle cesse de l\'etre a la mise en production, et');
  console.log('   plus rien ne fait la difference.');

  titre(5, 'LE VERIFICATEUR, SUR LES DEUX');
  for (const [etiquette, paquet] of [
    ['candidature.json', propre], ['a-corriger.json', fautif],
  ]) {
    const soucis = verifier(paquet.donnees, paquet.flux);
    const erreurs = soucis.filter((s) => s.gravite === 'erreur').length;
    ligne(etiquette,
      `${erreurs} erreur(s), ${soucis.length - erreurs} avertissement(s)`, 22);
  }
  console.log();
  for (const s of verifier(fautif.donnees, fautif.flux)) {
    console.log(`      ${s.gravite === 'erreur' ? 'ERREUR   ' : 'attention'} ${s.ou}`);
  }
  console.log();
  console.log('   ⚠️ Le vérificateur n\'attrape PAS la branche inversee de la');
  console.log('   section 2. Il ne peut pas : les deux branchements sont');
  console.log('   syntaxiquement identiques, et seule l\'intention du');
  console.log('   concepteur les separe.');
  console.log();
  console.log('   C\'est la limite de toute verification statique sur un');
  console.log('   workflow : elle voit ce qui est mal FORME, pas ce qui est');
  console.log('   mal PENSE. Pour la seconde, il faut faire circuler des');
  console.log('   items — ce que fait la section 2, et ce qu\'un test peut');
  console.log('   faire a chaque modification.');

  console.log('\n   Au chapitre suivant : ce qu\'un agent IA ajoute.\n');
}

if (require.main === module) principal();
module.exports = { principal };
