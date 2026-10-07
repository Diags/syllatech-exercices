"""Ce que le cours affirme, mesuré sur le vrai SDK `anthropic` (transport simulé).

Chaque test porte une phrase du cours. S'il échoue après une mise à jour du
SDK, c'est le cours qui doit changer.
"""

import anthropic
import pytest

from jobportal import assistant, donnees
from jobportal.fausse_api import FausseAPI, appel_outil, reflexion, texte


@pytest.fixture
def api():
    return FausseAPI()


# ------------------------------------------------------------ chapitre 1

def test_le_premier_bloc_n_est_pas_forcement_du_texte(api):
    api.repondre(reflexion(), texte("Il y a trois offres à Lyon."))
    reponse = api.client().messages.create(model=assistant.MODELE, max_tokens=16000,
                                           messages=[{"role": "user", "content": "x"}])
    with pytest.raises(AttributeError):
        reponse.content[0].text
    assert assistant.texte_de(reponse) == "Il y a trois offres à Lyon."


def test_demander_envoie_le_modele_le_systeme_et_la_question(api):
    api.repondre(texte("Bonjour"))
    assert assistant.demander(api.client(), "Quelles offres à Lyon ?") == "Bonjour"
    corps = api.requetes[0].corps
    assert corps["model"] == "claude-opus-5-5"
    assert corps["max_tokens"] == 16000
    assert corps["messages"] == [{"role": "user", "content": "Quelles offres à Lyon ?"}]
    assert corps["system"].startswith("Tu es l'assistant")


def test_un_refus_ne_se_lit_pas_comme_une_reponse(api):
    api.repondre(stop="refusal", stop_details={"type": "refusal", "category": "cyber", "explanation": None})
    assert assistant.demander(api.client(), "x") == "Je ne peux pas répondre à cette demande."


def test_l_api_est_sans_etat_tout_l_historique_repart(api):
    api.repondre(reflexion(), texte("Enchanté, Awa."))
    api.repondre(texte("Vous vous appelez Awa."))
    conversation = assistant.Conversation(api.client())
    conversation.envoyer("Je m'appelle Awa.")
    conversation.envoyer("Comment je m'appelle ?")
    second = api.requetes[1].corps["messages"]
    assert [m["role"] for m in second] == ["user", "assistant", "user"]
    # le bloc de réflexion repart avec le texte, tel quel
    assert [b["type"] for b in second[1]["content"]] == ["thinking", "text"]


# ------------------------------------------------------------ chapitre 2

def test_le_flux_arrive_par_morceaux_et_se_reconstitue(api):
    api.repondre(texte("Trois offres correspondent à votre recherche."))
    morceaux = []
    final = assistant.demander_en_flux(api.client(), "x", afficher=morceaux.append)
    assert len(morceaux) == 6
    assert "".join(morceaux) == "Trois offres correspondent à votre recherche."
    assert assistant.texte_de(final) == "".join(morceaux)
    assert api.requetes[0].corps["stream"] is True


def test_un_429_est_retente_deux_fois_par_le_sdk(api):
    for _ in range(3):
        api.echouer(429, "rate_limit_error")
    with pytest.raises(anthropic.RateLimitError):
        assistant.demander(api.client(), "x")
    assert len(api.requetes) == 3


def test_un_429_puis_un_succes_ne_se_voit_pas(api):
    api.echouer(429, "rate_limit_error")
    api.repondre(texte("ok"))
    assert assistant.demander(api.client(), "x") == "ok"
    assert len(api.requetes) == 2


def test_un_400_n_est_jamais_retente(api):
    api.echouer(400, "invalid_request_error")
    with pytest.raises(anthropic.BadRequestError):
        assistant.demander_sans_planter(api.client(), "x")
    assert len(api.requetes) == 1


def test_la_gestion_d_erreurs_rend_un_message_sur_un_429(api):
    for _ in range(3):
        api.echouer(429, "rate_limit_error")
    assert "sollicité" in assistant.demander_sans_planter(api.client(), "x")


