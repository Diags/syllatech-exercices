"""L'analyseur HCL, et ce qu'il refuse.

Un analyseur qui accepte tout ne prouve rien : la moitie de ces tests
verifie qu'une erreur de syntaxe s'arrete ici, avec un message qui nomme
la ligne.
"""

from __future__ import annotations

import pytest

from jobportal.evaluation import ErreurEvaluation, evaluer
from jobportal.hcl import Analyseur, ErreurHcl, Reference


def analyser(source: str):
    return Analyseur(source).analyser()


def test_un_bloc_avec_ses_etiquettes():
    blocs = analyser('resource "conteneur" "web" { nom = "a" }')

    assert len(blocs) == 1
    assert blocs[0].type == "resource"
    assert blocs[0].etiquettes == ["conteneur", "web"]
    assert blocs[0].attributs["nom"] == "a"


def test_les_blocs_imbriques():
    blocs = analyser("""
    variable "taille" {
      type = string
      validation {
        condition     = true
        error_message = "non"
      }
    }
    """)

    validation = blocs[0].enfant("validation")
    assert validation is not None
    assert validation.attributs["condition"] is True


def test_les_commentaires_sont_ignores():
    blocs = analyser("""
    # un commentaire
    resource "conteneur" "web" {   // un autre
      nom = "a"   # et encore un
    }
    """)

    assert blocs[0].attributs["nom"] == "a"


def test_une_interpolation_est_decoupee():
    blocs = analyser('resource "c" "w" { nom = "avant-${var.x}-apres" }')

    assert evaluer(blocs[0].attributs["nom"], {"var": {"x": "ICI"}}) \
        == "avant-ICI-apres"


def test_une_reference_simple_reste_une_reference():
    blocs = analyser('resource "c" "w" { nom = var.x }')

    assert isinstance(blocs[0].attributs["nom"], Reference)
    assert evaluer(blocs[0].attributs["nom"], {"var": {"x": "valeur"}}) \
        == "valeur"


def test_une_boucle_liste():
    blocs = analyser('output "o" { value = [for v in var.l : v] }')

    assert evaluer(blocs[0].attributs["value"],
                   {"var": {"l": ["a", "b"]}}) == ["a", "b"]


def test_une_boucle_objet():
    blocs = analyser(
        'output "o" { value = {for k, v in var.m : k => v} }')

    assert evaluer(blocs[0].attributs["value"],
                   {"var": {"m": {"a": 1}}}) == {"a": 1}


def test_une_indexation():
    blocs = analyser('output "o" { value = var.l[1] }')

    assert evaluer(blocs[0].attributs["value"],
                   {"var": {"l": ["a", "b"]}}) == "b"


def test_les_fonctions():
    blocs = analyser('output "o" { value = contains(["a", "b"], var.x) }')

    assert evaluer(blocs[0].attributs["value"], {"var": {"x": "a"}}) is True
    assert evaluer(blocs[0].attributs["value"], {"var": {"x": "z"}}) is False


def test_une_accolade_manquante_est_signalee():
    with pytest.raises(ErreurHcl, match="manquant"):
        analyser('resource "c" "w" { nom = "a"')


def test_un_caractere_inattendu_est_signale():
    with pytest.raises(ErreurHcl):
        analyser('resource "c" "w" { nom = @ }')


def test_une_reference_inconnue_leve():
    """⚠️ Le comportement qui evite les catastrophes silencieuses.

    Une variable mal orthographiee doit arreter le plan, pas produire un
    conteneur nomme « jobportal- » parce que la valeur etait vide.
    """
    blocs = analyser('resource "c" "w" { nom = var.inexistante }')

    with pytest.raises(ErreurEvaluation, match="introuvable"):
        evaluer(blocs[0].attributs["nom"], {"var": {}})


def test_une_fonction_inconnue_leve():
    blocs = analyser('output "o" { value = base64sha256("x") }')

    with pytest.raises(ErreurEvaluation, match="fonction inconnue"):
        evaluer(blocs[0].attributs["value"], {})
