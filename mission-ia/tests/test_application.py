"""L'application, mesurée sans Ollama : les vrais clients sur un serveur simulé."""

import json

import pytest

from jobportal import agent, outils
from jobportal.donnees import OFFRES
from jobportal.fausse_ollama import FausseOllama
from jobportal.recherche import Index


@pytest.fixture
def serveur():
    return FausseOllama()


def index_simule(serveur, question_proche_de=0):
    """Un index sur les 24 offres, chacune sur son axe ; la question vise l'offre demandée."""
    axes = [[1.0 if i == j else 0.0 for j in range(len(OFFRES))] for i in range(len(OFFRES))]
    serveur.vecteurs(*axes)
    index = Index(serveur.client(), OFFRES)
    question = [0.0] * len(OFFRES)
    question[question_proche_de] = 1.0
    return index, question


# ---------------------------------------------------------------- les outils

def test_filtrer_rend_exactement_les_offres_du_critere():
    refs = [o["reference"] for o in json.loads(outils.filtrer_offres(contrat="Alternance"))]
    assert refs == ["OFF-110", "OFF-118"]


def test_une_reference_inconnue_revient_en_erreur_pas_en_exception():
    assert "n'existe pas" in json.loads(outils.compter_candidatures("OFF-999"))["erreur"]


def test_le_classement_commence_par_l_offre_la_plus_demandee():
    premier = json.loads(outils.classement_candidatures(1))[0]
    assert (premier["reference"], premier["candidatures"]) == ("OFF-103", 21)


def test_un_outil_inconnu_ou_mal_appele_revient_en_erreur(serveur):
    assert "outil inconnu" in json.loads(outils.executer(None, "supprimer_offre", {}))["erreur"]
    assert "arguments invalides" in json.loads(outils.executer(None, "compter_candidatures", {"ref": "x"}))["erreur"]


def test_un_outil_ne_rend_pas_la_description():
    assert all("description" not in o for o in json.loads(outils.filtrer_offres(ville="Lyon")))


# ---------------------------------------------------------------- la recherche

def test_la_recherche_classe_par_similarite(serveur):
    index, question = index_simule(serveur, question_proche_de=2)
    serveur.vecteurs(question)
    assert index.chercher("x", k=1)[0]["reference"] == "OFF-103"
    assert serveur.requetes[0].corps["model"] == "bge-m3"
    assert len(serveur.requetes[0].corps["input"]) == len(OFFRES)


# ---------------------------------------------------------------- l'agent

def test_l_agent_execute_l_outil_et_renvoie_son_resultat(serveur):
    index, _ = index_simule(serveur)
    serveur.appeler_outils(("compter_candidatures", {"reference": "OFF-103"}))
    serveur.repondre("L'offre OFF-103 a reçu 21 candidatures.", prompt_eval_count=600, eval_count=15)
    texte, trace = agent.repondre_agent(serveur.client(), index, "Combien pour OFF-103 ?")
    assert texte == "L'offre OFF-103 a reçu 21 candidatures."
    premiere, seconde = serveur.requetes[1].corps, serveur.requetes[2].corps
    assert [t["function"]["name"] for t in premiere["tools"]] == [s["function"]["name"] for s in outils.SCHEMAS]
    assert premiere["options"]["num_predict"] == 400
    resultat = seconde["messages"][-1]
    assert resultat["role"] == "tool" and resultat["tool_name"] == "compter_candidatures"
    assert json.loads(resultat["content"]) == {"reference": "OFF-103", "candidatures": 21}
    assert trace.appels_modele == 2 and [o["nom"] for o in trace.outils] == ["compter_candidatures"]
    assert trace.jetons_sortie == 20 + 15  # la première réponse (20 jetons par défaut), puis la seconde


def test_l_agent_s_arrete_au_bout_de_tours_max(serveur):
    index, _ = index_simule(serveur)
    for _ in range(4):
        serveur.appeler_outils(("classement_candidatures", {"n": 1}))
    texte, trace = agent.repondre_agent(serveur.client(), index, "x", tours_max=4)
    assert "reformulez" in texte
    assert trace.appels_modele == 4


# ---------------------------------------------------------------- l'approche guidée

