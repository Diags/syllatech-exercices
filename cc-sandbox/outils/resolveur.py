#!/usr/bin/env python3
"""Le résolveur — « ce chemin est-il écrivable ? ce domaine est-il joignable ? »

    python outils/resolveur.py configs/atelier.json --ecrire ~/.ssh/id_rsa
    python outils/resolveur.py configs/atelier.json --joindre api.github.com

POURQUOI CET OUTIL

Un bac à sable ne se teste pas en le regardant. Trois choses se combinent :

1. **La spécificité.** Un `denyRead` tient à l'intérieur d'un `allowRead` plus
   large, et un `allowRead` plus étroit rouvre une partie d'un `denyRead`. Ce
   n'est ni « deny d'abord » ni « allow d'abord » : la règle la plus longue
   gagne, comme pour des routes.
2. **Les chemins protégés**, que *rien* ne peut rouvrir — sauf une clé, et
   elle coupe toute la couche.
3. **La portée.** Plusieurs clés ne sont honorées que depuis les réglages
   utilisateur, gérés ou `--settings`. Écrites dans le `.claude/settings.json`
   d'un dépôt, elles sont **ignorées en silence**.

C'est la troisième qui coûte le plus cher, parce qu'elle ne ressemble pas à
une erreur : la clé est au bon endroit du JSON, bien orthographiée, relue par
deux personnes — et sans effet.

⚠️ CE N'EST PAS LE BAC À SABLE. C'est un modèle de ses règles, écrit d'après
la documentation, qui répond à la même question. Le vrai bac à sable tourne
sur macOS, Linux et WSL2 — **pas sur Windows natif**. Sur cette machine, on ne
peut donc que raisonner : ce module rend ce raisonnement exécutable et
testable, ce qui vaut mieux que de le garder en tête.

La constante `LIMITES`, en bas, dit ce qu'il ne modélise pas.
"""

from __future__ import annotations

import fnmatch
import json
import sys
from dataclasses import dataclass, field, replace
from pathlib import PurePosixPath

for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except Exception:      # noqa: BLE001
        pass


# ------------------------------------------------------- les chemins protégés
#
# Le bac à sable refuse l'écriture sur ces chemins QUOI QU'ON ÉCRIVE.
#
# « There is no way to exempt one of these paths: an allowWrite entry or an
# Edit allow rule that covers the path doesn't lift the protection. »
#
# La raison est structurelle : une commande qui pourrait éditer ces fichiers
# pourrait s'accorder des permissions, ou ajouter un hook que Claude Code
# exécute HORS du bac à sable. Le bac à sable se refermerait lui-même.

# Groupe 1 — « In your working directory and the directories above it ».
PROTEGES_REMONTEE = [
    ".claude/settings.json", ".claude/settings.local.json",
    ".claude/skills/**", ".claude/agents/**", ".claude/commands/**",
    ".claude/hooks/**", ".claude/workflows/**",
    ".claude/scheduled_tasks.json", ".mcp.json",
]

# Groupe 2 — « In your working directory only ».
PROTEGES_A_LA_RACINE = [
    ".bashrc", ".zshrc", ".gitconfig", ".vscode/**", ".idea/**",
    ".git/hooks/**", ".git/config",
]

# Groupe 3 — ce qui ferait du dossier de travail un dépôt git nu.
PROTEGES_DEPOT_NU = ["HEAD", "objects/**", "refs/**"]

# ⚠️ Et, dans le même groupe, « config » et « hooks » à la racine — mais
# SEULEMENT s'ils existent déjà. « even when the config directory belongs to
# your project rather than to git » : un projet qui a un dossier « config/ » à
# sa racine découvre que les commandes sandboxées ne peuvent pas y écrire. Ce
# n'est pas un bug, c'est cette règle.
PROTEGES_DEPOT_NU_SI_EXISTANTS = ["config/**", "hooks/**"]

# Groupe 4 — « In ~/.claude, or the directory CLAUDE_CONFIG_DIR points to ».
PROTEGES_MAISON = [
    ".claude/**", ".claude.json", ".claude/.credentials.json",
]


# ---------------------------------------------------------------- les portées
#
# Certaines clés élargissent ce que les commandes sandboxées peuvent faire.
# Claude Code ne les honore donc que depuis des réglages que VOUS contrôlez :
# utilisateur, gérés, ou « --settings ». Dans le .claude/settings.json d'un
# dépôt — un fichier qu'un « git pull » peut modifier — elles sont ignorées.
#
# Aucune erreur n'est levée. C'est le sujet de tout ce projet.

