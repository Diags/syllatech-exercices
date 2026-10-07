"""L'assistant du portail, chapitre par chapitre : le code du cours, tel quel.

Chaque fonction prend le client en paramètre. En production, c'est
`anthropic.Anthropic()` (la clé vient de ANTHROPIC_API_KEY) ; dans les tests
et les scripts de chapitre, c'est le même SDK branché sur jobportal.fausse_api.
"""

import json
from datetime import datetime

import anthropic
from anthropic import beta_tool
from pydantic import BaseModel

from jobportal import donnees

MODELE = "claude-opus-5-5"


def texte_de(reponse) -> str:
    """Le texte d'une réponse. Le premier bloc n'est pas forcément du texte :
    Opus 5.5 réfléchit toujours, et rend d'abord un bloc « thinking »."""
    # >>> depart: rendre le texte de la réponse. Sur Opus 5.5, le premier bloc peut être un bloc « thinking », qui n'a pas d'attribut text : filtrez par type.
    #     return reponse.content[0].text
    return "".join(bloc.text for bloc in reponse.content if bloc.type == "text")
    # <<<


# ---------------------------------------------------------------- chapitre 1
# Premier appel : la Messages API

SYSTEME = "Tu es l'assistant du portail d'emploi. Réponds en français, en trois phrases au plus."


def demander(client: anthropic.Anthropic, question: str) -> str:
    reponse = client.messages.create(
        model=MODELE,
        max_tokens=16000,
        system=SYSTEME,
        messages=[{"role": "user", "content": question}],
    )
    if reponse.stop_reason == "refusal":
        return "Je ne peux pas répondre à cette demande."
    return texte_de(reponse)


class Conversation:
    """L'API est sans état : chaque requête renvoie tout l'historique."""

    def __init__(self, client: anthropic.Anthropic):
        self.client = client
        self.messages = []

    def envoyer(self, question: str) -> str:
        self.messages.append({"role": "user", "content": question})
        reponse = self.client.messages.create(
            model=MODELE, max_tokens=16000, messages=self.messages
        )
        # On garde TOUS les blocs, réflexion comprise, pas seulement le texte.
        self.messages.append({"role": "assistant", "content": reponse.content})
        return texte_de(reponse)


# ---------------------------------------------------------------- chapitre 2
# Streaming, erreurs et nouvelles tentatives

def demander_en_flux(client: anthropic.Anthropic, question: str, afficher=print):
    with client.messages.stream(
        model=MODELE,
        max_tokens=64000,
        messages=[{"role": "user", "content": question}],
    ) as flux:
        for morceau in flux.text_stream:
            afficher(morceau)
        return flux.get_final_message()


def demander_sans_planter(client: anthropic.Anthropic, question: str) -> str:
    try:
        return demander(client, question)
    except anthropic.RateLimitError:
        # Le SDK a déjà réessayé deux fois avant d'arriver ici.
        return "Le service est très sollicité : réessayez dans un instant."
    except anthropic.APIStatusError as erreur:
        if erreur.status_code >= 500:
            return "Le service est momentanément indisponible."
        raise  # 400, 401, 404 : réessayer ne changera rien, c'est notre requête.
    except anthropic.APIConnectionError:
        return "Connexion impossible : vérifiez le réseau."


# ---------------------------------------------------------------- chapitre 3
# Les outils : la boucle agentique

OUTILS = [
    {
        "name": "rechercher_offres",
        "description": "Recherche les offres du portail par mot-clé : titre, entreprise "
                       "ou ville. Rend la référence, le titre, la ville et le contrat.",
        "input_schema": {
            "type": "object",
            "properties": {
                "mot_cle": {"type": "string", "description": "par exemple « java » ou « Lyon »"}
            },
            "required": ["mot_cle"],
        },
    },
    {
        "name": "compter_candidatures",
        "description": "Rend le nombre de candidatures reçues pour une offre, "
                       "à partir de sa référence.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reference": {"type": "string", "description": "par exemple OFF-101"}
            },
            "required": ["reference"],
        },
    },
]


