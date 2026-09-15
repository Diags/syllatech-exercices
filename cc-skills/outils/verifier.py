#!/usr/bin/env python3
"""Le vérificateur de skills — ce que `/doctor` ne dit pas.

Une skill qui ne se déclenche jamais ne lève aucune erreur. Une skill dont le
script est introuvable échoue **au moment où on en a besoin**, pas avant. Rien
ne vous prévient à l'écriture.

Cet outil relit vos `SKILL.md` et signale ce qui ne se verra qu'à l'usage :

    python outils/verifier.py [dossier]

Il ne remplace pas `/doctor` — il attrape ce qui se répare en amont.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:   # noqa: BLE001
        pass

# Les champs que la documentation reconnaît. Un champ inconnu n'est pas une
# erreur bloquante — mais c'est presque toujours une faute de frappe, et elle
# est silencieuse : le champ est ignoré, la skill se comporte autrement que
# prévu, et rien ne le dit.
CHAMPS_CONNUS = {
    "name", "description", "when_to_use", "disable-model-invocation",
    "user-invocable", "allowed-tools", "disallowed-tools", "argument-hint",
    "arguments", "model", "effort", "context", "agent", "background",
    "paths", "shell", "hooks", "metadata", "license", "compatibility",
}

MAX_NOM_DESCRIPTION = 1536       # tronqués au-delà, dans les listes de skills


@dataclass
class Souci:
    gravite: str        # "erreur" ou "attention"
    skill: str
    message: str


def frontmatter(texte: str) -> tuple[dict, str]:
    """Extrait le frontmatter YAML. Volontairement minimal : pas de
    dépendance pour lire quatre clés."""
    if not texte.startswith("---"):
        return {}, texte
    fin = texte.find("\n---", 3)
    if fin == -1:
        return {}, texte
    brut, corps = texte[3:fin], texte[fin + 4:]

    champs: dict[str, str] = {}
    cle = None
    for ligne in brut.splitlines():
        if not ligne.strip():
            continue
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", ligne)
        if m:
            cle = m.group(1)
            champs[cle] = m.group(2).strip()
        elif cle and ligne.startswith((" ", "\t")):
            # Continuation d'une valeur sur plusieurs lignes.
            champs[cle] = (champs[cle] + " " + ligne.strip()).strip()
    return champs, corps


def verifier_une(dossier: Path) -> list[Souci]:
    nom_dossier = dossier.name
    fichier = dossier / "SKILL.md"
    if not fichier.exists():
        return [Souci("erreur", nom_dossier, "SKILL.md absent : le dossier est ignoré")]

    texte = fichier.read_text(encoding="utf-8")
    champs, corps = frontmatter(texte)
    soucis: list[Souci] = []

    # --- la description, seul déclencheur automatique -------------------
    description = champs.get("description", "")
    if not description:
        soucis.append(Souci("erreur", nom_dossier,
                            "pas de description : Claude ne saura JAMAIS quand "
                            "l'invoquer. Elle ne se déclenchera qu'au slash."))
    elif len(description) < 30:
        soucis.append(Souci("attention", nom_dossier,
                            f"description très courte ({len(description)} signes) — "
                            "c'est le seul indice dont dispose le modèle pour "
                            "choisir cette skill plutôt qu'une autre"))
    if not re.search(r"quand|lorsqu|utiliser|pour ", description, re.IGNORECASE) and description:
        soucis.append(Souci("attention", nom_dossier,
                            "la description dit CE QUE fait la skill, pas QUAND "
                            "l'employer. Ajoutez le déclencheur."))

    nom = champs.get("name", nom_dossier)
    if nom != nom_dossier:
        soucis.append(Souci("attention", nom_dossier,
                            f"« name: {nom} » diffère du dossier — la skill "
                            f"s'invoque par /{nom_dossier}, pas /{nom}"))
    if len(nom) + len(description) > MAX_NOM_DESCRIPTION:
        soucis.append(Souci("attention", nom_dossier,
                            f"nom + description = {len(nom) + len(description)} signes, "
                            f"tronqués à {MAX_NOM_DESCRIPTION} dans les listes"))

    # TODO : signaler les champs de frontmatter absents de CHAMPS_CONNUS. « descriptio » au lieu de « description » est ignore en SILENCE : la skill ne se declenche jamais et rien ne le dit.
    pass

    # --- LE défaut qui ne se voit qu'à l'usage ---------------------------
    # Un chemin de script relatif est résolu depuis le DOSSIER DE TRAVAIL,
    # pas depuis la skill. Le script est introuvable, et on ne l'apprend
    # qu'au moment où la skill s'exécute.
    # TODO : signaler tout script lance par un chemin RELATIF. Les chemins qui partent de ${CLAUDE_SKILL_DIR}, ${CLAUDE_PLUGIN_ROOT}, / ou ~ sont corrects. Le test test_le_chemin_relatif_du_cours_est_attrape exige que le message cite CLAUDE_SKILL_DIR.
    pass

    # --- les scripts référencés existent-ils ? --------------------------
    for m in re.finditer(r"\$\{CLAUDE_SKILL_DIR\}/([^\s`\"')]+)", texte):
        if not (dossier / m.group(1)).exists():
            soucis.append(Souci("erreur", nom_dossier,
                                f"script référencé mais absent : {m.group(1)}"))

    if "$ARGUMENTS" in corps or re.search(r"\$\d\b", corps):
        if "argument-hint" not in champs and "arguments" not in champs:
            soucis.append(Souci("attention", nom_dossier,
                                "la skill utilise des arguments sans « argument-hint » : "
                                "l'autocomplétion ne dira pas quoi taper"))

    return soucis


def verifier(racine: Path) -> list[Souci]:
    dossier = racine / ".claude" / "skills"
    if not dossier.exists():
        return [Souci("erreur", "—", f"aucun dossier {dossier}")]
    soucis = []
    for d in sorted(p for p in dossier.iterdir() if p.is_dir()):
        soucis += verifier_une(d)
    return soucis


def main() -> int:
    racine = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
    soucis = verifier(racine)

    erreurs = [s for s in soucis if s.gravite == "erreur"]
    for s in soucis:
        marque = "ERREUR    " if s.gravite == "erreur" else "attention "
        print(f"  {marque} {s.skill:<16} {s.message}")
    if not soucis:
        print("  Aucun problème détecté.")
    print(f"\n  {len(erreurs)} erreur(s), {len(soucis) - len(erreurs)} avertissement(s)")
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
