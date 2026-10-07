"""Le banc de la mission : écrit AVANT le code, avec le client.

Chaque cas est une question réelle d'un candidat ou d'un recruteur, avec ce que
la réponse doit contenir pour être jugée bonne. Rien n'est noté « à l'œil » :
les références attendues sont CALCULÉES depuis les données du portail (un
filtre, pas une liste recopiée), et la note se calcule.

Quatre sortes de contrôle :
- references : les offres attendues sont toutes citées, et aucune autre ;
- faits : des nombres qui doivent figurer dans la réponse (un salaire, un
  nombre de candidatures) ;
- refus : une question hors sujet est déclinée, sans citer d'offre ;
- inconnu : une offre ou une entreprise absente du portail est dite absente,
  sans offre inventée.
"""

import re

from jobportal.donnees import CANDIDATURES, OFFRES


def _refs(filtre) -> set[str]:
    return {o["reference"] for o in OFFRES if filtre(o)}


def _cas(identifiant, public, question, **attendu):
    return {"id": identifiant, "public": public, "question": question, **attendu}


MAX_CANDIDATURES = max(CANDIDATURES.values())
REF_MAX = next(r for r, n in CANDIDATURES.items() if n == MAX_CANDIDATURES)

CAS = [
    _cas("java-lyon", "candidat", "Quelles sont les offres de développeur Java à Lyon ?",
         references=_refs(lambda o: o["ville"] == "Lyon" and "Java" in o["titre"])),
    _cas("data-a-distance", "candidat", "Je cherche un poste dans la data, en télétravail complet.",
         references=_refs(lambda o: o["categorie"] == "Données" and o["mode"] == "à distance")),
    _cas("cdd-grenoble", "candidat", "Y a-t-il un CDD à Grenoble ?",
         references=_refs(lambda o: o["contrat"] == "CDD" and o["ville"] == "Grenoble")),
    _cas("salaire-ia", "candidat", "Quel salaire pour le poste d'ingénieur IA chez Lumen ?",
         references={"OFF-103"}, faits=[58000, 72000]),
    _cas("alternance", "candidat", "Quelles offres en alternance ?",
         references=_refs(lambda o: o["contrat"] == "Alternance")),
    _cas("designer-freelance", "candidat", "Une mission de designer en freelance ?",
         references=_refs(lambda o: o["categorie"] == "Design" and o["contrat"] == "Freelance")),
    _cas("securite-paris", "candidat", "Un poste en cybersécurité à Paris ?", references={"OFF-120"}),
    _cas("kubernetes", "candidat", "Quelle offre demande de connaître Kubernetes ?",
         references=_refs(lambda o: "Kubernetes" in o["description"])),
    _cas("candidatures-103", "recruteur", "Combien de candidatures a reçues l'offre OFF-103 ?",
         references={"OFF-103"}, faits=[CANDIDATURES["OFF-103"]]),
    _cas("plus-de-candidatures", "recruteur", "Quelle offre a reçu le plus de candidatures ?",
         references={REF_MAX}, faits=[MAX_CANDIDATURES]),
    _cas("offre-inconnue", "recruteur", "Combien de candidatures pour l'offre OFF-999 ?", inconnu=True),
    _cas("entreprise-absente", "candidat", "Quelles offres propose Google ?", inconnu=True),
    _cas("meteo", "hors sujet", "Quel temps fera-t-il à Lyon demain ?", refus=True),
    _cas("poeme", "hors sujet", "Écris-moi un poème sur la mer.", refus=True),
]

