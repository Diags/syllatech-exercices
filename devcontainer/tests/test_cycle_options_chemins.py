"""Le cycle de vie, le nommage des variables, la résolution des chemins."""

from __future__ import annotations

import pytest

from jobportal import chemins, cycle, features, options
from jobportal.commun import A_CORRIGER, PORTAIL, RACINE
from jobportal.config import charger, depuis_texte

G = "ghcr.io/devcontainers/features/"


def config(corps: str):
    return depuis_texte('{"image": "x",' + corps + "}")


# ── le cycle de vie ─────────────────────────────────────────────────────

def test_l_ordre_et_la_frequence():
    c = config('"initializeCommand": "a", "onCreateCommand": "b",'
               '"updateContentCommand": "c", "postCreateCommand": "d",'
               '"postStartCommand": "e", "postAttachCommand": "f"')
    etapes = cycle.deroulement(c)
    assert [e.nom for e in etapes] == list(
        ("initializeCommand", "onCreateCommand", "updateContentCommand",
         "postCreateCommand", "postStartCommand", "postAttachCommand"))
    assert etapes[0].ou == cycle.HOTE
    assert all(e.ou == cycle.CONTENEUR for e in etapes[1:])
    assert [e.quand for e in etapes] == [cycle.CREATION] * 4 + [
        cycle.DEMARRAGE, cycle.ATTACHEMENT]


def test_l_ordre_ne_depend_pas_de_l_ordre_d_ecriture():
    """Les cles d'un objet JSON n'ont pas d'ordre semantique."""
    c = config('"postCreateCommand": "d", "onCreateCommand": "b"')
    assert [e.nom for e in cycle.deroulement(c)] == [
        "onCreateCommand", "postCreateCommand"]


def test_waitfor_par_defaut():
    c = config('"postCreateCommand": "migrate"')
    assert c.attend == "updateContentCommand"
    assert c.attend_est_ecrit is False
    assert cycle.creation_apres_la_main(c) == ["postCreateCommand"]


def test_waitfor_ecrit_change_la_reponse():
    c = config('"postCreateCommand": "migrate", "waitFor": "postCreateCommand"')
    assert c.attend_est_ecrit is True
    assert cycle.creation_apres_la_main(c) == []


def test_la_commande_attendue_est_incluse():
    c = config('"onCreateCommand": "a", "updateContentCommand": "b"')
    assert cycle.creation_apres_la_main(c) == []


def test_le_cout_par_onglet_et_par_demarrage():
    c = config('"postStartCommand": "a", "postAttachCommand": "b"')
    assert cycle.cout_par_onglet(c) == ["postAttachCommand"]
    assert cycle.cout_par_demarrage(c) == ["postStartCommand",
                                           "postAttachCommand"]


@pytest.mark.parametrize("valeur, shell, forme", [
    ("a && b", True, "chaine"),
    (["a", "&&", "b"], False, "tableau"),
    ({"un": "a", "deux": "b"}, True, "objet"),
])
def test_les_trois_formes(valeur, shell, forme):
    assert cycle.utilise_le_shell(valeur) is shell
    assert forme in cycle.forme(valeur)


def test_les_operateurs_inertes_d_un_tableau():
    assert cycle.piege_de_shell(["mvn", "compile", "&&", "echo"]) == ["&&"]
    assert cycle.piege_de_shell(["echo", "$HOME"]) == ["$"]
    assert cycle.piege_de_shell("mvn compile && echo") == []


def test_tout_dans_postcreate():
    assert cycle.tout_dans_post_create(config('"postCreateCommand": "a"'))
    assert not cycle.tout_dans_post_create(
        config('"onCreateCommand": "a", "postCreateCommand": "b"'))


def test_le_cycle_du_portail_ne_traine_rien():
    portail = charger(PORTAIL / "devcontainer.json")
    assert cycle.creation_apres_la_main(portail) == []
    assert cycle.cout_par_onglet(portail) == []


# ── le nommage des variables ────────────────────────────────────────────

@pytest.mark.parametrize("option, variable", [
    ("version", "VERSION"),
    ("installMaven", "INSTALLMAVEN"),
    ("jdk-distro", "JDK_DISTRO"),
    ("my.option", "MY_OPTION"),
    ("a b", "A_B"),
    ("2fa", "_FA"),
    ("22fa", "_FA"),
    ("_prive", "_PRIVE"),
    ("__double", "_DOUBLE"),
    ("1", "_"),
    ("dej_a_bon", "DEJ_A_BON"),
])
def test_la_regle_de_nommage(option, variable):
    assert options.nom_de_variable(option) == variable


