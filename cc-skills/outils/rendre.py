#!/usr/bin/env python3
"""Le harnais : voir ce qu'une skill DEVIENT, sans lancer de session.

Une skill n'est pas le fichier qu'on écrit : c'est le texte qui arrive dans le
contexte du modèle. Entre les deux, trois transformations — et c'est là que se
cachent les surprises.

    python outils/rendre.py --index                 ce qui est TOUJOURS chargé
    python outils/rendre.py migration "colonne statut"   ce qui l'est au déclenchement
    python outils/rendre.py --cout                  la facture des deux

Le chapitre 1 affirme que les skills se chargent « à la demande ». Cet outil
le rend mesurable : `--cout` met côte à côte ce que coûtent vos skills en
permanence et ce qu'elles coûteraient si tout était dans CLAUDE.md.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verifier import frontmatter                    # noqa: E402

for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except Exception:   # noqa: BLE001
        pass

RACINE = Path(__file__).resolve().parent.parent
SKILLS = RACINE / ".claude" / "skills"

# Une approximation, pas une mesure : ~4 signes par token en anglais, un peu
# moins en français accentué. L'ordre de grandeur suffit à trancher, et c'est
# tout ce qu'on demande à ce compteur.
SIGNES_PAR_TOKEN = 3.6


def tokens(texte: str) -> int:
    return round(len(texte) / SIGNES_PAR_TOKEN)


def lire(nom: str) -> tuple[dict, str]:
    fichier = SKILLS / nom / "SKILL.md"
    if not fichier.exists():
        print(f"  Pas de skill « {nom} ». Disponibles : "
              f"{', '.join(sorted(d.name for d in SKILLS.iterdir() if d.is_dir()))}")
        raise SystemExit(2)
    return frontmatter(fichier.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ le rendu

def executer_commandes(corps: str, dossier: Path) -> tuple[str, list[tuple[str, int]]]:
    """Exécute les blocs !`commande` et met leur SORTIE à la place.

    C'est le point que la vidéo ne montre pas : ces commandes tournent sur la
    machine, au moment du rendu, AVANT que le modèle ne lise quoi que ce soit.
    Leur sortie n'est pas résumée : elle est collée telle quelle dans le
    prompt. Un `git log` un lundi de retour de congés peut donc peser vingt
    fois la skill qui l'appelle.
    """
    # >>> depart: remplacer chaque bloc !`commande` par la SORTIE de la commande, et relever son cout. subprocess.run(commande, shell=True, cwd=dossier, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=20) — stdin FERME, comme au vrai rendu. Rendre (texte rendu, [(commande, tokens(sortie)), ...]). Trois tests le verifient.
    #     return corps, []
    rendu, mesures, i = [], [], 0
    while True:
        debut = corps.find("!`", i)
        if debut == -1:
            rendu.append(corps[i:])
            break
        fin = corps.find("`", debut + 2)
        if fin == -1:
            rendu.append(corps[i:])
            break
        rendu.append(corps[i:debut])
        commande = corps[debut + 2:fin]
        try:
            # stdin fermé, comme au vrai rendu : aucune session n'est là pour
            # répondre. Une commande qui LIT l'entrée standard rend donc du
            # vide — `git shortlog` sans révision en est l'exemple parfait, et
            # il ne signale rien. Le timeout, lui, évite qu'un rendu ne bloque.
            r = subprocess.run(commande, shell=True, cwd=dossier, capture_output=True,
                               stdin=subprocess.DEVNULL, text=True, encoding="utf-8",
                               errors="replace", timeout=20)
            sortie = (r.stdout or r.stderr or "").rstrip()
        except Exception as e:       # noqa: BLE001 - une commande peut tout faire
            sortie = f"(échec : {e})"
        rendu.append(sortie)
        mesures.append((commande, tokens(sortie)))
        i = fin + 1
    return "".join(rendu), mesures
    # <<<


def rendre(nom: str, arguments: str) -> None:
    champs, corps = lire(nom)
    brut = len(corps)
    corps, mesures = executer_commandes(corps, RACINE)
    corps = corps.replace("$ARGUMENTS", arguments)
    for n, mot in enumerate(arguments.split(), start=1):
        corps = corps.replace(f"${n}", mot)
    corps = corps.replace("${CLAUDE_SKILL_DIR}", str(SKILLS / nom))

    print(f"\n{'=' * 72}\nCE QUE LE MODELE RECOIT — skill « {nom} »"
          f"{f', invoquée /{nom} {arguments}' if arguments else ''}\n{'=' * 72}\n")
    print(corps.strip())

    print(f"\n{'-' * 72}")
    print(f"  SKILL.md écrit     {brut:>6} signes  ~{tokens(' ' * brut):>5} tokens")
    for commande, t in mesures:
        print(f"  + !`{commande[:40]:<40}` {'':>6}  ~{t:>5} tokens  (exécutée ici)")
    print(f"  = reçu par le modèle {len(corps):>4} signes  ~{tokens(corps):>5} tokens")
    if mesures and tokens(corps) > 2 * tokens(" " * brut):
        print("\n  Le rendu pèse plus du double du fichier : ce que vous relisez")
        print("  dans SKILL.md n'est PAS ce que le modèle lit. Les commandes !`…`")
        print("  n'ont pas de taille prévisible — la vôtre dépend du dépôt.")


# ------------------------------------------------------------------ l'index

def index() -> None:
    """Ce qui est dans le contexte EN PERMANENCE : nom + description, rien d'autre."""
    print(f"\n{'=' * 72}\nCE QUI EST TOUJOURS CHARGE (avant tout déclenchement)\n{'=' * 72}\n")
    total = 0
    for d in sorted(p for p in SKILLS.iterdir() if p.is_dir()):
        champs, _ = frontmatter((d / "SKILL.md").read_text(encoding="utf-8"))
        ligne = f"{champs.get('name', d.name)}: {champs.get('description', '')}"
        total += tokens(ligne)
        print(f"  {champs.get('name', d.name)}")
        print(f"     {champs.get('description', '(aucune)')[:96]}…\n")
    print(f"  ~{total} tokens en tout, en permanence.\n")
    print("  Et c'est TOUT. Le corps des skills, leurs scripts, leurs fichiers")
    print("  de référence : rien de cela n'est chargé tant qu'aucune skill ne")
    print("  se déclenche. C'est ce que « chargement à la demande » veut dire.")
    print("\n  Conséquence directe sur la description : c'est le SEUL texte dont")
    print("  le modèle dispose pour choisir. Une description qui dit ce que fait")
    print("  la skill sans dire QUAND l'employer ne se déclenche jamais — et")
    print("  aucune erreur ne vous le signale.")


