/** Le peu que les six chapitres partagent. */

'use strict';

function titre(numero, texte) {
  console.log(`\n${numero}. ${texte}`);
  console.log('   ' + '─'.repeat(texte.length));
}

function ligne(gauche, droite, largeur = 34) {
  console.log(`   ${String(gauche).padEnd(largeur)} ${droite}`);
}

function plier(texte, largeur = 64) {
  const lignes = [];
  let courante = '';
  for (const mot of String(texte).split(/\s+/)) {
    if ((`${courante} ${mot}`).trim().length > largeur) {
      lignes.push(courante);
      courante = mot;
    } else courante = (`${courante} ${mot}`).trim();
  }
  if (courante) lignes.push(courante);
  return lignes;
}

/** Un tableau aligné : entêtes puis lignes de cellules. */
function tableau(entetes, lignes, largeurs) {
  const l = largeurs || entetes.map((e) => Math.max(e.length + 2, 12));
  console.log('   ' + entetes.map((e, i) => String(e).padEnd(l[i])).join(''));
  for (const cellules of lignes) {
    console.log('   ' + cellules.map((c, i) => String(c).padEnd(l[i])).join(''));
  }
}

module.exports = { titre, ligne, plier, tableau };