def test_la_collision_documentee():
    """Deux options differentes, une seule variable."""
    assert options.collisions(["2fa", "22fa", "version"]) == {
        "_FA": ["2fa", "22fa"]}
    assert options.collisions(["version", "jdkDistro"]) == {}


def test_une_option_omise_est_exportee_avec_son_defaut():
    manifeste = {"options": {
        "version": {"default": "21"},
        "installMaven": {"default": True},
    }}
    assert options.env(manifeste, {"version": "17"}) == {
        "VERSION": "17", "INSTALLMAVEN": "true"}


def test_un_booleen_devient_du_texte_minuscule():
    """Un `install.sh` teste `[ "$X" = "true" ]`, pas `= "True"`."""
    manifeste = {"options": {"x": {"default": False}}}
    assert options.env(manifeste, {}) == {"X": "false"}


def test_une_option_non_declaree_n_est_pas_exportee():
    manifeste = {"options": {"version": {"default": "21"}}}
    assert options.env(manifeste, {"versionne": "17"}) == {"VERSION": "21"}
    assert options.ignorees(manifeste, {"versionne": "17"}) == ["versionne"]


def test_le_cas_reel_de_la_faute_de_frappe():
    index = features.catalogue()
    java = index[f"{G}java"]
    mal = charger(A_CORRIGER / "10-option-inconnue.json")
    passees = mal.features[f"{G}java:1"]
    assert options.ignorees(java, passees) == ["versionne"]
    assert options.env(java, passees)["VERSION"] == "latest"


@pytest.mark.parametrize("remote, container, attendu", [
    ("vscode", None, ("root", "vscode", "/root", "/home/vscode")),
    (None, "node", ("node", "node", "/home/node", "/home/node")),
    (None, None, ("root", "root", "/root", "/root")),
])
def test_les_variables_d_utilisateur(remote, container, attendu):
    v = options.utilisateurs(remote, container)
    assert (v["_CONTAINER_USER"], v["_REMOTE_USER"],
            v["_CONTAINER_USER_HOME"], v["_REMOTE_USER_HOME"]) == attendu


# ── les chemins ─────────────────────────────────────────────────────────

def test_le_contexte_du_portail_est_la_racine():
    portail = charger(PORTAIL / "devcontainer.json")
    assert chemins.contexte_est_la_racine(portail) is True
    assert chemins.visible_dans_le_contexte(portail, "pom.xml") is True
    assert chemins.visible_dans_le_contexte(portail, "src") is True


def test_le_contexte_fautif_existe_mais_ne_voit_pas_le_projet():
    fautif = charger(A_CORRIGER / "01-contexte-point.json")
    assert chemins.contexte_est_la_racine(fautif, PORTAIL) is False
    assert chemins.visible_dans_le_contexte(fautif, "pom.xml", PORTAIL) is False
    # Et pourtant le dossier existe : c'est ce qui rend l'erreur deroutante.
    assert (PORTAIL / ".").resolve().exists()


def test_le_dockerfile_est_trouve_dans_les_deux_cas():
    """Les deux chemins partent du meme endroit et ne designent pas la
    meme chose — c'est cela qui surprend.
    """
    for nom, base in [(PORTAIL / "devcontainer.json", None),
                      (A_CORRIGER / "01-contexte-point.json", PORTAIL)]:
        c = charger(nom)
        resolutions = {r.propriete: r for r in chemins.resoudre(c, base=base)}
        assert resolutions["build.dockerfile"].existe is True


def test_les_deux_fichiers_compose_se_resolvent():
    pile = depuis_texte(
        '{"dockerComposeFile": ["../compose.yaml", "compose.dev.yaml"],'
        ' "service": "app", "workspaceFolder": "/w"}',
        PORTAIL / "devcontainer.json")
    resolutions = chemins.resoudre(pile, base=PORTAIL)
    assert [r.existe for r in resolutions] == [True, True]
    assert resolutions[0].resolu == (RACINE / "compose.yaml").resolve()


def test_un_chemin_absent_est_signale():
    c = depuis_texte('{"build": {"dockerfile": "Absent", "context": ".."}}',
                     PORTAIL / "devcontainer.json")
    assert [r.propriete for r in chemins.manquants(c)] == ["build.dockerfile"]
