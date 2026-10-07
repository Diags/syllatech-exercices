"""Code Interpreter — la forme réelle de l'API, sur un exécuteur local.

Le cours écrit :

    from bedrock_agentcore.tools.code_interpreter_client import code_session

    with code_session("eu-west-1") as session:
        resultat = session.invoke("executeCode",
                                  {"language": "python", "code": "..."})

`code_session` et `CodeInterpreter` **existent** dans le SDK installé — ce
module le vérifie et affiche leur vraie signature. Mais ils ouvrent une
session AgentCore chez AWS : sans compte, sans région et sans rôle IAM, rien
ne s'exécute.

CE QUI EST SUBSTITUÉ

L'exécution distante. `Bac` exécute le code **ici**, dans un espace de noms
séparé, avec la même méthode `invoke(method, params)` et le même cycle
session → exécutions → destruction.

⚠️ CE N'EST PAS LA MÊME ISOLATION. Celle d'AgentCore est un environnement
distant, jetable, sans accès à votre réseau ni à vos secrets. Celle-ci est un
dictionnaire Python : elle sépare les VARIABLES, pas les privilèges. Le
chapitre 2 mesure ce qu'elle enseigne — le cycle et le flux de données — et
dit ce qu'elle ne prouve pas.
"""

from __future__ import annotations

import io
import contextlib
from dataclasses import dataclass, field


class SessionFermee(Exception):
    pass


@dataclass
class Evenement:
    """Un événement du flux que rend `invoke`."""

    type: str                  # "stdout", "resultat", "erreur"
    contenu: str


@dataclass
class Bac:
    """La forme de `CodeInterpreter`, sur un exécuteur local.

    Les noms sont ceux du SDK : `start`, `invoke`, `stop`, et un `session_id`.
    """

    region: str = "eu-west-1"
    session_id: str | None = None
    espace: dict = field(default_factory=dict)
    executions: int = 0
    fichiers: dict[str, str] = field(default_factory=dict)

    # -- cycle de vie -----------------------------------------------

    def start(self) -> str:
        self.session_id = f"ci-{self.region}-{id(self) % 100000:05d}"
        # L'espace de noms est neuf : rien de la session précédente n'y est.
        self.espace = {"__builtins__": __builtins__}
        return self.session_id

    def stop(self) -> None:
        """La session est JETABLE, et c'est la moitié de la sécurité.

        Tout ce qui a été installé, écrit ou calculé disparaît. Un code
        malveillant exécuté au tour 3 ne peut donc rien laisser pour le tour 4.
        """
        self.session_id = None
        self.espace = {}
        self.fichiers = {}

    def __enter__(self) -> "Bac":
        self.start()
        return self

    def __exit__(self, *_) -> None:
        self.stop()

    # -- la seule méthode du SDK ------------------------------------

    def invoke(self, method: str, params: dict | None = None) -> list[Evenement]:
        if self.session_id is None:
            raise SessionFermee("appelez start(), ou utilisez « with »")
        params = params or {}
        if method == "executeCode":
            return self._executer(params.get("code", ""))
        if method == "writeFiles":
            for fichier in params.get("content", []):
                self.fichiers[fichier["path"]] = fichier["text"]
            return [Evenement("resultat", f"{len(self.fichiers)} fichier(s)")]
        if method == "listFiles":
            return [Evenement("resultat", ", ".join(sorted(self.fichiers)))]
        raise ValueError(f"methode inconnue : {method}")

    def _executer(self, code: str) -> list[Evenement]:
        self.executions += 1
        # Les fichiers televerses sont lisibles depuis le code, comme dans la
        # vraie sandbox : on televerse, puis le code lit. C'est ce qui evite
        # de faire passer les donnees par le CONTEXTE du modele.
        # >>> depart: executer le code dans self.espace, en capturant stdout, et rendre les evenements. L'espace est GARDE d'un appel a l'autre — c'est ce qui permet d'ecrire une fonction au tour 1 et de l'appeler au tour 2. Une exception devient un Evenement("erreur", ...) et NE tue pas la session : l'agent doit pouvoir lire l'erreur et corriger. Les fichiers televerses sont exposes sous FICHIERS. Cinq tests le verifient.
        #     return [Evenement("stdout", "")]
        self.espace["FICHIERS"] = dict(self.fichiers)
        sortie = io.StringIO()
        try:
            # ⚠️ L'espace de noms est GARDÉ d'un appel à l'autre : c'est ce qui
            # permet d'écrire une fonction au tour 1 et de l'appeler au tour 2.
            # C'est aussi ce qui fait qu'une variable mal nommée persiste.
            with contextlib.redirect_stdout(sortie):
                exec(code, self.espace)      # noqa: S102
        except Exception as erreur:          # noqa: BLE001
            return [Evenement("erreur", f"{type(erreur).__name__}: {erreur}")]
        texte = sortie.getvalue().strip()
        return [Evenement("stdout", texte)] if texte else []
        # <<<


def code_session(region: str = "eu-west-1") -> Bac:
    """Le nom du SDK, sur le bac local. À utiliser avec `with`."""
    return Bac(region=region)


def sdk_reel() -> dict:
    """Ce que le SDK installé expose vraiment — pour pouvoir le comparer."""
    import inspect

    from bedrock_agentcore.tools import code_interpreter_client as reel

    return {
        "code_session": str(inspect.signature(reel.code_session)),
        "invoke": str(inspect.signature(reel.CodeInterpreter.invoke)),
        "methodes": sorted(m for m in dir(reel.CodeInterpreter)
                           if not m.startswith("_")),
    }


# --------------------------------------------- ce que le modèle reçoit

def cout_en_signes(texte: str) -> int:
    return len(texte)


def sans_sandbox(code: str, resultat: str) -> str:
    """Ce qu'un agent sans sandbox remonte : le code, et un calcul de tête."""
    return f"J'ai calcule : {code}\nResultat (de tete) : {resultat}"


def avec_sandbox(evenements: list[Evenement]) -> str:
    """Ce qui remonte au modèle : le RÉSULTAT seul.

    Le code ne revient pas dans le contexte. C'est la différence qui compte à
    la dixième itération : l'historique ne grossit pas du code généré.
    """
    return "\n".join(e.contenu for e in evenements if e.type != "erreur")