def cout() -> None:
    permanent = 0
    demande = 0
    for d in sorted(p for p in SKILLS.iterdir() if p.is_dir()):
        champs, corps = frontmatter((d / "SKILL.md").read_text(encoding="utf-8"))
        permanent += tokens(f"{champs.get('name', d.name)}: {champs.get('description', '')}")
        demande += tokens(corps)

    print(f"\n{'=' * 72}\nLA FACTURE\n{'=' * 72}\n")
    print(f"  {'':<44}{'tokens':>8}")
    print(f"  {'index des skills (toujours chargé)':<44}{permanent:>8}")
    print(f"  {'corps des skills (chargé au déclenchement)':<44}{demande:>8}")
    print(f"  {'les mêmes procédures dans CLAUDE.md':<44}{permanent + demande:>8}")
    print(f"\n  Rapport : {(permanent + demande) / max(permanent, 1):.1f}× moins de contexte")
    print(f"  consommé en permanence, pour un contenu identique.\n")
    print("  À trois skills l'écart est modeste. Il ne l'est plus à trente, ni")
    print("  quand une skill embarque 300 lignes de charte de style. C'est le")
    print("  vrai argument du chargement à la demande, et il est arithmétique.")
    print("\n  Le compteur est approché (~3,6 signes par token) : on cherche un")
    print("  ordre de grandeur, pas une facture au token près.")


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    if sys.argv[1] == "--index":
        index()
    elif sys.argv[1] == "--cout":
        cout()
    else:
        rendre(sys.argv[1], " ".join(sys.argv[2:]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
