/**
 * Charger un workflow n8n, et l'analyser avec le VRAI `Workflow`.
 *
 * `n8n-workflow` est la bibliothèque que n8n utilise lui-même : le graphe,
 * l'ordre d'exécution et les expressions viennent d'elle. Les fichiers de
 * `flux/` sont au format d'export de l'éditeur — on peut les y importer tels
 * quels.
 *
 * ⚠️ L'ENTRÉE ESM DE LA BIBLIOTHÈQUE EST CASSÉE
 *
 * `import 'n8n-workflow'` échoue sur la version 2.16.0 :
 *
 *     ERR_MODULE_NOT_FOUND … dist/esm/logger-proxy
 *
 * Le build ESM publié contient un import sans extension, ce que Node refuse.
 * C'est pourquoi ce projet est en CommonJS — `require` fonctionne, lui. Ce
 * n'est pas un choix de style : c'est la seule entrée qui marche.
 */

'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { Workflow } = require('n8n-workflow');

const { EXIGENT_DES_IDENTIFIANTS, registre } = require('./typesDeNoeuds');

const RACINE = path.join(__dirname, '..');

/** Les deux types de lien qu'un workflow du job portal utilise. */
const TYPES_DE_LIEN = ['main', 'error'];

/** Lit un JSON d'export n8n. */
function lireJson(nom) {
  const chemin = nom.endsWith('.json') ? nom : path.join(RACINE, 'flux', `${nom}.json`);
  return JSON.parse(fs.readFileSync(chemin, 'utf8'));
}

/**
 * Construit le vrai `Workflow` de n8n à partir d'un export.
 *
 * ⚠️ LE CONSTRUCTEUR MUTE LES NŒUDS QU'ON LUI PASSE. n8n normalise chaque
 * `parameters` contre les `properties` DÉCLARÉES par le type de nœud, et
 * jette tout ce qui n'y figure pas. Avec le registre minimal de ce projet —
 * `properties: []` — il ne reste donc rien.
 *
 * Ce n'est pas un défaut du registre : c'est le comportement de n8n, et il
 * explique un vrai incident. Un workflow exporté depuis une version où un
 * champ existait, réimporté dans une version où il a été renommé, perd ce
 * champ SANS erreur — l'éditeur affiche un nœud aux paramètres vides.
 *
 * On travaille donc toujours sur une COPIE : le JSON d'origine reste
 * intact pour l'analyse des expressions, et le `Workflow` sert au graphe.
 */
function construire(donnees) {
  return new Workflow({
    id: donnees.id || donnees.name || 'sans-id',
    name: donnees.name,
    nodes: structuredClone(donnees.nodes),
    connections: structuredClone(donnees.connections),
    active: Boolean(donnees.active),
    settings: donnees.settings,
    nodeTypes: registre,
  });
}

function charger(nom) {
  const donnees = lireJson(nom);
  return { donnees, flux: construire(donnees) };
}

// ----------------------------------------------------- lire le graphe

function noms(flux) {
  return Object.keys(flux.nodes);
}

function declencheurs(flux) {
  return flux.getTriggerNodes().map((n) => n.name);
}

/**
 * Les nœuds qu'aucun chemin ne relie à un déclencheur.
 *
 * ⚠️ n8n les affiche dans l'éditeur, sans un mot. Ils ne s'exécutent jamais —
 * et l'on cherche pourquoi « le nœud ne fait rien » alors qu'il n'est
 * simplement pas branché.
 */
