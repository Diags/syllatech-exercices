/**
 * Ce que les workflows du job portal doivent garantir.
 *
 *     npm test        (node --test tests/)
 *
 * Les tests marqués « reel » passent par `n8n-workflow` : le graphe et les
 * expressions sont ceux de n8n. S'ils cassent a une montee de version, c'est
 * n8n qui a change — et chaque assertion correspond a une phrase d'un
 * chapitre.
 */

'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { DateTime } = require('luxon');

const flux = require('../jobportal/flux');
const {
  champsLus, estUneExpression, evaluer, gabaritSansSigneEgal,
  noeudsReferences, parametres,
} = require('../jobportal/expressions');
const { candidatures, faireCirculer } = require('../jobportal/execution');
const { verifier } = require('../outils/verifier-flux');
const { TYPES } = require('../jobportal/typesDeNoeuds');

const propre = () => flux.charger('candidature');
const fautif = () => flux.charger('a-corriger');
const contexte = (json) => ({ $json: json, $now: DateTime.now(), $itemIndex: 0 });

// ------------------------------------------------------------- le graphe

test('reel : le workflow se construit avec le vrai Workflow de n8n', () => {
  const { donnees, flux: graphe } = propre();
  assert.equal(flux.noms(graphe).length, donnees.nodes.length);
  assert.deepEqual(flux.declencheurs(graphe), ['Webhook candidature']);
});

test("un noeud est un declencheur par sa methode trigger, pas son groupe", () => {
  assert.ok(TYPES['n8n-nodes-base.webhook'].trigger);
  assert.ok(!TYPES['n8n-nodes-base.set'].trigger);
});

test('le constructeur Workflow MUTE les noeuds qu on lui passe', () => {
  // n8n normalise `parameters` contre les `properties` du type, et jette ce
  // qui n'y figure pas. `construire` travaille donc sur une copie — sans
  // cela, l'analyse des expressions ne verrait plus rien.
  const { donnees } = propre();
  const avant = JSON.stringify(donnees.nodes[1].parameters);
  flux.construire(donnees);
  assert.equal(JSON.stringify(donnees.nodes[1].parameters), avant);
});

test('un noeud branche uniquement sur une sortie d erreur n est pas orphelin', () => {
  // `getChildNodes` ne suit que « main » par defaut : sans le parcours des
  // deux types, on declarerait orphelin le seul noeud qui journalise.
  const { flux: graphe } = propre();
  assert.deepEqual(flux.orphelins(graphe), []);
});

test('un noeud detache est signale', () => {
  const { flux: graphe } = fautif();
  assert.deepEqual(flux.orphelins(graphe), ['Notes internes']);
});

// -------------------------------------------------------- les expressions

test('reel : le moteur de n8n evalue les expressions', () => {
  const { flux: graphe } = propre();
  const donnees = { poste: 'devops', nom: '  Diaguily  ', salaire: 62 };
  assert.equal(evaluer(graphe, '={{ $json.poste }}', contexte(donnees)),
    'devops');
  assert.equal(evaluer(graphe, '={{ $json.nom.trim() }}', contexte(donnees)),
    'Diaguily');
  assert.equal(evaluer(graphe, '={{ $json.salaire > 60 }}', contexte(donnees)),
    true);
});

test('reel : sans le signe « = », n8n rend la chaine telle quelle', () => {
  const { flux: graphe } = propre();
  const donnees = { poste: 'devops' };
  assert.equal(evaluer(graphe, '={{ $json.poste }}', contexte(donnees)),
    'devops');
  assert.equal(evaluer(graphe, '{{ $json.poste }}', contexte(donnees)),
    '{{ $json.poste }}');
});

test('reel : un chemin absent rend undefined, sans lever', () => {
  const { flux: graphe } = propre();
  const donnees = { poste: 'devops' };
  assert.equal(evaluer(graphe, '={{ $json.post }}', contexte(donnees)),
    undefined);
  // Celle-ci dereferencerait `undefined` en JavaScript ordinaire.
  assert.equal(evaluer(graphe, '={{ $json.a.b.c }}', contexte(donnees)),
    undefined);
});

test('reel : $now est un DateTime Luxon, pas une Date', () => {
  const { flux: graphe } = propre();
  const rendu = evaluer(graphe, '={{ $now.toISO() }}', contexte({}));
  assert.match(String(rendu), /^\d{4}-\d{2}-\d{2}T/);
});

test('on distingue un gabarit litteral d une expression', () => {
  assert.ok(estUneExpression('={{ $json.x }}'));
  assert.ok(!estUneExpression('{{ $json.x }}'));
  assert.ok(gabaritSansSigneEgal('{{ $json.x }}'));
  assert.ok(!gabaritSansSigneEgal('={{ $json.x }}'));
  assert.ok(!gabaritSansSigneEgal('du texte ordinaire'));
});

test('on retrouve les champs et les noeuds lus par une expression', () => {
  assert.deepEqual(champsLus('={{ $json.nom + $json.poste }}'),
    ['nom', 'poste']);
  assert.deepEqual(noeudsReferences("={{ $('Normaliser').item.json.email }}"),
    ['Normaliser']);
});

test('les parametres d un workflow se lisent a plat', () => {
  const { donnees } = propre();
  const plats = parametres(donnees);
  assert.ok(plats.length > 10);
  assert.ok(plats.some((p) => p.noeud === 'Normaliser'
    && String(p.valeur).includes('$json.nom')));
});

// --------------------------------------------------------- le tapis roulant

