"""La composition des SLA, et le decoupage d'un VPC."""

from __future__ import annotations

import pytest

from jobportal import disponibilite as d
from jobportal import reseau as r


# ── les SLA ──────────────────────────────────────────────────────────────

def test_en_serie_les_disponibilites_se_multiplient():
    """⚠️ LA MESURE DU CHAPITRE 1 : trois fois 99,9 % font 99,70 %."""
    chaine = d.Chaine("trois", [d.Composant(f"s{i}", 0.999) for i in (1, 2, 3)])

    assert chaine.disponibilite == pytest.approx(0.999 ** 3)
    assert chaine.disponibilite < 0.999
    assert d.panne_par_an(chaine.disponibilite) == pytest.approx(
        3 * d.panne_par_an(0.999), rel=0.01)


def test_une_chaine_est_toujours_pire_que_son_maillon_faible():
    chaine = d.Chaine("melange", [
        d.Composant("solide", 0.99999),
        d.Composant("fragile", 0.99),
    ])

    assert chaine.disponibilite < chaine.maillon_faible.effective
    assert chaine.maillon_faible.nom == "fragile"


def test_en_parallele_ce_sont_les_pannes_qui_se_multiplient():
    seul = d.Composant("web", 0.999)
    double = d.Composant("web", 0.999, repliques=2)
    triple = d.Composant("web", 0.999, repliques=3)

    assert (1 - double.effective) == pytest.approx((1 - seul.disponibilite) ** 2)
    assert (1 - triple.effective) == pytest.approx((1 - seul.disponibilite) ** 3)
    assert d.panne_par_an(double.effective) < 60          # moins d'une minute


def test_les_neuf():
    assert d.neuf(3) == pytest.approx(0.999)
    assert d.panne_par_an(d.neuf(3)) == pytest.approx(31557.6, rel=1e-6)
    with pytest.raises(d.ErreurDisponibilite):
        d.neuf(0)


def test_une_disponibilite_absurde_est_refusee():
    with pytest.raises(d.ErreurDisponibilite, match="hors de"):
        d.Composant("x", 1.5)
    with pytest.raises(d.ErreurDisponibilite, match="replique"):
        d.Composant("x", 0.99, repliques=0)
    with pytest.raises(d.ErreurDisponibilite, match="vide"):
        _ = d.Chaine("vide").disponibilite


@pytest.mark.parametrize("constatee, part", [
    (0.99995, 0.00),
    (0.9990, 0.10),
    (0.9800, 0.25),
    (0.9000, 1.00),
])
def test_le_bareme_de_remise(constatee: float, part: float):
    assert d.remise(constatee)[0] == part


def test_la_remise_ne_couvre_jamais_la_perte():
    """⚠️ Un SLA est un bareme de remise, pas une garantie de service."""
    incident = d.Incident(minutes=240, facture_mensuelle=4200,
                          chiffre_daffaires_par_heure=9000)

    assert incident.remise == pytest.approx(420.0)
    assert incident.perte == pytest.approx(36000.0)
    assert incident.reste_a_charge > incident.remise * 50


def test_la_duree_est_lisible():
    assert d.duree(0) == "0 s"
    assert d.duree(90) == "1 min 30 s"
    assert "h" in d.duree(d.panne_par_an(0.999))


# ── le reseau ────────────────────────────────────────────────────────────

def test_cinq_adresses_disparaissent_par_sous_reseau():
    """⚠️ Un /24 donne 251 adresses, pas 254."""
    assert r.SousReseau("x", r.reseau("10.0.0.0/24")).utilisables == 251
    assert r.SousReseau("x", r.reseau("10.0.0.0/28")).utilisables == 11
    assert r.SousReseau("x", r.reseau("10.0.0.0/16")).utilisables == 65531


def test_le_decoupage_donne_le_bon_nombre_de_sous_reseaux():
    assert len(r.decouper("10.0.0.0/16", 24)) == 256
    assert len(r.decouper("10.0.0.0/16", 20)) == 16
    assert len(r.decouper("10.0.0.0/16", 16)) == 1


def test_un_prefixe_plus_grand_que_le_vpc_est_refuse():
    with pytest.raises(r.ErreurReseau, match="PLUS GRAND"):
        r.decouper("10.0.0.0/16", 8)
    with pytest.raises(r.ErreurReseau, match="n'existe pas"):
        r.decouper("10.0.0.0/16", 40)
    with pytest.raises(r.ErreurReseau, match="illisible"):
        r.reseau("10.0.0.0/pas-un-prefixe")


def test_les_chevauchements_invisibles():
    assert r.chevauchent("10.0.0.0/16", "10.0.128.0/17")
    assert r.chevauchent("172.16.0.0/12", "172.20.0.0/16")
    assert not r.chevauchent("10.0.0.0/16", "10.1.0.0/16")


def test_un_sous_reseau_qui_chevauche_est_refuse():
    vpc = r.Vpc("x", r.reseau("10.0.0.0/16"))
    vpc.ajouter(r.SousReseau("a", r.reseau("10.0.0.0/20")))

    with pytest.raises(r.ErreurReseau, match="chevauche"):
        vpc.ajouter(r.SousReseau("b", r.reseau("10.0.8.0/24")))


def test_un_sous_reseau_hors_du_vpc_est_refuse():
    vpc = r.Vpc("x", r.reseau("10.0.0.0/16"))

    with pytest.raises(r.ErreurReseau, match="n'est pas"):
        vpc.ajouter(r.SousReseau("a", r.reseau("10.1.0.0/24")))


def test_deux_vpc_qui_se_chevauchent_ne_sappairent_pas():
    """⚠️ Le routage serait ambigu — et personne ne le voit venir."""
    prod = r.Vpc("prod", r.reseau("10.0.0.0/16"))
    rachat = r.Vpc("rachat", r.reseau("10.0.0.0/16"))
    partenaire = r.Vpc("partenaire", r.reseau("172.16.0.0/16"))

    possible, raison = r.appairable(prod, rachat)
    assert not possible
    assert "chevauchent" in raison
    assert r.appairable(prod, partenaire)[0]


def test_le_plan_couvre_toutes_les_zones():
    plan = r.planifier("jobportal", "10.0.0.0/16", ["a", "b", "c"])

    noms = [s.nom for s in plan.vpc.sous_reseaux]
    assert len(noms) == 6
    assert sum(1 for s in plan.vpc.sous_reseaux if s.public) == 3
    assert {s.zone for s in plan.vpc.sous_reseaux} == {"a", "b", "c"}
    assert plan.vpc.libres > 0


def test_un_sous_reseau_trop_petit_pour_un_cluster():
    petit = r.SousReseau("prive", r.reseau("10.0.0.0/24"))

    tient, besoin, disponibles = r.tiendrait(petit, pods_par_noeud=30,
                                             noeuds=12)
    assert not tient
    assert besoin == 372
    assert disponibles == 251
