"""Ce que l'observabilite doit garantir.

Lancer :  uv run --extra dev pytest -q

Le SDK Langfuse est REEL : seul l'exportateur est local. Ce qui est teste ici
est donc ce que le serveur recevrait, pas une imitation.
"""

from __future__ import annotations

import json

import pytest
from langfuse import observe
from opentelemetry import trace

from jobportal import donnees
from jobportal.assistant import repondre
from jobportal.collecteur import PREFIXE, Collecteur, brancher
from jobportal.evaluation import (JEU_METIER, Registre, executer, score_juge,
                                  score_regle, score_utilisateur)
from jobportal.prompts import Depot, PromptIntrouvable


@pytest.fixture
def trace_locale():
    client, collecteur = brancher()
    yield client, collecteur
    client.flush()


# ------------------------------------------------- le SDK est bien reel

def test_le_decorateur_produit_un_span(trace_locale):
    client, collecteur = trace_locale

    @observe()
    def etape():
        return "fait"

    etape()
    client.flush()
    assert [o.nom for o in collecteur.observations] == ["etape"]


def test_les_attributs_sont_ceux_de_langfuse(trace_locale):
    """Si ce test tombe, c'est que le SDK a change de convention — et le
    projet ne mesure plus ce qu'il annonce."""
    client, collecteur = trace_locale
    repondre("Quelles offres DevOps ?", "diaguily", "s-1")
    client.flush()
    attributs = {c for o in collecteur.observations for c in o.attributs}
    assert f"{PREFIXE}observation.input" in attributs
    assert f"{PREFIXE}observation.output" in attributs
    assert f"{PREFIXE}observation.type" in attributs


def test_la_hierarchie_est_conservee(trace_locale):
    """Un enfant se TERMINE avant son parent, donc il est exporte avant lui.
    Resoudre la parente a l'export donnerait un arbre plat — et un arbre plat
    a l'air d'une trace sans hierarchie."""
    client, collecteur = trace_locale
    repondre("Quelles offres DevOps ?", "diaguily", "s-1")
    client.flush()
    arbre = collecteur.arbre()
    profondeurs = {o.nom: p for p, o in arbre}
    assert profondeurs["repondre"] == 0
    assert profondeurs["rechercher_contexte"] == 1
    assert profondeurs["generer"] == 1


def test_un_span_otel_brut_rejoint_la_meme_trace(trace_locale):
    """Les trois chemins d'integration produisent la MEME chose : des spans
    OTEL. C'est ce qui permet de tracer Spring et Python ensemble."""
    client, collecteur = trace_locale
    tracer = trace.get_tracer("test.maison")
    with tracer.start_as_current_span("etape-maison"):
        repondre("Quelles offres DevOps ?", "d", "s")
    client.flush()
    arbre = collecteur.arbre()
    assert arbre[0][1].nom == "etape-maison"
    assert arbre[0][0] == 0
    assert any(o.nom == "repondre" and p == 1 for p, o in arbre)


# ---------------------------------------------------- les generations

def test_une_generation_porte_le_modele_et_l_usage(trace_locale):
    client, collecteur = trace_locale
    repondre("Quelles offres DevOps ?", "d", "s")
    client.flush()
    generation = collecteur.generations()[0]
    assert generation.metadonnees["observation.model.name"] == "haiku"
    usage = json.loads(generation.metadonnees["observation.usage_details"])
    assert usage["input"] > 0 and usage["output"] > 0


def test_sans_as_type_le_span_n_est_pas_une_generation(trace_locale):
    """LE defaut du chapitre 2 : l'etape apparait dans la trace, au meme
    endroit, avec la meme duree — et n'entre pas dans le tableau des couts."""
    client, collecteur = trace_locale

    @observe()                          # as_type oublie
    def generer_mal():
        return "x"

    generer_mal()
    client.flush()
    assert collecteur.generations() == []
    assert collecteur.observations[0].genre == "span"


def test_le_trace_porte_l_identite(trace_locale):
    """user_id et session_id ne servent pas a la trace : ils servent a la
    RETROUVER."""
    client, collecteur = trace_locale
    repondre("Quelles offres DevOps ?", "diaguily", "s-42")
    client.flush()
    racine = collecteur.racines[0]
    assert "assistant-carriere" in str(racine.metadonnees.get("trace.tags", ""))


