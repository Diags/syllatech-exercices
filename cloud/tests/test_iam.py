"""Le moteur IAM : l'ordre d'evaluation, les jokers, les conditions."""

from __future__ import annotations

from pathlib import Path

import pytest

from jobportal import iam

POLITIQUES = Path(__file__).resolve().parent.parent / "politiques"

CATALOGUE = ["s3:GetObject", "s3:ListBucket", "s3:PutObject",
             "s3:DeleteObject", "s3:DeleteBucket", "s3:PutBucketPolicy",
             "iam:CreateUser", "ec2:RunInstances"]
CV = "arn:aws:s3:::cv-candidats/cv-001.pdf"


def charger(nom: str) -> iam.Politique:
    return iam.charger_fichier(POLITIQUES / f"{nom}.json")


# ── l'ordre d'evaluation ─────────────────────────────────────────────────

def test_rien_nest_permis_par_defaut():
    vide = iam.charger({"Statement": []}, "vide")

    verdict = iam.evaluer(vide, iam.Demande("s3:GetObject", CV))

    assert verdict.resultat == iam.REFUSE_IMPLICITEMENT
    assert not verdict.autorise


def test_un_allow_qui_correspond_autorise():
    politique = charger("lecture-seule-corrigee")

    assert iam.evaluer(politique, iam.Demande("s3:GetObject", CV)).autorise


def test_un_deny_explicite_lemporte_sur_tout():
    """⚠️ Meme sur un Allow « * » venu d'une autre politique."""
    administrateur = iam.charger({
        "Statement": [{"Sid": "tout", "Effect": "Allow",
                       "Action": "*", "Resource": "*"}]}, "admin")
    garde_fou = charger("garde-fou")
    journal = "arn:aws:s3:::journaux-audit/2026-09.log"

    assert iam.evaluer(administrateur,
                       iam.Demande("s3:DeleteObject", journal)).autorise
    verdict = iam.evaluer([administrateur, garde_fou],
                          iam.Demande("s3:DeleteObject", journal))
    assert verdict.resultat == iam.REFUSE_EXPLICITEMENT
    assert verdict.declaration.identifiant == "ProtegerLesJournaux"


def test_le_garde_fou_ne_deborde_pas_de_son_perimetre():
    administrateur = iam.charger({
        "Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}]},
        "admin")
    garde_fou = charger("garde-fou")

    assert iam.evaluer([administrateur, garde_fou],
                       iam.Demande("s3:DeleteObject", CV)).autorise


# ── la piece a conviction ────────────────────────────────────────────────

def test_la_politique_lecture_seule_accorde_la_suppression():
    """⚠️ LA MESURE DU CHAPITRE 3. Elle s'appelle « lecture seule »."""
    accordees = iam.actions_accordees(charger("lecture-seule"), CATALOGUE, CV)

    assert "s3:DeleteObject" in accordees
    assert "s3:DeleteBucket" in accordees
    assert "s3:PutBucketPolicy" in accordees
    assert len(accordees) == 6


def test_la_version_corrigee_naccorde_que_la_lecture():
    accordees = iam.actions_accordees(charger("lecture-seule-corrigee"),
                                      CATALOGUE, CV)

    # ⚠️ `s3:ListBucket` y figure parce que la politique le nomme ET
    # designe l'objet : le moteur applique le JSON, pas l'intention. AWS
    # limite `ListBucket` a l'ARN du bucket ; c'est une difference assumee,
    # documentee dans le README.
    assert accordees == ["s3:GetObject", "s3:ListBucket"]


def test_not_action_accorde_tout_le_reste():
    """⚠️ Une inversion, pas une exclusion."""
    accordees = iam.actions_accordees(charger("tout-sauf-iam"), CATALOGUE,
                                      "arn:aws:s3:::n-importe-quoi/x")

    assert "iam:CreateUser" not in accordees
    assert "ec2:RunInstances" in accordees
    assert "s3:DeleteBucket" in accordees
    assert len(accordees) == len(CATALOGUE) - 1


# ── les conditions ───────────────────────────────────────────────────────

def test_une_cle_absente_fait_echouer_la_condition():
    """⚠️ LE TROU DU CHAPITRE 3 : le Deny ne s'applique pas."""
    fautive = charger("sans-mfa")
    demande = iam.Demande("s3:PutObject", CV, {})

    assert iam.evaluer(fautive, demande).autorise


def test_if_exists_bouche_le_trou():
    corrigee = charger("sans-mfa-corrigee")
    demande = iam.Demande("s3:PutObject", CV, {})

    verdict = iam.evaluer(corrigee, demande)
    assert verdict.resultat == iam.REFUSE_EXPLICITEMENT


@pytest.mark.parametrize("contexte, avec_bool, avec_if_exists", [
    ({"aws:MultiFactorAuthPresent": True}, True, True),
    ({"aws:MultiFactorAuthPresent": False}, False, False),
    ({}, True, False),
])
def test_les_trois_cas_de_mfa(contexte, avec_bool, avec_if_exists):
    demande = iam.Demande("s3:PutObject", CV, contexte)

    assert iam.evaluer(charger("sans-mfa"), demande).autorise is avec_bool
    assert iam.evaluer(charger("sans-mfa-corrigee"),
                       demande).autorise is avec_if_exists


def test_la_condition_dadresse_source():
    politique = charger("depuis-le-bureau")

    dedans = iam.Demande("ec2:RunInstances", "*",
                         {"aws:SourceIp": "203.0.113.42"})
    dehors = iam.Demande("ec2:RunInstances", "*",
                         {"aws:SourceIp": "192.0.2.10"})

    assert iam.evaluer(politique, dedans).autorise
    assert not iam.evaluer(politique, dehors).autorise


# ── les jokers ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("motif, action, attendu", [
    ("s3:*", "s3:GetObject", True),
    ("s3:Get*", "s3:GetObject", True),
    ("s3:Get*", "s3:PutObject", False),
    ("*", "n-importe-quoi", True),
    ("S3:GETOBJECT", "s3:getobject", True),      # insensible a la casse
    ("s3:Get?bject", "s3:GetObject", True),
])
def test_les_jokers(motif: str, action: str, attendu: bool):
    politique = iam.charger({
        "Statement": [{"Effect": "Allow", "Action": motif,
                       "Resource": "*"}]}, "x")

    assert iam.evaluer(politique, iam.Demande(action, "x")).autorise is attendu