def test_un_gros_max_tokens_sans_flux_est_refuse_avant_tout_envoi(api):
    with pytest.raises(ValueError, match="Streaming is required"):
        api.client().messages.create(model=assistant.MODELE, max_tokens=128000,
                                     messages=[{"role": "user", "content": "x"}])
    assert api.requetes == []


# ------------------------------------------------------------ chapitre 3

def test_la_boucle_renvoie_tous_les_resultats_dans_un_seul_message(api):
    api.repondre(appel_outil("t1", "rechercher_offres", {"mot_cle": "java"}),
                 appel_outil("t2", "compter_candidatures", {"reference": "OFF-101"}), stop="tool_use")
    api.repondre(texte("Deux offres Java ; OFF-101 a reçu 12 candidatures."))
    reponse = assistant.boucle_agentique(api.client(), "Offres Java et candidatures ?")
    assert reponse.startswith("Deux offres Java")
    assert len(api.requetes) == 2
    dernier = api.requetes[1].corps["messages"][-1]
    assert dernier["role"] == "user"
    assert [r["tool_use_id"] for r in dernier["content"]] == ["t1", "t2"]
    assert dernier["content"][1]["content"] == "12"


def test_une_erreur_d_outil_revient_au_modele_en_is_error(api):
    api.repondre(appel_outil("t1", "compter_candidatures", {"reference": "OFF-999"}), stop="tool_use")
    api.repondre(texte("Cette offre n'existe pas."))
    assistant.boucle_agentique(api.client(), "x")
    resultat = api.requetes[1].corps["messages"][-1]["content"][0]
    assert resultat["is_error"] is True
    assert "OFF-999" in resultat["content"]


def test_la_boucle_s_arrete_au_dela_de_tours_max(api):
    for i in range(3):
        api.repondre(appel_outil(f"t{i}", "rechercher_offres", {"mot_cle": "java"}), stop="tool_use")
    with pytest.raises(RuntimeError):
        assistant.boucle_agentique(api.client(), "x", tours_max=3)


# ------------------------------------------------------------ chapitre 4

def test_le_tool_runner_tire_le_schema_de_la_signature_et_de_la_docstring(api):
    api.repondre(texte("ok"))
    assistant.avec_tool_runner(api.client(), "x")
    outils = {o["name"]: o for o in api.requetes[0].corps["tools"]}
    assert set(outils) == {"rechercher_offres", "compter_candidatures"}
    schema = outils["rechercher_offres"]["input_schema"]
    assert schema["properties"]["mot_cle"]["type"] == "string"
    assert schema["required"] == ["mot_cle"]
    assert "par exemple « java »" in schema["properties"]["mot_cle"]["description"]
    assert schema["additionalProperties"] is False


def test_le_tool_runner_fait_la_boucle_a_votre_place(api):
    api.repondre(appel_outil("t1", "compter_candidatures", {"reference": "OFF-103"}), stop="tool_use")
    api.repondre(texte("OFF-103 a reçu 21 candidatures."))
    assert assistant.avec_tool_runner(api.client(), "x") == "OFF-103 a reçu 21 candidatures."
    assert len(api.requetes) == 2
    resultat = api.requetes[1].corps["messages"][-1]["content"][0]
    assert resultat["type"] == "tool_result" and "21" in str(resultat["content"])


def test_parse_rend_un_objet_valide_et_envoie_le_schema(api):
    api.repondre(texte('{"titre": "Ingénieur IA", "ville": "Lyon", "contrat": "CDI", '
                       '"competences": ["Python", "RAG"], "teletravail": false}'))
    fiche = assistant.extraire_fiche(api.client(), "Ingénieur IA à Lyon, CDI, Python et RAG, sur site.")
    assert isinstance(fiche, assistant.FicheOffre)
    assert fiche.competences == ["Python", "RAG"]
    format_ = api.requetes[0].corps["output_config"]["format"]
    assert format_["type"] == "json_schema"
    assert set(format_["schema"]["required"]) == {"titre", "ville", "contrat", "competences", "teletravail"}


