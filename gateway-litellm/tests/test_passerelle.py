"""Ce que la passerelle et le proxy doivent garantir.

Lancer :  uv run --extra dev pytest -q

⚠️ La premiere commande paie une trentaine de secondes d'import de litellm.
C'est le paquet, pas la suite : elle s'execute ensuite en moins d'une seconde.

Les tests marques « reel » passent par le vrai `litellm.Router` : routage,
bascule, comptage de jetons et calcul du cout sont ceux de la bibliotheque.
Seule la reponse du fournisseur est remplacee, par le champ `mock_response`
de litellm lui-meme.
"""

from __future__ import annotations

import asyncio
import time

import pytest

from jobportal.budgets import (BudgetDepasse, CleInconnue, ModeleInterdit,
                               Registre, depassement_possible)
from jobportal.commun import SECRET_JWT, config
from jobportal.jetons import (JetonInvalide, lire_sans_verifier, signer,
                              verifier)
from jobportal.observabilite import (Sonde, TableauDeBord, brancher,
                                     sondes_branchees)
from jobportal.passerelle import Passerelle, Refuse
from jobportal.proxy import Proxy, charger
from outils.verifier_config import verifier as verifier_config

PANNE = "litellm.RateLimitError"


def modele(alias: str, vrai: str, reponse: str = "ok") -> dict:
    return {"model_name": alias,
            "litellm_params": {"model": vrai, "api_key": "factice",
                               "mock_response": reponse}}


@pytest.fixture
def registre() -> Registre:
    return Registre()


@pytest.fixture
def passerelle() -> Passerelle:
    reg = Registre()
    coffre = {"data": reg.generer("data", 1.00).cle,
              "rh": reg.generer("rh", 0.02, modeles=("rapide",)).cle}
    return Passerelle(proxy=Proxy.depuis(config()), registre=reg,
                      secret_jwt=SECRET_JWT, coffre=coffre)


def jwt(equipe: str, **options) -> str:
    return signer(f"{equipe}@exemple.fr", equipe,
                  options.pop("secret", SECRET_JWT), **options)


def erreurs(soucis) -> list:
    return [s for s in soucis if s.gravite == "erreur"]


# ------------------------------------------------------------- les jetons

def test_un_jeton_valide_porte_son_equipe():
    jeton = verifier(jwt("data"), SECRET_JWT)
    assert jeton.equipe == "data"
    assert not jeton.expire


@pytest.mark.parametrize("etiquette,fabrique", [
    ("signature d'un autre secret", lambda: jwt("data", secret="autre")),
    ("expire", lambda: jwt("data", duree=-1)),
    ("sans equipe", lambda: signer("d", "", SECRET_JWT)),
    ("alg none", lambda: jwt("data", algorithme="none")),
    ("deux parties", lambda: "abc.def"),
    ("base64 casse", lambda: "!!!.???.***"),
])
def test_les_jetons_refuses(etiquette, fabrique):
    with pytest.raises(JetonInvalide):
        verifier(fabrique(), SECRET_JWT)


def test_alg_none_est_refuse_alors_qu_il_est_bien_forme():
    """Une bibliotheque qui lit l'algorithme DANS le jeton pour decider
    comment le verifier accepte celui-ci — sans secret. L'algorithme attendu
    est celui du SERVEUR."""
    faux = signer("mallory", "finance", SECRET_JWT, algorithme="none")
    assert len(faux.split(".")) == 3
    assert lire_sans_verifier(faux)["team"] == "finance"
    with pytest.raises(JetonInvalide):
        verifier(faux, SECRET_JWT)


def test_un_jwt_n_est_pas_un_coffre():
    """Sa charge utile se lit sans le secret. Y mettre une donnee
    confidentielle revient a la publier."""
    assert lire_sans_verifier(jwt("data"))["sub"] == "data@exemple.fr"


# ------------------------------------------------------------ les budgets

def test_une_cle_revoquee_ne_passe_plus(registre):
    cle = registre.generer("data", 1.0)
    registre.autoriser(cle.cle, "claude")
    registre.revoquer(cle.cle)
    with pytest.raises(CleInconnue):
        registre.autoriser(cle.cle, "claude")


def test_revoquer_une_cle_n_en_touche_aucune_autre(registre):
    une = registre.generer("data", 1.0)
    autre = registre.generer("rh", 1.0)
    registre.revoquer(une.cle)
    assert registre.autoriser(autre.cle, "claude") is autre