PORTEES = ("projet", "utilisateur", "gere", "cli")
PORTEES_PRIVILEGIEES = ("utilisateur", "gere", "cli")

CLES_PRIVILEGIEES: dict[str, str] = {
    "filesystem.disabled":
        "couper l'isolation des fichiers depuis un fichier du depot "
        "permettrait a un depot clone de se desandboxer lui-meme",
    "network.strictAllowlist":
        "un depot pourrait sinon transformer une demande en refus, ou "
        "l'inverse, sans que personne ne le relise",
    "network.tlsTerminate":
        "terminer TLS est un dechiffrement : il ne s'active pas depuis un "
        "fichier partage",
    "credentials.allowPlaintextInject":
        "injecter un secret dans une requete en clair ne s'autorise pas "
        "depuis un fichier partage",
    "credentials[].mode=mask":
        "masquer AUTORISE le proxy a envoyer le vrai secret aux injectHosts. "
        "Un depot ne choisit pas a qui vos secrets sont envoyes",
}


@dataclass
class Ignoree:
    """Une clé écrite, acceptée, et sans aucun effet."""

    cle: str
    portee: str
    pourquoi: str
    consequence: str
    noms: tuple[str, ...] = ()

    def __str__(self) -> str:
        return f"{self.cle} (portee « {self.portee} ») : {self.consequence}"


@dataclass
class Verdict:
    autorise: bool
    raison: str
    regle: str = ""

    def __str__(self) -> str:
        return f"{'AUTORISE' if self.autorise else 'REFUSE  '}  {self.raison}"


@dataclass
class Config:
    """Un bloc « sandbox » de settings.json, lu et normalisé."""

    enabled: bool = False
    failIfUnavailable: bool = False
    allowUnsandboxedCommands: bool = True
    autoAllowBashIfSandboxed: bool = True
    filesystem: dict = field(default_factory=dict)
    network: dict = field(default_factory=dict)
    credentials: dict = field(default_factory=dict)
    portee: str = "projet"

    @classmethod
    def depuis(cls, donnees: dict, portee: str = "projet") -> "Config":
        bac = donnees.get("sandbox", donnees)
        return cls(
            enabled=bool(bac.get("enabled", False)),
            failIfUnavailable=bool(bac.get("failIfUnavailable", False)),
            allowUnsandboxedCommands=bool(
                bac.get("allowUnsandboxedCommands", True)),
            autoAllowBashIfSandboxed=bool(
                bac.get("autoAllowBashIfSandboxed", True)),
            filesystem=dict(bac.get("filesystem") or {}),
            network=dict(bac.get("network") or {}),
            credentials=dict(bac.get("credentials") or {}),
            portee=portee,
        )

    @classmethod
    def fichier(cls, chemin, portee: str = "projet") -> "Config":
        from pathlib import Path
        return cls.depuis(json.loads(Path(chemin).read_text(encoding="utf-8")),
                          portee)


# ----------------------------------------- la configuration TELLE QU'APPLIQUÉE

def appliquee(config: Config) -> tuple[Config, list[Ignoree]]:
    """Rend la configuration QUI S'APPLIQUE, et la liste de ce qui a été jeté.

    C'est la fonction centrale du module, et c'est celle qu'on n'écrit jamais
    quand on relit une configuration à l'œil : on lit ce qui est écrit, pas ce
    qui s'applique. Entre les deux, il y a la portée.

    Toutes les autres fonctions passent par ici. Poser une question sur la
    configuration écrite plutôt que sur la configuration appliquée donnerait
    la bonne réponse à la mauvaise question.
    """
    # TODO : rendre la configuration APPLIQUEE et la liste des cles jetees. Hors des portees privilegiees, cinq cles sont ignorees : filesystem.disabled, network.strictAllowlist, network.tlsTerminate, credentials.allowPlaintextInject, et toute entree credentials en mode mask (envVars ET files). Un mask ignore ne devient pas un deny : l'entree DISPARAIT, donc la vraie valeur reste lisible. Cinq tests le verifient.
    return config, []


# ---------------------------------------------------------------- les chemins