# ------------------------------------------------------------ chapitre 5

def test_le_cache_est_pose_sur_le_prompt_systeme(api):
    api.repondre(texte("ok"))
    assistant.demander_avec_cache(api.client(), "x")
    bloc = api.requetes[0].corps["system"][0]
    assert bloc["cache_control"] == {"type": "ephemeral"}
    assert bloc["text"] == assistant.CONSIGNES


def test_le_prefixe_est_identique_d_un_appel_a_l_autre(api):
    api.repondre(texte("a"))
    api.repondre(texte("b"))
    assistant.demander_avec_cache(api.client(), "Première question")
    assistant.demander_avec_cache(api.client(), "Seconde question")
    assert api.requetes[0].corps["system"] == api.requetes[1].corps["system"]


def test_une_horloge_dans_le_prompt_systeme_change_le_prefixe(api, monkeypatch):
    import datetime as dt

    instants = iter([dt.datetime(2026, 10, 5, 9, 0, 0), dt.datetime(2026, 10, 5, 9, 0, 1)])

    class Horloge(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return next(instants)

    monkeypatch.setattr(assistant, "datetime", Horloge)
    api.repondre(texte("a"))
    api.repondre(texte("b"))
    assistant.demander_avec_horloge(api.client(), "x")
    assistant.demander_avec_horloge(api.client(), "x")
    assert api.requetes[0].corps["system"] != api.requetes[1].corps["system"]


def test_le_cout_se_calcule_depuis_usage(api):
    api.repondre(texte("a"), usage={"input_tokens": 50, "output_tokens": 300,
                                    "cache_creation_input_tokens": 0, "cache_read_input_tokens": 2000})
    reponse = assistant.demander_avec_cache(api.client(), "x")
    # 50 × 4 $ + 2 000 × 0,20 $ + 300 × 20 $, par million de jetons
    assert assistant.cout_en_dollars(reponse.usage) == pytest.approx(0.0066)


def test_un_lot_porte_un_custom_id_par_requete(api):
    api.repondre_brut({"id": "msgbatch_001", "type": "message_batch", "processing_status": "in_progress",
                       "request_counts": {"processing": 2, "succeeded": 0, "errored": 0, "canceled": 0,
                                          "expired": 0},
                       "created_at": "2026-10-05T09:00:00Z", "expires_at": "2026-10-06T09:00:00Z",
                       "ended_at": None, "cancel_initiated_at": None, "archived_at": None, "results_url": None})
    lot = assistant.resumer_en_lot(api.client(), donnees.OFFRES[:2])
    assert lot.processing_status == "in_progress"
    assert api.requetes[0].chemin == "/v1/messages/batches"
    assert [r["custom_id"] for r in api.requetes[0].corps["requests"]] == ["OFF-101", "OFF-102"]


# ------------------------------------------------------------ chapitre 6

def test_la_production_envoie_le_repli_l_effort_et_l_entete_beta(api):
    api.repondre(texte("ok"))
    assert assistant.demander_en_production(api.client(), "x") == "ok"
    requete = api.requetes[0]
    assert requete.corps["fallbacks"] == "default"
    assert requete.corps["output_config"] == {"effort": "medium"}
    assert "server-side-fallback-2026-07-01" in requete.entetes["anthropic-beta"]


def test_un_refus_en_production_dit_sa_categorie(api):
    api.repondre(stop="refusal", stop_details={"type": "refusal", "category": "cyber", "explanation": None})
    assert "cyber" in assistant.demander_en_production(api.client(), "x")


def test_le_client_de_production_retente_quatre_fois(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "cle-de-test")
    client = assistant.client_de_production()
    assert client.max_retries == 4
    assert client.timeout == 120.0
