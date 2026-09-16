"""Ce que chaque niveau garantit — et ce qu'il ne garantit pas.

Lancer :  uv run --extra dev pytest -q

La moitie de ces tests verifie des ECHECS. Un bac a sable dont on surestime
la portee est plus dangereux que pas de bac a sable du tout : on lui confie
ce qu'on ne lui confierait pas.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "outils"))

from jobportal.conteneur import (OBLIGATOIRES, commande, durcie,  # noqa: E402
                                 verifier)
from jobportal.evasions import CODE_HONNETE, EVASIONS             # noqa: E402
from jobportal.niveaux import (BUILTINS_AUTORISES, bornes_disponibles,  # noqa: E402
                               naif, processus, restreindre, restreint)
from evasion import ORDRE, accord, mesurer                        # noqa: E402


@pytest.fixture(scope="module")
def mesures():
    return mesurer()


def evasion(nom_partiel: str):
    return next(e for e in EVASIONS if nom_partiel in e.nom)


# --------------------------------------------------- le code honnete d'abord

@pytest.mark.parametrize("niveau", ORDRE)
def test_le_code_honnete_passe_a_tous_les_niveaux(niveau):
    """Une isolation qui casse l'usage legitime sera retiree dans la semaine.
    Ce test passe avant tous les autres, et ce n'est pas un hasard."""
    from jobportal.niveaux import NIVEAUX
    resultat = NIVEAUX[niveau](CODE_HONNETE)
    assert resultat.echappe, resultat.erreur
    assert resultat.sortie.strip().endswith("285")


# ------------------------------------------------------------- niveau 1

def test_sans_isolation_tout_passe(mesures):
    assert all(mesures[e.nom]["naif"] for e in EVASIONS)


# ------------------------------------------------------------- niveau 2

def test_le_restreint_arrete_open_et_import():
    assert not restreint("open('x')").echappe
    assert not restreint("import os").echappe


def test_le_restreint_tombe_en_six_lignes():
    """LE resultat du projet : on ne peut pas isoler Python depuis Python.
    Si ce test se met a echouer, ce n'est pas une bonne nouvelle — c'est que
    le corpus ne mord plus, et il faut le mettre a jour."""
    resultat = restreint(evasion("__subclasses__").code)
    assert resultat.echappe, "la remontee par l'arbre des classes doit passer"
    assert resultat.sortie, "et elle doit avoir obtenu quelque chose"


def test_la_liste_blanche_de_builtins_est_celle_qu_on_ecrit_vraiment():
    """Retirer « type » ne sauverait rien : « ().__class__ » y mene sans lui.
    Le test existe pour qu'on ne croie pas l'avoir corrige en l'enlevant."""
    assert "type" in BUILTINS_AUTORISES
    sans_type = evasion("__subclasses__").code
    assert "type(" not in sans_type, "l'evasion n'utilise pas « type »"


def test_le_restreint_ne_contient_rien():
    """Il retire des NOMS, il ne contient pas. Ce qui s'en echappe s'echappe
    dans le processus appelant — d'ou la mesure en sous-processus."""
    with pytest.raises(NameError):
        restreindre("open('x')")


# ------------------------------------------------------------- niveau 3

def test_le_processus_arrete_une_boucle_infinie():
    resultat = processus("while True:\n    pass", delai=1.0)
    assert not resultat.echappe
    assert "delai" in resultat.motif


def test_le_processus_ne_retire_AUCUN_nom():
    """Et c'est normal : il contient, il ne restreint pas. « import os » y
    marche, et c'est sans importance — le processus meurt avec son bac."""
    assert processus("import os; print(os.name)").echappe


def test_le_processus_ne_ferme_ni_le_reseau_ni_le_disque(mesures):
    """Ce que seul le conteneur apporte. Le savoir evite de croire qu'un
    sous-processus suffit."""
    assert mesures["ouverture d'une socket"]["processus"]
    assert mesures["ecriture sur le disque de l'hote"]["processus"]


