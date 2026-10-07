#!/usr/bin/env python3
"""Le verificateur d'agent — ce qui se deploie et ne marche pas.

    uv run python outils/verifier_agent.py jobportal.agent

Il importe un module, y trouve un BedrockAgentCoreApp, et l'interroge : le
contrat est-il tenu ? Les sept defauts qu'il attrape ont tous ete mesures au
chapitre 1, et ils ont la meme forme — `agentcore launch` reussit, l'agent
repond 200, et quelque chose ne fait pas ce qu'on croit.
"""

from __future__ import annotations

import importlib
import inspect
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal.commun import silence            # noqa: E402
from jobportal.contrat import appeler           # noqa: E402

for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except Exception:      # noqa: BLE001
        pass


@dataclass
class Souci:
    gravite: str          # "erreur" ou "attention"
    ou: str
    message: str


def verifier(app, module=None) -> list[Souci]:
    soucis: list[Souci] = []

    # 1. Un entrypoint, et un seul --------------------------------------
    if not app.handlers:
        return [Souci("erreur", "@app.entrypoint",
                      "aucun entrypoint : /invocations rend 500 « No "
                      "entrypoint defined » a chaque appel")]

    if module is not None:
        decores = _fonctions_decorees(module)
        if len(decores) > 1:
            soucis.append(Souci(
                "erreur", "@app.entrypoint",
                f"{len(decores)} fonctions decorees ({', '.join(decores)}) "
                "mais le SDK n'en garde qu'UNE, sous la cle « main ». La "
                "derniere decoree gagne, et rien ne le signale."))

    fonction = next(iter(app.handlers.values()))
    parametres = list(inspect.signature(fonction).parameters)

    # 2. Le contexte, et donc la session --------------------------------
    if len(parametres) < 2:
        soucis.append(Souci(
            "attention", "signature de l'entrypoint",
            f"« {fonction.__name__}({', '.join(parametres)}) » ne prend pas "
            "le contexte. Sans lui, pas de session_id : impossible de "
            "rattacher un appel a une conversation, ni de separer deux "
            "utilisateurs dans vos journaux."))

    # 3. Ce que l'entrypoint rend ---------------------------------------
    with silence():
        nominal = appeler(app, {"prompt": "verification"})
    if nominal.code != 200:
        soucis.append(Souci("erreur", "/invocations",
                            f"un payload nominal rend {nominal.code} : "
                            f"{nominal.texte[:80]}"))
    elif not isinstance(nominal.json, dict):
        soucis.append(Souci(
            "erreur", "retour de l'entrypoint",
            f"le client recoit {type(nominal.json).__name__}, pas un objet "
            "JSON. Un retour non serialisable est str()-ifie SANS erreur : "
            "l'appelant recoit un repr Python dans une chaine."))

    # 4. Un payload vide ------------------------------------------------
    with silence():
        vide = appeler(app, {})
    if vide.code >= 500:
        soucis.append(Souci(
            "erreur", "payload vide",
            f"un payload {{}} rend {vide.code}. Le runtime en envoie lors "
            "des verifications : votre entrypoint doit rendre une erreur "
            "METIER, pas lever."))

    # 5. La fuite du message d'exception --------------------------------
    if not _attrape_les_exceptions(fonction):
        soucis.append(Souci(
            "attention", "gestion des erreurs",
            "aucun « try » dans l'entrypoint. Une exception qui remonte "
            "renvoie SON MESSAGE au client : nom d'hote interne, chemin de "
            "fichier ou fragment de requete SQL sortent alors du systeme."))

    # 6. La sante --------------------------------------------------------
    with silence():
        ping = appeler(app, chemin="/ping", methode="GET")
    if ping.code != 200 or "status" not in (ping.json or {}):
        soucis.append(Souci("erreur", "/ping",
                            f"la sonde de sante rend {ping.code} : "
                            f"{ping.texte[:60]}"))

    # 7. Le streaming involontaire ---------------------------------------
    if inspect.isgeneratorfunction(fonction):
        soucis.append(Souci(
            "attention", "entrypoint generateur",
            "l'entrypoint rend un generateur : le runtime passe en "
            "text/event-stream. C'est voulu pour un agent qui diffuse, et "
            "c'est une rupture de contrat si un « yield » s'y est glisse."))
    return soucis


