/**
 * Le registre de types de nœuds — ce que `n8n-workflow` exige pour construire
 * un `Workflow`.
 *
 * n8n sépare deux choses que l'on confond au début :
 *
 *   · le WORKFLOW — la liste des nœuds, leurs paramètres, et les connexions.
 *     C'est ce qu'on exporte en JSON, et c'est ce que ce projet manipule ;
 *   · les TYPES de nœuds — ce que « n8n-nodes-base.set » sait faire. Ils
 *     vivent dans le paquet `n8n-nodes-base`, qui pèse des centaines de Mo
 *     et embarque des centaines d'intégrations.
 *
 * Ce module fournit un registre minimal des types que le job portal utilise :
 * assez pour que le vrai `Workflow` se construise, se parcoure et s'analyse.
 *
 * ⚠️ CE QUI EST SUBSTITUÉ : le COMPORTEMENT des nœuds. Un « Set » d'ici ne
 * transforme rien ; il déclare seulement ses entrées, ses sorties et son
 * groupe. Tout ce que les chapitres mesurent — le graphe, les expressions,
 * le flux d'items — n'en dépend pas.
 */

'use strict';

/** Les groupes décident du rôle : « trigger » démarre une exécution. */
function typeDeNoeud(nom, groupe, entrees, sorties, options = {}) {
  return {
    description: {
      name: nom.split('.').pop(),
      displayName: options.affichage || nom.split('.').pop(),
      group: [groupe],
      version: 1,
      defaults: { name: options.affichage || nom },
      inputs: entrees,
      outputs: sorties,
      properties: [],
      ...options.description,
    },
    // n8n reconnaît un déclencheur à la PRÉSENCE de cette méthode, pas au
    // groupe. Un nœud rangé dans « trigger » qui ne l'a pas n'en est pas un,
    // et `getTriggerNodes()` ne le rendra pas.
    //
    // Ce fichier n'a pas de zone à compléter : sans déclencheur, plus rien
    // ne circule, et les chapitres 3 à 5 n'auraient plus rien à montrer.
    ...(groupe === 'trigger' ? { trigger: async () => ({}) } : {}),
  };
}

const TYPES = {
  'n8n-nodes-base.webhook': typeDeNoeud('n8n-nodes-base.webhook', 'trigger',
    [], ['main'], { affichage: 'Webhook' }),
  'n8n-nodes-base.scheduleTrigger': typeDeNoeud(
    'n8n-nodes-base.scheduleTrigger', 'trigger', [], ['main'],
    { affichage: 'Schedule Trigger' }),
  'n8n-nodes-base.set': typeDeNoeud('n8n-nodes-base.set', 'transform',
    ['main'], ['main'], { affichage: 'Edit Fields' }),
  'n8n-nodes-base.code': typeDeNoeud('n8n-nodes-base.code', 'transform',
    ['main'], ['main'], { affichage: 'Code' }),
  // ⚠️ Le nœud IF a DEUX sorties : vrai (index 0) et faux (index 1). Une
  // connexion posée sur la mauvaise inverse toute la logique, et rien ne le
  // signale — le chapitre 4 le mesure.
  'n8n-nodes-base.if': typeDeNoeud('n8n-nodes-base.if', 'transform',
    ['main'], ['main', 'main'], { affichage: 'IF' }),
  'n8n-nodes-base.httpRequest': typeDeNoeud('n8n-nodes-base.httpRequest',
    'output', ['main'], ['main'], { affichage: 'HTTP Request' }),
  'n8n-nodes-base.emailSend': typeDeNoeud('n8n-nodes-base.emailSend',
    'output', ['main'], ['main'], { affichage: 'Send Email' }),
  'n8n-nodes-base.postgres': typeDeNoeud('n8n-nodes-base.postgres',
    'output', ['main'], ['main'], { affichage: 'Postgres' }),
  'n8n-nodes-base.noOp': typeDeNoeud('n8n-nodes-base.noOp', 'transform',
    ['main'], ['main'], { affichage: 'No Operation' }),
  '@n8n/n8n-nodes-langchain.agent': typeDeNoeud(
    '@n8n/n8n-nodes-langchain.agent', 'transform', ['main'], ['main'],
    { affichage: 'AI Agent' }),
};

/** Les nœuds qui demandent des identifiants pour fonctionner. */
const EXIGENT_DES_IDENTIFIANTS = new Set([
  'n8n-nodes-base.emailSend',
  'n8n-nodes-base.postgres',
  '@n8n/n8n-nodes-langchain.agent',
]);

/** L'objet que `new Workflow({ nodeTypes })` attend. */
const registre = {
  getByName: (nom) => TYPES[nom],
  getByNameAndVersion: (nom) => TYPES[nom],
  getKnownTypes: () => TYPES,
};

module.exports = { TYPES, EXIGENT_DES_IDENTIFIANTS, registre, typeDeNoeud };