def _normaliser(chemin: str, travail: str = "/projet",
                maison: str = "/home/moi") -> str:
    chemin = chemin.replace("\\", "/")
    if chemin.startswith("~"):
        return (maison + chemin[1:]).rstrip("/") or maison
    if chemin.startswith("."):
        if chemin in (".", "./"):
            return travail
        # ⚠️ lstrip("./") retirerait TOUS les « . » et « / » de tête, donc
        # « .claude/settings.json » deviendrait « claude/settings.json ». Le
        # chemin protégé ne serait plus reconnu, et la protection disparaîtrait
        # sans que rien ne le dise. lstrip prend un ENSEMBLE de caractères, pas
        # un préfixe — c'est le piège classique.
        return f"{travail}/{chemin.removeprefix('./')}"
    if not chemin.startswith("/"):
        return f"{travail}/{chemin}"
    return chemin


def _sous(chemin: str, prefixe: str) -> bool:
    """Le chemin est-il couvert par ce préfixe ?

    Un préfixe couvre le chemin lui-même ET tout ce qui est dessous : lister
    « ~/projets » autorise « ~/projets/a/b.txt ». Une étoile reste un glob.
    """
    if "*" in prefixe:
        return fnmatch.fnmatchcase(chemin, prefixe) or fnmatch.fnmatchcase(
            chemin, prefixe.rstrip("/*") + "/*")
    if chemin == prefixe:
        return True
    return chemin.startswith(prefixe.rstrip("/") + "/")


def _plus_specifique(chemin: str,
                     regles: list[tuple[str, bool]]) -> tuple[bool, str] | None:
    """La règle la PLUS LONGUE qui couvre le chemin gagne.

    C'est ce que décrit la documentation : un « denyRead » tient à l'intérieur
    d'un « allowRead » plus large, et un « allowRead » plus étroit rouvre une
    partie d'un « denyRead ». La conséquence pratique : **l'ordre des entrées
    dans le JSON ne change rien**. Un test le vérifie en les mélangeant.
    """
    # TODO : rendre (autorise, prefixe) de la regle la PLUS LONGUE qui couvre le chemin, ou None si aucune ne le couvre. Ni « deny d'abord » ni « allow d'abord » : la specificite tranche, et c'est ce qui rend le resultat independant de l'ordre des entrees. Un test le verifie sur les 720 permutations de six regles.
    return None


def _remontee(travail: str) -> list[str]:
    chemin = PurePosixPath(travail)
    return [str(p) for p in [chemin, *chemin.parents] if str(p) != "/"] or [travail]


def protege(chemin: str, travail: str = "/projet", maison: str = "/home/moi",
            existants: set[str] | None = None) -> str | None:
    """Rend le motif protégé qui couvre ce chemin, ou None.

    « existants » liste les noms présents à la racine du dossier de travail :
    « config » et « hooks » ne sont protégés que **s'ils existent déjà**.
    """
    # TODO : rendre le motif protege qui couvre ce chemin, ou None. Quatre groupes : PROTEGES_REMONTEE dans le dossier de travail ET ses parents, PROTEGES_A_LA_RACINE et PROTEGES_DEPOT_NU dans le dossier de travail seul, PROTEGES_DEPOT_NU_SI_EXISTANTS seulement si le nom est dans « existants », PROTEGES_MAISON sous le dossier personnel. Attention : un prefixe de CHAINE n'est pas un prefixe de CHEMIN — passer par _sous. Vingt-cinq tests le verifient.
    return None


def peut_ecrire(config: Config, chemin: str, travail: str = "/projet",
                maison: str = "/home/moi",
                existants: set[str] | None = None) -> Verdict:
    config, _ = appliquee(config)
    if not config.enabled:
        return Verdict(True, "bac a sable desactive : aucune restriction")
    if config.filesystem.get("disabled"):
        return Verdict(True, "filesystem.disabled : plus aucune protection de "
                             "fichier, chemins proteges compris")

    motif = protege(chemin, travail, maison, existants)
    if motif:
        return Verdict(False,
                       f"chemin PROTEGE ({motif}) — un allowWrite ne leve PAS "
                       f"cette protection", motif)

    cible = _normaliser(chemin, travail, maison)
    regles = ([(_normaliser(p, travail, maison), True)
               for p in config.filesystem.get("allowWrite", [])]
              + [(_normaliser(p, travail, maison), False)
                 for p in config.filesystem.get("denyWrite", [])])
    verdict = _plus_specifique(cible, regles)
    if verdict is None:
        # Par défaut, une commande sandboxée écrit dans son dossier de travail.
        if _sous(cible, travail):
            return Verdict(True, "dans le dossier de travail (defaut)")
        return Verdict(False, "hors du dossier de travail, et aucun allowWrite")
    autorise, prefixe = verdict
    return Verdict(autorise,
                   f"{'allowWrite' if autorise else 'denyWrite'} « {prefixe} »",
                   prefixe)