def test_un_modele_hors_liste_est_interdit_pas_ralenti(registre):
    """Distinction qui decide du code HTTP : un modele hors liste ne sera
    JAMAIS autorise (403) ; un budget epuise le sera a la prochaine periode
    (429). Reessayer plus tard a un sens dans un cas, aucun dans l'autre."""
    cle = registre.generer("rh", 1.0, modeles=("rapide",))
    registre.autoriser(cle.cle, "rapide")
    with pytest.raises(ModeleInterdit):
        registre.autoriser(cle.cle, "claude")


def test_le_budget_se_verifie_avant_et_s_impute_apres(registre):
    cle = registre.generer("data", 0.0005)
    registre.autoriser(cle.cle, "claude")
    registre.imputer(cle.cle, 0.00033)
    registre.autoriser(cle.cle, "claude")       # encore sous le plafond
    registre.imputer(cle.cle, 0.00033)
    assert cle.depense > cle.budget_max, "le plafond est depasse"
    with pytest.raises(BudgetDepasse):
        registre.autoriser(cle.cle, "claude")


def test_le_depassement_maximal_est_le_cout_du_plus_cher_appel(registre):
    cle = registre.generer("data", 0.0005)
    assert depassement_possible(cle, 0.05) == 0.05
    registre.imputer(cle.cle, 1.0)
    assert depassement_possible(cle, 0.05) == 0.0, "plus rien ne passera"


def test_le_debit_se_compte_sur_la_minute_glissante():
    horloge = {"t": 1_000.0}
    registre = Registre(maintenant=lambda: horloge["t"])
    cle = registre.generer("data", 10.0, rpm=2)
    for _ in range(2):
        registre.autoriser(cle.cle, "claude")
        registre.imputer(cle.cle, 0.0)
    with pytest.raises(BudgetDepasse):
        registre.autoriser(cle.cle, "claude")
    horloge["t"] += 61
    assert registre.autoriser(cle.cle, "claude") is cle


def test_le_budget_repart_a_la_periode_suivante():
    horloge = {"t": 0.0}
    registre = Registre(maintenant=lambda: horloge["t"])
    cle = registre.generer("data", 0.001, duree_budget=100)
    registre.imputer(cle.cle, 0.01)
    with pytest.raises(BudgetDepasse):
        registre.autoriser(cle.cle, "claude")
    horloge["t"] += 101
    assert registre.autoriser(cle.cle, "claude") is cle
    assert cle.depense == 0.0


# ------------------------------------------------- le trajet complet

async def test_un_appel_nominal_est_impute_a_son_equipe(passerelle):
    appel = await passerelle.traiter(jwt("data"), "claude", "Trois offres ?")
    assert appel.cout > 0
    cle = passerelle.coffre["data"]
    assert passerelle.registre.cles[cle].depense == pytest.approx(appel.cout)
    assert passerelle.journal[-1].equipe == "data"


@pytest.mark.parametrize("etiquette,jeton,alias,code", [
    ("jeton d'un autre secret", jwt("data", secret="autre"), "claude", 401),
    ("jeton expire", jwt("data", duree=-1), "claude", 401),
    ("equipe sans cle", jwt("finance"), "claude", 403),
    ("modele hors de la cle", jwt("rh"), "claude", 403),
])
async def test_les_refus_portent_le_bon_code(passerelle, etiquette, jeton,
                                             alias, code):
    with pytest.raises(Refuse) as capture:
        await passerelle.traiter(jeton, alias, "?")
    assert capture.value.code == code


async def test_un_refus_est_journalise(passerelle):
    """Un refus non journalise est un incident invisible : le taux d'erreur
    d'un tableau de bord bati sur le seul success_callback reste a zero."""
    with pytest.raises(Refuse):
        await passerelle.traiter(jwt("finance"), "claude", "?")
    assert passerelle.journal[-1].code == 403
    assert passerelle.journal[-1].equipe == "finance"


async def test_un_budget_epuise_rend_429_et_n_appelle_pas_le_proxy(passerelle):
    cle = passerelle.coffre["rh"]
    passerelle.registre.imputer(cle, 99.0)
    avant = len(passerelle.journal)
    with pytest.raises(Refuse) as capture:
        await passerelle.traiter(jwt("rh"), "rapide", "?")
    assert capture.value.code == 429
    assert passerelle.journal[avant].code == 429
    assert passerelle.journal[avant].cout == 0.0, "un refus ne coute rien"


def test_le_jeton_client_n_est_PAS_transmis_au_proxy(passerelle):
    """Le laisser passer « au cas ou » donnerait au proxy — et a sa base, et
    a ses journaux — l'identite de chaque utilisateur final."""
    client = jwt("data")
    entetes = passerelle.entetes_sortants(client)
    assert client not in str(entetes)
    assert entetes["Authorization"].endswith(passerelle.coffre["data"])


