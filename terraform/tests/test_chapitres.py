"""Les six chapitres tournent, et disent toujours la meme chose.

Ce qui est verifie ici n'est pas « ca n'a pas plante » mais « la mesure
annoncee est bien celle qui s'affiche ». Un chapitre dont la narration se
desaccorde de sa mesure devient faux sans faire d'erreur.
"""

from __future__ import annotations

import io
import runpy
from contextlib import redirect_stdout
from pathlib import Path

import pytest

CHAPITRES = Path(__file__).resolve().parent.parent / "chapitres"

_SORTIES: dict[str, str] = {}


def executer(nom: str) -> str:
    if nom in _SORTIES:
        return _SORTIES[nom]
    capture = io.StringIO()
    with redirect_stdout(capture):
        runpy.run_path(str(CHAPITRES / nom), run_name="__main__")
    _SORTIES[nom] = capture.getvalue()
    return _SORTIES[nom]


@pytest.mark.parametrize("fichier, attendu", [
    ("chapitre_1_declaratif.py", "Plan: 3 to add, 0 to change, 0 to destroy."),
    ("chapitre_2_hcl.py", "for_each (par cle)"),
    ("chapitre_3_etat.py", "mot_de_passe"),
    ("chapitre_4_modules.py", "module.reseau_prod.reseau.ce"),
    ("chapitre_5_environnements.py", "dev.tfstate"),
    ("chapitre_6_production.py", "prevent_destroy"),
])
def test_chaque_chapitre_tourne(fichier: str, attendu: str):
    sortie = executer(fichier)

    assert attendu in sortie, f"{fichier} n'a pas affiche « {attendu} »"


def test_le_chapitre_1_montre_lidempotence():
    sortie = executer("chapitre_1_declaratif.py")

    assert "No changes. Your infrastructure matches the configuration." in sortie
    assert "(remplacement)" in sortie
    assert "force un remplacement" in sortie


def test_le_chapitre_2_mesure_lecart_for_each_count():
    """⚠️ La mesure qui tranche : 1 destruction contre 3."""
    sortie = executer("chapitre_2_hcl.py")

    assert "→ 1 detruite(s), 0 creee(s)" in sortie
    assert "→ 3 detruite(s), 2 creee(s)" in sortie
    assert "taille doit valoir small ou medium" in sortie


def test_le_chapitre_3_montre_le_verrou_et_la_perte_detat():
    sortie = executer("chapitre_3_etat.py")

    assert "l'etat est verrouille par « collegue »" in sortie
    assert "Objets reellement existants : 3" in sortie
    assert "adresses suivies : 3" in sortie


def test_le_chapitre_4_montre_quatre_ressources_pour_deux_appels():
    sortie = executer("chapitre_4_modules.py")

    assert "Plan: 4 to add, 0 to change, 0 to destroy." in sortie
    assert "reseau-jobportal-staging" in sortie


def test_le_chapitre_5_montre_lisolation():
    sortie = executer("chapitre_5_environnements.py")

    assert "dev    0 objets" in sortie
    assert "prod   3 objets" in sortie


def test_le_chapitre_6_montre_la_derive_et_le_refus():
    sortie = executer("chapitre_6_production.py")

    assert "Terraform refuse de la detruire" in sortie
    assert "image : 'jobportal:0.1.0' → 'jobportal:1.4.0'" in sortie


def test_les_six_chapitres_existent():
    fichiers = sorted(chemin.name for chemin in CHAPITRES.glob("chapitre_*.py"))

    assert len(fichiers) == 6
