"""Compose : le graphe, l'interpolation, et la connexion refusee."""

from __future__ import annotations

from pathlib import Path

import pytest

from jobportal import compose

RACINE = Path(__file__).resolve().parent.parent
PILE = RACINE / "pile"


@pytest.fixture
def bonne() -> compose.Projet:
    projet, _ = compose.charger(PILE / "compose.yaml")
    return projet


@pytest.fixture
def naive() -> compose.Projet:
    projet, _ = compose.charger(PILE / "compose.naif.yaml")
    return projet


def test_le_nom_du_projet_vient_du_fichier(bonne):
    assert bonne.nom == "jobportal"
    assert bonne.reseau_par_defaut == "jobportal_default"


def test_les_dependances_sont_lues_sous_leurs_deux_formes(bonne, naive):
    assert bonne.services["app"].depend_de[0].condition == "service_healthy"
    assert bonne.services["app"].depend_de[0].attend_la_sante

    # ⚠️ La forme courte vaut `service_started`, et c'est tout le probleme.
    assert naive.services["app"].depend_de[0].condition == "service_started"
    assert not naive.services["app"].depend_de[0].attend_la_sante


def test_lordre_de_demarrage_est_topologique(bonne):
    ordre = compose.ordre(bonne)

    assert ordre.index("db") < ordre.index("app")
    assert set(ordre) == {"app", "db", "cache"}


def test_un_cycle_est_refuse():
    cyclique = compose.Projet("x", {
        "a": compose.Service("a", depend_de=[
            compose.Dependance("b", "service_started")]),
        "b": compose.Service("b", depend_de=[
            compose.Dependance("a", "service_started")]),
    })

    with pytest.raises(compose.ErreurCompose, match="cycle"):
        compose.ordre(cyclique)


def test_une_dependance_inexistante_est_refusee(tmp_path: Path):
    fichier = tmp_path / "compose.yaml"
    fichier.write_text("services:\n  a:\n    image: x\n    depends_on: [b]\n",
                       encoding="utf-8")

    with pytest.raises(compose.ErreurCompose, match="n'existe pas"):
        compose.charger(fichier)


def test_la_forme_courte_produit_une_connexion_refusee(naive):
    """⚠️ LA MESURE DU CHAPITRE 3."""
    evenements = compose.demarrer(naive)
    rates = compose.echecs(evenements)

    assert len(rates) == 1
    assert rates[0].service == "app"
    assert rates[0].instant < naive.services["db"].accepte_apres


def test_la_condition_service_healthy_attend_vraiment(bonne):
    evenements = compose.demarrer(bonne)

    assert compose.echecs(evenements) == []
    depart = [e for e in evenements
              if e.service == "app" and e.quoi == "conteneur cree"][0]
    assert depart.instant >= bonne.services["db"].accepte_apres


def test_le_healthcheck_passe_au_vert_au_tick_suivant(bonne):
    """⚠️ Pas a l'instant de la disponibilite : au tick d'apres."""
    base = bonne.services["db"]
    vert = compose.premier_vert(base.sante, base.accepte_apres)

    assert vert > base.accepte_apres
    assert vert - base.accepte_apres <= base.sante.intervalle
    assert vert % base.sante.intervalle == 0


def test_attendre_la_sante_dun_service_sans_healthcheck_leve(tmp_path: Path):
    fichier = tmp_path / "compose.yaml"
    fichier.write_text(
        "services:\n"
        "  a:\n    image: x\n    depends_on:\n      b:\n"
        "        condition: service_healthy\n"
        "  b:\n    image: y\n", encoding="utf-8")
    projet, _ = compose.charger(fichier)

    with pytest.raises(compose.ErreurCompose, match="healthcheck"):
        compose.demarrer(projet)


def test_linterpolation_lit_le_env_et_les_defauts(bonne):
    app = bonne.services["app"]

    assert app.environnement["DB_PASSWORD"] == "mot-de-passe-factice-du-cours"
    assert app.environnement["SPRING_PROFILES_ACTIVE"] == "dev"
    assert "db:5432/jobportal" in app.environnement["DB_URL"]


def test_lenvironnement_lemporte_sur_le_fichier_env():
    projet, _ = compose.charger(PILE / "compose.yaml",
                                {"PROFIL": "production"})

    assert projet.services["app"].environnement[
        "SPRING_PROFILES_ACTIVE"] == "production"


def test_une_variable_absente_devient_une_chaine_vide():
    """⚠️ Compose demarre quand meme — c'est le service qui echouera."""
    manquantes: list[str] = []
    rendu = compose.interpoler("x-${ABSENTE}-y", {}, manquantes)

    assert rendu == "x--y"
    assert manquantes == ["ABSENTE"]


def test_expose_ne_publie_rien_ports_publie(bonne, naive):
    assert bonne.services["db"].ports_publies == []
    assert bonne.services["db"].exposes == [5432]
    assert naive.services["db"].ports_publies == [(5432, 5432)]


def test_les_durees_sont_lues_avec_leur_unite():
    assert compose._secondes("2s") == 2.0
    assert compose._secondes("500ms") == 0.5
    assert compose._secondes("1m") == 60.0
    with pytest.raises(compose.ErreurCompose):
        compose._secondes("bientot")