def test_le_cout_se_calcule_a_partir_de_l_usage():
    """C'est ce que Langfuse fait cote serveur. On le refait ici pour que le
    chiffre soit verifiable."""
    assert donnees.cout("haiku", 1_000_000, 0) == pytest.approx(0.25)
    assert donnees.cout("opus", 0, 1_000_000) == pytest.approx(75.0)
    assert donnees.cout("haiku", 100, 100) < donnees.cout("sonnet", 100, 100)


# ------------------------------------------------------- les prompts

def test_un_label_ne_pointe_que_sur_une_version():
    depot = Depot()
    depot.publier("p", "v1", labels={"production"})
    depot.publier("p", "v2", labels={"production"})
    etiquetees = [v.numero for v in depot.versions("p") if "production" in v.labels]
    assert etiquetees == [2]


def test_deplacer_un_label_change_la_production():
    """AUCUN redeploiement — et c'est aussi le danger : un prompt qui change
    sans passer par la revue de code."""
    depot = Depot()
    depot.publier("p", "premier")
    depot.publier("p", "second", labels={"production"})
    assert depot.get_prompt("p").numero == 2
    depot.etiqueter("p", 1, "production")
    assert depot.get_prompt("p").numero == 1


def test_une_variable_oubliee_reste_litterale():
    """Aucune erreur — juste un prompt qui parle d'une variable au lieu de sa
    valeur, et un modele qui fait de son mieux avec."""
    depot = Depot()
    version = depot.publier("p", "Tu conseilles {{portail}}.", labels={"prod"})
    assert version.compile() == "Tu conseilles {{portail}}."
    assert version.compile(portail="syllatech") == "Tu conseilles syllatech."


def test_les_variables_attendues_sont_lisibles():
    depot = Depot()
    version = depot.publier("p", "{{a}} et {{b}} et {{a}}")
    assert version.variables == {"a", "b"}


def test_un_label_inexistant_leve_une_erreur_explicite():
    depot = Depot()
    depot.publier("p", "x", labels={"production"})
    with pytest.raises(PromptIntrouvable, match="staging"):
        depot.get_prompt("p", label="staging")


# ---------------------------------------------------- les evaluations

def test_les_trois_scores_ne_mesurent_pas_la_meme_chose():
    reponse = "3 offre(s) : Ingenieur DevOps — Lyon — 52k"
    assert score_utilisateur(True) == 1.0
    assert score_regle(reponse, "DevOps") == 1.0
    assert score_regle(reponse, "COBOL") == 0.0
    assert 0.0 < score_juge(reponse, "Quelles offres DevOps ?") <= 1.0


def test_un_score_de_regle_est_deterministe():
    """C'est ce qui le rend utilisable en non-regression : le meme verdict
    aujourd'hui et dans six mois."""
    for _ in range(5):
        assert score_regle("abc DevOps", "devops") == 1.0


def test_le_dataset_attrape_le_cas_limite():
    """v1 rend « Rien. », v2 une phrase qui contient « Aucune ». C'est ce
    qu'un dataset attrape et qu'une relecture manque."""
    def v1(question):
        return " ; ".join(donnees.query(donnees.mot_cle(question))) or "Rien."

    def v2(question):
        offres = donnees.query(donnees.mot_cle(question))
        return (f"{len(offres)} offre(s) : " + " ; ".join(offres) if offres
                else "Aucune offre ne correspond.")

    assert executer("v1", v1).moyenne == 0.8
    assert executer("v2", v2).moyenne == 1.0


def test_le_dataset_couvre_un_cas_sans_resultat():
    """Un jeu de cas ou tout reussit ne mesure rien."""
    assert any(cas.attendu == "Aucune" for cas in JEU_METIER)


def test_le_registre_moyenne_par_nom():
    registre = Registre()
    registre.create_score("t1", "regle", 1.0)
    registre.create_score("t2", "regle", 0.0)
    registre.create_score("t3", "autre", 1.0)
    assert registre.moyenne("regle") == 0.5
    assert registre.moyenne("inconnu") == 0.0


# ------------------------------------------------------ le collecteur

def test_un_collecteur_neuf_est_vide():
    assert Collecteur().observations == []


def test_vider_remet_a_zero(trace_locale):
    client, collecteur = trace_locale
    repondre("x", "d", "s")
    client.flush()
    assert collecteur.observations
    collecteur.vider()
    assert collecteur.observations == []


def test_la_base_est_deterministe():
    assert donnees.query("DevOps") == donnees.query("DevOps")