def test_guide_une_reference_citee_est_comptee_par_le_code_sans_recherche(serveur):
    index, _ = index_simule(serveur)
    serveur.repondre("L'offre OFF-103 a reçu 21 candidatures.")
    texte, trace = agent.repondre_guide(serveur.client(), index, "Combien pour OFF-103 ?")
    chemins = [r.chemin for r in serveur.requetes[1:]]
    assert chemins == ["/api/chat"]  # pas d'embedding : aucune recherche
    contenu = serveur.requetes[1].corps["messages"][1]["content"]
    assert '"candidatures": 21' in contenu and "OFF-103" in contenu
    assert [o["nom"] for o in trace.outils] == ["compter_candidatures"]
    # Le modèle n'a aucun outil à appeler. (Mesuré : ollama 0.6.3 envoie toujours
    # « tools », ici une liste vide.)
    assert serveur.requetes[1].corps["tools"] == []


def test_guide_une_reference_inconnue_arrive_au_modele_comme_absente(serveur):
    index, _ = index_simule(serveur)
    serveur.repondre("L'offre OFF-999 n'existe pas.")
    agent.repondre_guide(serveur.client(), index, "Combien pour OFF-999 ?")
    assert "n'existe pas dans le portail" in serveur.requetes[1].corps["messages"][1]["content"]


def test_guide_sinon_le_code_cherche_les_offres(serveur):
    index, question = index_simule(serveur, question_proche_de=0)
    serveur.vecteurs(question)
    serveur.repondre("OFF-101.")
    _, trace = agent.repondre_guide(serveur.client(), index, "Java à Lyon ?")
    assert [o["nom"] for o in trace.outils] == ["rechercher_offres"]
    assert serveur.requetes[2].corps["messages"][1]["content"].count('"reference"') == 5


def test_guide_la_regle_de_classement_ne_connait_que_la_formulation_du_banc():
    assert agent.CLASSEMENT.search("Quelle offre a reçu le plus de candidatures ?")
    assert not agent.CLASSEMENT.search("Quelle offre attire le plus de candidats ?")  # le jeu de validation


def test_relier_ajoute_la_reference_d_une_offre_nommee_sans_elle():
    from jobportal.donnees import PAR_REFERENCE
    texte = agent.relier_references("L'offre Ingénieur IA a reçu 21 candidatures.", [PAR_REFERENCE["OFF-103"]])
    assert texte == "L'offre Ingénieur IA (OFF-103) a reçu 21 candidatures."


def test_relier_ne_touche_pas_une_offre_deja_citee_ni_une_offre_non_fournie():
    from jobportal.donnees import PAR_REFERENCE
    assert agent.relier_references("Ingénieur IA, OFF-103.", [PAR_REFERENCE["OFF-103"]]) == "Ingénieur IA, OFF-103."
    assert agent.relier_references("Ingénieur IA.", [PAR_REFERENCE["OFF-101"]]) == "Ingénieur IA."


def test_relier_un_titre_court_ne_s_accroche_pas_dans_un_titre_long():
    from jobportal.donnees import PAR_REFERENCE
    offres = [PAR_REFERENCE["OFF-115"], PAR_REFERENCE["OFF-101"]]  # « Développeur Java », « … senior »
    texte = agent.relier_references("Voici le Développeur Java senior.", offres)
    assert texte == "Voici le Développeur Java senior (OFF-101)."


def test_guide_relie_s_appuie_sur_les_sources_de_la_trace(serveur):
    index, _ = index_simule(serveur)
    serveur.repondre("L'offre Ingénieur IA en a reçu 21.")
    texte, trace = agent.repondre_guide_relie(serveur.client(), index, "Quelle offre a reçu le plus de candidatures ?")
    assert trace.sources == ["OFF-103", "OFF-108", "OFF-107"]  # le classement donné au modèle
    assert "(OFF-103)" in texte


# ---------------------------------------------------------------- le RAG

def test_le_rag_donne_au_modele_les_offres_trouvees(serveur):
    index, question = index_simule(serveur, question_proche_de=0)
    serveur.vecteurs(question)
    serveur.repondre("OFF-101.")
    texte, trace = agent.repondre_rag(serveur.client(), index, "Java à Lyon ?")
    contenu = serveur.requetes[2].corps["messages"][1]["content"]
    assert "OFF-101" in contenu and contenu.count('"reference"') == 5  # les cinq plus proches
    assert serveur.requetes[2].corps["messages"][0]["content"] == agent.SYSTEME_RAG
    assert trace.appels_modele == 1
