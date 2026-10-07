"""Ce que la memoire temporelle doit garantir.

Lancer :  uv run --extra dev pytest -q

Le cœur de ces tests est l'INVALIDATION : un fait qui devient faux doit se
fermer, pas disparaitre. C'est ce qui separe Zep d'un magasin de souvenirs.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from jobportal.graphe import Fait, Graphe, extraire, maintenant
from jobportal.memoire import Memoire, MemoireNaive, Message


def le(annee: int, mois: int, jour: int) -> datetime:
    return datetime(annee, mois, jour, tzinfo=timezone.utc)


@pytest.fixture
def client() -> Memoire:
    memoire = Memoire()
    memoire.user.add(user_id="diaguily", first_name="Diaguily")
    memoire.thread.create(thread_id="t", user_id="diaguily")
    return memoire


def dire(client: Memoire, texte: str, quand: datetime, fil: str = "t"):
    return client.thread.add_messages(
        fil, [Message(role="user", content=texte, created_at=quand)])


# ------------------------------------------------------- l'extraction

def test_un_message_produit_plusieurs_faits():
    faits = extraire("Diaguily", "Je cherche du DevOps a Lyon en CDI")
    predicats = {f.predicat for f in faits}
    assert predicats == {"lieu", "contrat", "metier"}


def test_la_ville_est_reconnue_sans_preposition():
    """Exiger « a Lyon » ferait rater « finalement je prefere Lyon » — et
    c'est exactement la phrase qui doit invalider la precedente."""
    faits = extraire("D", "Finalement je prefere Lyon")
    assert [f.objet for f in faits] == ["lyon"]


def test_un_message_sans_fait_n_en_produit_aucun():
    assert extraire("D", "Bonjour, comment allez-vous ?") == []


# ------------------------------------------------- LE test du projet

def test_un_fait_nouveau_ferme_l_ancien():
    graphe = Graphe()
    graphe.ajouter_message("D", "Je cherche a Paris", le(2026, 3, 1))
    graphe.ajouter_message("D", "Finalement je prefere Lyon", le(2026, 7, 17))

    lieux = graphe.historique("D", "lieu")
    assert [f.objet for f in lieux] == ["paris", "lyon"]
    assert lieux[0].invalid_at == le(2026, 7, 17)
    assert lieux[1].valide


def test_un_fait_ferme_n_est_pas_supprime():
    """C'est ce qui permet de repondre a « pourquoi m'as-tu propose Paris
    en mars ? »."""
    graphe = Graphe()
    graphe.ajouter_message("D", "Je cherche a Paris", le(2026, 3, 1))
    graphe.ajouter_message("D", "Plutot Lyon", le(2026, 7, 17))
    assert len(graphe.faits) == 2
    assert len(graphe.valides("D")) == 1


def test_un_fait_identique_ne_ferme_rien():
    """Sinon repeter une preference la remettrait a zero, et l'on perdrait
    depuis quand elle tient."""
    graphe = Graphe()
    graphe.ajouter_message("D", "Je cherche a Lyon", le(2026, 1, 1))
    graphe.ajouter_message("D", "Toujours Lyon", le(2026, 2, 1))
    lieux = graphe.historique("D", "lieu")
    assert len(lieux) == 2
    assert lieux[0].valide, "le premier reste ouvert"
    assert lieux[0].valid_at == le(2026, 1, 1)


def test_deux_predicats_differents_ne_se_ferment_pas():
    """Changer de ville n'efface pas le salaire vise. Un extracteur qui
    melangerait les predicats ferait disparaitre des faits a chaque message."""
    graphe = Graphe()
    graphe.ajouter_message("D", "Je vise 55k a Paris", le(2026, 1, 1))
    graphe.ajouter_message("D", "Plutot Lyon", le(2026, 2, 1))
    valides = {f.predicat: f.objet for f in graphe.valides("D")}
    assert valides["lieu"] == "lyon"
    assert valides["salaire"] == "55"


def test_une_ingestion_dans_le_desordre_ne_produit_pas_d_intervalle_inverse():
    """« valide du 17 juillet au 1er mars » n'est pas une donnee bizarre :
    il rend toute lecture a une date passee fausse, pour toujours, sans
    lever la moindre erreur."""
    graphe = Graphe()
    graphe.ajouter_message("D", "Finalement Lyon", le(2026, 7, 17))
    graphe.ajouter_message("D", "Je cherche a Paris", le(2026, 3, 1))
    for fait in graphe.faits:
        if fait.invalid_at:
            assert fait.invalid_at > fait.valid_at, str(fait)
    lieux = graphe.historique("D", "lieu")
    assert [f.objet for f in lieux] == ["paris", "lyon"]
    assert lieux[1].valide


# ------------------------------------------------- la lecture datee

def test_on_retrouve_ce_qu_on_croyait_a_une_date():
    graphe = Graphe()
    graphe.ajouter_message("D", "Je cherche a Paris", le(2026, 3, 1))
    graphe.ajouter_message("D", "Plutot Lyon", le(2026, 7, 17))

    en_mai = [f.objet for f in graphe.a_la_date("D", le(2026, 5, 1))
              if f.predicat == "lieu"]
    en_aout = [f.objet for f in graphe.a_la_date("D", le(2026, 8, 1))
               if f.predicat == "lieu"]
    assert en_mai == ["paris"]
    assert en_aout == ["lyon"]


