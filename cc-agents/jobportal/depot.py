"""Le chaînon manquant : un dépôt à explorer.

Le cours parle de « cartographier un module », de « cinquante fichiers lus »,
d'un « diff de branche ». Aucune vidéo ne peut fournir ce dépôt — et sans lui,
rien n'est mesurable. Celui-ci en tient lieu : 52 fichiers répartis en quatre
modules, avec des dépendances, des points d'entrée, et **de vrais défauts**
plantés à des endroits connus (c'est le corrigé du réviseur du chapitre 4).

Il est généré, donc déterministe : la même exploration rend les mêmes chiffres
sur toutes les machines, et les mesures de ce projet sont reproductibles.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class Fichier:
    chemin: str
    module: str
    lignes: list[str] = field(default_factory=list)

    @property
    def texte(self) -> str:
        return "\n".join(self.lignes)

    def __len__(self) -> int:
        return len(self.texte)


# Les modules du job portal, avec leur rôle et leur taille.
MODULES = {
    "auth": ("authentification et sessions", 12),
    "offres": ("catalogue des offres d'emploi", 18),
    "candidatures": ("dépôt et suivi des candidatures", 14),
    "build": ("configuration de construction et CI", 8),
}

# Les défauts plantés, par chemin. Ils sont RÉELS : le réviseur les trouvera en
# lisant le code, pas en lisant cette table. La table sert au corrigé, pour
# mesurer ce que le réviseur rate et ce qu'il invente.
DEFAUTS = {
    "auth/jetons.py": ("secret en dur", "SECRET = \"dev-secret-2019\""),
    "auth/session.py": ("comparaison de mot de passe non constante",
                        "if mot_de_passe == stocke:"),
    "offres/recherche.py": ("requête SQL concaténée",
                            "sql = \"SELECT * FROM offres WHERE titre LIKE '%\" + terme + \"%'\""),
    "candidatures/depot.py": ("aucune limite de taille au téléversement",
                              "contenu = fichier.read()"),
    "build/publier.sh": ("identifiants en clair dans la CI",
                         "DEPLOY_KEY=AKIAIOSFODNN7EXAMPLE"),
}


def construire(graine: int = 11) -> list[Fichier]:
    alea = random.Random(graine)
    fichiers: list[Fichier] = []

    for module, (role, combien) in MODULES.items():
        for n in range(combien):
            nom = _nom(module, n, alea)
            chemin = f"{module}/{nom}"
            shell = nom.endswith(".sh")
            lignes = ([f"#!/bin/sh", f"# {role} — {nom}", ""] if shell
                      else [f'"""{role} — {nom}."""', ""])

            # Du code plausible, et surtout du VOLUME : c'est le volume qui
            # rend la délégation rentable, et il doit donc être réel.
            for f in range(alea.randint(3, 9)):
                lignes += _bloc_shell(f, alea) if shell else _fonction(module, f, alea)

            if chemin in DEFAUTS:
                etiquette, code = DEFAUTS[chemin]
                lignes.insert(2, f"# {etiquette}")
                lignes.insert(3, code)
                lignes.insert(4, "")

            fichiers.append(Fichier(chemin, module, lignes))

    return fichiers


def _nom(module: str, n: int, alea: random.Random) -> str:
    fixes = {
        "auth": ["jetons.py", "session.py", "mots_de_passe.py"],
        "offres": ["recherche.py", "modele.py", "api.py"],
        "candidatures": ["depot.py", "suivi.py", "notifications.py"],
        "build": ["publier.sh", "verifier.sh", "version.py"],
    }[module]
    if n < len(fixes):
        return fixes[n]
    return f"{alea.choice(['gestion', 'outils', 'valide', 'convertit', 'lit', 'ecrit'])}_{n}.py"


def _bloc_shell(n: int, alea: random.Random) -> list[str]:
    """Un script shell contient du shell. Un detail — mais un projet
    pedagogique qui met du Python dans un .sh perd la confiance qu'il demande
    par ailleurs."""
    etape = alea.choice(["build", "test", "lint", "publie", "notifie"])
    return [
        f"{etape}_{n}() {{",
        f'  echo "== {etape} =="',
        f"  {alea.choice(['npm run', 'make', 'python -m'])} {etape} || exit 1",
        "}",
        "",
    ]


def _fonction(module: str, n: int, alea: random.Random) -> list[str]:
    nom = alea.choice(["charger", "enregistrer", "valider", "convertir", "lister", "compter"])
    return [
        f"def {nom}_{module}_{n}(entree):",
        f'    """{alea.choice(["Renvoie", "Calcule", "Prepare"])} '
        f'{alea.choice(["la liste", "le total", "le resultat"])}."""',
        "    resultat = []",
        "    for element in entree:",
        f"        if element.get('{alea.choice(['actif', 'valide', 'public'])}'):",
        "            resultat.append(element)",
        "    return resultat",
        "",
    ]


DEPOT = construire()
PAR_CHEMIN = {f.chemin: f for f in DEPOT}


def lire(chemin: str) -> str:
    if chemin not in PAR_CHEMIN:
        raise FileNotFoundError(chemin)
    return PAR_CHEMIN[chemin].texte


def lister(module: str | None = None) -> list[str]:
    return [f.chemin for f in DEPOT if module is None or f.module == module]


def chercher(motif: str, module: str | None = None) -> list[tuple[str, int, str]]:
    trouves = []
    for f in DEPOT:
        if module and f.module != module:
            continue
        for n, ligne in enumerate(f.lignes, start=1):
            if motif.lower() in ligne.lower():
                trouves.append((f.chemin, n, ligne.strip()))
    return trouves


def diff() -> list[Fichier]:
    """Le « diff de la branche » du chapitre 4 : ce qui a changé, pas tout le
    dépôt. Trois fichiers, dont deux portent un vrai défaut."""
    return [PAR_CHEMIN[c] for c in ("auth/jetons.py", "auth/session.py",
                                    "offres/recherche.py", "build/publier.sh",
                                    "candidatures/suivi.py")]
