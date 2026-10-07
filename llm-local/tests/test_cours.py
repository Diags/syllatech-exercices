"""Ce que le cours affirme sur les clients, mesuré sans Ollama : le vrai client
`ollama` (et le vrai client `openai`) sur un transport simulé."""

import json

import ollama
import openai
import pytest

from jobportal import assistant
from jobportal.donnees import ANNONCES, CONTRATS, MODES, OFFRES
from jobportal.fausse_ollama import FausseOllama
from jobportal.fiche import SCHEMA_FICHE, champs_justes, extraire_fiche


@pytest.fixture
def serveur():
    return FausseOllama()


# ---------------------------------------------------------------- chapitre 1

def test_demander_envoie_le_modele_les_consignes_et_la_question(serveur):
    serveur.repondre("Trois offres à Lyon.")
    assert assistant.demander(serveur.client(), "Quelles offres à Lyon ?") == "Trois offres à Lyon."
    requete = serveur.requetes[0]
    assert requete.chemin == "/api/chat"
    assert requete.corps["model"] == "qwen2.5:1.5b-instruct-q4_K_M"
    assert [m["role"] for m in requete.corps["messages"]] == ["system", "user"]
    assert requete.corps["stream"] is False  # le client désactive le flux, que le serveur active par défaut


def test_un_modele_absent_leve_une_response_error_404(serveur):
    serveur.echouer(404, "model 'mistral' not found")
    with pytest.raises(ollama.ResponseError) as erreur:
        assistant.demander(serveur.client(), "x", modele="mistral")
    assert erreur.value.status_code == 404


# ---------------------------------------------------------------- chapitre 2

def test_le_flux_arrive_par_morceaux_et_se_reconstitue(serveur):
    serveur.repondre("Trois offres correspondent à votre recherche.")
    morceaux = []
    texte = assistant.demander_en_flux(serveur.client(), "x", afficher=morceaux.append)
    assert texte == "Trois offres correspondent à votre recherche."
    assert len(morceaux) == 6 + 1  # un par mot, puis le dernier message, vide, qui porte les compteurs
    assert serveur.requetes[0].corps["stream"] is True


def test_la_sortie_structuree_envoie_le_schema_avec_ses_valeurs_permises(serveur):
    attendu = ANNONCES[0]["attendu"]
    serveur.repondre(json.dumps(attendu))
    fiche, _ = extraire_fiche(serveur.client(), "qwen2.5:1.5b-instruct-q4_K_M", ANNONCES[0]["texte"])
    assert fiche == attendu
    corps = serveur.requetes[0].corps
    assert corps["format"] == SCHEMA_FICHE
    assert corps["format"]["properties"]["contrat"]["enum"] == CONTRATS
    assert corps["format"]["properties"]["mode"]["enum"] == MODES
    assert corps["options"] == {"temperature": 0, "seed": 42}


def test_le_client_openai_parle_a_ollama_par_v1(serveur):
    serveur.repondre("Bonjour")
    assert assistant.demander_via_openai(serveur.client_openai(), "x") == "Bonjour"
    requete = serveur.requetes[0]
    assert requete.chemin == "/v1/chat/completions"
    assert requete.corps["model"] == "qwen2.5:1.5b-instruct-q4_K_M"


