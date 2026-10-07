import json

from fastapi.testclient import TestClient

from jobportal.agent import Trace
from jobportal.api import creer_application
from jobportal.donnees import OFFRES
from jobportal.fausse_ollama import FausseOllama
from jobportal.observabilite import Journal, centile, cout_local_eur, resumer


def ligne(duree, entree=500, sortie=40, outils=("rechercher_offres",)):
    return {"duree_ms": duree, "jetons_entree": entree, "jetons_sortie": sortie,
            "outils": [{"nom": o} for o in outils]}


def test_le_centile_au_plus_proche_rang():
    valeurs = list(range(1, 21))  # 1..20
    assert centile(valeurs, 50) == 10
    assert centile(valeurs, 95) == 19
    assert centile([7], 95) == 7
    # Le rang s'arrondit vers le HAUT : 2,5 donne le rang 3. round(), arrondi bancaire,
    # donnait 2 — et une médiane de 1..5 égale à 2.
    assert centile([1, 2, 3, 4, 5], 50) == 3


def test_le_resume_donne_volume_vitesse_et_outils():
    r = resumer([ligne(1000), ligne(3000, outils=("compter_candidatures",)), ligne(2000)])
    assert r["requetes"] == 3 and r["duree_ms_mediane"] == 2000 and r["duree_ms_max"] == 3000
    assert r["outils"] == {"rechercher_offres": 2, "compter_candidatures": 1}
    assert resumer([]) == {"requetes": 0}


def test_le_cout_local_est_un_calcul_sur_une_hypothese():
    # 4 s de calcul, sur une machine à 1,80 € de l'heure (hypothèse) : 0,002 €.
    assert cout_local_eur(4000, 1.80) == 0.002


def test_le_journal_ecrit_une_ligne_json_par_requete(tmp_path):
    journal = Journal(tmp_path / "traces.jsonl")
    trace = Trace(identifiant="abc", question="x", modele="m", duree_ms=1200)
    journal.ecrire(trace, "réponse")
    journal.ecrire(trace, "autre")
    lignes = [json.loads(l) for l in (tmp_path / "traces.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(lignes) == 2 and lignes[0]["duree_ms"] == 1200 and lignes[0]["longueur_reponse"] == 7
    assert "_debut" not in lignes[0]


def test_les_metriques_resument_les_requetes_servies(tmp_path):
    serveur = FausseOllama()
    serveur.vecteurs(*[[1.0, 0.0]] * len(OFFRES))
    serveur.repondre("21 candidatures pour OFF-103.")
    serveur.repondre("12 candidatures pour OFF-101.")
    api = TestClient(creer_application(serveur.client(), journal=Journal(tmp_path / "t.jsonl")))
    api.post("/question", json={"question": "Combien pour OFF-103 ?"})
    api.post("/question", json={"question": "Combien pour OFF-101 ?"})
    m = api.get("/metriques").json()
    assert m["requetes"] == 2 and m["outils"] == {"compter_candidatures": 2}
