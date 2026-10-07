"""Ce que les agents type-safe doivent garantir.

Lancer :  uv run --extra dev pytest -q

Aucun appel reseau, aucune cle : `TestModel` verifie la plomberie,
`FunctionModel` simule un vrai comportement.
"""

from __future__ import annotations


import pytest
from pydantic import ValidationError
from pydantic_ai import Agent, UnexpectedModelBehavior, capture_run_messages
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.models.test import TestModel

from jobportal.agents import (Analyse, Deps, Recommandation, agent_conseil,
                              agent_offres, agent_personnalise, agent_strict)
from jobportal.donnees import DatabaseConn
from jobportal.graphe import SEUIL, conseiller, graphe
from jobportal.modele import modele, modele_conseiller, modele_diffuseur


@pytest.fixture
def db():
    return DatabaseConn()


@pytest.fixture
def deps(db):
    return Deps(candidat_id=5, db=db)


async def combien(db: DatabaseConn) -> dict[int, int]:
    """Le nombre d'offres par candidat.

    `next(c for c in ... if await ...)` construit un generateur ASYNCHRONE, que
    `next()` refuse. On resout donc l'attente d'abord, on filtre ensuite.
    """
    return {c: len(await db.offres(c)) for c in db.noms}


# ------------------------------------------------- la sortie est validee

def test_la_sortie_est_du_type_declare():
    assert isinstance(agent_conseil(TestModel()).run_sync("x").output, Analyse)


@pytest.mark.parametrize("champs", [
    {"conseil": "Accepte", "risque": 42},     # hors bornes
    {"conseil": "Accepte", "risque": -1},
    {"conseil": "", "risque": 3},             # chaine vide
])
def test_une_sortie_hors_contrainte_est_refusee(champs):
    """Les contraintes ne sont pas de la documentation : elles s'executent."""
    with pytest.raises(ValidationError):
        Analyse(**champs)


def test_les_bornes_passent_dans_le_schema_envoye_au_modele():
    schema = Analyse.model_json_schema()["properties"]["risque"]
    assert schema["minimum"] == 0 and schema["maximum"] == 10


# -------------------------------------------------- deps et outils

async def test_l_outil_recoit_les_deps_de_l_execution(db):
    """Deux deps, deux resultats, avec le MEME agent."""
    agent = agent_offres(modele_conseiller())
    a = await agent.run("Mes offres ?", deps=Deps(3, db))
    b = await agent.run("Mes offres ?", deps=Deps(7, db))
    assert a.output.offres_citees != b.output.offres_citees


def test_le_modele_voit_la_docstring_et_le_schema_de_l_outil(deps):
    espion = TestModel()
    agent_offres(espion).run_sync("x", deps=deps)
    outil = espion.last_model_request_parameters.function_tools[0]
    assert outil.name == "offres_du_candidat"
    assert "offres suivies" in outil.description
    assert outil.parameters_json_schema["properties"]["seulement_actives"]["type"] == "boolean"


async def test_l_agent_se_sert_vraiment_du_retour_de_l_outil(deps, db):
    """Ce que TestModel ne peut PAS verifier : il appelle bien les outils,
    mais sa reponse finale ne depend pas de ce qu'ils ont rendu. Un agent qui
    ignore ses outils passe tous les tests de plomberie."""
    resultat = await agent_offres(modele_conseiller()).run("Mes offres ?", deps=deps)
    reelles = await db.offres(deps.candidat_id)
    assert resultat.output.offres_citees
    assert all(o in reelles for o in resultat.output.offres_citees)


# ------------------------------------------------ le validateur de sortie

async def test_une_offre_inventee_ne_sort_jamais_de_l_agent(deps):
    """Pydantic valide la FORME ; le validateur valide le SENS. Une offre
    inventee produit une sortie parfaitement valide au sens du schema."""

    def menteur(messages, info):
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {
            "resume": "voici", "offres_citees": ["Astronaute — Mars, 900k"],
            "confiance": 9})])

    with pytest.raises(UnexpectedModelBehavior):
        await agent_strict(FunctionModel(menteur)).run("Mes offres ?", deps=deps)


async def test_le_validateur_laisse_passer_les_vraies_offres(deps):
    resultat = await agent_strict(modele_conseiller()).run("Mes offres ?", deps=deps)
    assert isinstance(resultat.output, Recommandation)


async def test_le_message_de_reprise_arrive_au_modele(deps):
    """ModelRetry n'est pas une exception pour l'appelant : c'est une
    correction renvoyee au modele. On verifie qu'il la recoit."""
    vus = []

    def menteur(messages, info):
        vus.append(messages)
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {
            "resume": "x", "offres_citees": ["Inexistante"], "confiance": 1})])

    with pytest.raises(UnexpectedModelBehavior):
        await agent_strict(FunctionModel(menteur)).run("x", deps=deps)
    dernier = "".join(str(p) for m in vus[-1] for p in m.parts)
    assert "n'existent pas" in dernier


# ------------------------------------------ instructions dynamiques

def instructions(resultat) -> str:
    for message in resultat.all_messages():
        rendu = getattr(message, "instructions", None)
        if rendu:
            return rendu
    return ""