test('50 items font 50 executions par noeud traverse', () => {
  const { donnees, flux: graphe } = propre();
  const passages = faireCirculer(donnees, graphe, candidatures(50));
  assert.equal(passages.get('Normaliser').executions, 50);
  assert.equal(passages.get('Normaliser').itemsEntres, 50);
});

test('chaque expression est reevaluee une fois par item', () => {
  const { donnees, flux: graphe } = propre();
  const un = faireCirculer(donnees, graphe, candidatures(1));
  const cinquante = faireCirculer(donnees, graphe, candidatures(50));
  const total = (p) => [...p.values()]
    .reduce((s, x) => s + x.expressionsEvaluees, 0);
  assert.equal(total(cinquante), total(un) * 50);
});

test('le IF aiguille sans perdre d items', () => {
  const { donnees, flux: graphe } = propre();
  const passages = faireCirculer(donnees, graphe, candidatures(50));
  const entres = passages.get("Assez d'experience ?").itemsEntres;
  const gauche = passages.get('Enregistrer').itemsEntres;
  const droite = passages.get('Refus poli').itemsEntres;
  assert.equal(gauche + droite, entres);
});

test('les deux branches sont INVERSEES dans le workflow a corriger', () => {
  // Le defaut qu'aucune verification statique ne voit : les candidats
  // qualifies recoivent le courriel de refus.
  const bon = propre();
  const mauvais = fautif();
  const a = faireCirculer(bon.donnees, bon.flux, candidatures(50));
  const b = faireCirculer(mauvais.donnees, mauvais.flux, candidatures(50));
  assert.equal(a.get('Enregistrer').itemsEntres, 20);
  assert.equal(b.get('Enregistrer').itemsEntres, 30);
  assert.equal(a.get('Refus poli').itemsEntres, 30);
  assert.equal(b.get('Refus poli').itemsEntres, 20);
});

test('une faute de frappe dans un champ rend une expression vide', () => {
  const { donnees, flux: graphe } = fautif();
  const passages = faireCirculer(donnees, graphe, candidatures(50));
  // « $json.post » au lieu de « $json.poste » : une par item.
  assert.equal(passages.get('Normaliser').videsRendus, 50);
});

test('les expressions $(...) sont comptees a part, pas comme vides', () => {
  // Elles demandent le proxy de donnees complet de n8n. Les compter comme
  // vides ferait croire a un defaut du workflow.
  const { donnees, flux: graphe } = propre();
  const passages = faireCirculer(donnees, graphe, candidatures(10));
  assert.ok(passages.get('Accuser reception').horsContexte > 0);
  assert.equal(passages.get('Accuser reception').videsRendus, 0);
});

// --------------------------------------------------------- le verificateur

test('le workflow livre ne leve rien', () => {
  const { donnees, flux: graphe } = propre();
  assert.deepEqual(verifier(donnees, graphe), []);
});

test('le workflow a corriger leve ses quatre erreurs', () => {
  const { donnees, flux: graphe } = fautif();
  const soucis = verifier(donnees, graphe);
  const ou = soucis.map((s) => s.ou);
  assert.ok(ou.some((o) => o.startsWith('orphelin /')));
  assert.ok(ou.some((o) => o.includes('assignments[0]')), 'le signe = manquant');
  assert.ok(ou.some((o) => o.includes('assignments[2]')), 'reference en aval');
  assert.ok(ou.some((o) => o.startsWith('identifiants /')));
  assert.equal(soucis.filter((s) => s.gravite === 'erreur').length, 4);
  assert.equal(soucis.filter((s) => s.gravite === 'attention').length, 2);
});

test('une reference vers un noeud en AVAL est une erreur', () => {
  const { donnees, flux: graphe } = fautif();
  const souci = verifier(donnees, graphe)
    .find((s) => s.message.includes("$('Decision')"));
  assert.ok(souci, 'la reference doit etre signalee');
  assert.match(souci.message, /pas en AMONT/);
});

test('un workflow sans declencheur est une erreur bloquante', () => {
  const donnees = {
    name: 'sans depart',
    nodes: [{
      id: '1', name: 'Seul', type: 'n8n-nodes-base.set', typeVersion: 1,
      position: [0, 0], parameters: {},
    }],
    connections: {}, active: false, settings: {},
  };
  const soucis = verifier(donnees, flux.construire(donnees));
  assert.ok(soucis.some((s) => s.ou === 'declencheur'));
});

test('un IF dont les deux sorties vont au meme noeud est signale', () => {
  const donnees = {
    name: 'condition inutile',
    nodes: [
      { id: '1', name: 'Depart', type: 'n8n-nodes-base.webhook', typeVersion: 1,
        position: [0, 0], parameters: {} },
      { id: '2', name: 'Choix', type: 'n8n-nodes-base.if', typeVersion: 1,
        position: [200, 0], parameters: {} },
      { id: '3', name: 'Suite', type: 'n8n-nodes-base.noOp', typeVersion: 1,
        position: [400, 0], parameters: {} },
    ],
    connections: {
      Depart: { main: [[{ node: 'Choix', type: 'main', index: 0 }]] },
      Choix: {
        main: [
          [{ node: 'Suite', type: 'main', index: 0 }],
          [{ node: 'Suite', type: 'main', index: 0 }],
        ],
      },
    },
    active: false, settings: {},
  };
  const soucis = verifier(donnees, flux.construire(donnees));
  assert.ok(soucis.some((s) => s.ou === 'IF / Choix'));
});