# -------------------------------------------------- le proxy, pour de vrai

async def test_reel_les_trois_alias_repondent():
    proxy = Proxy.depuis(config())
    for alias in ("claude", "rapide", "local"):
        appel = await proxy.appeler(alias, "bonjour")
        assert appel.contenu
        assert appel.jetons > 0


async def test_reel_le_cout_vient_de_la_table_de_litellm():
    proxy = Proxy.depuis(config())
    cher = await proxy.appeler("claude", "bonjour")
    bon_marche = await proxy.appeler("rapide", "bonjour")
    assert cher.jetons == bon_marche.jetons, "meme reponse simulee"
    assert cher.cout > bon_marche.cout * 10, "les tarifs different"


async def test_reel_la_bascule_se_produit_et_se_voit():
    proxy = Proxy({
        "model_list": [modele("claude", "anthropic/claude-sonnet-4-5", PANNE),
                       modele("rapide", "openai/gpt-4o-mini")],
        "litellm_settings": {"fallbacks": [{"claude": ["rapide"]}],
                             "num_retries": 0}})
    appel = await proxy.appeler("claude", "bonjour")
    assert appel.alias == "claude", "l'application a demande claude"
    assert "gpt-4o-mini" in appel.modele_reel, "c'est rapide qui a repondu"
    assert appel.bascule, "et cela doit se voir dans le journal"


async def test_reel_les_reessais_coutent_du_temps_avant_la_bascule():
    """Ils servent quand la panne est BREVE. Ils nuisent quand elle dure : on
    paie l'attente, puis on bascule quand meme."""
    durees = {}
    for reessais in (0, 2):
        proxy = Proxy({
            "model_list": [modele("a", "anthropic/claude-sonnet-4-5", PANNE),
                           modele("b", "openai/gpt-4o-mini")],
            "litellm_settings": {"fallbacks": [{"a": ["b"]}],
                                 "num_retries": reessais}})
        debut = time.perf_counter()
        await proxy.appeler("a", "bonjour")
        durees[reessais] = time.perf_counter() - debut
    assert durees[2] > durees[0] * 3, durees


async def test_reel_un_fallback_vers_un_alias_inconnu_rend_l_erreur_DU_PRINCIPAL():
    """Le piege du chapitre 4 : le Router accepte la regle a la construction,
    et l'erreur rendue est celle du modele principal. On cherche donc la
    panne du mauvais cote."""
    proxy = Proxy({
        "model_list": [modele("claude", "anthropic/claude-sonnet-4-5", PANNE)],
        "litellm_settings": {"fallbacks": [{"claude": ["fantome"]}],
                             "num_retries": 0}})
    with pytest.raises(Exception) as capture:
        await proxy.appeler("claude", "bonjour")
    assert "RateLimit" in type(capture.value).__name__


async def test_reel_le_meme_alias_deux_fois_repartit_la_charge():
    """On croit remplacer la premiere entree ; LiteLLM y voit deux
    deploiements et repartit. Une part des requetes part donc vers l'autre
    modele, avec l'autre prix."""
    proxy = Proxy({"model_list": [
        modele("rapide", "openai/gpt-4o", "A"),
        modele("rapide", "openai/gpt-4o-mini", "B")]})
    vus = set()
    for _ in range(20):
        vus.add((await proxy.appeler("rapide", "x")).modele_reel)
    assert len(vus) == 2, vus


