"""Ce que le modele du bac a sable doit garantir.

Lancer :  uv run --extra dev pytest -q

Ces tests ne verifient pas le bac a sable : ils verifient que le MODELE dit
ce que la documentation dit. Chaque test nomme la regle qu'il fixe, pour
qu'une divergence future soit un echec et pas une derive.
"""

from __future__ import annotations

import itertools
import json

import pytest

from outils.commun import RACINE, config
from outils.resolveur import (CLES_PRIVILEGIEES, PORTEES_PRIVILEGIEES, Config,
                              appliquee, identifiants, motif_inerte,
                              peut_ecrire, peut_joindre, peut_lire, protege)
from outils.verifier import verifier


def erreurs(config_) -> list:
    return [s for s in verifier(config_) if s.gravite == "erreur"]


# ------------------------------------------------------- les deux defauts

def test_sans_reglage_on_lit_tout_l_ordinateur():
    """« Default read behavior: read access to the entire computer. Note that
    this default still allows reading credential files such as
    ~/.aws/credentials. » C'est la raison d'etre du bloc credentials."""
    nu = Config(enabled=True)
    for chemin in ("/etc/hosts", "~/.aws/credentials", "~/.ssh/id_rsa"):
        assert peut_lire(nu, chemin).autorise, chemin


def test_sans_reglage_on_n_ecrit_que_dans_le_dossier_de_travail():
    nu = Config(enabled=True)
    assert peut_ecrire(nu, "./src/a.py").autorise
    assert not peut_ecrire(nu, "~/notes.md").autorise
    assert not peut_ecrire(nu, "/usr/bin/curl").autorise


def test_le_bac_a_sable_desactive_n_interdit_rien():
    eteint = Config(enabled=False, filesystem={"denyRead": ["~/"]})
    assert peut_lire(eteint, "~/.ssh/id_rsa").autorise


# ------------------------------------------------ la regle de specificite

def test_un_deny_tient_dans_un_allow_plus_large():
    c = Config(enabled=True, filesystem={"allowRead": ["~/"],
                                         "denyRead": ["~/.ssh"]})
    assert peut_lire(c, "~/photos/a.jpg").autorise
    assert not peut_lire(c, "~/.ssh/id_rsa").autorise


def test_un_allow_plus_etroit_rouvre_une_partie_d_un_deny():
    c = Config(enabled=True, filesystem={"allowRead": ["~/projets/public"],
                                         "denyRead": ["~/"]})
    assert peut_lire(c, "~/projets/public/notes.md").autorise
    assert not peut_lire(c, "~/projets/prive/notes.md").autorise


def test_l_ordre_des_entrees_ne_change_aucun_verdict():
    """720 permutations, un seul resultat. Ce n'est pas une evidence : une
    ACL, un pare-feu ou un .gitignore repondraient differemment selon
    l'ordre. C'est ce qui permet a plusieurs fichiers de reglages de fusionner
    leurs listes sans que la fusion decide du resultat."""
    regles = [("allowRead", "."), ("allowRead", "~/p/notes"),
              ("allowRead", "~/p/notes/brouillon"), ("denyRead", "~/"),
              ("denyRead", "~/p/notes/prive"),
              ("denyRead", "~/p/notes/brouillon/cles")]
    cibles = ["./a.py", "~/photos/a.jpg", "~/p/notes/i.md",
              "~/p/notes/prive/x.md", "~/p/notes/brouillon/b.md",
              "~/p/notes/brouillon/cles/id_rsa"]

    obtenus = set()
    for ordre in itertools.permutations(regles):
        fs: dict[str, list[str]] = {"allowRead": [], "denyRead": []}
        for cle, chemin in ordre:
            fs[cle].append(chemin)
        c = Config(enabled=True, filesystem=fs)
        obtenus.add(tuple(peut_lire(c, x).autorise for x in cibles))

    assert len(obtenus) == 1
    assert obtenus.pop() == (True, False, True, False, True, False)


def test_ouvrir_un_dossier_n_ouvre_pas_son_parent():
    c = Config(enabled=True, filesystem={"allowWrite": ["/tmp/build"]})
    assert peut_ecrire(c, "/tmp/build/a.js").autorise
    assert not peut_ecrire(c, "/tmp/autre/a.js").autorise


# Les trois tests qui suivent fixent une seule regle : un prefixe de CHEMIN
# n'est pas un prefixe de CHAINE. Remplacer la comparaison par segments de
# `_sous` par un `startswith` passait les 59 autres tests — un trou qu'on
# n'ecrit jamais expres, et qu'aucune sortie de chapitre ne montre.

