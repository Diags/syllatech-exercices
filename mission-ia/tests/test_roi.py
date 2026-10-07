import pytest

from jobportal.roi import Hypotheses, gain_mensuel, mois_pour_rembourser

# Des hypothèses d'exemple pour tester le calcul, pas des chiffres de client.
EXEMPLE = Hypotheses(questions_par_mois=1200, minutes_par_question=4, cout_horaire_eur=45,
                     part_traitee=0.5, cout_mensuel_eur=300)


def test_le_gain_est_le_temps_economise_moins_le_cout():
    # 1 200 × 0,5 × 4 min = 40 h ; 40 h × 45 € = 1 800 € ; moins 300 € de fonctionnement.
    assert gain_mensuel(EXEMPLE) == 1500.0


def test_le_remboursement_se_compte_en_mois():
    assert mois_pour_rembourser(EXEMPLE, investissement_eur=15000) == 10.0


def test_un_assistant_qui_coute_plus_qu_il_ne_rapporte_ne_se_rembourse_jamais():
    trop_cher = Hypotheses(100, 4, 45, 0.5, 300)
    assert gain_mensuel(trop_cher) < 0
    assert mois_pour_rembourser(trop_cher, 15000) is None


def test_une_part_traitee_hors_de_0_1_est_refusee():
    with pytest.raises(ValueError):
        gain_mensuel(Hypotheses(1200, 4, 45, 12, 300))  # 12 cas justes n'est pas une proportion