def test_le_client_openai_refuse_de_demarrer_sans_cle(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(openai.OpenAIError, match="Missing credentials"):
        openai.OpenAI(base_url="http://localhost:11434/v1")
    assert assistant.client_compatible_openai().api_key == "ollama"


def test_creer_un_assistant_envoie_la_base_les_consignes_et_les_reglages(serveur):
    serveur.repondre_brut({"status": "success"})
    assistant.creer_assistant(serveur.client())
    requete = serveur.requetes[0]
    assert requete.chemin == "/api/create"
    assert requete.corps["model"] == "assistant-portail"
    assert requete.corps["from"] == "qwen2.5:1.5b-instruct-q4_K_M"
    assert requete.corps["system"] == assistant.SYSTEME
    assert requete.corps["parameters"] == {"temperature": 0.2, "num_ctx": 8192}


# ---------------------------------------------------------------- chapitre 3

def _charge(modele: str, taille: int) -> dict:
    return {"models": [{"model": modele, "name": modele, "size": taille, "size_vram": 0,
                        "digest": "x", "expires_at": "2026-10-06T12:00:00Z", "context_length": 4096}]}


def test_la_vitesse_se_lit_dans_les_durees_d_ollama(serveur):
    serveur.repondre("…", eval_count=96, eval_duration=4_000_000_000, load_duration=2_500_000_000)
    serveur.repondre_brut(_charge("q4", 1_170_000_000))
    mesure = assistant.mesurer_vitesse(serveur.client(), "q4", "x")
    assert mesure == {"jetons_par_s": 24.0, "chargement_s": 2.5, "memoire_mo": 1170.0}
    assert serveur.requetes[0].corps["options"] == {"temperature": 0, "num_predict": 96}
    assert serveur.requetes[1].chemin == "/api/ps"


def test_la_comparaison_alterne_les_modeles_et_change_le_prompt(serveur):
    for _ in range(3):
        for modele, duree in (("q4", 3_000_000_000), ("q8", 6_000_000_000)):
            serveur.repondre("…", eval_count=96, eval_duration=duree)
            serveur.repondre_brut(_charge(modele, 1))
    medianes = assistant.comparer_quantizations(serveur.client(), ["q4", "q8"], "x", tours=3)
    assert medianes == {"q4": 32.0, "q8": 16.0}
    chats = [r.corps for r in serveur.requetes if r.chemin == "/api/chat"]
    assert [c["model"] for c in chats] == ["q4", "q8"] * 3  # en alternance, pas en blocs
    assert [c["messages"][0]["content"] for c in chats[::2]] == ["Essai 0. x", "Essai 1. x", "Essai 2. x"]


# ---------------------------------------------------------------- chapitre 4

def test_la_note_compte_les_champs_justes():
    attendu = ANNONCES[0]["attendu"]
    assert champs_justes(attendu, attendu) == 5
    assert champs_justes({**attendu, "ville": " lyon "}, attendu) == 5  # ni casse ni espaces
    assert champs_justes({**attendu, "salaire_max": 62}, attendu) == 4  # 62 au lieu de 62000
    assert champs_justes({}, attendu) == 0


def test_evaluer_parcourt_tout_le_banc(serveur):
    for annonce in ANNONCES:
        serveur.repondre(json.dumps(annonce["attendu"]))
    serveur.reponses[0] = ("chat", {**serveur.reponses[0][1],
                                    "texte": json.dumps({**ANNONCES[0]["attendu"], "mode": "sur site"})})
    assert assistant.evaluer(serveur.client(), "qwen2.5:1.5b-instruct-q4_K_M") == (59, 60)
    assert len(serveur.requetes) == len(ANNONCES) == 12


# ---------------------------------------------------------------- chapitre 5

def test_la_production_garde_le_modele_charge_et_fixe_le_contexte(serveur):
    serveur.repondre("ok")
    assistant.demander_en_production(serveur.client(), "x")
    corps = serveur.requetes[0].corps
    assert corps["keep_alive"] == "30m"
    assert corps["options"] == {"num_ctx": 8192, "temperature": 0.2}


def test_le_client_de_production_a_un_delai(serveur):
    assert assistant.client_de_production()._client.timeout.read == 120


# ---------------------------------------------------------------- chapitre 6

def test_indexer_envoie_une_offre_par_texte(serveur):
    serveur.vecteurs(*[[1.0, 0.0]] * len(OFFRES))
    index = assistant.indexer(serveur.client(), OFFRES)
    assert len(index) == len(OFFRES)
    corps = serveur.requetes[0].corps
    assert serveur.requetes[0].chemin == "/api/embed"
    assert corps["model"] == "bge-m3"
    assert corps["input"][0] == "Développeur Java senior chez Nordeau, CDI à Lyon, hybride"


def test_rechercher_classe_par_similarite_cosinus(serveur):
    index = [[1.0, 0.0], [0.0, 1.0], [0.7, 0.7]]
    serveur.vecteurs([0.0, 1.0])
    trouvees = assistant.rechercher(serveur.client(), "x", OFFRES[:3], index, k=2)
    assert [o["reference"] for o in trouvees] == ["OFF-102", "OFF-103"]


def test_le_rag_donne_au_modele_les_offres_trouvees(serveur):
    index = [[1.0, 0.0], [0.0, 1.0], [0.7, 0.7], [-1.0, 0.0]]
    serveur.vecteurs([1.0, 0.1])
    serveur.repondre("OFF-101 et OFF-103.")
    assert assistant.repondre_avec_rag(serveur.client(), "Java à Lyon ?", OFFRES[:4], index) == "OFF-101 et OFF-103."
    question = serveur.requetes[1].corps["messages"][-1]["content"]
    assert "OFF-101" in question and "OFF-103" in question and "OFF-102" in question
    assert "OFF-104" not in question  # la 4e offre, la plus éloignée, n'est pas donnée au modèle
