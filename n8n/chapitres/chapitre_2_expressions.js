/**
 * Chapitre 2 — Nœuds, données et expressions.
 *
 *     node chapitres/chapitre_2_expressions.js
 *
 * Toutes les évaluations de ce chapitre passent par le VRAI moteur de n8n :
 *
 *     new Expression(workflow).resolveSimpleParameterValue(valeur, contexte)
 *
 * C'est la méthode que n8n appelle pour chaque champ de chaque nœud.
 */

'use strict';

const { DateTime } = require('luxon');

const { titre, ligne, tableau } = require('../jobportal/commun');
const flux = require('../jobportal/flux');
const {
  champsLus, estUneExpression, evaluer, gabaritSansSigneEgal, parametres,
} = require('../jobportal/expressions');

const ITEM = {
  nom: '  Diaguily SYLLA  ',
  poste: 'devops',
  salaire: 62,
  entreprise: { nom: 'CloudCorp', ville: 'Lyon' },
};

function principal() {
  const { flux: graphe } = flux.charger('candidature');
  const contexte = { $json: ITEM, $now: DateTime.now(), $itemIndex: 0 };

  titre(1, 'CE QUE LE VRAI MOTEUR EVALUE');
  const essais = [
    '={{ $json.poste }}',
    '={{ $json.nom.trim() }}',
    '={{ $json.entreprise.ville }}',
    '={{ $json.salaire > 60 ? "senior" : "junior" }}',
    '={{ $now.toISO() }}',
    '={{ $itemIndex }}',
    '={{ 1 + 1 }}',
  ];
  for (const essai of essais) {
    let resultat;
    try {
      resultat = JSON.stringify(evaluer(graphe, essai, contexte));
    } catch (erreur) {
      resultat = `ERREUR ${erreur.constructor.name}`;
    }
    console.log(`   ${essai.padEnd(48)} → ${String(resultat).slice(0, 34)}`);
  }
  console.log();
  console.log('   Rien n\'est simule : c\'est la classe `Expression` de n8n.');

  titre(2, 'LE SIGNE « = » EST LA MOITIE DE L\'HISTOIRE');
  for (const essai of ['={{ $json.poste }}', '{{ $json.poste }}']) {
    ligne(JSON.stringify(essai),
      `→ ${JSON.stringify(evaluer(graphe, essai, contexte))}`, 26);
  }
  console.log();
  console.log('   Sans le « = » en tete, n8n rend la CHAINE, telle quelle.');
  console.log('   L\'editeur pose ce signe tout seul quand on bascule un champ');
  console.log('   en mode « Expression » — un workflow ecrit a la main, genere,');
  console.log('   ou recopie d\'une page web ne l\'a pas.');
  console.log();
  console.log('   Le candidat recoit alors un courriel qui commence par');
  console.log('   « Bonjour {{ $json.nom }} ». Aucune erreur, aucun');
  console.log('   avertissement, et le workflow est « vert » dans l\'historique.');

  titre(3, 'UN CHEMIN ABSENT NE LEVE PAS');
  for (const essai of [
    '={{ $json.poste }}',
    '={{ $json.post }}',
    '={{ $json.entreprise.pays }}',
    '={{ $json.absent.profond.encore }}',
  ]) {
    const resultat = evaluer(graphe, essai, contexte);
    ligne(essai, `→ ${JSON.stringify(resultat)}`, 40);
  }
  console.log();
  console.log('   La deuxieme ligne est une faute de frappe — « post » au lieu');
  console.log('   de « poste ». Elle rend `undefined`, pas une erreur. Et la');
  console.log('   quatrieme, qui deréférencerait `undefined` en JavaScript');
  console.log('   ordinaire, rend `undefined` elle aussi : n8n avale la');
  console.log('   TypeError.');
  console.log();
  console.log('   C\'est confortable pour ecrire, et c\'est ce qui fait qu\'un');
  console.log('   champ vide descend dans tout le reste du workflow sans que');
  console.log('   personne ne s\'en apercoive.');

  titre(4, 'CE QUE CHAQUE NŒUD LIT VRAIMENT');
  const { donnees } = flux.charger('candidature');
  const lignes = [];
  for (const { noeud, chemin, valeur } of parametres(donnees)) {
    if (!estUneExpression(valeur)) continue;
    const champs = champsLus(valeur);
    if (champs.length) lignes.push([noeud, chemin.slice(0, 30), champs.join(', ')]);
  }
  tableau(['noeud', 'champ du parametre', 'lit $json.'], lignes, [24, 34, 20]);
  console.log();
  console.log('   Cette liste est ce qu\'il faut avoir sous les yeux quand le');
  console.log('   format du webhook change. n8n ne la donne pas : il faudrait');
  console.log('   ouvrir chaque noeud, un par un.');

  titre(5, 'LE MEME REGARD SUR LE WORKFLOW A CORRIGER');
  const { donnees: fautif } = flux.charger('a-corriger');
  let gabarits = 0;
  let total = 0;
  for (const { noeud, chemin, valeur } of parametres(fautif)) {
    if (typeof valeur !== 'string' || !valeur.includes('{{')) continue;
    total += 1;
    const litteral = gabaritSansSigneEgal(valeur);
    gabarits += litteral ? 1 : 0;
    const etat = litteral ? 'LITTERAL (pas de « = »)' : 'expression';
    console.log(`   ${noeud.padEnd(14)}${chemin.slice(0, 30).padEnd(32)}${etat}`);
  }
  console.log();
  console.log(`   ${gabarits} champ sur ${total} n'est pas une expression, et`);
  console.log('   dans l\'editeur les deux se ressemblent — le mode');
  console.log('   « Expression » se voit a une petite bascule, pas au contenu');
  console.log('   du champ.');

  console.log('\n   Au chapitre suivant : ce qui circule, et combien de fois.\n');
}

if (require.main === module) principal();
module.exports = { principal };
