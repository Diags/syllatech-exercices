"""Les annonces d'entraînement du fine-tuning, générées par gabarits.

Le banc d'évaluation (jobportal.donnees.ANNONCES) ne doit RIEN prêter à
l'entraînement : ni ses villes, ni ses phrases. Sinon le modèle apprend les
réponses du contrôle, et le score après fine-tuning ne mesure plus rien. Les
villes ci-dessous sont donc toutes différentes des douze du banc, et les
gabarits ne reprennent aucune de ses phrases — `verifier_separation()` le
contrôle à chaque génération.
"""

import json
import random

from jobportal.donnees import ANNONCES

VILLES = ["Nice", "Dijon", "Tours", "Metz", "Brest", "Angers", "Reims", "Caen", "Limoges", "Pau",
          "Annecy", "Orléans", "Nancy", "Amiens", "Poitiers", "Perpignan", "Besançon", "Rouen",
          "Clermont-Ferrand", "Le Mans"]
ENTREPRISES = ["Arcadie", "Boréal", "Cobalt", "Dune", "Écume", "Fjord", "Galène", "Halo", "Iris", "Jade"]
TITRES = ["développeur Python", "chef de projet digital", "technicien support", "data analyst",
          "ingénieur réseau", "comptable", "chargé de recrutement", "développeur mobile",
          "administrateur système", "consultant SAP", "responsable marketing", "testeur logiciel"]

CONTRATS = {
    "CDI": ["CDI", "contrat à durée indéterminée", "poste en CDI", "embauche en CDI"],
    "CDD": ["CDD de 6 mois", "contrat à durée déterminée de 9 mois", "CDD", "CDD (remplacement)"],
    "Freelance": ["mission freelance", "en indépendant", "prestation en freelance", "freelance"],
    "Stage": ["stage de fin d'études", "stage de 6 mois", "stage"],
    "Alternance": ["alternance", "contrat d'apprentissage", "en alternance sur 2 ans"],
}
MODES = {
    "sur site": ["sur site", "en présentiel", "100 % au bureau", "pas de télétravail possible"],
    "hybride": ["hybride", "2 jours de télétravail par semaine", "télétravail partiel", "3 jours sur site"],
    "à distance": ["full remote", "100 % télétravail", "entièrement à distance", "télétravail complet"],
}
FOURCHETTES = {"CDI": (35, 75), "CDD": (30, 55), "Freelance": (45, 110), "Stage": (7, 16),
               "Alternance": (11, 20)}

GABARITS = [
    "{entreprise} recherche un {titre} ({contrat}) basé à {ville}. Mode de travail : {mode}. "
    "Rémunération : {salaire}.",
    "Offre : {titre} — {ville}. Type de contrat : {contrat}. Organisation : {mode}. Salaire : {salaire}.",
    "À {ville}, {entreprise} ouvre un poste de {titre} : {contrat}, {mode}, {salaire}.",
    "{titre} H/F | {ville} | {contrat} | {mode} | {salaire}",
    "Nous recrutons pour notre site de {ville} : {titre}. {contrat}, {mode}. Package : {salaire}.",
]

CONSIGNE_JSON = (
    "Tu extrais la fiche d'une annonce d'emploi. Salaires en euros bruts ANNUELS, en nombre "
    "entier (52 k€ = 52000). Ville : la ville du poste, sans département. Réponds uniquement par "
    "un objet JSON avec les clés ville, contrat, mode, salaire_min, salaire_max. contrat parmi "
    "CDI, CDD, Freelance, Stage, Alternance ; mode parmi sur site, hybride, à distance."
)


def _salaire(hasard: random.Random, contrat: str) -> tuple[str, int, int]:
    bas, haut = FOURCHETTES[contrat]
    a = hasard.randint(bas, haut - 3)
    b = hasard.randint(a + 1, min(a + 15, haut))
    if contrat == "Stage":
        mensuel = round(a * 1000 / 12 / 50) * 50
        return f"{mensuel} € par mois, soit {mensuel * 12} € par an", mensuel * 12, mensuel * 12
    forme = hasard.choice([
        "{a} 000 à {b} 000 € brut annuel", "{a}-{b} k€", "entre {a} et {b} K€ par an", "{a}k€ – {b}k€",
    ])
    return forme.format(a=a, b=b), a * 1000, b * 1000


def generer(n: int = 240, graine: int = 7) -> list[dict]:
    """n exemples {texte, attendu} : l'annonce, et la fiche que le modèle doit rendre."""
    hasard = random.Random(graine)
    exemples = []
    for _ in range(n):
        contrat = hasard.choice(list(CONTRATS))
        mode = hasard.choice(list(MODES))
        ville = hasard.choice(VILLES)
        texte_salaire, smin, smax = _salaire(hasard, contrat)
        texte = hasard.choice(GABARITS).format(
            entreprise=hasard.choice(ENTREPRISES), titre=hasard.choice(TITRES), ville=ville,
            contrat=hasard.choice(CONTRATS[contrat]), mode=hasard.choice(MODES[mode]), salaire=texte_salaire)
        exemples.append({"texte": texte, "attendu": {"ville": ville, "contrat": contrat, "mode": mode,
                                                     "salaire_min": smin, "salaire_max": smax}})
    return exemples


def en_conversation(exemple: dict) -> list[dict]:
    """Un exemple au format conversation : ce que le modèle lit, et ce qu'il doit écrire."""
    return [
        {"role": "system", "content": CONSIGNE_JSON},
        {"role": "user", "content": exemple["texte"]},
        {"role": "assistant", "content": json.dumps(exemple["attendu"], ensure_ascii=False)},
    ]


def verifier_separation(exemples: list[dict]) -> None:
    """Aucune ville ni aucune phrase du banc d'évaluation dans l'entraînement."""
    villes_du_banc = {a["attendu"]["ville"] for a in ANNONCES}
    communes = villes_du_banc & {e["attendu"]["ville"] for e in exemples}
    if communes:
        raise ValueError(f"villes du banc présentes dans l'entraînement : {communes}")
    for annonce in ANNONCES:
        for exemple in exemples:
            if annonce["texte"][:40] in exemple["texte"]:
                raise ValueError(f"phrase du banc reprise : {annonce['texte'][:40]}")
