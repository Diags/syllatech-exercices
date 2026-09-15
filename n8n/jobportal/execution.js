/**
 * Le tapis roulant d'items — le modèle mental de n8n, rendu mesurable.
 *
 * « Un nœud ne traite pas une valeur mais un TABLEAU d'items : si 50
 * candidatures entrent, le nœud suivant s'exécute 50 fois. »
 *
 * C'est la phrase du cours, et c'est celle qui explique la moitié des
 * surprises. Ce module la rend comptable : combien d'items entrent dans
 * chaque nœud, combien de fois chaque expression est évaluée, et où les
 * items disparaissent.
 *
 * ⚠️ CE QUI EST SUBSTITUÉ : l'exécution des nœuds. Un « Postgres » d'ici
 * n'écrit rien, un « Send Email » n'envoie rien. Ce qui est réel : le
 * routage des items dans le graphe, l'évaluation des expressions (par le
 * vrai moteur de n8n), et le compte.
 *
 * Ce n'est donc pas un moteur n8n. C'est un compteur — et c'est ce qui
 * manque quand on regarde un workflow dans l'éditeur.
 */

'use strict';

const { enfantsDirects } = require('./flux');
const {
  estUneExpression, evaluer, noeudsReferences,
} = require('./expressions');

// n8n donne `$now` sous forme de DateTime Luxon, pas de Date JavaScript :
// c'est pourquoi `{{ $now.toISO() }}` marche dans l'editeur. Luxon arrive
// avec n8n-workflow ; le passer ici evite de compter comme « vide » une
// expression qui marcherait tres bien dans n8n.
const { DateTime } = require('luxon');

/** Ce qu'on sait d'un nœud après le passage des items. */
class Passage {
  constructor(noeud) {
    this.noeud = noeud;
    this.itemsEntres = 0;
    this.itemsSortis = 0;
    this.expressionsEvaluees = 0;
    this.videsRendus = 0;       // expressions qui rendent undefined ou ''
    this.horsContexte = 0;      // expressions que CE contexte ne peut pas
    this.executions = 0;        // combien de fois le nœud a « tourné »
  }

  get perdus() {
    return this.itemsEntres - this.itemsSortis;
  }
}

/**
 * Fait circuler des items depuis le déclencheur, et compte tout.
 *
 * `decision` décide, pour un nœud IF, quels items prennent la sortie vraie.
 * Par défaut : ceux dont `annees >= 3`.
 */
function faireCirculer(donnees, flux, items, options = {}) {
  const decision = options.decision
    || ((item) => Number(item.json.annees ?? 0) >= 3);
  const depart = flux.getTriggerNodes()[0];
  if (!depart) throw new Error('aucun declencheur : rien ne peut circuler');

  const passages = new Map();
  const parNom = new Map(donnees.nodes.map((n) => [n.name, n]));
  const pour = (nom) => {
    if (!passages.has(nom)) passages.set(nom, new Passage(nom));
    return passages.get(nom);
  };

  const visiter = (nom, entrants, vus) => {
    if (vus.has(nom) || entrants.length === 0) return;
    const passage = pour(nom);
    passage.itemsEntres += entrants.length;
    // Un nœud « tourne » une fois par item : c'est ce que le cours appelle
    // le traitement item par item, et ce qui surprend quand on regarde les
    // journaux.
    passage.executions += entrants.length;

    const noeud = parNom.get(nom);
    const sortants = entrants.map((item, index) => {
      const contexte = { $json: item.json, $itemIndex: index,
                         $now: DateTime.now() };
      for (const valeur of valeursDe(noeud)) {
        if (!estUneExpression(valeur)) continue;
        // ⚠️ `$('Autre noeud')` demande le proxy de donnees complet de n8n,
        // qui n'existe qu'au cours d'une vraie execution. Les compter comme
        // « vides » ferait croire a un defaut du workflow alors que c'est
        // une limite de CE contexte. On les compte a part.
        if (noeudsReferences(valeur).length > 0) {
          passage.horsContexte += 1;
          continue;
        }
        passage.expressionsEvaluees += 1;
        let resultat;
        try {
          resultat = evaluer(flux, valeur, contexte);
        } catch {
          resultat = undefined;
        }
        if (resultat === undefined || resultat === null || resultat === '') {
          passage.videsRendus += 1;
        }
      }
      return item;
    });

    if (noeud && noeud.type === 'n8n-nodes-base.if') {
      // TODO : aiguiller les items sur les DEUX sorties du IF — index 0 pour ceux qui satisfont la condition, index 1 pour les autres. Le IF ne filtre pas, il aiguille : la somme des deux branches vaut le nombre d'items entres. ⚠️ Si la branche « faux » n'est branchee nulle part, ses items s'arretent la, en silence. Trois tests le verifient.
      passage.itemsSortis += sortants.length; return;
    }

    passage.itemsSortis += sortants.length;
    for (const cible of enfantsDirects(flux, nom, 'main')) {
      visiter(cible, sortants, new Set(vus).add(nom));
    }
  };

  visiter(depart.name, items, new Set());
  return passages;
}

/** Les valeurs de paramètre d'un nœud, à plat. */
function valeursDe(noeud) {
  const sortie = [];
  const descendre = (objet) => {
    if (objet === null || objet === undefined) return;
    if (typeof objet === 'object') {
      for (const v of Object.values(objet)) descendre(v);
      return;
    }
    sortie.push(objet);
  };
  descendre(noeud ? noeud.parameters : {});
  return sortie;
}

/** Un lot de candidatures, pour faire tourner le tapis. */
function candidatures(combien) {
  return Array.from({ length: combien }, (_, n) => ({
    json: {
      nom: `  Candidat ${n + 1}  `,
      poste: n % 3 === 0 ? 'devops' : 'java',
      email: `candidat${n + 1}@exemple.fr`,
      annees: n % 5,
    },
  }));
}

module.exports = { Passage, faireCirculer, valeursDe, candidatures };
