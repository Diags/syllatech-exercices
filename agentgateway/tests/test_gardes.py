"""Les guardrails : l'action par défaut, les builtins, et la mesure.

⚠️ Les motifs des builtins sont ceux de ce projet, pas ceux d'agentgateway
(ils vivent dans son code Rust, et ne sont pas publiés). Ce fichier teste
donc le MÉCANISME et les valeurs par défaut — pas la qualité des motifs
amont.
"""

from __future__ import annotations

import pytest

from jobportal import gardes
from jobportal.commun import PORTAIL
from jobportal.config import charger

CARTE = "Paiement par 4539 1488 0343 6467, merci."
ANODIN = "Le candidat a trois ans d'experience."


def test_l_action_par_defaut_est_mask():
    constat = gardes.appliquer({"rules": [{"builtin": "creditCard"}]}, CARTE)
    assert constat.declenche is True
    assert constat.action == gardes.ACTION_PAR_DEFAUT == "mask"
    assert constat.bloque is False
    assert constat.masque is True
    assert "4539" not in constat.texte


def test_reject_bloque_et_ne_masque_pas():
    constat = gardes.appliquer(
        {"action": "reject", "rules": [{"builtin": "creditCard"}]}, CARTE)
    assert constat.bloque is True
    assert constat.texte == CARTE       # rien n'est transmis, donc rien masque


def test_un_texte_anodin_ne_declenche_pas():
    constat = gardes.appliquer(
        {"action": "reject", "rules": [{"builtin": "creditCard"}]}, ANODIN)
    assert constat.declenche is False


def test_un_motif_maison():
    constat = gardes.appliquer(
        {"action": "reject", "rules": [{"pattern": "[Cc]onfidentiel"}]},
        "Document Confidentiel — ne pas diffuser.")
    assert constat.declenche is True
    assert constat.motifs == ["pattern:[Cc]onfidentiel"]


@pytest.mark.parametrize("nom", ["ssn", "creditCard", "phoneNumber",
                                 "email", "caSin"])
def test_les_cinq_builtins_ont_un_motif(nom):
    assert gardes.BUILTINS[nom]


def test_un_builtin_inconnu_est_signale():
    """`credit_card` est ce qu'ecrit le support ; le schema ne le connait pas."""
    assert gardes.builtins_inconnus([{"builtin": "credit_card"}]) == ["credit_card"]
    assert gardes.builtins_inconnus([{"builtin": "creditCard"}]) == []


def test_un_builtin_inconnu_ne_declenche_jamais():
    """Le pire des deux mondes si le schema ne l'attrapait pas : une regle
    qui a l'air posee et qui ne filtre rien.
    """
    constat = gardes.appliquer(
        {"action": "reject", "rules": [{"builtin": "credit_card"}]}, CARTE)
    assert constat.declenche is False


# ── ou vivent les gardes ────────────────────────────────────────────────

def test_les_gardes_se_lisent_sous_policies_ai_promptguard():
    politiques = {"ai": {"promptGuard": {"request": [
        {"regex": {"action": "reject", "rules": [{"builtin": "email"}]}}]}}}
    assert len(gardes.gardes_de(politiques)) == 1
    assert gardes.gardes_de(politiques, "response") == []


def test_la_forme_du_support_ne_se_lit_pas():
    """`policies.promptGuard` — sans `ai`, et avec un objet au lieu d'une
    liste. Le schema le refuse ; ce lecteur ne trouve rien non plus.
    """
    politiques = {"promptGuard": {"request": {"regex": {"rules": []}}}}
    assert gardes.gardes_de(politiques) == []


def test_passer_un_texte_dans_les_gardes_d_une_route():
    route = charger(PORTAIL / "03-securite.yaml").routes()[0]
    constats = gardes.passer(route.politiques, CARTE)
    assert len(constats) == 1
    assert constats[0].bloque is True
    assert gardes.passer(route.politiques, ANODIN)[0].declenche is False


def test_la_route_du_portail_pose_bien_reject():
    route = charger(PORTAIL / "03-securite.yaml").routes()[0]
    bloc = gardes.gardes_de(route.politiques)[0]["regex"]
    assert bloc["action"] == "reject"
    assert gardes.builtins_inconnus(bloc["rules"]) == []


# ── la mesure ───────────────────────────────────────────────────────────

def test_la_mesure_compte_les_quatre_cas():
    bloc = {"action": "reject", "rules": [{"builtin": "creditCard"}]}
    corpus = [(CARTE, True), (ANODIN, False),
              ("Article 4539 1488 0343 6467 du code", False),
              ("Carte absente", True)]
    compte = gardes.mesurer(bloc, corpus)
    assert compte == {"vrai positif": 1, "faux positif": 1,
                      "vrai negatif": 1, "faux negatif": 1}
    assert sum(compte.values()) == len(corpus)


def test_un_garde_parfait_n_existe_pas_sur_ce_corpus():
    """Le point du chapitre 5 : le meme motif produit les deux fautes."""
    bloc = {"action": "reject", "rules": [{"builtin": "creditCard"}]}
    compte = gardes.mesurer(bloc, [
        ("Carte 4539 1488 0343 6467", True),
        ("Reference 4539 1488 0343 6467 du marche", False),
    ])
    assert compte["vrai positif"] == 1
    assert compte["faux positif"] == 1