def test_avant_le_premier_fait_on_ne_sait_rien():
    graphe = Graphe()
    graphe.ajouter_message("D", "Je cherche a Paris", le(2026, 3, 1))
    assert graphe.a_la_date("D", le(2026, 1, 1)) == []


# ------------------------------------------------ users et threads

def test_un_nouveau_fil_repart_d_un_historique_vide_et_de_la_meme_memoire(client):
    dire(client, "Je cherche du DevOps a Lyon", le(2026, 7, 1))
    client.thread.create(thread_id="jeudi", user_id="diaguily")

    assert client.threads["jeudi"].messages == []
    contexte = client.thread.get_user_context("jeudi")
    assert any("lyon" in f.texte for f in contexte.faits)


def test_deux_utilisateurs_ne_se_voient_pas(client):
    dire(client, "Je cherche a Lyon", le(2026, 7, 1))
    client.user.add(user_id="marie", first_name="Marie")
    client.thread.create(thread_id="m", user_id="marie")
    dire(client, "Je cherche a Nantes", le(2026, 7, 1), fil="m")

    faits_marie = client.thread.get_user_context("m").faits
    assert all("Marie" == f.sujet for f in faits_marie)
    assert not any("lyon" in f.texte for f in faits_marie)


def test_un_message_d_assistant_ne_nourrit_pas_la_memoire(client):
    """Extraire les mots de l'assistant ferait croire a l'agent qu'il a
    APPRIS ce qu'il vient de dire."""
    avant = len(client.graphe.faits)
    client.thread.add_messages("t", [
        Message(role="assistant", content="Je vous propose Bordeaux en freelance")])
    assert len(client.graphe.faits) == avant


# ------------------------------------------------ le bloc de contexte

def test_le_bloc_ne_contient_que_des_faits_valides(client):
    dire(client, "Je cherche a Paris", le(2026, 3, 1))
    dire(client, "Plutot Lyon", le(2026, 7, 17))
    contexte = client.thread.get_user_context("t").context
    assert "lyon" in contexte
    assert "paris" not in contexte


def test_le_bloc_plafonne_la_ou_l_historique_croit(client):
    """C'est la propriete qui compte a la centieme session."""
    naive = MemoireNaive()
    villes = ["Paris", "Lyon", "Nantes", "Bordeaux", "Lille", "Toulouse"]
    tailles = []
    for n, ville in enumerate(villes * 2, start=1):
        texte = f"Finalement je prefere {ville}"
        dire(client, texte, le(2026, 1, 1).replace(day=min(28, n)))
        naive.ajouter("diaguily", texte)
        tailles.append((len(client.thread.get_user_context("t").context),
                        len(naive.contexte("diaguily"))))

    bloc_final, histo_final = tailles[-1]
    assert bloc_final < histo_final
    assert max(b for b, _ in tailles) - min(b for b, _ in tailles[3:]) < 40, \
        "le bloc doit plafonner"


def test_un_utilisateur_inconnu_donne_un_bloc_vide():
    memoire = Memoire()
    memoire.user.add(user_id="neuf", first_name="Neuf")
    memoire.thread.create(thread_id="t", user_id="neuf")
    assert "aucun fait" in memoire.thread.get_user_context("t").context


# ------------------------------------------------- les faits metier

def test_un_fait_metier_entre_dans_le_meme_graphe(client):
    fait = client.graph.add("diaguily", {
        "event_type": "candidature_envoyee",
        "offre": "DevOps Senior — CloudCorp Lyon",
        "salaire_propose": 62000}, le(2026, 7, 20))
    assert fait.source == "json"
    assert "CloudCorp" in fait.texte and "62 k" in fait.texte
    assert fait in client.graphe.valides("Diaguily")


def test_la_recherche_ne_rend_que_des_faits_valides(client):
    """Chercher dans les faits fermes donnerait des reponses perimees avec
    l'assurance du present."""
    dire(client, "Je cherche a Lyon", le(2026, 3, 1))
    dire(client, "En fait Bordeaux", le(2026, 8, 1))
    trouves = client.graph.search("diaguily", "lieu du poste")
    assert trouves and all(f.valide for f in trouves)
    assert all("lyon" not in f.texte for f in trouves)


def test_la_recherche_rend_vide_quand_rien_ne_correspond(client):
    dire(client, "Je cherche a Lyon", le(2026, 3, 1))
    assert client.graph.search("diaguily", "cuisine moleculaire") == []


# --------------------------------------------- la memoire naive, en face

def test_la_memoire_naive_garde_les_deux_versions():
    """Elle donne au modele Paris ET Lyon sans dire lequel est actuel. Il
    choisit — jamais de facon stable."""
    naive = MemoireNaive()
    naive.ajouter("d", "Je cherche a Paris")
    naive.ajouter("d", "Finalement Lyon")
    contexte = naive.contexte("d")
    assert "Paris" in contexte and "Lyon" in contexte
