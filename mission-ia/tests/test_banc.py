"""Le juge doit être juste avant de juger quoi que ce soit."""

from jobportal.banc import CAS, CAS_VALIDATION, nombres, noter
from jobportal.donnees import PAR_REFERENCE


def cas(identifiant):
    return next(c for c in CAS + CAS_VALIDATION if c["id"] == identifiant)


def test_le_jeu_de_validation_est_distinct_et_calcule_depuis_les_donnees():
    assert not {c["question"] for c in CAS} & {c["question"] for c in CAS_VALIDATION}
    assert cas("v-dev-bordeaux")["references"] == {"OFF-110", "OFF-121"}
    assert cas("v-cdi-marseille")["references"] == {"OFF-113", "OFF-119", "OFF-123"}
    assert cas("v-stage-data")["references"] == {"OFF-111"}
    assert cas("v-salaire-comptable")["references"] == {"OFF-119"}
    for c in CAS_VALIDATION:
        assert c.get("references", set()) <= set(PAR_REFERENCE)


def test_les_references_attendues_sont_calculees_depuis_les_donnees():
    assert cas("java-lyon")["references"] == {"OFF-101", "OFF-115", "OFF-124"}
    assert cas("data-a-distance")["references"] == {"OFF-107", "OFF-108"}
    assert cas("plus-de-candidatures")["references"] == {"OFF-103"}
    for c in CAS:
        assert c.get("references", set()) <= set(PAR_REFERENCE)  # aucune référence qui n'existe pas


def test_les_nombres_se_lisent_sous_toutes_leurs_formes():
    assert {58000, 72000} <= nombres("entre 58 000 et 72 000 € brut")
    assert {58000, 72000} <= nombres("de 58k€ à 72 k€")
    assert 21 in nombres("l'offre a reçu 21 candidatures")


def test_une_reponse_juste_est_jugee_juste():
    note = noter(cas("java-lyon"), "Trois offres : OFF-101, OFF-115 et OFF-124.")
    assert note["juste"] is True


def test_une_offre_oubliee_ou_inventee_fait_echouer():
    assert noter(cas("java-lyon"), "OFF-101 et OFF-115.")["juste"] is False
    note = noter(cas("java-lyon"), "OFF-101, OFF-115, OFF-124, et aussi OFF-103.")
    assert note["controles"]["aucune autre offre citée"] is False


def test_un_chiffre_faux_fait_echouer():
    assert noter(cas("salaire-ia"), "OFF-103 : de 58 000 à 72 000 €.")["juste"] is True
    assert noter(cas("salaire-ia"), "OFF-103 : de 55 000 à 70 000 €.")["juste"] is False


def test_un_refus_ne_cite_aucune_offre():
    assert noter(cas("meteo"), "Je ne peux pas répondre : je ne traite que les offres d'emploi.")["juste"]
    assert not noter(cas("meteo"), "Il fera beau. Voyez aussi OFF-101.")["juste"]


def test_reprendre_la_reference_de_la_question_n_est_pas_inventer():
    assert noter(cas("offre-inconnue"), "L'offre OFF-999 n'existe pas dans le portail.")["juste"]
    assert not noter(cas("offre-inconnue"), "OFF-999 n'existe pas, mais voyez OFF-101.")["juste"]
