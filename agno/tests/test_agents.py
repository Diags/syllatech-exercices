"""Ce que les agents Agno doivent garantir.

Lancer :  uv run --extra dev pytest -q

Aucun appel reseau, aucune cle : un `ModeleFactice` qui respecte le contrat
d'Agno tient lieu de fournisseur.
"""

from __future__ import annotations

import json

import pytest
from agno.agent import Agent
from agno.db.in_memory import InMemoryDb
from agno.models.response import ModelResponse

from jobportal.agents import (conseiller, conseiller_avec_memoire,
                              conseiller_documente, conseiller_outille, equipe)
from jobportal.connaissances import DOCUMENTS, INDEX, recherche
from jobportal.donnees import query, rechercher_offres, salaire_du_marche
from jobportal.modele import ModeleFactice, en_factice, modele


class Espion(ModeleFactice):
    """Le meme modele, qui garde ce qu'on lui envoie tour par tour."""

    def invoke(self, messages=None, **kwargs):
        if not hasattr(self, "vus"):
            self.vus = []
        self.vus.append(list(messages or []))
        return super().invoke(messages=messages, **kwargs)

    @property
    def envoye(self) -> str:
        return "\n".join(str(m.content) for m in self.vus[-1])


# ---------------------------------------------------- le contrat du modele

def test_invoke_doit_rendre_un_ModelResponse():
    """Le piege du fichier modele.py : rendre un dict produit
    « 'dict' object has no attribute 'role' », qui ne dit rien de la cause."""
    reponse = ModeleFactice().invoke(messages=[])
    assert isinstance(reponse, ModelResponse)
    assert reponse.role == "assistant"


def test_le_modele_factice_s_integre_a_un_agent():
    assert conseiller(ModeleFactice()).run("Bonjour").content


# ----------------------------------------------------------- les outils

def test_l_outil_expose_sa_docstring_et_son_schema():
    espion = ModeleFactice()
    conseiller_outille(espion).run("Le marche DevOps ?")
    assert set(espion.outils_recus) == {"rechercher_offres", "salaire_du_marche"}


def test_l_agent_se_sert_du_retour_de_l_outil():
    """LE test qui compte : un agent qui appelle bien ses outils mais dont la
    reponse ne depend pas de leur retour passe toute la plomberie."""
    resultat = conseiller_outille(ModeleFactice()).run("Le marche DevOps ?")
    reelles = json.loads(rechercher_offres("DevOps"))
    assert any(o.split(" — ")[0] in resultat.content for o in reelles)


def test_l_outil_choisi_depend_de_la_question():
    """Prendre tools[0] marche tant qu'il n'y a qu'un outil, puis devient
    faux en silence."""
    salaire = ModeleFactice()
    conseiller_outille(salaire).run("Quel salaire pour Python ?")
    assert salaire.appels == ["salaire_du_marche"]

    offres = ModeleFactice()
    conseiller_outille(offres).run("Quelles offres DevOps ?")
    assert offres.appels == ["rechercher_offres"]


def test_une_question_hors_sujet_ne_declenche_aucun_outil():
    """Sinon on ne pourrait pas mesurer ce qu'un appel d'outil coute."""
    hors_sujet = ModeleFactice()
    conseiller_outille(hors_sujet).run("Bonjour, comment vas-tu ?")
    assert hors_sujet.appels == []


def test_le_raisonnement_est_un_outil_pas_un_modele():
    avec = ModeleFactice()
    conseiller_outille(avec, avec_raisonnement=True).run("Le marche DevOps ?")
    assert "think" in avec.outils_recus
    sans = ModeleFactice()
    conseiller_outille(sans).run("Le marche DevOps ?")
    assert "think" not in sans.outils_recus


# ------------------------------------------------------ les connaissances

def test_le_retriever_a_la_signature_qu_agno_attend():
    resultats = recherche(agent=None, query="teletravail", num_documents=2)
    assert isinstance(resultats, list) and resultats
    assert set(resultats[0]) >= {"titre", "contenu"}


@pytest.mark.parametrize("question, attendu", [
    ("Combien de jours de teletravail ?", "Politique de teletravail"),
    ("prime de cooptation", "Cooptation"),
    ("periode d'essai cadre", "Periode d'essai"),
])
def test_la_recherche_lexicale_trouve_ce_qui_partage_ses_mots(question, attendu):
    assert recherche(query=question, num_documents=1)[0]["titre"] == attendu


def test_la_recherche_lexicale_rate_ce_qui_n_a_aucun_mot_commun():
    """La limite qu'un embedding comble. La demontrer vaut mieux que
    l'affirmer : c'est la vraie raison d'etre d'un LanceDb."""
    trouves = recherche(query="Que touche-t-on en recommandant quelqu'un ?",
                        num_documents=1)
    assert not trouves or trouves[0]["titre"] != "Cooptation"


def test_bm25_ne_privilegie_pas_le_document_le_plus_long():
    plus_long = max(range(len(DOCUMENTS)), key=lambda i: len(DOCUMENTS[i][1]))
    resultats = INDEX.chercher("cooptation prime", 1)
    assert resultats[0]["titre"] != DOCUMENTS[plus_long][0]


