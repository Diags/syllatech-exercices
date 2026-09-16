"""Le verdict — un objet Pydantic, pas une phrase.

Le cours le dit en une ligne : « on ne veut pas *le candidat a l'air bon*, on
veut un objet ». Ce module écrit cet objet, et surtout ses BORNES.

POURQUOI LES BORNES COMPTENT PLUS QUE LA STRUCTURE

Typer la réponse ne rend pas l'agent honnête : cela rend son enveloppe
prévisible. Un attaquant qui contrôle la sortie du code contrôle une partie
de ce que l'agent écrira — mais s'il ne peut écrire que dans un `resume` de
400 signes, il ne peut plus :

  · rendre 40 Ko de texte qu'une page affichera ;
  · placer du texte dans `score`, qui est un entier ;
  · inventer un champ que l'application lirait.

C'est la même idée qu'une colonne `VARCHAR(400)` : la contrainte n'empêche
pas d'écrire des bêtises, elle empêche d'écrire n'importe où.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

LONGUEUR_RESUME = 400


class Verdict(BaseModel):
    """Ce que l'évaluateur a le droit de rendre. Rien d'autre."""

    # >>> depart: borner chaque champ. score entre 0 et 100 ; tests_passes au plus 20 entrees ; resume au plus LONGUEUR_RESUME signes ; et « extra: forbid » pour qu'un champ invente soit REFUSE et non ignore — sinon la ligne en trop finit dans un dictionnaire que quelqu'un lira. Neuf tests le verifient.
    #     score: int = 0
    #     tests_passes: list[str] = Field(default_factory=list)
    #     comportement_suspect: bool = False
    #     resume: str = ""
    score: int = Field(ge=0, le=100,
                       description="note sur 100 de la solution du candidat")
    tests_passes: list[str] = Field(
        default_factory=list, max_length=20,
        description="noms des verifications reussies")
    comportement_suspect: bool = Field(
        default=False,
        description="le code a-t-il tente autre chose que l'exercice")
    resume: str = Field(max_length=LONGUEUR_RESUME,
                        description="une phrase de justification")

    # ⚠️ `extra="forbid"` : un champ inventé fait échouer la validation au
    # lieu d'être ignoré. Sans cela, un modèle qui rend
    # `{"score": 100, "acces_admin": true}` passe, et la ligne en trop finit
    # dans un dictionnaire que quelqu'un lira un jour.
    model_config = {"extra": "forbid"}
    # <<<

    @field_validator("resume")
    @classmethod
    def _sans_saut_de_ligne(cls, valeur: str) -> str:
        """Un résumé sur une ligne.

        Pas par coquetterie : un résumé multiligne peut porter un faux
        en-tête (« SYSTEME : … ») qui ressemble, dans un journal ou une page,
        à un message du système plutôt qu'à du texte de candidat.
        """
        return " ".join(valeur.split())


class VerdictLibre(BaseModel):
    """Ce qu'on obtient SANS sortie typée : une chaîne, et c'est tout.

    Elle est ici pour être comparée au chapitre 2 — pas pour être utilisée.
    """

    texte: str
