"""Trois façons d'exécuter le code d'un candidat, de la pire à la moins pire.

    EnLocal          exec() dans VOTRE processus — ce que fait PythonTools
    SousProcessus    un interpréteur séparé, avec un délai
    Bride            le même, sans variables d'environnement, dossier vide,
                     sortie plafonnée

⚠️ AUCUN DE CES TROIS N'EST UN BAC À SABLE. Le troisième est ce qu'on peut
faire en Python pur et portable ; un vrai isolement demande un conteneur, un
micro-VM ou `seccomp`. Le chapitre 3 mesure ce que chaque niveau arrête, et
dit exactement où il s'arrête.

LA MESURE QUI COMPTE N'EST PAS CELLE QU'ON ATTEND

Les trois niveaux se distinguent sur la famille « machine ». Sur la famille
« verdict », **les trois donnent le même résultat** : le code s'exécute
proprement, ne touche à rien, et sa sortie remonte intacte. C'est le chapitre
4 qui s'en occupe, et aucun exécuteur ne peut y faire quoi que ce soit.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

DELAI = 5.0
SORTIE_MAX = 10_000

JEU = '[{"titre": "DevOps", "salaire": 62}, {"titre": "Java", "salaire": 55}]'
HARNAIS = f'''
import json
OFFRES = json.loads({JEU!r})
'''
VERIFICATION = '''
resultat = trier(OFFRES)
assert [o["salaire"] for o in resultat] == [62, 55], "le tri est faux"
print("OK tri decroissant")
'''


@dataclass
class Execution:
    """Ce qu'on sait après avoir fait tourner une soumission."""

    niveau: str
    sortie: str
    erreur: str
    code_retour: int
    duree_ms: float
    interrompu: bool = False

    @property
    def reussie(self) -> bool:
        return self.code_retour == 0 and not self.interrompu

    def __str__(self) -> str:
        etat = ("INTERROMPU" if self.interrompu
                else "ok" if self.reussie else "echec")
        return f"{etat:<11}{self.duree_ms:>7.0f} ms  {self.sortie[:46]!r}"


class Executeur:
    nom = "?"
    protege: tuple[str, ...] = ()

    def executer(self, code: str) -> Execution:
        raise NotImplementedError


class EnLocal(Executeur):
    """`exec()` dans le processus courant. C'est ce que fait `PythonTools`.

    ⚠️ Le code hérite de TOUT : vos fichiers, vos variables d'environnement,
    votre réseau, vos droits. `agno.tools.python.PythonTools.run_python_code`
    fait littéralement `exec(code, self.safe_globals, self.safe_locals)` — et
    « safe » ne désigne que le dictionnaire de noms, pas le processus.

    Cette classe existe pour être MESURÉE, pas pour être utilisée. Elle
    n'exécute d'ailleurs que le corpus du projet, qui est inoffensif : les
    soumissions « machine » lisent un chemin et impriment, elles n'effacent
    rien.
    """

    nom = "en local"

    def executer(self, code: str) -> Execution:
        import contextlib
        import io

        debut = time.perf_counter()
        sortie, erreur, retour = io.StringIO(), "", 0
        espace: dict = {}
        try:
            with contextlib.redirect_stdout(sortie):
                exec(HARNAIS + code + VERIFICATION, espace)   # noqa: S102
        except Exception as souci:                            # noqa: BLE001
            erreur, retour = f"{type(souci).__name__}: {souci}", 1
        return Execution(self.nom, sortie.getvalue()[:SORTIE_MAX], erreur,
                         retour, (time.perf_counter() - debut) * 1000)


class SousProcessus(Executeur):
    """Un interpréteur séparé, avec un délai. Le minimum vital.

    Ce que cela apporte : le code ne peut plus toucher à la mémoire de votre
    programme, et une boucle infinie est coupée. Ce que cela n'apporte pas :
    il a toujours vos variables d'environnement, votre dossier courant et
    votre réseau.
    """

    nom = "sous-processus"
    protege = ("memoire du processus", "boucle infinie")

    def _commande(self, fichier: Path) -> list[str]:
        return [sys.executable, "-I", str(fichier)]

    def _environnement(self) -> dict:
        return dict(os.environ)

    def _dossier(self, base: Path) -> Path:
        return Path.cwd()

    def executer(self, code: str) -> Execution:
        with tempfile.TemporaryDirectory() as base:
            fichier = Path(base) / "soumission.py"
            fichier.write_text(HARNAIS + code + VERIFICATION, encoding="utf-8")
            debut = time.perf_counter()
            try:
                fini = subprocess.run(
                    self._commande(fichier), capture_output=True, text=True,
                    timeout=DELAI, env=self._environnement(),
                    cwd=str(self._dossier(Path(base))))
            except subprocess.TimeoutExpired:
                return Execution(self.nom, "", f"delai de {DELAI:.0f} s depasse",
                                 -1, DELAI * 1000, interrompu=True)
            return Execution(self.nom, (fini.stdout or "")[:SORTIE_MAX],
                             (fini.stderr or "")[:SORTIE_MAX],
                             fini.returncode,
                             (time.perf_counter() - debut) * 1000)


class Bride(SousProcessus):
    """Le même, mais sans rien lui donner.

    · environnement VIDE — plus de clés d'API à lire ;
    · dossier courant vide et jetable — plus de fichiers du projet ;
    · sortie plafonnée — plus de réponse de 400 Mo.

    ⚠️ Il reste le RÉSEAU. Le couper en Python portable n'est pas possible :
    il faut un conteneur, un espace de noms réseau ou un pare-feu. Le chapitre
    3 le mesure et ne prétend pas le contraire.
    """

    nom = "bride"
    protege = ("memoire du processus", "boucle infinie",
               "variables d'environnement", "fichiers du projet")

    def _environnement(self) -> dict:
        # TODO : ne laisser au sous-processus que le strict necessaire pour demarrer — PATH et SYSTEMROOT — et rien d'autre. Toute variable qui reste est lisible par le code du candidat, cles d'API comprises. ⚠️ Vider l'environnement ne vaut que ce que le LANCEUR y remet ensuite : sous « uv run », PYTHONUSERBASE reapparait. Un test le verifie sur la propriete qui compte, pas sur un compte exact.
        return dict(os.environ)

    def _dossier(self, base: Path) -> Path:
        vide = base / "vide"
        vide.mkdir(exist_ok=True)
        return vide


NIVEAUX: tuple[Executeur, ...] = (EnLocal(), SousProcessus(), Bride())
