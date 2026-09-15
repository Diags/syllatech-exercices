#!/usr/bin/env python3
"""Le vérificateur de configuration — ce qui casse ENTRE les fichiers.

    python outils/verifier_config.py [dossier]
    python outils/verifier_config.py --ci       code 1 s'il reste une erreur

POURQUOI CET OUTIL

Chaque cours Claude Code vérifie sa propre pièce : `/hooks` liste les hooks,
`/doctor` relit les skills, `claude mcp list` teste les serveurs. Personne ne
vérifie la **cohérence entre les pièces**, et c'est là que se trouve le
pourrissement réel d'un `.claude/` :

  · un hook qui appelle un script supprimé il y a trois mois ;
  · un sous-agent qui déclare un outil dont le nom a changé ;
  · une règle de permission MCP qui nomme un serveur retiré du `.mcp.json` ;
  · un `CLAUDE.md` qui documente `npm run check` alors que le script s'appelle
    `lint` depuis la refonte.

Aucun de ces défauts ne lève d'erreur. Tous se voient à l'usage, une fois. Le
dernier est le plus coûteux, parce que `CLAUDE.md` est lu **à chaque session** :
une commande fausse y est répétée à l'agent des centaines de fois.

⚠️ UNE PRÉCAUTION SUR LA LISTE D'OUTILS

`OUTILS_CONNUS` est un instantané. Claude Code en ajoute ; un nom absent de
cette liste n'est donc pas forcément une faute. C'est pourquoi un outil inconnu
produit un **avertissement**, jamais une erreur : un vérificateur qui crie faux
finit désactivé, et il emporte avec lui les contrôles qui étaient justes.
"""

from __future__ import annotations

import json
import re
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path

for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except Exception:      # noqa: BLE001
        pass

# Les outils intégrés, tels qu'on les nomme dans un « tools: » de sous-agent,
# dans un matcher de hook, ou dans une règle de permission.
OUTILS_CONNUS = {
    "Bash", "Edit", "Glob", "Grep", "Read", "Write", "NotebookEdit",
    "WebFetch", "WebSearch", "TodoWrite", "Task", "Agent", "Skill",
    "PowerShell", "ToolSearch", "AskUserQuestion", "SlashCommand",
}

# Les évènements de hook. Un nom mal orthographié ici ne déclenche jamais rien.
EVENEMENTS = {
    "PreToolUse", "PostToolUse", "UserPromptSubmit", "Notification",
    "Stop", "SubagentStop", "PreCompact", "SessionStart", "SessionEnd",
}

# Ce qui, dans un `.mcp.json` versionné, ne doit jamais être écrit en clair.
SECRET = re.compile(r"(?:Bearer\s+|token|key|secret|password|pat)[\"'\s:=]*"
                    r"([A-Za-z0-9_\-]{16,})", re.IGNORECASE)


@dataclass
class Souci:
    gravite: str        # "erreur" ou "attention"
    ou: str
    message: str


# ------------------------------------------------------------------ lecture

def _charger(chemin: Path) -> dict:
    if not chemin.exists():
        return {}
    try:
        return json.loads(chemin.read_text(encoding="utf-8"))
    except ValueError as souci:
        raise ValueError(f"{chemin.name} : JSON invalide — {souci}") from souci


def _frontmatter(texte: str) -> tuple[dict, str]:
    if not texte.startswith("---"):
        return {}, texte
    fin = texte.find("\n---", 3)
    if fin == -1:
        return {}, texte
    champs, cle = {}, None
    for ligne in texte[3:fin].splitlines():
        if not ligne.strip():
            continue
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", ligne)
        if m:
            cle = m.group(1)
            champs[cle] = m.group(2).strip()
        elif cle and ligne.startswith((" ", "\t")):
            champs[cle] = (champs[cle] + " " + ligne.strip()).strip()
    return champs, texte[fin + 4:]


# ------------------------------------------------------------- les contrôles

def verifier_hooks(racine: Path, reglages: dict) -> list[Souci]:
    soucis: list[Souci] = []
    for evenement, entrees in (reglages.get("hooks") or {}).items():
        if evenement not in EVENEMENTS:
            soucis.append(Souci("erreur", f"hooks/{evenement}",
                                "evenement inconnu : ce hook ne se declenchera "
                                f"JAMAIS. Connus : {', '.join(sorted(EVENEMENTS))}"))
        for entree in entrees or []:
            matcher = entree.get("matcher", "")
            for nom in re.split(r"[|,]", matcher):
                nom = nom.strip()
                if nom and nom not in OUTILS_CONNUS and not re.search(r"[*.]", nom):
                    soucis.append(Souci("attention", f"hooks/{evenement}",
                                        f"matcher « {nom} » : outil inconnu de "
                                        "cette liste. Faute de frappe ?"))
            for hook in entree.get("hooks") or []:
                soucis += _verifier_commande(racine, f"hooks/{evenement}",
                                             hook.get("command", ""))
    return soucis


