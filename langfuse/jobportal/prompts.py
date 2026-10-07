"""La gestion de prompts — la forme reelle, et l'equivalent local.

CE QUE FAIT LE VRAI LANGFUSE

    prompt = get_client().get_prompt("assistant-carriere", label="production")
    texte = prompt.compile(portail="syllatech")

`get_prompt` interroge l'API : il faut un serveur. Ce module implemente le
MEME contrat en local — versions, labels, compilation — pour que le mecanisme
soit mesurable. C'est une substitution, et elle est dite.

CE QUE LE CHAPITRE DOIT FAIRE COMPRENDRE

Deplacer un label ne redeploie rien. C'est l'argument central, et c'est aussi
le danger central : un prompt qui change sans passer par la revue de code
change le comportement de la production sans aucune trace dans git.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class PromptIntrouvable(LookupError):
    """Levee quand aucune version ne porte le label demande."""


@dataclass
class Version:
    numero: int
    modele: str
    texte: str
    labels: set[str] = field(default_factory=set)

    def compile(self, **variables) -> str:
        """Substitue les `{{variable}}`.

        ⚠️ Une variable absente reste LITTERALE : « {{portail}} » part tel quel
        au modele. Aucune erreur — juste un prompt qui parle d'une variable au
        lieu de sa valeur. On le verifie donc explicitement.
        """
        # >>> depart: substituer chaque {{variable}} par sa valeur. Une variable absente doit rester LITTERALE — c'est le comportement reel, et un test l'exige : aucune erreur, juste un prompt qui parle d'une variable au lieu de sa valeur.
        #     return self.texte
        texte = self.texte
        for nom, valeur in variables.items():
            texte = texte.replace("{{" + nom + "}}", str(valeur))
        return texte
        # <<<

    @property
    def variables(self) -> set[str]:
        import re
        return set(re.findall(r"\{\{(\w+)\}\}", self.texte))


class Depot:
    """Les versions d'un prompt, et les labels qui pointent dessus."""

    def __init__(self) -> None:
        self._versions: dict[str, list[Version]] = {}

    def publier(self, nom: str, texte: str, modele: str = "haiku",
                labels: set[str] | None = None) -> Version:
        versions = self._versions.setdefault(nom, [])
        version = Version(len(versions) + 1, modele, texte, set(labels or ()))
        # Un label ne pointe que sur UNE version : le poser ailleurs le retire
        # d'ou il etait. C'est exactement ce qu'on veut — et ce qui fait qu'un
        # deploiement de prompt est instantane et sans redemarrage.
        # >>> depart: retirer le label des versions precedentes. Un label ne pointe que sur UNE version — c'est ce qui fait qu'un deploiement de prompt est instantane, et qu'un retour arriere l'est aussi. Deux tests le verifient.
        #     pass
        for autre in versions:
            autre.labels -= version.labels
        # <<<
        versions.append(version)
        return version

    def etiqueter(self, nom: str, numero: int, label: str) -> None:
        for version in self._versions.get(nom, []):
            version.labels.discard(label)
            if version.numero == numero:
                version.labels.add(label)

    def get_prompt(self, nom: str, label: str = "production") -> Version:
        for version in reversed(self._versions.get(nom, [])):
            if label in version.labels:
                return version
        raise PromptIntrouvable(
            f"aucune version de « {nom} » ne porte le label « {label} ». "
            f"En production, get_prompt echoue — ou sert le cache, ce qui est pire.")

    def versions(self, nom: str) -> list[Version]:
        return list(self._versions.get(nom, []))