def test_le_joker_de_ressource_ne_traverse_pas_les_buckets():
    politique = iam.charger({
        "Statement": [{"Effect": "Allow", "Action": "s3:*",
                       "Resource": "arn:aws:s3:::cv-candidats/*"}]}, "x")

    assert iam.evaluer(politique, iam.Demande("s3:GetObject", CV)).autorise
    assert not iam.evaluer(
        politique,
        iam.Demande("s3:GetObject", "arn:aws:s3:::autre/x")).autorise


# ── ce que le moteur refuse ──────────────────────────────────────────────

@pytest.mark.parametrize("brut, motif", [
    ({"Statement": [{"Effect": "Peut-etre", "Action": "*", "Resource": "*"}]},
     "Allow ou Deny"),
    ({"Statement": [{"Effect": "Allow", "Action": "*", "NotAction": "x",
                     "Resource": "*"}]}, "ensemble"),
    ({"Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*",
                     "Condition": {"Bidule": {"a": "b"}}}]}, "operateur"),
    ({"Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*",
                     "Principal": "*"}]}, "Principal"),
    ({"Version": "2008-10-17", "Statement": []}, "version"),
    ({}, "sans « Statement »"),
])
def test_ce_qui_nest_pas_gere_leve(brut, motif):
    with pytest.raises(iam.ErreurIam, match=motif):
        iam.charger(brut)


def test_lexplication_nomme_la_declaration_qui_a_decide():
    politique = charger("sans-mfa")
    demande = iam.Demande("s3:PutObject", CV, {})

    lignes = iam.expliquer(iam.evaluer(politique, demande), demande)

    assert any("absente de la demande" in ligne for ligne in lignes)
    assert any("AccorderLeReste" in ligne for ligne in lignes)


def test_la_politique_du_developpeur():
    politique = charger("developpeur")
    essais = [
        ("s3:GetObject", CV, True),
        ("s3:PutObject", CV, False),
        ("s3:PutObject", "arn:aws:s3:::bac-a-sable/essai.txt", True),
        ("rds:DeleteDBInstance",
         "arn:aws:rds:eu-west-3:1:db:jobportal-prod", False),
    ]
    for action, ressource, attendu in essais:
        verdict = iam.evaluer(politique, iam.Demande(action, ressource))
        assert verdict.autorise is attendu, f"{action} sur {ressource}"