def _verifier_commande(racine: Path, ou: str, commande: str) -> list[Souci]:
    """Le script appelé existe-t-il ?

    Le défaut le plus courant d'un `.claude/` ancien : le hook survit au
    script. Il échoue alors à chaque déclenchement, et l'échec d'un hook ne
    remonte pas toujours jusqu'à vous.
    """
    soucis = []
    for morceau in shlex.split(commande, posix=False):
        morceau = morceau.strip('"\'')
        if not re.search(r"\.(py|sh|js|mjs|ts)$", morceau):
            continue
        # >>> depart: verifier que le script existe, apres avoir retire le prefixe $CLAUDE_PROJECT_DIR/ (ou ${CLAUDE_PROJECT_DIR}/). Le hook survit au script : il echoue alors a chaque declenchement, et l'echec d'un hook ne remonte pas toujours. Deux tests le verifient.
        #     continue
        chemin = morceau.replace("$CLAUDE_PROJECT_DIR/", "").replace(
            "${CLAUDE_PROJECT_DIR}/", "")
        if not (racine / chemin).exists():
            soucis.append(Souci("erreur", ou,
                                f"le script « {chemin} » n'existe pas. Le hook "
                                "echouera a chaque declenchement."))
        # <<<
    return soucis


def verifier_agents(racine: Path) -> list[Souci]:
    soucis: list[Souci] = []
    dossier = racine / ".claude" / "agents"
    for fichier in sorted(dossier.glob("*.md")) if dossier.exists() else []:
        champs, _ = _frontmatter(fichier.read_text(encoding="utf-8"))
        ou = f"agents/{fichier.stem}"
        for obligatoire in ("name", "description"):
            if obligatoire not in champs:
                soucis.append(Souci("erreur", ou,
                                    f"« {obligatoire} » absent : l'agent ne "
                                    "sera jamais choisi automatiquement."))
        if champs.get("name", fichier.stem) != fichier.stem:
            soucis.append(Souci("attention", ou,
                                f"« name: {champs['name']} » differe du fichier "
                                f"— l'agent s'invoque par {fichier.stem}"))
        for outil in [o.strip() for o in champs.get("tools", "").split(",") if o.strip()]:
            if outil not in OUTILS_CONNUS and not outil.startswith("mcp__"):
                soucis.append(Souci("attention", ou,
                                    f"outil « {outil} » inconnu de cette liste"))
    return soucis


def verifier_skills(racine: Path) -> list[Souci]:
    soucis: list[Souci] = []
    dossier = racine / ".claude" / "skills"
    for skill in sorted(d for d in dossier.iterdir() if d.is_dir()) \
            if dossier.exists() else []:
        fichier = skill / "SKILL.md"
        ou = f"skills/{skill.name}"
        if not fichier.exists():
            soucis.append(Souci("erreur", ou, "SKILL.md absent : dossier ignore"))
            continue
        texte = fichier.read_text(encoding="utf-8")
        champs, corps = _frontmatter(texte)
        if not champs.get("description"):
            soucis.append(Souci("erreur", ou,
                                "pas de description : la skill ne se "
                                "declenchera jamais toute seule."))
        for m in re.finditer(r"(?:^|\s)(?:node|python|python3|bash|sh)\s+"
                             r"([^\s`]+\.(?:js|mjs|py|sh))", corps):
            chemin = m.group(1)
            if chemin.startswith(("${CLAUDE_SKILL_DIR}", "${CLAUDE_PLUGIN_ROOT}",
                                  "/", "~")):
                continue
            soucis.append(Souci("erreur", ou,
                                f"« {chemin} » : chemin relatif au dossier de "
                                f"travail, pas a la skill. Ecrivez "
                                f"${{CLAUDE_SKILL_DIR}}/{chemin}"))
        for m in re.finditer(r"\$\{CLAUDE_SKILL_DIR\}/([^\s`\"')]+)", texte):
            if not (skill / m.group(1)).exists():
                soucis.append(Souci("erreur", ou,
                                    f"script reference mais absent : {m.group(1)}"))
    return soucis