def test_os_environ_est_resolu_au_demarrage(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-de-test")
    proxy = Proxy.depuis(config())
    declares = proxy.routeur.model_list
    cles = {d["litellm_params"].get("api_key") for d in declares}
    assert "sk-de-test" in cles
    assert not any(str(c).startswith("os.environ/") for c in cles)


# ------------------------------------------------------ l'observabilite

async def test_la_sonde_recoit_modele_cout_jetons_et_latence():
    sonde = brancher(Sonde())
    proxy = Proxy.depuis(config())
    await proxy.appeler("claude", "bonjour")
    await asyncio.sleep(0.3)
    (mesure,) = [m for m in sonde.mesures if "claude" in m.modele]
    assert mesure.cout > 0 and mesure.jetons > 0 and mesure.latence_ms >= 0


async def test_brancher_debranche_vraiment_la_precedente():
    """Reassigner litellm.callbacks ne suffit pas : litellm derive une liste
    interne qu'il ne reconstruit pas. outils/mesurer_doublon.py le mesure
    dans un processus neuf.

    La liste derivee se remplit au PREMIER appel : la compter avant d'appeler
    rendrait zero, et ne prouverait rien.
    """
    proxy = Proxy.depuis(config())
    oubliee = brancher(Sonde())
    await proxy.appeler("rapide", "x")
    await asyncio.sleep(0.3)
    assert len(oubliee.mesures) == 1

    gardee = brancher(Sonde())
    await proxy.appeler("rapide", "x")
    await asyncio.sleep(0.3)
    assert sondes_branchees() == 1, "une seule sonde reste enregistree"
    assert len(gardee.mesures) == 1
    assert len(oubliee.mesures) == 1, "l'ancienne ne recoit plus rien"


def test_le_tableau_de_bord_separe_appels_et_refus():
    from jobportal.passerelle import Trace

    tableau = TableauDeBord(journal=[
        Trace("data", "claude", "claude", 0.01, 30, 100.0, False),
        Trace("data", "claude", "gpt-4o", 0.02, 30, 200.0, True),
        Trace("data", "claude", "", 0.0, 0, 0.0, False, code=429)])
    ligne = tableau.par_equipe()["data"]
    assert ligne["appels"] == 2 and ligne["refus"] == 1
    assert ligne["bascules"] == 1
    assert ligne["cout"] == pytest.approx(0.03)
    assert ligne["latence_moyenne_ms"] == pytest.approx(150.0)


async def test_un_modele_sans_prix_est_facture_zero_et_se_detecte():
    sonde = brancher(Sonde())
    proxy = Proxy({"model_list": [
        modele("maison", "openai/modele-introuvable-xyz"),
        modele("rapide", "openai/gpt-4o-mini")]})
    await proxy.appeler("maison", "x")
    await proxy.appeler("rapide", "x")
    await asyncio.sleep(0.3)
    assert sonde.gratuits() == ["modele-introuvable-xyz"]


# ------------------------------------------------------- le verificateur

def test_la_configuration_livree_ne_leve_rien():
    assert verifier_config(charger(config())) == []


def test_la_configuration_fautive_leve_les_cinq():
    ou = {s.ou for s in erreurs(verifier_config(charger(config("a-corriger"))))}
    assert "claude / api_key" in ou
    assert "general_settings / master_key" in ou
    assert "model_list / claude" in ou
    assert "fallbacks / claude → gpt" in ou
    assert any("modele-maison-v3" in o for o in ou)


def test_une_cle_par_os_environ_ne_leve_rien():
    propre = {"model_list": [{"model_name": "a", "litellm_params": {
        "model": "openai/gpt-4o", "api_key": "os.environ/OPENAI_API_KEY"}}],
        "litellm_settings": {"fallbacks": [{"a": ["a"]}],
                             "success_callback": ["prometheus"]},
        "general_settings": {"master_key": "os.environ/LITELLM_MASTER_KEY"}}
    assert erreurs(verifier_config(propre)) == []


async def test_la_presence_de_la_cle_ne_suffit_PAS_a_prouver_un_prix():
    """Apres un seul appel vers un modele inconnu, litellm INSERE sa cle dans
    model_cost — avec un dictionnaire VIDE. Un verificateur qui teste
    « modele in model_cost » est donc juste au demarrage et faux des le
    premier appel : la pire des deux situations."""
    from litellm import model_cost

    inconnu = "openai/modele-jamais-tarife-abc"
    fautive = {"model_list": [modele("x", inconnu)]}
    assert any(inconnu.split("/")[-1] in s.ou or inconnu in s.ou
               for s in erreurs(verifier_config(fautive)))

    await Proxy({"model_list": [modele("x", inconnu)]}).appeler("x", "bonjour")
    assert inconnu in model_cost, "litellm l'a enregistre a l'usage"
    assert model_cost[inconnu] == {}, "mais sans aucun tarif"
    assert erreurs(verifier_config(fautive)), "le verificateur tient encore"


def test_un_modele_local_a_zero_dollar_n_est_pas_une_erreur():
    """« ollama/llama3 » est dans la table avec des zeros EXPLICITES : un
    modele auto-heberge ne coute effectivement rien au jeton."""
    local = {"model_list": [{"model_name": "local", "litellm_params": {
        "model": "ollama/llama3", "api_base": "http://ollama:11434"}}],
        "litellm_settings": {"fallbacks": [{"local": ["local"]}],
                             "success_callback": ["prometheus"]},
        "general_settings": {"master_key": "os.environ/LITELLM_MASTER_KEY"}}
    assert erreurs(verifier_config(local)) == []