# Le jeu de VALIDATION : des questions écrites à part, jamais regardées pour
# régler l'assistant. Un assistant réglé en lisant les 14 cas du banc peut
# « apprendre le banc » au lieu du métier ; ce jeu-là le révèle.
CAS_VALIDATION = [
    _cas("v-dev-bordeaux", "candidat", "Des offres de développeur à Bordeaux ?",
         references=_refs(lambda o: o["ville"] == "Bordeaux" and "éveloppeur" in o["titre"])),
    _cas("v-cdi-marseille", "candidat", "Je veux un CDI à Marseille.",
         references=_refs(lambda o: o["ville"] == "Marseille" and o["contrat"] == "CDI")),
    _cas("v-stage-data", "candidat", "Un stage en data ?",
         references=_refs(lambda o: o["contrat"] == "Stage" and o["categorie"] == "Données")),
    _cas("v-postulants-120", "recruteur", "Combien de personnes ont postulé à OFF-120 ?",
         references={"OFF-120"}, faits=[CANDIDATURES["OFF-120"]]),
    _cas("v-salaire-comptable", "candidat", "Quelle est la fourchette de salaire du poste de comptable ?",
         references=_refs(lambda o: o["titre"] == "Comptable"), faits=[36000, 42000]),
    _cas("v-amazon", "candidat", "Avez-vous des offres chez Amazon ?", inconnu=True),
    _cas("v-crepes", "hors sujet", "Peux-tu me donner une recette de crêpes ?", refus=True),
    _cas("v-plus-demandee", "recruteur", "Quelle offre attire le plus de candidats ?",
         references={REF_MAX}, faits=[MAX_CANDIDATURES]),
]

# Ce qui, dans une réponse, signale un refus ou une absence. Une liste de mots
# reste un juge imparfait : on la publie, et l'on relit les réponses notées.
REFUS = re.compile(r"ne peux pas|je ne peux|ne suis pas en mesure|uniquement|seulement des|hors de (mon|ce)"
                   r"|pas (de|d') ?(lien|rapport)|je suis l'assistant|je réponds (aux|sur)", re.I)
INCONNU = re.compile(r"aucune|introuvable|n'existe pas|pas trouvé|ne trouve pas|inconnue?|pas d'offre"
                     r"|ne figure pas|aucun résultat|n'a pas été trouvée|pas dans (le|notre) portail", re.I)
REFERENCE = re.compile(r"OFF-\d{3}")
NOMBRE = re.compile(r"(\d{1,3}(?:[   .]\d{3})+|\d+)(?:[   ]?([kK])(?:€|\b))?")


def nombres(texte: str) -> set[int]:
    """Les nombres d'un texte, écrits « 58 000 », « 58000 » ou « 58 k€ »."""
    trouves = set()
    for chiffres, kilo in NOMBRE.findall(texte):
        valeur = int(re.sub(r"\D", "", chiffres))
        trouves.add(valeur * 1000 if kilo else valeur)
    return trouves


def noter(cas: dict, reponse: str) -> dict:
    """Chaque contrôle du cas, juste ou faux, et le verdict : juste si tous le sont."""
    citees = set(REFERENCE.findall(reponse))
    controles = {}
    if "references" in cas:
        controles["toutes les offres attendues citées"] = cas["references"] <= citees
        controles["aucune autre offre citée"] = citees <= cas["references"]
    if "faits" in cas:
        controles["les chiffres attendus présents"] = set(cas["faits"]) <= nombres(reponse)
    # >>> depart: un refus doit être signalé (REFUS), sans offre citée ; une absence doit être signalée (INCONNU), sans offre inventée — reprendre la référence de la question n'est pas inventer.
    if cas.get("refus"):
        controles["refus signalé"] = bool(REFUS.search(reponse))
        controles["aucune offre citée"] = not citees
    if cas.get("inconnu"):
        controles["absence signalée"] = bool(INCONNU.search(reponse))
        # « L'offre OFF-999 n'existe pas » reprend la question : ce n'est pas une invention.
        controles["aucune offre inventée"] = not (citees - set(REFERENCE.findall(cas["question"])))
    # <<<
    return {"id": cas["id"], "controles": controles, "juste": all(controles.values()),
            "citees": sorted(citees)}
