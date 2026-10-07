"""Ce que les agents font vraiment — l'analyse, sans modèle.

Pourquoi pas d'appel à un modèle ? Parce que ce projet doit tourner après un
`uv sync`, sans clé. Et parce que ce que le cours enseigne n'est pas *comment
un modèle trouve un bug* : c'est **l'orchestration** — l'isolation des
contextes, le filtrage des outils, la vérification adversariale, le coût.
Tout cela est ici authentique et mesurable.

L'analyse, elle, est déterministe : des motifs cherchés dans le code. Y compris
— et c'est délibéré — des motifs qui produisent de **faux positifs**, parce
qu'un réviseur réel en produit, et que le chapitre 4 porte entièrement sur ce
qu'on en fait.
"""

from __future__ import annotations

import re

from .agents import Agent, Rapport
from .depot import MODULES

ROLES = {m: role for m, (role, _) in MODULES.items()}

# ---------------------------------------------------------------- l'explorateur


def explorer(module: str):
    """Rend la fonction de travail d'un explorateur sur un module donné."""

    def travail(agent: Agent, tache: str, outils: dict) -> Rapport:
        chemins = outils["Glob"](module)
        # L'agent lit TOUT le module. C'est cela qui coûte — et qui reste
        # chez lui : la session principale ne verra que le rapport final.
        for chemin in chemins:
            outils["Read"](chemin)

        entrees = [c for c in chemins if c.rsplit("/", 1)[-1] in
                   ("api.py", "session.py", "depot.py", "publier.sh")]
        risques = outils["Grep"]("secret", module) + outils["Grep"]("SELECT", module)

        texte = (
            f"## {module}\n"
            f"1. Role : {ROLES[module]} ({len(chemins)} fichiers).\n"
            f"2. Points d'entree : {', '.join(entrees) or 'aucun evident'}\n"
            f"3. Dependances : internes au module\n"
            f"4. Zones a risque : {len(risques)} ligne(s) a regarder de pres"
            f"{' — ' + risques[0][0] if risques else ''}\n"
        )
        return Rapport(agent.nom, texte)

    return travail


# ------------------------------------------------------------------ le réviseur

# Les motifs de la PREMIÈRE passe. Un réviseur lancé sur un diff trouve
# toujours quelque chose : c'est sa nature. Trois motifs désignent de vrais
# défauts, deux ne désignent que des préférences de style.
MOTIFS = [
    ("identifiant", r"([A-Z_]*(?:SECRET|KEY|TOKEN)[A-Z_]*)\s*=\s*[\"']?([\w\-]+)",
     "identifiant en dur dans le code"),
    ("sql", r"(SELECT[^\"']*[\"']\s*\+\s*(\w+)|\+\s*(\w+)\s*\+\s*[\"']%)",
     "requete SQL concatenee : injection possible"),
    ("temps", r"if\s+(\w*mot_de_passe\w*|\w*secret\w*)\s*==\s*(\w+)",
     "comparaison de secret non constante en temps"),
    ("style", r"for \w+ in entree:",
     "cette boucle pourrait etre une comprehension de liste"),
    ("style", r"def \w+\(entree\):",
     "le parametre « entree » gagnerait a etre type"),
]

# Un vrai réviseur ne répète pas vingt fois la même remarque de style : il en
# cite quelques-unes. On plafonne donc, pour que le rapport brut ressemble à
# ce qu'on reçoit vraiment — et non à une sortie de linter.
MAX_PAR_MOTIF = 3

# Les valeurs publiques de documentation. Les reconnaître est exactement le
# genre de re-vérification qu'un constat mérite : elles ressemblent trait pour
# trait à un identifiant fuité, et n'en sont pas.
PLACEHOLDERS = ("EXAMPLE", "CHANGEME", "XXXX", "PLACEHOLDER", "TODO", "FIXME")


def reviser(fichiers, adversarial: bool = True):
    """Rend la fonction de travail d'un réviseur sur un diff.

    `adversarial` est LE point du chapitre 4. À False, l'agent rend tout ce
    qu'il a trouvé. À True, il **relit chaque constat dans le code** avant de
    le présenter, et ne garde que ce qu'il peut prouver.
    """

    def travail(agent: Agent, tache: str, outils: dict) -> Rapport:
        bruts = []
        for f in fichiers:
            texte = outils["Read"](f.chemin)
            lignes = texte.split("\n")
            for genre, motif, message in MOTIFS:
                for n, m in enumerate(re.finditer(motif, texte)):
                    if n >= MAX_PAR_MOTIF:
                        break
                    num = texte[:m.start()].count("\n") + 1
                    bruts.append({"fichier": f.chemin, "ligne": num, "genre": genre,
                                  "message": message, "code": lignes[num - 1].strip()})

        if not adversarial:
            return _rapport(agent, bruts, len(bruts))

        # LA SECONDE PASSE. Elle ne consulte pas le motif qui a produit le
        # constat : elle relit la ligne et cherche une preuve indépendante.
        retenus = []
        for c in bruts:
            verdict, raison = verifier(c)
            if verdict != "ecarte":
                retenus.append({**c, "verdict": verdict, "raison": raison})
        return _rapport(agent, retenus, len(bruts))

    return travail


def verifier(constat: dict) -> tuple[str, str]:
    """Relit un constat dans le code. Rend (verdict, raison).

    Trois issues, et c'est important qu'il y en ait trois : un constat n'est
    pas seulement vrai ou faux. Certains **ressemblent** à un vrai défaut sans
    en être un, et les jeter aussi sèchement que le bruit ferait perdre une
    information réelle.

        confirme  la ligne porte une conséquence nommable
        douteux   la ligne a l'air d'un défaut, la preuve est faible
        ecarte    aucune preuve : c'est une préférence, pas un défaut
    """
    code = constat["code"]

    # TODO : relire la ligne et rendre un verdict SANS consulter le motif qui a produit le constat. identifiant : placeholder (EXAMPLE, CHANGEME...) -> douteux, valeur < 8 signes -> ecarte, sinon confirme. sql : deux litteraux concatenes -> ecarte, sinon confirme. temps : confirme. Tout le reste : ecarte. Six tests le verifient.
    return "confirme", ""


def _rapport(agent: Agent, constats: list[dict], bruts: int) -> Rapport:
    if not constats:
        texte = "### Aucun constat retenu"
    else:
        lignes = []
        for c in constats:
            marque = {"confirme": "CONFIRME", "douteux": "DOUTEUX "}.get(c.get("verdict"), "")
            raison = f"\n  → {c['raison']}" if c.get("raison") else ""
            lignes.append(f"- {marque} {c['fichier']}:{c['ligne']} — {c['message']}{raison}")
        texte = "### Constats\n" + "\n".join(lignes)
    texte += f"\n\n({bruts} constat(s) brut(s), {len(constats)} presente(s))"
    return Rapport(agent.nom, texte, constats=constats)
