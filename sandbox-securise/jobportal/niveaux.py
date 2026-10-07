"""Les quatre niveaux d'isolation, et ce que chacun arrête vraiment.

    naif        aucune isolation — le code du chapitre 1
    restreint   builtins retirés, dans LE MÊME processus
    processus   un interprète séparé, avec timeout et bornes
    conteneur   namespaces, cgroups, seccomp — PAS EXÉCUTÉ ICI

Les trois premiers s'exécutent sur votre machine. Le quatrième demande Docker
et un noyau Linux ; il est ici **généré et vérifié**, pas lancé — voir
`conteneur.py`. Le dire est plus utile que de le simuler : un projet qui
prétend isoler alors qu'il ne fait rien est exactement le défaut que ce cours
dénonce.

⚠️ N'UTILISEZ PAS `restreint` EN PRODUCTION. Il est ici pour être cassé, et il
l'est — en une ligne, par une technique publiée depuis vingt ans. Son seul
usage légitime est pédagogique.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent

# Le budget d'un travail d'apprenant. Volontairement serré : une soumission
# qui met plus de deux secondes est soit fausse, soit hostile.
DELAI = 3.0
MEMOIRE_MAX = 256 * 1024 * 1024


@dataclass
class Resultat:
    sortie: str
    erreur: str
    code: int
    echappe: bool          # le code non fiable a-t-il obtenu ce qu'il voulait ?
    motif: str = ""        # ce qui l'a arrêté, quand il l'a été

    @property
    def bloque(self) -> bool:
        return not self.echappe


# ------------------------------------------------------ 1. aucune isolation

def naif(code: str) -> Resultat:
    """Le code du chapitre 1, tel quel.

    Il tourne avec VOS droits, VOTRE système de fichiers, VOTRE réseau. Pas de
    timeout : une boucle infinie fige le service. Pas de borne mémoire.

    Il est ici pour être mesuré, pas pour être utilisé. Le timeout ajouté
    ci-dessous ne fait pas partie de l'anti-patron : il empêche seulement ce
    projet de se figer en se démontrant lui-même.
    """
    try:
        r = subprocess.run([sys.executable, "-c", code], capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           timeout=DELAI, cwd=RACINE)
    except subprocess.TimeoutExpired:
        return Resultat("", "delai depasse", -1, echappe=True,
                        motif="AUCUNE borne : le service serait fige")
    return Resultat(r.stdout.strip(), r.stderr.strip(), r.returncode,
                    echappe=r.returncode == 0)


# ------------------------- 2. restreint : le faux sandbox, dans le processus

# Ce qu'on laisse. La liste a l'air prudente, et c'est précisément le piège :
# elle donne l'impression d'avoir réfléchi, alors qu'elle ne protège de rien.
BUILTINS_AUTORISES = {
    "abs", "all", "any", "bool", "dict", "divmod", "enumerate", "filter",
    "float", "int", "len", "list", "map", "max", "min", "print", "range",
    "repr", "reversed", "round", "set", "sorted", "str", "sum", "tuple", "zip",
    "True", "False", "None", "Exception", "ValueError", "TypeError",
    # « type » est dans toutes les listes qu'on ecrit spontanement, et
    # il ouvre a lui seul l'arbre des classes. Le retirer ne sauverait
    # rien — « ().__class__ » y mene sans lui.
    "type",
}


def restreindre(code: str) -> str:
    """`exec` avec des builtins réduits. **Ce n'est pas un sandbox.**

    Il arrête `open` et `import`, ce qui suffit à donner un faux sentiment de
    sécurité pendant des mois. Il n'arrête ni la remontée par
    `().__class__.__bases__`, ni une boucle infinie, ni une explosion mémoire —
    et ces trois-là sont dans le corpus.

    Il tourne DANS LE MÊME PROCESSUS que l'appelant. Tout ce qui s'en échappe
    s'échappe chez vous, avec vos droits.
    """
    import builtins

    autorises = {nom: getattr(builtins, nom)
                 for nom in BUILTINS_AUTORISES if hasattr(builtins, nom)}
    sortie: list[str] = []
    autorises["print"] = lambda *a, **k: sortie.append(
        " ".join(str(x) for x in a))

    exec(code, {"__builtins__": autorises}, {})   # noqa: S102 - c'est le sujet
    return "\n".join(sortie)


def restreint(code: str) -> Resultat:
    """Mesure le niveau « restreint » SANS figer le harnais.

    ⚠️ Lisez ceci avant d'interpréter les chiffres. La restriction, elle, est
    bien en-processus : c'est `restreindre()` ci-dessus, et c'est ce qu'on
    déploierait. Mais la MESURER en-processus rendrait ce projet impossible à
    exécuter — la boucle infinie du corpus figerait le harnais lui-même, et
    l'explosion mémoire tuerait la machine.

    On lance donc la même fonction dans un sous-processus **pour la mesurer**.
    Ce sous-processus apporte un délai que le niveau n'a PAS : les deux lignes
    du corpus marquées « deni de service » apparaissent donc comme bloquées ici
    alors qu'elles ne le sont pas en vrai. `outils/evasion.py` le signale
    explicitement, et un test le vérifie.

    Ce détour est en lui-même l'argument du chapitre 4 : un sandbox qu'on ne
    peut pas mesurer sans risque n'est pas un sandbox.
    """
    amorce = (
        "import sys, json\n"
        f"sys.path.insert(0, {str(RACINE)!r})\n"
        "from jobportal.niveaux import restreindre\n"
        "code = sys.stdin.read()\n"
        "try:\n"
        "    print(json.dumps({'ok': True, 'sortie': restreindre(code)}))\n"
        "except BaseException as e:\n"
        "    print(json.dumps({'ok': False, 'erreur': f'{type(e).__name__}: {e}'}))\n"
    )
    try:
        r = subprocess.run([sys.executable, "-c", amorce], input=code,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=DELAI, cwd=RACINE)
    except subprocess.TimeoutExpired:
        return Resultat("", "", -1, echappe=False,
                        motif="delai DU HARNAIS (le niveau, lui, n'en a pas)")

    import json
    try:
        rendu = json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return Resultat("", r.stderr.strip()[-200:], r.returncode,
                        echappe=False, motif="processus mort (memoire ?)")

    if rendu["ok"]:
        return Resultat(rendu["sortie"], "", 0, echappe=True)
    return Resultat("", rendu["erreur"], 1, echappe=False,
                    motif=rendu["erreur"].split(":")[0])


# ---------------------------- 3. processus : un interprète séparé, et borné

GARDE = """
import resource, sys
resource.setrlimit(resource.RLIMIT_AS, ({memoire}, {memoire}))
resource.setrlimit(resource.RLIMIT_NPROC, (0, 0))
"""


def processus(code: str, delai: float = DELAI) -> Resultat:
    """Un interprète séparé, avec un délai dur et un dossier de travail jetable.

    Ce que ce niveau apporte VRAIMENT, et c'est beaucoup :

      · une boucle infinie ne fige plus que le sous-processus, tué au délai ;
      · une explosion mémoire ne tue plus que lui ;
      · la remontée par `__subclasses__` n'atteint plus VOTRE processus.

    Ce qu'il n'apporte PAS, et c'est tout aussi important :

      · le réseau reste ouvert — un processus a toujours une pile réseau ;
      · le disque reste accessible là où l'utilisateur peut écrire ;
      · le dossier parent reste lisible.

    Les bornes `resource` sont POSIX. Sous Windows, le module n'existe pas :
    le délai s'applique, les bornes mémoire non. Ce projet le dit au lieu de
    laisser croire le contraire — `bornes_disponibles()` répond honnêtement.
    """
    # >>> depart: lancer le code dans un interprete SEPARE (sys.executable, -I), avec un delai DUR, dans un dossier temporaire jetable, et un environnement reduit. Sur POSIX, prefixer le code de GARDE pour poser RLIMIT_AS et RLIMIT_NPROC. Cinq tests le verifient.
    #     return Resultat("", "a implementer", 1, echappe=False)
    with tempfile.TemporaryDirectory(prefix="bac-a-sable-") as bac:
        amorce = (GARDE.format(memoire=MEMOIRE_MAX) if bornes_disponibles()
                  else "")
        # Le code tourne dans un dossier VIDE et jetable. Ce n'est pas une
        # prison — un chemin absolu en sort — mais c'est ce qui empêche le
        # plus banal des accidents : écrire dans le dossier du service.
        try:
            r = subprocess.run(
                [sys.executable, "-I", "-c", amorce + "\n" + code],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=delai, cwd=bac,
                env={"PATH": os.environ.get("PATH", ""),
                     "SYSTEMROOT": os.environ.get("SYSTEMROOT", "")})
        except subprocess.TimeoutExpired:
            return Resultat("", "", -1, echappe=False,
                            motif=f"delai de {delai:g}s depasse")
        return Resultat(r.stdout.strip(), r.stderr.strip(), r.returncode,
                        echappe=r.returncode == 0,
                        motif="" if r.returncode == 0 else "erreur d'execution")
    # <<<


def bornes_disponibles() -> bool:
    """Vrai si `resource` existe — donc sur POSIX, pas sous Windows.

    Le savoir change la mesure : sous Windows, l'explosion mémoire n'est
    arrêtée que par le délai, pas par une borne. Une isolation dont on ignore
    ce qu'elle fait sur la machine de production n'est pas une isolation.
    """
    try:
        import resource      # noqa: F401
    except ImportError:
        return False
    return True


NIVEAUX = {"naif": naif, "restreint": restreint, "processus": processus}