def test_les_instructions_dynamiques_varient_avec_les_deps(db):
    a = agent_personnalise(TestModel()).run_sync("x", deps=Deps(5, db))
    b = agent_personnalise(TestModel()).run_sync("x", deps=Deps(12, db))
    assert "Candidat05" in instructions(a)
    assert "Candidat12" in instructions(b)


def test_sans_decorateur_aucune_instruction_n_est_envoyee(deps):
    assert instructions(agent_offres(TestModel()).run_sync("x", deps=deps)) == ""


# ---------------------------------------------------- l'historique

def test_l_historique_ne_se_transporte_pas_tout_seul(deps):
    agent = agent_offres(modele_conseiller())
    r1 = agent.run_sync("Mes offres ?", deps=deps)
    sans = agent.run_sync("Et en DevOps ?", deps=deps)
    avec = agent.run_sync("Et en DevOps ?", deps=deps,
                          message_history=r1.new_messages())
    assert len(sans.all_messages()) == len(r1.all_messages())
    assert len(avec.all_messages()) > len(sans.all_messages())


# ---------------------------------------------------- le streaming

async def test_un_objet_partiel_est_deja_valide():
    """La difficulte reelle : a mi-chemin le JSON est INCOMPLET. On recoit
    quand meme un objet du bon type, avec ce qui est deja la."""
    from pydantic import BaseModel, Field

    class Rapport(BaseModel):
        titre: str = Field(min_length=1)
        points: list[str] = Field(default_factory=list)

    agent = Agent(modele_diffuseur(), output_type=Rapport)
    partiels = []
    async with agent.run_stream("x") as flux:
        async for partiel in flux.stream_output():
            partiels.append(partiel)

    assert all(isinstance(p, Rapport) for p in partiels)
    assert partiels[0].titre == "Marche D", "le premier morceau coupe un mot"
    assert partiels[-1].titre == "Marche DevOps 2026"
    assert len(partiels[-1].points) == 3


# ------------------------------------------------------- le graphe

def test_l_ancienne_construction_de_graphe_ne_marche_plus():
    """La video montre Graph(nodes=[...]). Un test, pour que personne ne
    perde une heure a se demander pourquoi."""
    from pydantic_graph import Graph
    with pytest.raises(TypeError):
        Graph(nodes=[])


def test_le_graphe_se_dessine_sans_s_executer():
    rendu = graphe.render()
    for nom in ("collecter", "analyser", "renoncer"):
        assert nom in rendu
    assert "<<choice>>" in rendu, "la decision doit apparaitre comme un choix"


async def test_un_candidat_actif_passe_par_analyser(db):
    candidat = next(c for c, n in (await combien(db)).items() if n >= SEUIL)
    _, etat = await conseiller(candidat, db, modele_conseiller())
    assert etat.etapes == ["collecter", "analyser"]
    assert etat.recommandation is not None


async def test_un_candidat_peu_actif_evite_le_modele(db):
    """La branche qui vaut de l'argent : aucune recommandation produite,
    donc aucun appel de modele."""
    candidat = next(c for c, n in (await combien(db)).items() if n < SEUIL)
    sortie, etat = await conseiller(candidat, db, modele_conseiller())
    assert etat.etapes == ["collecter", "renoncer"]
    assert etat.recommandation is None
    assert "trop peu" in sortie


async def test_les_deux_branches_sont_reellement_empruntees(db):
    """Un graphe dont une branche n'est jamais prise n'enseigne rien."""
    chemins = set()
    for candidat in db.noms:
        _, etat = await conseiller(candidat, db, modele_conseiller())
        chemins.add(etat.etapes[-1])
    assert chemins == {"analyser", "renoncer"}


# ------------------------------------------------------ la production

def test_les_messages_sont_capturables_sans_logfire(deps):
    with capture_run_messages() as messages:
        agent_offres(modele_conseiller()).run_sync("Mes offres ?", deps=deps)
    genres = [type(p).__name__ for m in messages for p in m.parts]
    assert "ToolCallPart" in genres and "ToolReturnPart" in genres


def test_l_usage_est_compte_a_chaque_run():
    resultat = Agent(TestModel(), output_type=str).run_sync("x")
    assert resultat.usage.requests >= 1
    assert resultat.usage.input_tokens > 0


def test_sans_cle_le_modele_factice_est_rendu(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert isinstance(modele(), TestModel)


def test_le_modele_passe_en_parametre_l_emporte_sur_le_defaut(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    impose = modele_conseiller()
    assert modele(impose) is impose


# -------------------------------------------------------- les donnees

async def test_la_base_est_deterministe():
    assert await DatabaseConn().offres(3) == await DatabaseConn().offres(3)


async def test_le_filtre_actives_reduit_bien_la_liste(db):
    candidat = next(c for c, n in (await combien(db)).items() if n >= 4)
    assert len(await db.offres(candidat, True)) <= len(await db.offres(candidat))


async def test_un_candidat_inconnu_leve_une_erreur_claire(db):
    with pytest.raises(KeyError, match="999"):
        await db.nom(999)