def executer_outil(nom: str, entree: dict) -> str:
    if nom == "rechercher_offres":
        return json.dumps(donnees.rechercher(entree["mot_cle"]), ensure_ascii=False)
    if nom == "compter_candidatures":
        return str(donnees.compter_candidatures(entree["reference"]))
    raise ValueError(f"outil inconnu : {nom}")


def boucle_agentique(client: anthropic.Anthropic, question: str, tours_max: int = 10) -> str:
    messages = [{"role": "user", "content": question}]
    for _ in range(tours_max):
        reponse = client.messages.create(
            model=MODELE, max_tokens=16000, tools=OUTILS, messages=messages
        )
        if reponse.stop_reason != "tool_use":
            return texte_de(reponse)
        messages.append({"role": "assistant", "content": reponse.content})
        # >>> depart: exécuter chaque bloc tool_use avec executer_outil, et renvoyer TOUS les tool_result du tour dans un seul message utilisateur. Une exception d'outil repart en is_error : elle ne doit pas faire planter la boucle.
        #     resultats = []
        #     messages.append({"role": "user", "content": resultats})
        resultats = []
        for bloc in reponse.content:
            if bloc.type != "tool_use":
                continue
            resultat = {"type": "tool_result", "tool_use_id": bloc.id}
            try:
                resultat["content"] = executer_outil(bloc.name, bloc.input)
            except (KeyError, ValueError) as erreur:
                resultat["content"] = f"Erreur : {erreur}"
                resultat["is_error"] = True
            resultats.append(resultat)
        # Tous les résultats du tour dans UN SEUL message utilisateur.
        messages.append({"role": "user", "content": resultats})
        # <<<
    raise RuntimeError("trop de tours : l'agent ne converge pas")


# ---------------------------------------------------------------- chapitre 4
# Tool Runner et sorties structurées

@beta_tool
def rechercher_offres(mot_cle: str) -> str:
    """Recherche les offres du portail par mot-clé : titre, entreprise ou ville.

    Args:
        mot_cle: par exemple « java » ou « Lyon ».
    """
    return json.dumps(donnees.rechercher(mot_cle), ensure_ascii=False)


@beta_tool
def compter_candidatures(reference: str) -> str:
    """Rend le nombre de candidatures reçues pour une offre.

    Args:
        reference: la référence de l'offre, par exemple OFF-101.
    """
    return str(donnees.compter_candidatures(reference))


def avec_tool_runner(client: anthropic.Anthropic, question: str) -> str:
    runner = client.beta.messages.tool_runner(
        model=MODELE,
        max_tokens=16000,
        tools=[rechercher_offres, compter_candidatures],
        messages=[{"role": "user", "content": question}],
    )
    return texte_de(runner.until_done())


class FicheOffre(BaseModel):
    titre: str
    ville: str
    contrat: str
    competences: list[str]
    teletravail: bool


def extraire_fiche(client: anthropic.Anthropic, annonce: str) -> FicheOffre:
    reponse = client.messages.parse(
        model=MODELE,
        max_tokens=16000,
        messages=[{"role": "user", "content": f"Extrais la fiche de l'annonce :\n{annonce}"}],
        output_format=FicheOffre,
    )
    return reponse.parsed_output


# ---------------------------------------------------------------- chapitre 5
# Prompt caching et coûts