def main() -> int:
    cible = sys.argv[1] if len(sys.argv) > 1 else "jobportal.agent"
    module = importlib.import_module(cible)
    app = next((o for o in vars(module).values()
                if type(o).__name__ == "BedrockAgentCoreApp"), None)
    if app is None:
        print(f"\n  Aucun BedrockAgentCoreApp dans « {cible} ».\n")
        return 2

    soucis = verifier(app, module)
    erreurs = [s for s in soucis if s.gravite == "erreur"]
    print(f"\n  {cible}\n")
    for souci in soucis:
        etiquette = "ERREUR    " if souci.gravite == "erreur" else "attention "
        print(f"  {etiquette} {souci.ou}")
        for ligne_ in _plier(souci.message, 64):
            print(f"             {ligne_}")
    if not soucis:
        print("  Aucun probleme detecte.")
    print(f"\n  {len(erreurs)} erreur(s), "
          f"{len(soucis) - len(erreurs)} avertissement(s)\n")
    return 1 if erreurs else 0


def _fonctions_decorees(module) -> list[str]:
    """Les fonctions portant @<quelque chose>.entrypoint, par l'AST.

    Le decorateur du SDK rend la fonction INCHANGEE : ni `__wrapped__`, ni
    attribut, rien qui distingue une fonction decoree d'une autre a
    l'execution. Chercher la marque dans l'objet ne donne donc jamais rien —
    il faut lire le fichier.
    """
    import ast

    try:
        arbre = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    except (OSError, SyntaxError, TypeError):
        return []
    noms = []
    for nœud in ast.walk(arbre):
        if not isinstance(nœud, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorateur in nœud.decorator_list:
            if (isinstance(decorateur, ast.Attribute)
                    and decorateur.attr == "entrypoint"):
                noms.append(nœud.name)
    return noms


def _attrape_les_exceptions(fonction) -> bool:
    """L'entrypoint contient-il un vrai `try` ?

    ⚠️ La version naive de ce test etait `"try" not in inspect.getsource(...)`.
    Elle ne s'est JAMAIS declenchee — parce que `getsource` inclut la ligne du
    decorateur, et que « @app.en-TRY-point » contient la sous-chaine. Un test
    qui passe toujours a exactement la meme valeur qu'aucun test, et c'est
    plus difficile a voir.

    On analyse donc l'arbre syntaxique, ou un `try` est un nœud, pas trois
    lettres.
    """
    import ast
    import textwrap

    # >>> depart: rendre True si l'entrypoint contient un vrai bloc « try ». ⚠️ Ne PAS chercher la sous-chaine dans le source : getsource inclut la ligne du decorateur, et « @app.en-TRY-point » la contient — le test passerait alors toujours, ce qui vaut exactement un test absent. Passer par l'arbre syntaxique. Un test le verifie.
    #     return True
    try:
        arbre = ast.parse(textwrap.dedent(inspect.getsource(fonction)))
    except (OSError, SyntaxError):
        return True          # source indisponible : on ne reproche rien
    return any(isinstance(n, ast.Try) for n in ast.walk(arbre))
    # <<<


def _plier(texte: str, largeur: int) -> list[str]:
    lignes, courante = [], ""
    for mot in texte.split():
        if len(courante) + len(mot) + 1 > largeur:
            lignes.append(courante)
            courante = mot
        else:
            courante = f"{courante} {mot}".strip()
    if courante:
        lignes.append(courante)
    return lignes


if __name__ == "__main__":
    sys.exit(main())
