/**
 * Chapitre 5 — n8n + IA : les workflows intelligents.
 *
 *     node chapitres/chapitre_5_ia.js
 *
 * Un nœud « AI Agent » est un nœud comme les autres : il reçoit des items,
 * il en rend. Ce qui change est le PRIX — il est payant, lent, et il tourne
 * une fois par item comme tous les autres.
 *
 * ⚠️ Aucun modèle n'est appelé. Les coûts sont des ordres de grandeur
 * annoncés comme tels ; le chapitre les fait varier pour montrer où ils
 * basculent, pas pour établir une facture.
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

// Ordres de grandeur, pas des mesures : un appel de modele bon marche,
// quelques centaines de jetons d'entree et de sortie.
const PRIX_PAR_APPEL = 0.0008;     // dollars
const LATENCE_PAR_APPEL = 1.4;     // secondes

function avecAgent(donnees) {
  const copie = structuredClone(donnees);
  copie.name = 'Candidature avec tri IA';
  copie.nodes.push({
    id: 'ia1',
    name: 'Resumer le profil',
    type: '@n8n/n8n-nodes-langchain.agent',
    typeVersion: 1,
    position: [330, 300],
    parameters: {
      promptType: 'define',
      text: "={{ 'Resume en une phrase le profil : ' + $json.nom }}",
    },
    credentials: { openAiApi: { id: '9', name: 'Modele' } },
    onError: 'continueErrorOutput',
  });
  // On l'insère entre « Normaliser » et le IF.
  copie.connections.Normaliser = {
    main: [[{ node: 'Resumer le profil', type: 'main', index: 0 }]],
  };
  copie.connections['Resumer le profil'] = {
    main: [[{ node: "Assez d'experience ?", type: 'main', index: 0 }]],
    error: [[{ node: "Journaliser l'echec", type: 'main', index: 0 }]],
  };
  return copie;
}

function principal() {
  const base = flux.charger('candidature');

  titre(1, 'UN NŒUD IA EST UN NŒUD');
  const donnees = avecAgent(base.donnees);
  const graphe = flux.construire(donnees);
  ligne('noeuds avant', String(base.donnees.nodes.length), 22);
  ligne('noeuds apres', String(donnees.nodes.length), 22);
  ligne('place dans le flux',
    flux.enfantsDirects(graphe, 'Normaliser', 'main').join(', '), 22);
  console.log();
  console.log('   Il se branche comme les autres, recoit des items comme les');
  console.log('   autres, et rend des items comme les autres. La seule chose');
  console.log('   qui le distingue est ce qu\'il coute.');

  titre(2, 'LE PRIX DE « UNE FOIS PAR ITEM »');
  tableau(['candidatures', 'appels au modele', 'cout (~)', 'duree (~)'],
    [1, 50, 500, 5000].map((combien) => {
      const passages = faireCirculer(donnees, graphe, candidatures(combien));
      const agent = passages.get('Resumer le profil');
      const appels = agent ? agent.executions : 0;
      return [
        String(combien), String(appels),
        `${(appels * PRIX_PAR_APPEL).toFixed(2)} $`,
        `${(appels * LATENCE_PAR_APPEL / 60).toFixed(1)} min`,
      ];
    }), [16, 20, 14, 14]);
  console.log();
  console.log('   Les deux dernieres colonnes sont des ORDRES DE GRANDEUR,');
  console.log('   annonces comme tels : aucun modele n\'est appele ici. Ce qui');
  console.log('   est mesure, c\'est le NOMBRE D\'APPELS — et il vient du');
  console.log('   graphe, pas d\'une estimation.');
  console.log();
  console.log('   La derniere ligne est celle qui compte : un workflow qui');
  console.log('   marche tres bien sur un webhook devient deux heures');
  console.log('   d\'attente et quatre dollars quand on le branche sur une');
  console.log('   requete SQL nocturne. Le workflow n\'a pas change.');

  titre(3, 'METTRE L\'IA APRES LE FILTRE, PAS AVANT');
  const apres = structuredClone(donnees);
  apres.connections.Normaliser = {
    main: [[{ node: "Assez d'experience ?", type: 'main', index: 0 }]],
  };
  apres.connections["Assez d'experience ?"] = {
    main: [
      [{ node: 'Resumer le profil', type: 'main', index: 0 }],
      [{ node: 'Refus poli', type: 'main', index: 0 }],
    ],
  };
  apres.connections['Resumer le profil'] = {
    main: [[{ node: 'Enregistrer', type: 'main', index: 0 }]],
    error: [[{ node: "Journaliser l'echec", type: 'main', index: 0 }]],
  };
  const grapheApres = flux.construire(apres);

  for (const [etiquette, d, g] of [
    ['IA avant le filtre', donnees, graphe],
    ['IA apres le filtre', apres, grapheApres],
  ]) {
    const passages = faireCirculer(d, g, candidatures(50));
    const agent = passages.get('Resumer le profil');
    const appels = agent ? agent.executions : 0;
    ligne(etiquette, `${appels} appels — ${(appels * PRIX_PAR_APPEL).toFixed(3)} $`,
      24);
  }
  console.log();
  console.log('   Le meme travail, la meme qualite de tri, et 60 % d\'appels en');
  console.log('   moins : il suffit de ne resumer que les profils qu\'on garde.');
  console.log();
  console.log('   C\'est le seul reglage de cout qui ne demande ni modele moins');
  console.log('   cher, ni prompt plus court — seulement de deplacer un noeud');
  console.log('   de deux crans vers la droite.');

  titre(4, 'CE QU\'UN NŒUD IA AJOUTE COMME MODE DE PANNE');
  for (const [panne, consequence] of [
    ['le fournisseur repond 429', 'un item perdu, ou tout le lot arrete'],
    ['la reponse n\'est pas du JSON', 'le noeud suivant recoit du texte'],
    ['la reponse est plausible et fausse', 'rien ne se voit, jamais'],
    ['le prompt contient $json.nom', 'un candidat ecrit le prompt'],
  ]) console.log(`   ${panne.padEnd(38)}${consequence}`);
  console.log();
  console.log('   La derniere ligne est la plus importante, et c\'est celle');
  console.log('   qu\'on ne voit pas venir : `{{ $json.nom }}` dans un prompt,');
  console.log('   c\'est le contenu d\'un formulaire public qui arrive dans les');
  console.log('   instructions du modele. Le cours « Securiser les agents IA »');
  console.log('   traite exactement cela.');
  console.log();
  console.log('   Les trois premieres se traitent avec `onError` — que le');
  console.log('   noeud ajoute ici declare. La quatrieme ne se traite pas avec');
  console.log('   un reglage de n8n.');

  console.log('\n   Au chapitre suivant : l\'auto-hebergement.\n');
}

if (require.main === module) principal();
module.exports = { principal };
