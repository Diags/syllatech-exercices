/**
 * Chapitre 6 — Production : self-hosting et bonnes pratiques.
 *
 *     node chapitres/chapitre_6_production.js
 *
 * n8n s'auto-héberge, et c'est son argument principal. Ce chapitre regarde
 * ce que cela engage : ce qui est dans le JSON, ce qui n'y est PAS, et ce
 * qu'un workflow versionné promet à celui qui l'importe.
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
const { verifier } = require('../outils/verifier-flux');

function principal() {
  const propre = flux.charger('candidature');
  const fautif = flux.charger('a-corriger');

  titre(1, 'CE QU\'UN EXPORT CONTIENT, ET CE QU\'IL NE CONTIENT PAS');
  const noeudAvecIdentifiants = propre.donnees.nodes
    .find((n) => n.credentials);
  console.log('   Un noeud avec identifiants, tel qu\'il est exporte :\n');
  console.log(`      "credentials": ${JSON.stringify(noeudAvecIdentifiants.credentials)}`);
  console.log();
  console.log('   Un identifiant, une etiquette — et AUCUN secret. Le mot de');
  console.log('   passe SMTP reste dans la base de n8n, chiffre par la cle');
  console.log('   N8N_ENCRYPTION_KEY.');
  console.log();
  console.log('   C\'est une bonne nouvelle pour git, et un piege a l\'import :');
  console.log('   sur une autre installation, l\'identifiant « 2 » ne designe');
  console.log('   rien. Le workflow se charge, s\'affiche, et echoue au premier');
  console.log('   passage.');

  titre(2, 'LA CLE DE CHIFFREMENT EST LE SEUL VRAI SECRET');
  for (const [quoi, ou, consequence] of [
    ['les workflows', 'la base', 'se reimportent'],
    ['les identifiants', 'la base, chiffres', 'illisibles sans la cle'],
    ['N8N_ENCRYPTION_KEY', "l'environnement", 'perdue = tout a ressaisir'],
    ['les executions', 'la base', 'grossissent sans fin par defaut'],
  ]) console.log(`   ${quoi.padEnd(22)}${ou.padEnd(22)}${consequence}`);
  console.log();
  console.log('   La troisieme ligne est celle qui coute une soiree : une');
  console.log('   sauvegarde de la base sans la cle ne restaure aucun');
  console.log('   identifiant. Et n8n en genere une au premier demarrage si');
  console.log('   elle n\'est pas fournie — on ne sait donc pas toujours qu\'on');
  console.log('   en a une a sauvegarder.');

  titre(3, 'CE QUE LE VOLUME DOCKER PORTE');
  tableau(['chemin', 'contenu', 'si on l\'oublie'], [
    ['/home/node/.n8n', 'base SQLite, cle, config', 'tout disparait au restart'],
    ['(variable)', 'N8N_ENCRYPTION_KEY', 'identifiants irrecuperables'],
  ], [22, 28, 30]);
  console.log();
  console.log('   La commande du chapitre 1 monte bien `n8n_data`. C\'est la');
  console.log('   ligne la plus importante de tout le cours, et c\'est celle');
  console.log('   qu\'on retire en copiant une commande depuis un forum.');

  titre(4, 'CE QU\'UNE VERIFICATION AVANT IMPORT ATTRAPE');
  for (const [etiquette, paquet] of [
    ['candidature.json', propre], ['a-corriger.json', fautif],
  ]) {
    const soucis = verifier(paquet.donnees, paquet.flux);
    const erreurs = soucis.filter((s) => s.gravite === 'erreur').length;
    ligne(etiquette,
      `${erreurs} erreur(s), ${soucis.length - erreurs} avertissement(s)`, 22);
  }
  console.log();
  console.log('   Ce controle tient dans un fichier et se met dans une CI :');
  console.log('   un workflow versionne se relit comme du code, et il y a');
  console.log('   quatre choses qu\'une relecture humaine rate a tous les');
  console.log('   coups — le signe « = », un orphelin, un identifiant absent,');
  console.log('   et une reference vers un noeud en aval.');

  titre(5, 'CE QUE LA VERIFICATION NE VOIT PAS');
  const passages = faireCirculer(fautif.donnees, fautif.flux, candidatures(50));
  ligne('a-corriger : refus envoyes',
    String((passages.get('Refus poli') || {}).itemsEntres || 0), 30);
  ligne('  …a des candidats', 'de 3 ans d\'experience ou plus', 30);
  console.log();
  console.log('   La branche inversee du chapitre 4 passe toutes les');
  console.log('   verifications statiques : les deux branchements sont');
  console.log('   syntaxiquement identiques. Seule une execution avec des');
  console.log('   donnees connues la revele.');
  console.log();
  console.log('   D\'ou la seule bonne pratique qui compte ici : un workflow de');
  console.log('   production merite un jeu de donnees de reference et une');
  console.log('   assertion sur ce qui en sort. `tests/` de ce projet en est');
  console.log('   un exemple — trois lignes par regle metier.');

  titre(6, 'CE QUE CE PROJET NE PROUVE PAS');
  for (const limite of [
    'n8n lui-meme ne tourne pas : ce projet utilise `n8n-workflow`, la',
    '  bibliotheque, pas l\'application. Aucun editeur, aucun serveur ;',
    'les noeuds n\'executent rien : un « Postgres » n\'ecrit pas, un',
    '  « Send Email » n\'envoie pas. Le registre de types est minimal ;',
    'l\'ordre d\'execution reel (executionOrder v1, position des noeuds)',
    '  n\'est pas reproduit — le projet parle d\'ordre de LECTURE ;',
    'les couts du chapitre 5 sont des ordres de grandeur annonces comme',
    '  tels : aucun modele n\'est appele.',
  ]) console.log(limite.startsWith('  ') ? `   ${limite}` : `   · ${limite}`);
  console.log();
  console.log('   Ce qui EST reel : le graphe, les expressions (vrai moteur');
  console.log('   n8n), le routage des items, et les sept controles du');
  console.log('   verificateur.');

  console.log('\n   node outils/verifier-flux.js flux/a-corriger.json\n');
}

if (require.main === module) principal();
module.exports = { principal };