def test_le_dossier_de_travail_est_jetable():
    """Pas une prison — un chemin absolu en sort — mais assez pour empecher
    le plus banal des accidents : ecrire dans le dossier du service."""
    resultat = processus("import os; print(os.getcwd())")
    assert resultat.echappe
    assert str(RACINE) not in resultat.sortie


def test_les_bornes_resource_sont_annoncees_honnetement():
    """Sous Windows elles n'existent pas. Le projet le DIT au lieu de laisser
    croire — c'est le defaut que ce cours denonce."""
    assert isinstance(bornes_disponibles(), bool)
    if sys.platform.startswith("win"):
        assert not bornes_disponibles()


# ----------------------------------------- le corpus dit-il encore vrai ?

@pytest.mark.parametrize("evasion_", EVASIONS, ids=lambda e: e.nom)
def test_le_niveau_annonce_tient_ce_qu_il_annonce(evasion_, mesures):
    assert accord(evasion_, mesures[evasion_.nom]), (
        f"« {evasion_.nom} » est annoncee arretee par « {evasion_.nommage} », "
        f"et ne l'est pas ici")


def test_les_niveaux_ne_sont_pas_une_echelle(mesures):
    """« restreint » arrete PLUS de lignes que « processus », et il est
    pourtant infiniment moins sur. Les deux ne font pas la meme chose."""
    arretees = {n: sum(1 for e in EVASIONS if not mesures[e.nom][n])
                for n in ORDRE}
    assert arretees["restreint"] > arretees["processus"]


# ------------------------------------------------------- le conteneur

def test_la_commande_generee_ne_manque_de_rien():
    assert verifier(commande("runner:python", "print(1)")) == []


def test_chaque_drapeau_obligatoire_est_rattache_a_une_evasion():
    """Un drapeau dont on ne sait pas ce qu'il empeche est un drapeau qu'on
    retire au premier probleme."""
    for drapeau, (retire, _) in OBLIGATOIRES.items():
        assert retire, drapeau


@pytest.mark.parametrize("drapeau", list(OBLIGATOIRES))
def test_retirer_un_drapeau_obligatoire_est_signale(drapeau):
    ligne = durcie(image="r", code="x").replace(drapeau.split("=")[0], "--zzz")
    assert any(s.drapeau == drapeau and s.gravite == "erreur"
               for s in verifier(ligne))


@pytest.mark.parametrize("contresens, motif", [
    ("docker run --rm --user root --network=none --read-only --cap-drop=ALL "
     "--security-opt=no-new-privileges --pids-limit=64 --memory=1m --cpus=1 i c",
     "--user"),
    ("docker run --rm --privileged --network=none --read-only --cap-drop=ALL "
     "--security-opt=no-new-privileges --pids-limit=64 --memory=1m --cpus=1 i c",
     "--privileged"),
    ("docker run --rm --network=host --read-only --cap-drop=ALL "
     "--security-opt=no-new-privileges --pids-limit=64 --memory=1m --cpus=1 i c",
     "--network"),
    ("docker run --rm -v /data:/data --network=none --read-only --cap-drop=ALL "
     "--security-opt=no-new-privileges --pids-limit=64 --memory=1m --cpus=1 i c",
     "-v"),
])
def test_un_drapeau_present_mais_neutralise_est_signale(contresens, motif):
    """Le plus difficile a voir en relecture : la commande a l'air durcie."""
    assert any(s.drapeau == motif and s.gravite == "erreur"
               for s in verifier(contresens)), verifier(contresens)


def test_une_pids_limit_trop_haute_est_signalee():
    ligne = durcie(image="r", code="x").replace("--pids-limit=64", "--pids-limit=4096")
    assert any("fork bomb" in s.message for s in verifier(ligne))


def test_gvisor_ne_change_que_le_runtime():
    sans = commande("r", "x")
    avec = commande("r", "x", runtime="runsc")
    assert "--runtime=runsc" in avec
    assert [a for a in avec if a != "--runtime=runsc"] == sans