def verifier_mcp(racine: Path, reglages: dict) -> list[Souci]:
    soucis: list[Souci] = []
    fichier = racine / ".mcp.json"
    serveurs: set[str] = set()
    if fichier.exists():
        brut = fichier.read_text(encoding="utf-8")
        for m in SECRET.finditer(brut):
            if "${" in brut[max(0, m.start() - 40):m.end()]:
                continue
            soucis.append(Souci("erreur", ".mcp.json",
                                f"secret en clair « {m.group(1)[:8]}… » : ce "
                                "fichier est versionne. Utilisez ${VARIABLE}."))
        serveurs = set(json.loads(brut).get("mcpServers", {}))

    # LE contrôle croisé : une règle qui nomme un serveur absent.
    permissions = reglages.get("permissions") or {}
    # >>> depart: signaler chaque regle « mcp__<serveur>__<outil> » dont le SERVEUR est absent de .mcp.json. La regle est acceptee, elle a l'air de proteger, et elle ne protege rien — aucun avertissement ne le dit.
    #     pass
    for genre in ("allow", "deny", "ask"):
        for regle in permissions.get(genre) or []:
            m = re.match(r"^mcp__([^_]+(?:_[^_]+)*)__", regle)
            if not m:
                continue
            serveur = m.group(1)
            if serveur not in serveurs:
                soucis.append(Souci("erreur", f"{genre} / {regle}",
                                    f"le serveur « {serveur} » n'est pas dans "
                                    ".mcp.json. La regle ne protege rien, et "
                                    "aucun avertissement ne le dit."))
    # <<<
    return soucis


def verifier_claude_md(racine: Path) -> list[Souci]:
    """Le contrôle que personne ne fait, et qui coûte le plus cher.

    `CLAUDE.md` est relu à CHAQUE session. Une commande fausse y est répétée à
    l'agent des centaines de fois, et il la lance des centaines de fois.
    """
    soucis: list[Souci] = []
    fichier = racine / "CLAUDE.md"
    if not fichier.exists():
        return [Souci("attention", "CLAUDE.md",
                      "absent : l'agent redecouvre le projet a chaque session")]
    texte = fichier.read_text(encoding="utf-8")

    scripts = set()
    paquet = racine / "package.json"
    if paquet.exists():
        scripts = set(json.loads(paquet.read_text(encoding="utf-8"))
                      .get("scripts", {}))

    # >>> depart: signaler chaque « npm run X » de CLAUDE.md absent de package.json. CLAUDE.md est relu a CHAQUE session : une commande fausse y est repetee a l'agent des centaines de fois, et il la lance des centaines de fois. Trois tests le verifient.
    #     pass
    for m in re.finditer(r"npm run ([\w:-]+)", texte):
        if scripts and m.group(1) not in scripts:
            soucis.append(Souci("erreur", "CLAUDE.md",
                                f"« npm run {m.group(1)} » n'existe pas dans "
                                f"package.json (scripts : {', '.join(sorted(scripts))})"))

    # <<<
    for m in re.finditer(r"[Ss]ous-agent `([\w-]+)`", texte):
        if not (racine / ".claude" / "agents" / f"{m.group(1)}.md").exists():
            soucis.append(Souci("erreur", "CLAUDE.md",
                                f"sous-agent « {m.group(1)} » documente mais "
                                "absent de .claude/agents/"))

    for m in re.finditer(r"[Ss]kill `([\w-]+)`", texte):
        if not (racine / ".claude" / "skills" / m.group(1) / "SKILL.md").exists():
            soucis.append(Souci("erreur", "CLAUDE.md",
                                f"skill « {m.group(1)} » documentee mais "
                                "absente de .claude/skills/"))

    for m in re.finditer(r"[Ss]erveur MCP `([\w-]+)`", texte):
        config = _charger(racine / ".mcp.json")
        if m.group(1) not in (config.get("mcpServers") or {}):
            soucis.append(Souci("erreur", "CLAUDE.md",
                                f"serveur MCP « {m.group(1)} » documente mais "
                                "absent de .mcp.json"))

    for m in re.finditer(r"`([\w/]+/)`", texte):
        chemin = racine / m.group(1)
        if not chemin.exists():
            soucis.append(Souci("attention", "CLAUDE.md",
                                f"le dossier « {m.group(1)} » n'existe pas"))
    return soucis


def verifier(racine: Path) -> list[Souci]:
    reglages = _charger(racine / ".claude" / "settings.json")
    return (verifier_hooks(racine, reglages)
            + verifier_agents(racine)
            + verifier_skills(racine)
            + verifier_mcp(racine, reglages)
            + verifier_claude_md(racine))


def main() -> int:
    arguments = [a for a in sys.argv[1:] if not a.startswith("--")]
    racine = Path(arguments[0]) if arguments else Path(__file__).resolve().parent.parent

    soucis = verifier(racine)
    erreurs = [s for s in soucis if s.gravite == "erreur"]

    print(f"\n  Configuration verifiee : {racine}\n")
    for s in soucis:
        marque = "ERREUR    " if s.gravite == "erreur" else "attention "
        print(f"  {marque} {s.ou}")
        print(f"             {s.message}")
    if not soucis:
        print("  Aucun probleme detecte.")
    print(f"\n  {len(erreurs)} erreur(s), {len(soucis) - len(erreurs)} avertissement(s)")

    if "--ci" in sys.argv:
        return 1 if erreurs else 0
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
