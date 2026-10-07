"""Ce que les equipages doivent garantir.

Lancer :  uv run --extra dev pytest -q

Aucun appel reseau, aucune cle : un `BaseLLM` factice tient lieu de
fournisseur, et il se sert vraiment de ses outils.
"""

from __future__ import annotations

import json
from typing import ClassVar

import pytest
from crewai import Agent, Crew, Process, Task
from crewai.flow.flow import Flow, listen, start
from pydantic import ValidationError

from jobportal import console
from jobportal.donnees import query, rechercher_offres, salaire_du_marche
from jobportal.equipe import (Rapport, Tendance, chercheur, economiste,
                              equipe_hierarchique, equipe_outillee,
                              equipe_sequentielle, equipe_simple, equipe_typee,
                              redacteur)
from jobportal.flux import VeilleFlow
from jobportal.modele import (ModeleFactice, _outils_du_prompt,
                              _premier_collegue, _schema_du_prompt)


class Compteur(ModeleFactice):
    """`BaseLLM` est un modele Pydantic : un attribut de classe non annote y
    est refuse. D'ou le ClassVar — piege classique du sous-classement."""

    total: ClassVar[int] = 0

    def call(self, *a, **k):
        Compteur.total += 1
        return super().call(*a, **k)


def lancer(fabrique, sujet="DevOps"):
    modele = ModeleFactice()
    with console.sans_bruit():
        resultat = fabrique(modele).kickoff(inputs={"sujet": sujet})
    return modele, resultat


# ------------------------------------------------- le modele factice

def test_un_BaseLLM_suffit_sans_litellm():
    """`crewai.LLM(model='factice')` leverait ImportError : le coeur ne
    connait qu'une liste fermee de fournisseurs. `BaseLLM` est la porte."""
    assert ModeleFactice().model == "factice"


def test_crewai_LLM_refuse_un_modele_inconnu():
    from crewai import LLM
    with pytest.raises(ImportError, match="litellm"):
        LLM(model="factice/inexistant")


def test_les_outils_arrivent_par_le_PROMPT_pas_par_tools():
    """Le piege qui rend un agent muet : `tools` et `available_functions`
    arrivent vides, CrewAI decrit les outils dans le texte du prompt."""
    modele, _ = lancer(equipe_outillee)
    assert modele.outils_vus, "des outils ont bien ete vus"
    assert all(isinstance(n, str) for lot in modele.outils_vus for n in lot)


def test_le_nom_a_emettre_est_derive_du_libelle():
    """Ni le libelle @tool, ni le nom de la fonction Python."""
    modele, _ = lancer(equipe_outillee)
    assert modele.appels == ["recherche_doffres_internes"]
    assert rechercher_offres.name == "Recherche d'offres internes"


def test_le_gabarit_react_n_est_pas_pris_pour_une_observation():
    """Le prompt contient « Observation: the result of the action ». Le
    prendre pour un vrai retour fait conclure l'agent avant d'avoir rien
    appele — et la reponse cite le gabarit, ce qui ressemble a un resultat."""
    from jobportal.modele import _deja_appele, _retours
    gabarit = "Observation: the result of the action"
    assert not _deja_appele(gabarit)
    assert _retours(gabarit) == []
    assert _deja_appele('Observation: ["une offre"]')


def test_le_schema_d_un_outil_est_relu_dans_le_prompt():
    prompt = ('Tool Name: delegate_work_to_coworker\nTool Arguments: {'
              '"required": ["task", "context", "coworker"]}')
    assert _schema_du_prompt("delegate_work_to_coworker", prompt) == [
        "task", "context", "coworker"]
    assert _schema_du_prompt("inconnu", prompt) == []


def test_le_collegue_est_lu_dans_la_description():
    prompt = "coworkers: Analyste du marche, Redacteur\nautre chose"
    assert _premier_collegue(prompt) == "Analyste du marche"


def test_les_outils_du_prompt_sont_extraits():
    assert _outils_du_prompt("Tool Name: a_b\nx\nTool Name: c_d") == ["a_b", "c_d"]


# ------------------------------------------------------- les agents

def test_deux_agents_ne_sont_pas_deux_clones():
    a, b = chercheur(), redacteur()
    assert a.role != b.role and a.goal != b.goal and a.backstory != b.backstory


def test_le_role_apparait_dans_la_reponse():
    """La promesse de CrewAI : des specialistes, pas des clones."""
    _, resultat = lancer(equipe_simple)
    assert chercheur().role in str(resultat)


def test_les_outils_se_donnent_par_agent():
    """Le moindre privilege applique aux agents : l'economiste n'a pas besoin
    de la recherche d'offres, et ne l'a pas."""
    assert len(chercheur(outils=True).tools) == 2
    assert [o.name for o in economiste().tools] == ["Salaire median du marche"]
    assert chercheur().tools == []


# ------------------------------------------------------- la sortie typee

