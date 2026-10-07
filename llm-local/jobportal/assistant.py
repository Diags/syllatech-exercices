"""L'assistant du portail, en local : le code du cours, tel quel.

Chaque fonction prend le client en paramètre. Sur votre machine, c'est
`ollama.Client()` (Ollama écoute sur http://localhost:11434) ; dans les tests,
c'est le même client branché sur jobportal.fausse_ollama.
"""

import math
import statistics

import ollama
import openai

from jobportal.donnees import ANNONCES, CHAMPS
from jobportal.fiche import champs_justes, extraire_fiche

MODELE = "qwen2.5:1.5b-instruct-q4_K_M"
EMBEDDINGS = "bge-m3"
SYSTEME = "Tu es l'assistant du portail d'emploi. Réponds en français, en trois phrases au plus."


# ---------------------------------------------------------------- chapitre 1
# Pourquoi en local, et premier modèle

def demander(client: ollama.Client, question: str, modele: str = MODELE) -> str:
    reponse = client.chat(
        model=modele,
        messages=[{"role": "system", "content": SYSTEME}, {"role": "user", "content": question}],
    )
    return reponse.message.content


# ---------------------------------------------------------------- chapitre 2
# Ollama depuis Python : flux, sortie structurée, API compatible OpenAI

def demander_en_flux(client: ollama.Client, question: str, afficher=print,
                     modele: str = MODELE) -> str:
    morceaux = []
    for morceau in client.chat(model=modele, messages=[{"role": "user", "content": question}],
                               stream=True):
        afficher(morceau.message.content)
        morceaux.append(morceau.message.content)
    return "".join(morceaux)


def client_compatible_openai(hote: str = "http://localhost:11434") -> openai.OpenAI:
    # Le client OpenAI exige une clé ; Ollama ne la lit pas. N'importe quelle valeur.
    return openai.OpenAI(base_url=f"{hote}/v1", api_key="ollama")


def demander_via_openai(client: openai.OpenAI, question: str, modele: str = MODELE) -> str:
    reponse = client.chat.completions.create(
        model=modele,
        messages=[{"role": "system", "content": SYSTEME}, {"role": "user", "content": question}],
    )
    return reponse.choices[0].message.content


def creer_assistant(client: ollama.Client, nom: str = "assistant-portail", base: str = MODELE):
    """Un modèle à soi, sans entraînement : la base, des consignes et des réglages."""
    return client.create(model=nom, from_=base, system=SYSTEME,
                         parameters={"temperature": 0.2, "num_ctx": 8192})


# ---------------------------------------------------------------- chapitre 3
# La quantization, mesurée

def mesurer_vitesse(client: ollama.Client, modele: str, prompt: str) -> dict:
    """Vitesse et mémoire, lues dans Ollama lui-même (durées en nanosecondes)."""
    r = client.chat(model=modele, messages=[{"role": "user", "content": prompt}],
                    options={"temperature": 0, "num_predict": 96})
    charge = next(m for m in client.ps().models if m.model == modele)
    return {"jetons_par_s": r.eval_count / (r.eval_duration / 1e9),
            "chargement_s": r.load_duration / 1e9,
            "memoire_mo": charge.size / 1e6}


def comparer_quantizations(client: ollama.Client, modeles: list[str], prompt: str,
                           tours: int = 7) -> dict:
    """En alternance : une charge passagère de la machine touche tous les modèles d'un tour.
    Le préfixe « Essai k » empêche Ollama de resservir un prompt déjà lu."""
    vitesses = {m: [] for m in modeles}
    # TODO : mesurer EN ALTERNANCE (à chaque tour, chaque modèle une fois), avec un prompt qui change à chaque tour. Ce squelette mesure en blocs : les tests le refusent.
    for modele in modeles:
        for k in range(tours):
            mesure = mesurer_vitesse(client, modele, prompt)
            vitesses[modele].append(mesure["jetons_par_s"])
    return {m: statistics.median(v) for m, v in vitesses.items()}


# ---------------------------------------------------------------- chapitre 4
# Choisir et évaluer un modèle

def evaluer(client: ollama.Client, modele: str) -> tuple[int, int]:
    """Les champs justes sur tout le banc d'annonces, et le total possible."""
    justes = 0
    for annonce in ANNONCES:
        fiche, _ = extraire_fiche(client, modele, annonce["texte"])
        justes += champs_justes(fiche, annonce["attendu"])
    return justes, len(ANNONCES) * len(CHAMPS)


# ---------------------------------------------------------------- chapitre 5
# Servir en production

def client_de_production(hote: str = "http://localhost:11434") -> ollama.Client:
    return ollama.Client(host=hote, timeout=120)


def demander_en_production(client: ollama.Client, question: str, modele: str = MODELE) -> str:
    reponse = client.chat(
        model=modele,
        messages=[{"role": "system", "content": SYSTEME}, {"role": "user", "content": question}],
        # TODO : fixer la fenêtre de contexte (num_ctx à 8192), une température de 0.2, et garder le modèle chargé 30 minutes (keep_alive).
    )
    return reponse.message.content


# ---------------------------------------------------------------- chapitre 6
# RAG local

def texte_offre(o: dict) -> str:
    return f"{o['titre']} chez {o['entreprise']}, {o['contrat']} à {o['ville']}, {o['mode']}"


def cosinus(a: list[float], b: list[float]) -> float:
    produit = sum(x * y for x, y in zip(a, b))
    return produit / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


def indexer(client: ollama.Client, offres: list[dict]) -> list[list[float]]:
    return client.embed(model=EMBEDDINGS, input=[texte_offre(o) for o in offres]).embeddings


def rechercher(client: ollama.Client, question: str, offres: list[dict], index,
               k: int = 3) -> list[dict]:
    vecteur = client.embed(model=EMBEDDINGS, input=question).embeddings[0]
    # TODO : classer les offres par similarité cosinus avec la question, et rendre les k plus proches.
    return offres[:k]


def repondre_avec_rag(client: ollama.Client, question: str, offres: list[dict], index,
                      modele: str = MODELE) -> str:
    trouvees = rechercher(client, question, offres, index)
    contexte = "\n".join(f"- {o['reference']} : {texte_offre(o)}" for o in trouvees)
    return demander(client, f"Offres du portail :\n{contexte}\n\nQuestion : {question}", modele)
