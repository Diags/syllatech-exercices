"""Le corpus d'évasions — des formes publiques, documentées depuis vingt ans.

Aucune nouveauté ici, et c'est voulu. Ces échappatoires sont dans la
documentation Python, dans les CVE, dans les articles de 2003 sur `rexec`.
L'intérêt n'est pas de les découvrir : c'est de les **rejouer contre chaque
niveau d'isolation** et de voir, ligne par ligne, où se situe la frontière.

Le résultat n'est pas une opinion. Il s'exécute.

Chaque évasion porte ce qu'elle cherche à obtenir et le niveau qui l'arrête.
`outils/evasion.py` vérifie que cette correspondance est exacte — et signale
quand elle ne l'est plus.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent


@dataclass
class Evasion:
    """Deux axes, et les confondre est l'erreur du debutant.

    `nommage`   le niveau qui empeche le code d'ATTEINDRE ce qu'il cherche.
    `dommage`   le niveau qui empeche le dommage d'atteindre l'HOTE.

    Ce ne sont PAS deux marches d'un escalier. « restreint » retire des noms
    sans rien contenir ; « processus » ne retire aucun nom et contient tout.
    Un interprete separe peut faire « import os » — et c'est sans importance,
    parce qu'il meurt avec son bac a sable.
    """

    nom: str
    code: str
    cherche: str          # ce qu'elle obtient si rien ne l'arrête
    nommage: str          # le niveau qui l'empeche d'atteindre sa cible
    dommage: str          # le niveau qui empeche l'hote d'etre touche
    note: str = ""


# Le code « honnête » : ce qu'un candidat est censé soumettre. Il doit passer
# à TOUS les niveaux — une isolation qui casse l'usage légitime sera retirée.
CODE_HONNETE = """
def resoudre(n):
    return sum(i * i for i in range(n))

print(resoudre(10))
"""

EVASIONS = [
    Evasion(
        nom="lecture d'un fichier du projet",
        code=f"print(open({str(RACINE / 'pyproject.toml')!r}).read()[:30])",
        cherche="lecture du systeme de fichiers",
        nommage="restreint",
        dommage="conteneur",
        note="un CHEMIN ABSOLU, volontairement : le dossier de travail jetable "
             "du niveau « processus » n'est pas une prison, et mesurer avec un "
             "chemin relatif ferait croire le contraire.",
    ),
    Evasion(
        nom="import direct",
        code="import os; print(os.getcwd())",
        cherche="acces au systeme",
        nommage="restreint",
        dommage="processus",
        note="« import » sans __import__ leve ImportError",
    ),
    Evasion(
        nom="remontee par __subclasses__",
        code=(
            "cls = ().__class__.__bases__[0]\n"
            "for s in cls.__subclasses__():\n"
            "    if s.__name__ == 'BuiltinImporter':\n"
            "        os = s().load_module('os')\n"
            "        print(os.getcwd())\n"
            "        break"),
        cherche="acces au systeme",
        nommage="conteneur",
        dommage="processus",
        note="LA faille : l'arbre des classes est accessible depuis n'importe "
             "quel objet. Retirer des builtins n'y change rien.",
    ),
    Evasion(
        nom="remontee par les globals d'une fonction",
        code=(
            "f = (lambda: 0)\n"
            "print(type(f.__globals__))"),
        cherche="acces aux globals de l'hote",
        nommage="conteneur",
        dommage="processus",
        note="un objet fonction porte son environnement avec lui",
    ),
    Evasion(
        nom="boucle infinie",
        code="while True:\n    pass",
        cherche="deni de service",
        nommage="processus",
        dommage="processus",
        note="aucune restriction de nom n'arrete une boucle",
    ),
    Evasion(
        nom="explosion memoire",
        code="x = 'a' * (10 ** 9)",
        cherche="deni de service",
        nommage="processus (POSIX)",
        dommage="processus (POSIX)",
        note="un seul appel, pas de boucle a detecter. RLIMIT_AS l'arrete sur "
             "POSIX ; sous Windows le module « resource » n'existe pas, et "
             "seul le delai finit par intervenir — si le processus ne fait pas "
             "tomber la machine avant.",
    ),
    Evasion(
        nom="ouverture d'une socket",
        code=("import socket\n"
              "s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n"
              "s.close()\n"
              "print('socket creee')"),
        cherche="exfiltration",
        nommage="conteneur",
        dommage="conteneur",
        note="on mesure la CAPACITE d'ouvrir une socket, pas l'atteinte d'un "
             "hote : joindre exemple.fr depend de la machine de test et non du "
             "sandbox, et une mesure qui depend du reseau ne mesure rien. Un "
             "processus separe a toujours une pile reseau — seul "
             "--network=none la retire.",
    ),
    Evasion(
        nom="ecriture sur le disque de l'hote",
        code=f"open({str(RACINE / 'temoin-evasion.txt')!r}, 'w').write('x')",
        cherche="persistance",
        nommage="conteneur",
        dommage="conteneur",
        note="un processus separe ecrit ou l'utilisateur ecrit — seul "
             "--read-only l'en empeche",
    ),
    Evasion(
        nom="lecture du voisinage",
        code=f"import os; print(len(os.listdir({str(RACINE.parent)!r})))",
        cherche="reconnaissance",
        nommage="conteneur",
        dommage="conteneur",
        note="voir le dossier parent suffit a cartographier la machine",
    ),
]


def par_niveau(niveau: str) -> list[Evasion]:
    return [e for e in EVASIONS if e.nommage == niveau]