def test_un_allowWrite_ne_deborde_pas_sur_un_dossier_au_nom_voisin():
    c = Config(enabled=True, filesystem={"allowWrite": ["/tmp/build"]})
    assert peut_ecrire(c, "/tmp/build/a.js").autorise
    assert not peut_ecrire(c, "/tmp/build-autre/a.js").autorise
    assert not peut_ecrire(c, "/tmp/buildozer").autorise


def test_un_denyRead_ne_deborde_pas_sur_un_home_voisin():
    """Un « ~/ » qui bloquerait aussi /home/moi2 refuserait des lectures
    legitimes — et personne ne saurait pourquoi."""
    c = Config(enabled=True, filesystem={"denyRead": ["~/"]})
    assert not peut_lire(c, "~/notes.md").autorise
    assert peut_lire(c, "/home/moi2/notes.md").autorise


def test_un_chemin_protege_ne_protege_pas_ce_qui_commence_pareil():
    """« .mcp.json » est protege ; « .mcp.json.bak » est un fichier ordinaire.
    Les confondre interdirait d'ecrire une sauvegarde, sans rien expliquer."""
    assert protege(".mcp.json") == ".mcp.json"
    assert protege(".mcp.json.bak") is None
    assert protege(".claude-backup/settings.json") is None


# --------------------------------------------------- LE test des chemins proteges

@pytest.mark.parametrize("chemin", [
    ".claude/settings.json", ".claude/settings.local.json",
    ".claude/hooks/pre.sh", ".claude/skills/deploy/SKILL.md",
    ".claude/agents/relecteur.md", ".claude/commands/deploy.md",
    ".claude/workflows/nuit.json", ".claude/scheduled_tasks.json",
    ".mcp.json", ".bashrc", ".zshrc", ".gitconfig", ".vscode/settings.json",
    ".idea/workspace.xml", ".git/hooks/pre-commit", ".git/config",
    "HEAD", "objects/ab/cdef", "refs/heads/main",
    "~/.claude/settings.json", "~/.claude.json",
    "~/.claude/.credentials.json",
])
def test_aucun_allowWrite_ne_leve_une_protection(chemin):
    """« There is no way to exempt one of these paths: an allowWrite entry or
    an Edit allow rule that covers the path doesn't lift the protection. »"""
    ouverte = Config(enabled=True,
                     filesystem={"allowWrite": [chemin, ".", "~/", "/"]})
    verdict = peut_ecrire(ouverte, chemin)
    assert not verdict.autorise
    assert "PROTEGE" in verdict.raison


def test_la_protection_remonte_au_dessus_du_dossier_de_travail():
    """« In your working directory and the directories above it. »"""
    c = Config(enabled=True)
    travail = "/travail/client/appli"
    for chemin in ("/travail/client/appli/.claude/settings.json",
                   "/travail/client/.claude/settings.json",
                   "/travail/.mcp.json"):
        assert not peut_ecrire(c, chemin, travail=travail).autorise, chemin
    assert peut_ecrire(c, f"{travail}/src/main.py", travail=travail).autorise


def test_bashrc_n_est_protege_que_dans_le_dossier_de_travail():
    """Groupe 2 : « In your working directory only ». Ailleurs, c'est le
    defaut d'ecriture qui refuse — pas la liste des chemins proteges."""
    assert protege(".bashrc") is not None
    assert protege("~/.bashrc") is None


def test_config_a_la_racine_n_est_protege_que_s_il_existe():
    """« plus config and hooks there when they already exist, even when the
    config directory belongs to your project rather than to git. » Un projet
    Rails, Symfony ou Spring a un dossier config/ a sa racine."""
    c = Config(enabled=True)
    assert peut_ecrire(c, "config/base.yml", existants=set()).autorise
    assert not peut_ecrire(c, "config/base.yml", existants={"config"}).autorise


def test_lstrip_aurait_desactive_la_detection():
    """.lstrip("./") retire un ENSEMBLE de caracteres, pas un prefixe :
    « .claude/settings.json » deviendrait « claude/settings.json », et le
    chemin protege ne serait plus reconnu. Le bug serait silencieux — ce test
    est la pour qu'il ne le soit pas."""
    assert ".claude/settings.json".lstrip("./") == "claude/settings.json"
    assert protege(".claude/settings.json") == ".claude/settings.json"


def test_filesystem_disabled_est_la_seule_sortie():
    """« The only way to turn the protection off is filesystem.disabled,
    which turns off filesystem isolation for every path. »"""
    coupee = Config(enabled=True, portee="utilisateur",
                    filesystem={"disabled": True})
    assert peut_ecrire(coupee, ".claude/settings.json").autorise
    assert peut_ecrire(coupee, "~/.claude.json").autorise


# --------------------------------------------------------------- le reseau

