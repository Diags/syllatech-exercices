#!/usr/bin/env python3
"""Verifier une skill AVANT de l'installer.

    uv run python outils/verifier_skill.py jobportal/skills/piegee
    uv run python outils/verifier_skill.py ~/.hermes/skills/une-skill

Il fait deux choses, avec le code de Hermes :

  · il ANALYSE le SKILL.md (agent.skill_utils) et signale ce qui empechera
    la skill d'etre trouvee, choisie ou conditionnee correctement ;
  · il SCANNE les fichiers (tools.skills_guard) et signale les menaces.

Les defauts de la premiere famille ne levent rien : la skill se charge, elle
apparait dans la liste, et elle ne sert jamais. Ceux de la seconde ne levent
rien non plus — jusqu'au jour ou ils servent.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal.competences import Competence          # noqa: E402
from jobportal.gardes import invisibles, scanner      # noqa: E402

for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except Exception:      # noqa: BLE001
        pass

GRAVITES = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def verifier(dossier: Path) -> tuple[list[str], list]:
    """Rend (defauts de forme, trouvailles du scanner)."""
    # >>> depart: rendre (defauts de forme, trouvailles du scanner). Les premiers viennent de Competence.defauts(), plus le cas « plateformes excluant cette machine » ; les secondes de skills_guard.scan_file sur CHAQUE fichier du dossier, triees par gravite. Deux tests le verifient.
    #     return [], []
    skill = dossier / "SKILL.md"
    if not skill.exists():
        return ([f"aucun SKILL.md dans {dossier}"], [])

    competence = Competence.depuis(dossier.name,
                                   skill.read_text(encoding="utf-8"))
    defauts = competence.defauts()
    if not competence.proposee_ici:
        defauts.append(
            f"« platforms: {competence.plateformes} » exclut cette machine "
            f"({sys.platform}) : la skill ne sera pas proposee, et rien ne "
            f"le dira")

    trouvailles = []
    for fichier in sorted(p for p in dossier.rglob("*") if p.is_file()):
        trouvailles += scanner(fichier)
    trouvailles.sort(key=lambda t: GRAVITES.get(t.severity, 9))
    return defauts, trouvailles
    # <<<


def main() -> int:
    logging.disable(logging.CRITICAL)
    chemins = [a for a in sys.argv[1:] if not a.startswith("--")]
    dossier = Path(chemins[0] if chemins else "jobportal/skills/piegee")

    defauts, trouvailles = verifier(dossier)
    critiques = [t for t in trouvailles if t.severity in ("critical", "high")]

    print(f"\n  {dossier}\n")
    for defaut in defauts:
        print("  DEFAUT     " + "\n             ".join(_plier(defaut, 62)))
    for trouvaille in trouvailles:
        print(f"  {trouvaille.severity.upper():<10} {trouvaille.category} — "
              f"{trouvaille.description}")
        print(f"             {trouvaille.file}:{trouvaille.line} — "
              f"{trouvaille.match[:56]}")

    texte = (dossier / "SKILL.md").read_text(encoding="utf-8") \
        if (dossier / "SKILL.md").exists() else ""
    codes = invisibles(texte)
    if codes:
        print(f"  INVISIBLE  {', '.join(codes)} dans SKILL.md — "
              f"invisibles a l'ecran et dans un diff")

    if not defauts and not trouvailles:
        print("  Rien a signaler.")
    print(f"\n  {len(defauts)} defaut(s) de forme, {len(trouvailles)} "
          f"trouvaille(s) dont {len(critiques)} critique(s) ou haute(s)\n")
    return 1 if critiques else 0


def _plier(texte: str, largeur: int) -> list[str]:
    lignes, courante = [], ""
    for mot in texte.split():
        if len(courante) + len(mot) + 1 > largeur:
            lignes.append(courante)
            courante = mot
        else:
            courante = f"{courante} {mot}".strip()
    return lignes + ([courante] if courante else [])


if __name__ == "__main__":
    sys.exit(main())