def test_la_sortie_typee_est_un_modele_pydantic():
    _, resultat = lancer(equipe_typee)
    assert isinstance(resultat.pydantic, Rapport)
    assert resultat.pydantic.tendances


@pytest.mark.parametrize("impact", [0, 6, 42])
def test_un_impact_hors_bornes_est_refuse(impact):
    with pytest.raises(ValidationError):
        Tendance(titre="x", impact=impact, source="y")


def test_les_bornes_partent_dans_le_schema():
    champ = Tendance.model_json_schema()["properties"]["impact"]
    assert champ["minimum"] == 1 and champ["maximum"] == 5


# ------------------------------------------------------------ les outils

def test_l_agent_cite_une_offre_reelle():
    """Un agent qui appelle bien ses outils mais dont la reponse ne depend
    pas de leur retour passe toute la plomberie."""
    _, resultat = lancer(equipe_outillee)
    reelles = json.loads(rechercher_offres.run(mot_cle="DevOps"))
    assert any(o.split(" — ")[0] in str(resultat) for o in reelles)


def test_l_outil_choisi_depend_de_la_question():
    modele = ModeleFactice()
    agent = economiste(modele)
    tache = Task(description="Quel salaire pour {sujet} ?",
                 expected_output="Un chiffre", agent=agent)
    with console.sans_bruit():
        Crew(agents=[agent], tasks=[tache]).kickoff(inputs={"sujet": "Python"})
    assert modele.appels == ["salaire_median_du_marche"]


def test_la_base_est_deterministe():
    assert query("DevOps") == query("DevOps")


def test_le_salaire_median_est_reel():
    assert "52k" in salaire_du_marche.run(mot_cle="Python")
    assert "aucune offre" in salaire_du_marche.run(mot_cle="COBOL")


# ----------------------------------------------------- les processus

def test_le_contexte_circule_par_le_champ_context():
    """Sans `context=[...]`, la seconde tache repart de rien — et l'on
    obtient deux rapports independants sans qu'aucune erreur ne le dise."""
    _, resultat = lancer(equipe_sequentielle)
    assert redacteur().role in str(resultat)
    assert chercheur().role in str(resultat), "le rapport amont doit etre repris"


def test_un_hierarchique_coute_plus_qu_un_agent_seul():
    Compteur.total = 0
    with console.sans_bruit():
        equipe_outillee(Compteur()).kickoff(inputs={"sujet": "DevOps"})
    seul = Compteur.total

    Compteur.total = 0
    with console.sans_bruit():
        equipe_hierarchique(Compteur()).kickoff(inputs={"sujet": "DevOps"})
    assert Compteur.total > seul


def test_le_manager_delegue_vraiment():
    modele, resultat = lancer(equipe_hierarchique)
    assert "delegate_work_to_coworker" in modele.appels
    assert "error" not in str(resultat).lower(), (
        "une delegation ratee revient au modele comme une observation "
        "ordinaire, et la reponse cite alors le message d'erreur")


# ---------------------------------------------------------- les flows

def test_un_listen_ne_peut_pas_porter_le_nom_de_son_evenement():
    """Le code du chapitre 5 ne se construit pas sur CrewAI 1.x."""
    with pytest.raises(Exception, match="infinite loop"):
        class Mauvais(Flow):
            @start()
            def debut(self):
                return None

            @listen("publier")
            def publier(self):
                return None

        Mauvais()


def test_les_deux_branches_du_routeur_sont_empruntees():
    """Un routeur dont une branche ne sert jamais n'est pas un routeur."""
    chemins = []
    for vide in (False, True):
        flux = VeilleFlow(ModeleFactice(), "DevOps", collecte_vide=vide)
        with console.sans_bruit():
            flux.kickoff()
        chemins.append(flux.journal[-1])
    assert chemins == ["publier", "resoumettre"]


def test_la_branche_de_renoncement_n_appelle_aucun_agent():
    """C'est tout l'interet d'un routeur ecrit en Python : dans un crew, la
    meme decision serait prise par un modele, donc payee."""
    Compteur.total = 0
    flux = VeilleFlow(Compteur(), "DevOps", collecte_vide=True)
    with console.sans_bruit():
        flux.kickoff()
    assert Compteur.total == 0


def test_le_routeur_decide_sans_modele():
    flux = VeilleFlow(ModeleFactice(), "DevOps")
    flux.state["rapport"] = Rapport(tendances=[], resume="")
    assert flux.evaluer() == "resoumettre"
    flux.state["rapport"] = Rapport(
        tendances=[Tendance(titre="x", impact=3, source="y")], resume="")
    assert flux.evaluer() == "publier"


# --------------------------------------------------------- le paquet

def test_crewai_tools_est_un_paquet_separe():
    """Le chapitre 3 l'importe sans le dire : « crewai » ne le tire pas."""
    with pytest.raises(ModuleNotFoundError):
        import crewai_tools      # noqa: F401