def test_rien_n_est_pre_autorise_et_l_inconnu_est_DEMANDE():
    """La troisieme issue : ni un refus, ni un acces silencieux."""
    nu = Config(enabled=True)
    verdict = peut_joindre(nu, "registry.npmjs.org")
    assert verdict.autorise
    assert "DEMANDE" in verdict.raison


def test_un_deny_large_l_emporte_sur_un_allow_precis():
    """La couche reseau n'est PAS la couche fichiers : on ne rouvre pas un
    sous-domaine d'un deniedDomains comme on rouvre un sous-dossier."""
    c = Config(enabled=True, network={"allowedDomains": ["gist.github.com"],
                                      "deniedDomains": ["*.github.com"]})
    assert not peut_joindre(c, "gist.github.com").autorise


def test_le_joker_de_tete_couvre_le_domaine_apex():
    c = Config(enabled=True, network={"allowedDomains": ["*.github.com"]})
    for hote in ("api.github.com", "github.com", "a.b.github.com"):
        assert peut_joindre(c, hote).raison.startswith("allowedDomains"), hote


@pytest.mark.parametrize("motif,inerte", [
    ("*.github.com", False), ("*", False), ("github.com", False),
    ("api.*.com", True), ("github.*", True), ("*.*.com", True),
])
def test_seules_deux_formes_de_joker_agissent_sur_le_bac_a_sable(motif, inerte):
    """« A wildcard in any other position still matches fetches but has no
    effect on sandboxed commands. » Une regle qui marche a moitie."""
    assert motif_inerte(motif) is inerte
    c = Config(enabled=True, network={"deniedDomains": [motif]})
    refuse = not peut_joindre(c, "api.github.com").autorise
    assert refuse is (not inerte and motif != "github.com")


def test_strictAllowlist_supprime_la_troisieme_issue():
    c = Config(enabled=True, portee="utilisateur",
               network={"allowedDomains": ["api.github.com"],
                        "strictAllowlist": True})
    assert not peut_joindre(c, "pypi.org").autorise


# ---------------------------------------------------------- LES PORTEES

def test_les_cinq_cles_privilegiees_sont_ignorees_dans_un_depot():
    """« Setting it in a repository's .claude/settings.json or
    .claude/settings.local.json has no effect. » Aucune erreur n'est levee :
    c'est tout le sujet de ce projet."""
    ecrite = Config(
        enabled=True, portee="projet",
        filesystem={"disabled": True},
        network={"strictAllowlist": True, "tlsTerminate": True},
        credentials={"allowPlaintextInject": True,
                     "envVars": [{"name": "T", "mode": "mask"}],
                     "files": [{"path": "~/.netrc", "mode": "mask"}]})
    effective, ignorees = appliquee(ecrite)

    assert len(ignorees) == len(CLES_PRIVILEGIEES) + 1   # mask compte deux fois
    assert not effective.filesystem.get("disabled")
    assert not effective.network.get("strictAllowlist")
    assert not effective.network.get("tlsTerminate")
    assert not effective.credentials.get("allowPlaintextInject")
    assert effective.credentials["envVars"] == []
    assert effective.credentials["files"] == []


@pytest.mark.parametrize("portee", PORTEES_PRIVILEGIEES)
def test_les_memes_cles_s_appliquent_ailleurs(portee):
    ecrite = Config(enabled=True, portee=portee,
                    filesystem={"disabled": True},
                    network={"strictAllowlist": True})
    effective, ignorees = appliquee(ecrite)
    assert ignorees == []
    assert effective.filesystem["disabled"] is True


def test_un_mask_ignore_laisse_LA_VRAIE_VALEUR():
    """Le defaut le plus cher du projet : l'entree n'est ni appliquee NI
    refusee, elle est jetee. La variable garde sa valeur, les commandes la
    lisent en entier, et la configuration qu'on relit dit « mask »."""
    dans_le_depot = Config(
        enabled=True, portee="projet",
        network={"allowedDomains": ["api.github.com"], "tlsTerminate": True},
        credentials={"envVars": [{"name": "GITHUB_TOKEN", "mode": "mask",
                                  "injectHosts": ["api.github.com"]}]})
    (ident,) = identifiants(dans_le_depot)
    assert ident.visible == "LA VRAIE VALEUR"
    assert "IGNORE" in ident.mode


def test_appliquee_est_idempotente():
    """Toutes les fonctions du resolveur l'appellent ; l'appeler deux fois ne
    doit rien enlever de plus."""
    fautive = config("a-corriger", "projet")
    une_fois, premieres = appliquee(fautive)
    deux_fois, secondes = appliquee(une_fois)
    assert premieres and secondes == []
    assert deux_fois == une_fois


# --------------------------------------------------- les couches, ensemble

