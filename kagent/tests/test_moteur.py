"""Le controleur, les outils, le moteur, l'A2A et les traces."""

from __future__ import annotations

from pathlib import Path

import pytest

from jobportal import cluster as grappe
from jobportal import controleur, integration, moteur, outils, traces
from jobportal import yaml_minimal

MANIFESTES = Path(__file__).resolve().parent.parent / "manifestes"
QUESTION = "Diagnostique l'incident : des pods redemarrent."


@pytest.fixture
def api() -> controleur.Api:
    serveur = controleur.Api()
    for fichier in sorted(MANIFESTES.glob("*.yaml")):
        for document in yaml_minimal.charger_fichier_tous(fichier):
            serveur.appliquer(document)
    controleur.Controleur(serveur).reconcilier()
    return serveur


@pytest.fixture
def cluster() -> grappe.Cluster:
    return grappe.avec_incident()


@pytest.fixture
def m(api: controleur.Api, cluster: grappe.Cluster) -> moteur.Moteur:
    return moteur.Moteur(api, cluster)


# ── le controleur ────────────────────────────────────────────────────────

def test_apply_ne_cree_aucun_agent_executable():
    serveur = controleur.Api()
    for document in yaml_minimal.charger_fichier_tous(
            MANIFESTES / "agent-sre.yaml"):
        serveur.appliquer(document)
    agent = serveur.lire("Agent", "assistant-sre")

    assert agent is not None
    assert agent.conditions == []          # aucun statut avant reconciliation


def test_lordre_dapplication_na_pas_dimportance():
    serveur = controleur.Api()
    controle = controleur.Controleur(serveur)

    for document in yaml_minimal.charger_fichier_tous(
            MANIFESTES / "agent-sre.yaml"):
        serveur.appliquer(document)
    controle.reconcilier()
    assert not serveur.lire("Agent", "assistant-sre").pret

    for document in yaml_minimal.charger_fichier_tous(
            MANIFESTES / "plateforme.yaml"):
        serveur.appliquer(document)
    controle.reconcilier()
    assert serveur.lire("Agent", "assistant-sre").pret


def test_une_reference_manquante_ne_fait_pas_echouer_apply(api):
    """⚠️ LA MESURE DU CHAPITRE 1 : cree, jamais invocable."""
    orphelin = api.lire("Agent", "assistant-orphelin")

    assert orphelin is not None                       # il existe
    assert not orphelin.pret                          # et n'est pas pret
    accepte = orphelin.condition("Accepted")
    assert accepte.statut == "False"
    assert "modele-qui-nexiste-pas" in accepte.message


def test_un_agent_correct_est_pret(api):
    assert api.lire("Agent", "assistant-sre").pret
    assert api.lire("Agent", "orchestrateur").pret


def test_la_reconciliation_est_idempotente(api):
    controle = controleur.Controleur(api)
    controle.reconcilier()
    avant = [(a.nom, str(a.conditions)) for a in api.lister("Agent")]
    controle.reconcilier()

    assert [(a.nom, str(a.conditions)) for a in api.lister("Agent")] == avant


# ── les outils ───────────────────────────────────────────────────────────

def test_la_ligne_entre_lecture_et_action(m):
    lecture = outils.lecture_seule(m.catalogue)
    action = outils.actions(m.catalogue)

    assert "k8s_get_resources" in lecture
    assert "k8s_delete_resource" in action
    assert set(lecture).isdisjoint(action)
    assert len(lecture) + len(action) == len(m.catalogue)


def test_un_agent_de_diagnostic_est_en_lecture_seule(api, m):
    trousseau = m.trousseau(api.lire("Agent", "assistant-sre"))

    assert trousseau.en_lecture_seule
    assert trousseau.dangereux == []
    assert len(trousseau.accordes) == 4