def test_l_agent_documente_cherche_avant_de_repondre():
    espion = ModeleFactice()
    conseiller_documente(espion).run("Combien de jours de teletravail ?")
    assert espion.appels == ["search_knowledge_base"]


def test_la_recherche_recoit_la_question_entiere_pas_un_mot_cle():
    """Reduire « combien de jours de teletravail » a « teletravail » perd
    justement ce qu'on cherchait."""
    resultat = conseiller_documente(ModeleFactice()).run(
        "Combien de jours de teletravail par semaine ?")
    assert "Trois jours" in resultat.content


# ------------------------------------------------ memoire et session

def test_enable_user_memories_n_existe_plus():
    """Le parametre du cours. Un test, pour que personne ne cherche ailleurs."""
    with pytest.raises(TypeError, match="enable_user_memories"):
        Agent(model=ModeleFactice(), enable_user_memories=True)


def test_l_historique_grossit_a_chaque_tour():
    espion = Espion()
    agent = conseiller_avec_memoire(espion, InMemoryDb())
    tailles = []
    for question in ("Je cherche un poste DevOps", "Et en Python ?", "Et en Java ?"):
        agent.run(question, user_id="u", session_id="s1")
        tailles.append(len(espion.envoye))
    assert tailles[0] < tailles[1] < tailles[2]


def test_les_memoires_survivent_a_la_session():
    base = InMemoryDb()
    conseiller_avec_memoire(ModeleFactice(), base).run(
        "Je cherche un poste DevOps", user_id="u", session_id="s1")

    neuf = Espion()
    conseiller_avec_memoire(neuf, base).run(
        "Que sais-tu de moi ?", user_id="u", session_id="s2")
    memoires = [m.memory for m in base.get_user_memories(user_id="u")]
    assert memoires
    assert any(m in neuf.envoye for m in memoires)


def test_les_memoires_sont_cloisonnees_par_utilisateur():
    """Une fuite de donnees personnelles, pas un detail de confort."""
    base = InMemoryDb()
    conseiller_avec_memoire(ModeleFactice(), base).run(
        "Je cherche un poste DevOps", user_id="alice", session_id="s1")

    autre = Espion()
    conseiller_avec_memoire(autre, base).run(
        "Que sais-tu de moi ?", user_id="bob", session_id="s2")
    memoires = [m.memory for m in base.get_user_memories(user_id="alice")]
    assert memoires and all(m not in autre.envoye for m in memoires)


def test_un_historique_ne_traverse_pas_les_sessions():
    espion = Espion()
    base = InMemoryDb()
    agent = conseiller_avec_memoire(espion, base)
    agent.run("Je cherche un poste DevOps a Lyon", user_id="u", session_id="s1")
    premier = len(espion.envoye)
    agent.run("Bonjour", user_id="u", session_id="s2")
    assert "Lyon" not in espion.envoye or len(espion.envoye) < premier * 2


# --------------------------------------------------------- les equipes

def test_l_equipe_delegue_a_un_membre_reel():
    """Le coordinateur delegue par IDENTIFIANT derive du nom. Deleguer au nom
    echoue avec « Member with ID ... not found »."""
    resultat = equipe(ModeleFactice()).run("Le marche DevOps ?")
    assert "not found" not in str(resultat.content)


def test_l_equipe_cite_une_offre_reelle():
    resultat = equipe(ModeleFactice()).run("Quelles offres DevOps ?")
    reelles = json.loads(rechercher_offres("DevOps"))
    assert any(o.split(" — ")[0] in str(resultat.content) for o in reelles)


def test_une_equipe_coute_plus_qu_un_agent_seul():
    class Compteur(ModeleFactice):
        total = 0

        def invoke(self, **kwargs):
            Compteur.total += 1
            return super().invoke(**kwargs)

    Compteur.total = 0
    conseiller_outille(Compteur()).run("Le marche DevOps ?")
    seul = Compteur.total

    Compteur.total = 0
    equipe(Compteur()).run("Le marche DevOps ?")
    assert Compteur.total > seul


# --------------------------------------------------------- les donnees

def test_la_base_est_deterministe():
    assert query("DevOps") == query("DevOps")


def test_la_recherche_trouve_par_competence_aussi():
    """« Kubernetes » n'est dans aucun titre : il est dans les competences."""
    trouves = query("Kubernetes")
    assert trouves and all("Kubernetes" not in o["titre"] for o in trouves)


def test_le_salaire_median_est_reel():
    assert "58k" in salaire_du_marche("Python")
    assert "aucune offre" in salaire_du_marche("COBOL")


# ------------------------------------------------------- le choix du modele

def test_sans_cle_le_factice_est_rendu(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert isinstance(modele(), ModeleFactice)
    assert en_factice()


def test_le_modele_passe_en_parametre_l_emporte(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    impose = ModeleFactice()
    assert modele(impose) is impose