def test_filesystem_disabled_emporte_le_deny_de_fichier_mais_pas_le_mask():
    """« credentials.files deny read blocks — Not enforced. »
    « credentials.files mask entries applied as masks — Enforced: masking is
    independent of the filesystem layer. »"""
    secrets = {"files": [{"path": "~/.aws/credentials", "mode": "deny"},
                         {"path": "~/.netrc", "mode": "mask"}]}
    active = Config(enabled=True, portee="utilisateur", credentials=secrets)
    coupee = Config(enabled=True, portee="utilisateur", credentials=secrets,
                    filesystem={"disabled": True})

    assert not peut_lire(active, "~/.aws/credentials").autorise
    assert peut_lire(coupee, "~/.aws/credentials").autorise, "le deny tombe"

    for c in (active, coupee):
        verdict = peut_lire(c, "~/.netrc")
        assert verdict.autorise and "sentinelle" in verdict.raison


def test_les_envVars_survivent_a_filesystem_disabled():
    """« Environment variable scrubbing is independent of the filesystem
    layer. »"""
    coupee = Config(enabled=True, portee="utilisateur",
                    filesystem={"disabled": True},
                    credentials={"envVars": [{"name": "T", "mode": "deny"}]})
    (ident,) = identifiants(coupee)
    assert ident.visible == "(rien)"


# ------------------------------------------------------- le verificateur

def test_les_deux_configurations_saines_ne_levent_rien():
    assert verifier(config("depot", "projet")) == []
    assert verifier(config("utilisateur", "utilisateur")) == []


def test_la_configuration_fautive_leve_dans_les_deux_portees():
    """Et pas les memes : corriger la portee REVELE des erreurs qui
    n'existaient pas avant, parce que les masques ignores redeviennent des
    masques et que leurs conditions redeviennent exigibles."""
    en_depot = {s.ou for s in erreurs(config("a-corriger", "projet"))}
    chez_soi = {s.ou for s in erreurs(config("a-corriger", "utilisateur"))}

    assert "network.strictAllowlist" in en_depot
    assert "network.strictAllowlist" not in chez_soi
    assert "credentials / tlsTerminate" in chez_soi
    assert "credentials / tlsTerminate" not in en_depot
    assert "allowedDomains / api.*.com" in en_depot & chez_soi


def test_le_verificateur_ne_reproche_pas_un_chemin_protege_quand_la_couche_est_coupee():
    """Signaler « protege » alors que filesystem.disabled a enleve la couche
    serait faux, et un verificateur qui ment sur un cas rend suspects tous les
    autres. L'avertissement filesystem.disabled les liste a la place."""
    coupee = Config(enabled=True, portee="utilisateur",
                    filesystem={"disabled": True,
                                "allowWrite": [".claude/settings.json"]},
                    network={"allowedDomains": ["a.fr"]},
                    failIfUnavailable=True, allowUnsandboxedCommands=False)
    soucis = verifier(coupee)
    assert erreurs(coupee) == []
    (avertissement,) = soucis
    assert avertissement.ou == "filesystem.disabled"
    assert ".claude/settings.json" in avertissement.message


def test_un_bac_a_sable_desactive_rend_le_reste_decoratif():
    soucis = verifier(Config(enabled=False, portee="projet",
                             network={"allowedDomains": ["a.fr"]}))
    assert len(soucis) == 1
    assert soucis[0].ou == "sandbox.enabled"


def test_un_mask_sur_un_glob_retombe_en_deny():
    """« Claude Code falls back to deny for a mask entry it can't mask
    safely: a directory path, a glob pattern, a file larger than 8 MiB, or a
    file that isn't UTF-8 text. » L'outil casse au lieu de marcher."""
    c = Config(enabled=True, portee="utilisateur",
               network={"allowedDomains": ["a.fr"], "tlsTerminate": True},
               credentials={"files": [{"path": "~/.config/*/token.json",
                                       "mode": "mask"}]})
    assert any("retombe sur deny" in s.message for s in erreurs(c))


# ------------------------------------------------------------ les fichiers livres

def test_les_trois_configurations_sont_du_json_valide():
    for nom in ("depot", "utilisateur", "a-corriger"):
        chemin = RACINE / "configs" / f"{nom}.json"
        donnees = json.loads(chemin.read_text(encoding="utf-8"))
        assert "sandbox" in donnees
        assert donnees["$comment"], f"{nom} doit dire a quoi il sert"


def test_depot_json_ne_contient_aucune_cle_privilegiee():
    """C'est ce qui en fait un exemple utilisable : un fichier partage ne doit
    rien contenir qui soit ignore en silence."""
    _, ignorees = appliquee(config("depot", "projet"))
    assert ignorees == []