function orphelins(flux) {
  // >>> depart: rendre les noeuds qu'aucun chemin ne relie a un declencheur. ⚠️ `getChildNodes` ne suit que les connexions « main » par defaut : un noeud branche uniquement sur une sortie d'ERREUR passerait pour orphelin, et l'on retirerait le seul noeud qui journalise les echecs. Parcourir TYPES_DE_LIEN, et refermer la transitivite. Deux tests le verifient.
  //     return [];
  // ⚠️ `getChildNodes` ne suit que les connexions « main » par défaut. Un
  // nœud branché uniquement sur une sortie d'ERREUR passerait pour orphelin
  // — et l'on retirerait le seul nœud qui journalise les échecs. On parcourt
  // donc les deux types.
  const departs = declencheurs(flux);
  const atteints = new Set(departs);
  for (const depart of departs) {
    for (const type of TYPES_DE_LIEN) {
      for (const enfant of flux.getChildNodes(depart, type)) atteints.add(enfant);
    }
  }
  // Un nœud d'erreur peut être l'enfant d'un nœud lui-même atteint : on
  // referme la transitivité jusqu'au point fixe.
  let change = true;
  while (change) {
    change = false;
    for (const nom of [...atteints]) {
      for (const type of TYPES_DE_LIEN) {
        for (const enfant of flux.getChildNodes(nom, type)) {
          if (!atteints.has(enfant)) { atteints.add(enfant); change = true; }
        }
      }
    }
  }
  return noms(flux).filter((n) => !atteints.has(n));
  // <<<
}

/** Les nœuds qui exigent des identifiants et n'en déclarent aucun. */
function sansIdentifiants(donnees) {
  return donnees.nodes
    .filter((n) => EXIGENT_DES_IDENTIFIANTS.has(n.type))
    .filter((n) => !n.credentials || Object.keys(n.credentials).length === 0)
    .map((n) => n.name);
}

/**
 * Les nœuds sans gestion d'erreur déclarée.
 *
 * Par défaut, un nœud qui échoue ARRÊTE l'exécution. Sur un workflow qui
 * traite 50 candidatures, la 3ᵉ qui échoue empêche les 47 suivantes — et le
 * chapitre 4 le mesure.
 */
function sansGestionDErreur(donnees) {
  // >>> depart: rendre les noeuds A RISQUE — ceux qui exigent des identifiants, plus httpRequest — qui ne declarent ni `onError` ni `continueOnFail`. Par defaut, un noeud qui echoue ARRETE l'execution : sur un lot de 50 candidatures, la 3e qui echoue empeche les 47 suivantes, et ces 47 n'ont jamais existe. Deux tests le verifient.
  //     return [];
  const risques = new Set([...EXIGENT_DES_IDENTIFIANTS,
    'n8n-nodes-base.httpRequest']);
  return donnees.nodes
    .filter((n) => risques.has(n.type))
    .filter((n) => !n.onError && n.continueOnFail !== true)
    .map((n) => n.name);
  // <<<
}

/**
 * Un ordre topologique depuis le déclencheur — celui de la LECTURE.
 *
 * ⚠️ Ce n'est PAS l'ordre d'exécution de n8n : `getChildNodes` rend les
 * descendants sans ordre garanti, et n8n applique en plus `executionOrder`
 * (« v1 » range les branches de haut en bas). Ce tri-ci sert à lire le
 * graphe, pas à prédire une exécution — et le dire évite d'enseigner une
 * garantie qui n'existe pas.
 */
function ordreDeLecture(flux, depart) {
  const vus = new Set();
  const sortie = [];
  const visiter = (nom) => {
    if (vus.has(nom)) return;
    vus.add(nom);
    sortie.push(nom);
    for (const type of TYPES_DE_LIEN) {
      for (const enfant of enfantsDirects(flux, nom, type)) visiter(enfant);
    }
  };
  visiter(depart);
  return sortie;
}

/** Les enfants IMMÉDIATS, dans l'ordre des sorties déclarées. */
function enfantsDirects(flux, nom, type = 'main') {
  const liens = (flux.connectionsBySourceNode || {})[nom] || {};
  return (liens[type] || []).flat().map((l) => l.node);
}

module.exports = {
  RACINE, charger, construire, lireJson, noms, declencheurs, orphelins,
  sansIdentifiants, sansGestionDErreur, ordreDeLecture, enfantsDirects,
  TYPES_DE_LIEN,
};