def test_un_outil_non_accorde_est_refuse(api, m):
    trousseau = m.trousseau(api.lire("Agent", "assistant-sre"))

    with pytest.raises(outils.ErreurOutil, match="n'est pas accorde"):
        trousseau.appeler("k8s_delete_resource", nom="x")


def test_le_prompt_nest_pas_un_controle_dacces(api, m, cluster):
    """⚠️ Le prompt interdit la suppression ; le trousseau l'autorise."""
    agent = api.lire("Agent", "assistant-sre-etendu")
    assert "JAMAIS" in agent.spec["declarative"]["systemMessage"]

    trousseau = m.trousseau(agent)
    assert not trousseau.en_lecture_seule
    avant = len(cluster.pods)
    trousseau.appeler("k8s_delete_resource", genre="Pod",
                      nom="jobportal-web-5b9c")

    assert len(cluster.pods) == avant - 1
    assert cluster.journal_des_actions == ["supprime Pod/jobportal-web-5b9c"]


def test_un_outil_nomme_mais_absent_est_silencieux(api, m):
    trousseau = m.trousseau(api.lire("Agent", "assistant-outil-fantome"))

    assert trousseau.introuvables == ["k8s_get_podlogs"]
    assert api.lire("Agent", "assistant-outil-fantome").pret   # et Ready


# ── le grounding ─────────────────────────────────────────────────────────

def test_sans_outils_lagent_repond_de_memoire(m):
    session = m.invoquer("assistant-sans-outils", QUESTION)

    assert session.outils_appeles == []
    assert session.appels_de_modele == 1
    assert "liveness" in session.reponse         # plausible, et faux


def test_avec_outils_lagent_cite_ce_quil_a_lu(m):
    """⚠️ LA MESURE DU CHAPITRE 3."""
    session = m.invoquer("assistant-sre", QUESTION)

    assert session.outils_appeles == ["k8s_get_resources", "k8s_get_pod_logs",
                                      "k8s_get_events", "prometheus_query"]
    assert "OutOfMemoryError" in session.reponse
    assert "CrashLoopBackOff" in session.reponse
    assert "liveness" not in session.reponse.split("pas la sonde")[0]


def test_le_grounding_coute_plus_cher(m):
    sans = m.invoquer("assistant-sans-outils", QUESTION)
    avec = m.invoquer("assistant-sre", QUESTION)

    assert avec.jetons > sans.jetons * 10
    assert avec.appels_de_modele == 5
    assert sans.appels_de_modele == 1


# ── l'A2A ────────────────────────────────────────────────────────────────

def test_la_delegation_coute_plus_dappels(api, cluster):
    seul = moteur.Moteur(api, cluster).invoquer("assistant-sre", QUESTION)
    groupe = moteur.Moteur(api, cluster).invoquer("orchestrateur", QUESTION)

    assert groupe.delegations == ["agent-etat", "agent-metriques"]
    assert groupe.appels_de_modele > seul.appels_de_modele
    assert groupe.appels_de_modele == 8


def test_un_cycle_de_delegation_est_detecte(m):
    """⚠️ Chaque manifeste est valide ; le cycle n'apparait qu'a
    l'execution."""
    with pytest.raises(moteur.ErreurMoteur, match="cycle de delegation"):
        m.invoquer("agent-ping", QUESTION)


def test_un_agent_introuvable_leve(m):
    with pytest.raises(moteur.ErreurMoteur, match="introuvable"):
        m.invoquer("agent-imaginaire", QUESTION)


# ── les traces ───────────────────────────────────────────────────────────

def test_le_contexte_propage_donne_une_seule_trace(api, cluster):
    m = moteur.Moteur(api, cluster)
    m.invoquer("orchestrateur", QUESTION, propager=True)

    assert len(m.collecteur.traces) == 1
    assert len(m.collecteur.spans) == 14


