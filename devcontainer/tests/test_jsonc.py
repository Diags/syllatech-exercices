"""Le lecteur JSONC — et surtout ce qu'il ne doit PAS toucher."""

from __future__ import annotations

import pytest

from jobportal import jsonc
from jobportal.commun import A_CORRIGER, PORTAIL


def test_un_commentaire_de_ligne():
    assert jsonc.charger_texte('{"a": 1} // fin') == {"a": 1}


def test_un_commentaire_de_bloc():
    assert jsonc.charger_texte('{/* note */ "a": 1}') == {"a": 1}


def test_un_commentaire_de_bloc_sur_plusieurs_lignes():
    assert jsonc.charger_texte('{\n/* une\n note */\n"a": 1}') == {"a": 1}


def test_une_url_n_est_pas_un_commentaire():
    """Le piege du lecteur ecrit a la va-vite : `//` dans une chaine."""
    texte = '{"cmd": "curl https://exemple.test//api"}'
    assert jsonc.charger_texte(texte)["cmd"] == "curl https://exemple.test//api"


def test_un_slash_etoile_dans_une_chaine():
    assert jsonc.charger_texte('{"a": "/* pas un commentaire */"}')["a"] \
        == "/* pas un commentaire */"


def test_un_guillemet_echappe():
    texte = r'{"a": "il a dit \"bonjour\" // pas un commentaire"}'
    assert jsonc.charger_texte(texte)["a"] \
        == 'il a dit "bonjour" // pas un commentaire'


def test_un_antislash_final_avant_le_guillemet():
    assert jsonc.charger_texte(r'{"a": "c:\\"}')["a"] == "c:\\"


@pytest.mark.parametrize("texte, attendu", [
    ('{"a": 1,}', {"a": 1}),
    ('{"a": [1, 2,]}', {"a": [1, 2]}),
    ('{"a": {"b": 1,},}', {"a": {"b": 1}}),
])
def test_les_virgules_finales_sont_tolerees(texte, attendu):
    assert jsonc.charger_texte(texte) == attendu


def test_une_virgule_dans_une_chaine_reste():
    assert jsonc.charger_texte('{"a": "x,"}')["a"] == "x,"


# ── le signalement ──────────────────────────────────────────────────────

def test_les_virgules_finales_sont_signalees():
    """`allowTrailingCommas: false` — on les tolere pour en parler."""
    assert jsonc.virgules_finales('{\n"a": 1,\n}') == [2]
    assert jsonc.virgules_finales('{"a": 1}') == []


def test_une_virgule_dans_une_chaine_n_est_pas_signalee():
    assert jsonc.virgules_finales('{"a": "x,]"}') == []


def test_une_virgule_dans_un_commentaire_n_est_pas_signalee():
    assert jsonc.virgules_finales('{"a": 1 // x,}\n}') == []


# ── sur les vrais fichiers ──────────────────────────────────────────────

def test_aucun_fichier_du_projet_n_est_du_json_strict():
    """Tous portent des commentaires : c'est la mesure du chapitre 1."""
    fichiers = [PORTAIL / "devcontainer.json", *A_CORRIGER.glob("*.json")]
    assert fichiers
    for chemin in fichiers:
        texte = chemin.read_text(encoding="utf-8")
        assert jsonc.est_du_json_strict(texte) is False, chemin.name
        assert isinstance(jsonc.charger_texte(texte), dict)


def test_un_seul_fichier_porte_une_virgule_finale():
    avec = [p.name for p in sorted(A_CORRIGER.glob("*.json"))
            if jsonc.virgules_finales(p.read_text(encoding="utf-8"))]
    assert avec == ["12-virgule-finale.json"]


def test_le_devcontainer_du_portail_n_en_porte_pas():
    texte = (PORTAIL / "devcontainer.json").read_text(encoding="utf-8")
    assert jsonc.virgules_finales(texte) == []