CONSIGNES = """Tu es l'assistant du portail d'emploi syllatech. Tu aides deux publics : les
candidats, qui cherchent une offre et préparent leur candidature, et les
recruteurs, qui publient des offres et suivent les candidatures reçues.

Règles de réponse :
- Réponds en français, avec des phrases courtes, sans jargon inutile.
- N'invente jamais une offre, une entreprise, un salaire ou un chiffre : si
  l'information n'est pas dans le portail, dis-le et propose de chercher.
- Cite toujours la référence d'une offre (OFF-101, par exemple) quand tu en
  parles, pour que l'utilisateur la retrouve sur le site.
- Les salaires sont des fourchettes brutes annuelles en euros ; ne les
  présente jamais comme des montants nets.
- Ne communique jamais les coordonnées d'un candidat à un autre candidat, ni
  le détail d'une candidature à quelqu'un d'autre que le recruteur de l'offre.

Pour les candidats :
- Pose au plus une question pour préciser une recherche trop large (métier,
  ville, type de contrat, télétravail), puis propose des offres.
- Explique ce qui rend un profil intéressant pour une offre en t'appuyant sur
  les compétences demandées, sans promettre d'issue au processus.
- Pour une lettre de motivation, propose une trame courte, à personnaliser,
  plutôt qu'un texte complet à envoyer tel quel.

Pour les recruteurs :
- Aide à rédiger une offre claire : missions, compétences indispensables et
  souhaitables, contrat, mode de travail, fourchette de salaire.
- Signale une offre discriminante (âge, origine, situation familiale) et
  propose une formulation neutre.
- Résume les candidatures sans les classer sur des critères personnels.

Format :
- Une liste quand tu présentes plusieurs offres : référence, titre, ville,
  contrat.
- Pas plus de cinq offres à la fois ; propose d'affiner au-delà.
- Termine par une seule suggestion d'action concrète.
"""


def demander_avec_cache(client: anthropic.Anthropic, question: str):
    return client.messages.create(
        model=MODELE,
        max_tokens=16000,
        # >>> depart: poser le marqueur cache_control sur les consignes, pour qu'elles soient relues en cache d'un appel à l'autre.
        #     system=CONSIGNES,
        system=[{"type": "text", "text": CONSIGNES, "cache_control": {"type": "ephemeral"}}],
        # <<<
        messages=[{"role": "user", "content": question}],
    )


def demander_avec_horloge(client: anthropic.Anthropic, question: str):
    """L'erreur classique : l'heure dans le prompt système change le préfixe."""
    horloge = f"Nous sommes le {datetime.now():%d/%m/%Y %H:%M:%S}.\n"
    return client.messages.create(
        model=MODELE,
        max_tokens=16000,
        system=[{"type": "text", "text": horloge + CONSIGNES,
                 "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": question}],
    )


# Prix publiés de Claude Opus 5.5, en dollars par million de jetons.
PRIX = {"entree": 4.00, "sortie": 20.00, "ecriture_cache": 4.00 * 1.25, "lecture_cache": 0.20}


def cout_en_dollars(usage) -> float:
    # >>> depart: calculer le coût d'un appel depuis usage, poste par poste : entrée, écriture en cache, lecture en cache, sortie. Les prix sont par MILLION de jetons.
    #     return 0.0
    return (
        usage.input_tokens * PRIX["entree"]
        + (usage.cache_creation_input_tokens or 0) * PRIX["ecriture_cache"]
        + (usage.cache_read_input_tokens or 0) * PRIX["lecture_cache"]
        + usage.output_tokens * PRIX["sortie"]
    ) / 1_000_000
    # <<<


def resumer_en_lot(client: anthropic.Anthropic, offres: list[dict]):
    """La Batches API : les mêmes requêtes, traitées en différé, à moitié prix."""
    return client.messages.batches.create(
        requests=[
            {
                "custom_id": offre["reference"],
                "params": {
                    "model": MODELE,
                    "max_tokens": 1024,
                    "messages": [{"role": "user", "content": f"Résume en une phrase : {offre}"}],
                },
            }
            for offre in offres
        ]
    )


# ---------------------------------------------------------------- chapitre 6
# En production : repli, effort, limites

def client_de_production() -> anthropic.Anthropic:
    return anthropic.Anthropic(max_retries=4, timeout=120.0)


def demander_en_production(client: anthropic.Anthropic, question: str) -> str:
    reponse = client.beta.messages.create(
        model=MODELE,
        max_tokens=16000,
        # >>> depart: activer le repli côté serveur (en-tête bêta server-side-fallback-2026-07-01, fallbacks à "default") et fixer l'effort explicitement dans output_config.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "medium"},
        # <<<
        system=[{"type": "text", "text": CONSIGNES, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": question}],
    )
    if reponse.stop_reason == "refusal":
        categorie = reponse.stop_details.category if reponse.stop_details else None
        return f"Demande refusée par le modèle (catégorie : {categorie})."
    return texte_de(reponse)