def test_sans_propagation_la_trace_se_coupe(api, cluster):
    """⚠️ LA MESURE DU CHAPITRE 5 : memes spans, trois traces."""
    propage = moteur.Moteur(api, cluster)
    a = propage.invoquer("orchestrateur", QUESTION, propager=True)
    coupe = moteur.Moteur(api, cluster)
    b = coupe.invoquer("orchestrateur", QUESTION, propager=False)

    assert a.reponse == b.reponse                       # rien n'a echoue
    assert len(propage.collecteur.spans) == len(coupe.collecteur.spans)
    assert len(propage.collecteur.traces) == 1
    assert len(coupe.collecteur.traces) == 3


def test_les_spans_portent_les_attributs_gen_ai(api, cluster):
    m = moteur.Moteur(api, cluster)
    m.invoquer("assistant-sre", QUESTION)
    chats = m.collecteur.par_nom("chat")

    assert chats
    assert all("gen_ai.request.model" in s.attributs for s in chats)
    assert m.collecteur.total("gen_ai.usage.input_tokens") > 0
    entrees = [s.attributs["gen_ai.usage.input_tokens"] for s in chats]
    assert entrees == sorted(entrees)     # le contexte grossit a chaque tour


# ── l'integration Spring ─────────────────────────────────────────────────

def test_le_contrat_a2a_exige_une_tache(api, cluster):
    point = integration.PointDEntreeA2A(moteur.Moteur(api, cluster))

    assert point.poster("assistant-sre", {"sessionId": "x"}).erreur
    assert point.poster("assistant-sre", {"task": QUESTION}).reussi


def test_le_contrat_a2a_elague_aussi(api, cluster):
    point = integration.PointDEntreeA2A(moteur.Moteur(api, cluster))
    echange = point.poster("assistant-sre",
                           {"task": QUESTION, "userId": "marie"})

    assert echange.reussi
    assert echange.elagues == ["userId"]


@pytest.mark.parametrize("corps, type_, lisible, motif", [
    ('{"status": "completed", "result": "ok"}', "application/json", True, ""),
    ("<html>502</html>", "text/html", False, "et non en JSON"),
    ('{"status": "completed"', "application/json", False, "illisible"),
    ('{"resultat": "ok"}', "application/json", False, "obligatoire"),
])
def test_la_lecture_de_la_reponse(corps, type_, lisible, motif):
    """⚠️ Le cas qui coute une matinee : un 200 qui rend du HTML."""
    reponse, erreur = integration.lire_la_reponse(corps, type_)

    assert (reponse is not None) is lisible
    assert motif in erreur


def test_lagent_appelle_lapi_spring(api, cluster):
    spring = integration.ApiSpring()
    m = moteur.Moteur(api, cluster,
                      outils_en_plus=integration.outils_de_spring(spring))
    api.appliquer({
        "apiVersion": "kagent.dev/v1alpha2", "kind": "Agent",
        "metadata": {"name": "assistant-metier"},
        "spec": {"type": "Declarative", "declarative": {
            "modelConfig": "claude-config",
            "tools": [{"type": "McpServer", "mcpServer": {
                "name": "outils-jobportal", "kind": "RemoteMCPServer",
                "toolNames": ["rechercher_offres"]}}]}}})

    session = m.invoquer("assistant-metier",
                         "Quelles offres proposez-vous a Lyon ?")

    assert session.outils_appeles == ["rechercher_offres"]
    assert spring.appels == ["rechercher_offres"]
    assert spring.tickets == []          # aucun outil d'ecriture accorde


def test_la_trace_traverse_spring_et_lagent(api, cluster):
    m = moteur.Moteur(api, cluster)
    racine = m.collecteur.ouvrir("POST /api/diagnostics")
    integration.PointDEntreeA2A(m).poster(
        "assistant-sre",
        {"task": QUESTION, "metadata": {"traceparent": "00-abc-def-01"}},
        parent=racine)

    assert len(m.collecteur.traces) == 1
    assert m.collecteur.enfants(racine)