def peut_lire(config: Config, chemin: str, travail: str = "/projet",
              maison: str = "/home/moi") -> Verdict:
    config, _ = appliquee(config)
    if not config.enabled:
        return Verdict(True, "bac a sable desactive")

    cible = _normaliser(chemin, travail, maison)
    coupee = bool(config.filesystem.get("disabled"))

    # ⚠️ Les deux modes de « credentials.files » ne survivent PAS à la même
    # chose. « deny » est un blocage de lecture : il appartient à la couche
    # fichiers, et il tombe avec elle. « mask » remplace le CONTENU par une
    # sentinelle : c'est le proxy, pas la couche fichiers, et il tient.
    #
    # « credentials.files deny read blocks — Not enforced. The filesystem
    #   layer applies both. »
    # « credentials.files mask entries applied as masks — Enforced: masking is
    #   independent of the filesystem layer. »
    for entree in config.credentials.get("files", []):
        if not _sous(cible, _normaliser(entree["path"], travail, maison)):
            continue
        mode = entree.get("mode", "deny")
        if mode == "mask":
            return Verdict(True, f"credentials.files « {entree['path']} » "
                                 f"(mask) : LISIBLE, mais le contenu lu est "
                                 f"une sentinelle", entree["path"])
        if not coupee:
            return Verdict(False, f"credentials.files « {entree['path']} » "
                                  f"(deny)", entree["path"])
        return Verdict(True, f"credentials.files « {entree['path']} » (deny) "
                             f"MAIS filesystem.disabled : un blocage de "
                             f"lecture appartient a la couche fichiers",
                       entree["path"])

    if coupee:
        return Verdict(True, "filesystem.disabled : denyRead sans effet")

    regles = ([(_normaliser(p, travail, maison), True)
               for p in config.filesystem.get("allowRead", [])]
              + [(_normaliser(p, travail, maison), False)
                 for p in config.filesystem.get("denyRead", [])])
    verdict = _plus_specifique(cible, regles)
    if verdict is None:
        # « Default read behavior: read access to the entire computer. »
        return Verdict(True, "aucune regle : lisible par defaut")
    autorise, prefixe = verdict
    return Verdict(autorise,
                   f"{'allowRead' if autorise else 'denyRead'} « {prefixe} »",
                   prefixe)


# ------------------------------------------------------------------ le réseau

def peut_joindre(config: Config, hote: str) -> Verdict:
    config, _ = appliquee(config)
    if not config.enabled:
        return Verdict(True, "bac a sable desactive")

    reseau = config.network
    for motif in reseau.get("deniedDomains", []):
        if _domaine(hote, motif):
            return Verdict(False, f"deniedDomains « {motif} »", motif)
    for motif in reseau.get("allowedDomains", []):
        if _domaine(hote, motif):
            return Verdict(True, f"allowedDomains « {motif} »", motif)

    if reseau.get("strictAllowlist"):
        return Verdict(False, "strictAllowlist : hors liste = refuse, sans "
                              "demander", "strictAllowlist")
    # « Claude Code pre-allows no domains by default. The first time a command
    #   needs a new domain, Claude Code prompts for approval. »
    return Verdict(True, "hors liste : Claude Code DEMANDE (ce n'est ni un "
                         "refus, ni un acces silencieux)")


def _domaine(hote: str, motif: str) -> bool:
    """Les deux seules formes de joker que le bac à sable honore.

    « the sandbox honors two wildcard forms: a leading *. and a bare *. A
    wildcard in any other position, such as example.*, still matches fetches
    but has no effect on sandboxed commands. »

    Donc « api.*.com » ne bloque ni n'autorise rien côté bac à sable — alors
    qu'il agit toujours sur WebFetch. Une règle qui marche à moitié, et c'est
    la moitié silencieuse qui ne marche pas. « motif_inerte » la signale.
    """
    if motif == "*":
        return True
    if motif.startswith("*.") and "*" not in motif[2:]:
        return hote == motif[2:] or hote.endswith(motif[1:])
    if "*" in motif:
        return False            # joker mal placé : inerte pour le bac à sable
    return hote == motif


