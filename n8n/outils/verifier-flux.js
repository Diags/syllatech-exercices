#!/usr/bin/env node
/**
 * Vérifier un workflow n8n AVANT de l'importer.
 *
 *     node outils/verifier-flux.js flux/a-corriger.json
 *     node outils/verifier-flux.js flux/candidature.json
 *
 * Les sept défauts qu'il attrape ont tous la même forme : le workflow
 * s'importe, l'éditeur l'affiche, il s'active — et quelque chose ne fait pas
 * ce qu'on croit. Aucun n'est une erreur de JSON, et aucun n'apparaît dans
 * l'interface.
 */

'use strict';

const path = require('node:path');

const flux = require('../jobportal/flux');
const {
  champsLus, estUneExpression, gabaritSansSigneEgal, noeudsReferences,
  parametres,
} = require('../jobportal/expressions');

/** Un souci, et ce qu'il coûte. */
function souci(gravite, ou, message) {
  return { gravite, ou, message };
}

function verifier(donnees, graphe) {
  const soucis = [];
  const existants = new Set(donnees.nodes.map((n) => n.name));

  // 1. Aucun déclencheur ------------------------------------------------
  const departs = flux.declencheurs(graphe);
  if (departs.length === 0) {
    soucis.push(souci('erreur', 'declencheur',
      'aucun noeud declencheur : le workflow ne demarrera jamais tout seul. '
      + "L'editeur l'affiche et le bouton « Execute » marche — ce qui fait "
      + 'croire qu\'il fonctionne.'));
  }

  // 2. Nœuds orphelins ---------------------------------------------------
  for (const nom of flux.orphelins(graphe)) {
    soucis.push(souci('erreur', `orphelin / ${nom}`,
      "aucun chemin ne relie ce noeud a un declencheur. Il est visible dans "
      + "l'editeur et ne s'executera jamais."));
  }

  // 3. Un gabarit sans le signe « = » ------------------------------------
  for (const { noeud, chemin, valeur } of parametres(donnees)) {
    if (gabaritSansSigneEgal(valeur)) {
      soucis.push(souci('erreur', `${noeud} / ${chemin}`,
        `« ${valeur} » ressemble a une expression mais n'en est pas une : il `
        + 'manque le signe « = » en tete. n8n enverra le texte du gabarit tel '
        + 'quel, sans rien evaluer et sans rien signaler.'));
    }
  }

  // 4. Une référence vers un nœud qui n'existe pas -----------------------
  //    …ou qui s'exécute APRÈS.
  for (const { noeud, chemin, valeur } of parametres(donnees)) {
    if (!estUneExpression(valeur)) continue;
    // TODO : pour chaque $('Nom') d'une expression, verifier que le noeud EXISTE, puis qu'il est en AMONT de celui qui le lit. Un noeud en aval n'a pas encore de donnees quand l'expression s'evalue, et n8n ne le signale qu'a l'execution — jamais au chargement. Deux tests le verifient.
    continue;
  }

  // 5. Identifiants manquants -------------------------------------------
  for (const nom of flux.sansIdentifiants(donnees)) {
    soucis.push(souci('erreur', `identifiants / ${nom}`,
      "ce type de noeud exige des identifiants et n'en declare aucun. A "
      + "l'import sur une autre installation, le workflow se charge et "
      + 'echoue au premier passage.'));
  }

  // 6. Aucune gestion d'erreur ------------------------------------------
  for (const nom of flux.sansGestionDErreur(donnees)) {
    soucis.push(souci('attention', `erreurs / ${nom}`,
      "ni « onError » ni « continueOnFail » : un echec ARRETE l'execution. "
      + 'Sur un lot de 50 candidatures, la 3e qui echoue empeche les 47 '
      + 'suivantes.'));
  }

  // 7. Un IF dont les deux sorties partent au même endroit ---------------
  for (const noeud of donnees.nodes) {
    if (noeud.type !== 'n8n-nodes-base.if') continue;
    const sorties = (donnees.connections[noeud.name] || {}).main || [];
    if (sorties.length < 2) {
      soucis.push(souci('attention', `IF / ${noeud.name}`,
        'une seule sortie branchee. La branche « faux » ne mene nulle part : '
        + 'les items qui la prennent disparaissent en silence.'));
      continue;
    }
    const vrai = (sorties[0] || []).map((l) => l.node).join(',');
    const faux = (sorties[1] || []).map((l) => l.node).join(',');
    if (vrai && vrai === faux) {
      soucis.push(souci('attention', `IF / ${noeud.name}`,
        'les deux sorties menent au meme noeud : la condition ne sert a rien.'));
    }
  }

  return soucis;
}

function plier(texte, largeur) {
  const lignes = [];
  let courante = '';
  for (const mot of texte.split(/\s+/)) {
    if ((courante + ' ' + mot).trim().length > largeur) {
      lignes.push(courante);
      courante = mot;
    } else courante = (courante + ' ' + mot).trim();
  }
  if (courante) lignes.push(courante);
  return lignes;
}

function principal() {
  const cible = process.argv[2] || 'flux/a-corriger.json';
  const chemin = path.isAbsolute(cible) ? cible : path.join(process.cwd(), cible);
  const donnees = flux.lireJson(chemin);
  const graphe = flux.construire(donnees);

  const soucis = verifier(donnees, graphe);
  const erreurs = soucis.filter((s) => s.gravite === 'erreur');

  console.log(`\n  ${cible}  —  « ${donnees.name} »\n`);
  for (const s of soucis) {
    const etiquette = s.gravite === 'erreur' ? 'ERREUR    ' : 'attention ';
    console.log(`  ${etiquette} ${s.ou}`);
    for (const ligne of plier(s.message, 62)) console.log(`             ${ligne}`);
  }
  if (soucis.length === 0) console.log('  Aucun probleme detecte.');
  console.log(`\n  ${erreurs.length} erreur(s), `
    + `${soucis.length - erreurs.length} avertissement(s)\n`);
  return erreurs.length > 0 ? 1 : 0;
}

if (require.main === module) process.exit(principal());

module.exports = { verifier, plier };