def motif_inerte(motif: str) -> bool:
    return "*" in motif and motif != "*" and not (
        motif.startswith("*.") and "*" not in motif[2:])


# ----------------------------------------------------------- les identifiants

@dataclass
class Identifiant:
    nom: str
    mode: str
    visible: str
    remarque: str = ""


def identifiants(config: Config) -> list[Identifiant]:
    """Ce qu'une commande sandboxée voit réellement de chaque variable."""
    effective, ignorees = appliquee(config)
    sortie: list[Identifiant] = []

    for perdue in ignorees:
        if perdue.cle == "credentials.envVars[].mode=mask":
            for nom in perdue.noms:
                sortie.append(Identifiant(
                    nom, "mask (IGNORE)", "LA VRAIE VALEUR",
                    "entree ignoree hors des reglages utilisateur, geres ou "
                    "CLI : ni masquee, ni refusee"))

    for entree in effective.credentials.get("envVars", []):
        nom, mode = entree["name"], entree.get("mode", "deny")
        if mode == "deny":
            sortie.append(Identifiant(nom, mode, "(rien)",
                                      "la variable est retiree : les outils "
                                      "qui en ont besoin cassent"))
            continue

        remarques = []
        if not effective.network.get("tlsTerminate"):
            remarques.append(
                "network.tlsTerminate absent : le masquage ECHOUE — la "
                "sentinelle part telle quelle et l'authentification rate")
        for hote in entree.get("injectHosts", []):
            if not any(_domaine(hote, m)
                       for m in effective.network.get("allowedDomains", [])):
                remarques.append(
                    f"injectHosts « {hote} » n'est pas dans allowedDomains : "
                    f"la vraie valeur n'y sera jamais injectee")
            if hote.startswith("["):
                remarques.append(
                    f"injectHosts « {hote} » est crochete : cette liste-la "
                    f"veut l'adresse NUE, elle ne correspondra jamais")
        sortie.append(Identifiant(nom, mode, "une sentinelle",
                                  " ; ".join(remarques)))
    return sortie


# -------------------------------------------------------------- ce qui manque

LIMITES = """\
Ce module modelise les REGLES du bac a sable, pas le bac a sable.

Il ne modelise pas :
  · les differences entre Seatbelt (macOS) et seccomp/bubblewrap (Linux) —
    notamment qu'un « mask » de FICHIER est applique comme un « deny » sur
    macOS tant que l'isolation des fichiers est active ;
  · le repli d'un « mask » vers « deny » quand la cible est un dossier, un
    glob, un fichier de plus de 8 Mio ou du non-UTF-8 ;
  · les champs « extract », « decode », « maskClaims » et « maskDuplicates » ;
  · la suppression, sous Linux, d'un HEAD/objects/refs apparu pendant qu'une
    commande tourne ;
  · les regles WebFetch(domain:...) qui alimentent aussi la liste, ni les
    formes ambigues d'adresse IPv6 ;
  · les sockets Unix, les processus deja lances, et tout ce qui ne passe ni
    par un chemin ni par un domaine.

Et il ne s'execute pas sur Windows natif, parce que le bac a sable non plus :
la documentation demande WSL2.
"""


# --------------------------------------------------------- ligne de commande

def main() -> int:
    arguments = sys.argv[1:]
    if not arguments:
        print(__doc__)
        return 0
    portee = (arguments[arguments.index("--portee") + 1]
              if "--portee" in arguments else "projet")
    config = Config.fichier(arguments[0], portee=portee)

    for drapeau, fonction in (("--ecrire", peut_ecrire), ("--lire", peut_lire)):
        if drapeau in arguments:
            cible = arguments[arguments.index(drapeau) + 1]
            print(f"\n  {cible}\n  {fonction(config, cible)}\n")
            return 0
    if "--joindre" in arguments:
        hote = arguments[arguments.index("--joindre") + 1]
        print(f"\n  {hote}\n  {peut_joindre(config, hote)}\n")
        return 0

    _, ignorees = appliquee(config)
    print(f"\n  {arguments[0]}  (portee : {portee})\n")
    for perdue in ignorees:
        print(f"  IGNOREE  {perdue}")
    if not ignorees:
        print("  Toutes les cles de cette configuration s'appliquent.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
