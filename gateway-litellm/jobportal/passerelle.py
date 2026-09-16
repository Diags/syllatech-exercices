"""La passerelle — ce que fait Spring Cloud Gateway, en Python lisible.

Le cours montre le filtre Spring :

    .oauth2ResourceServer(o -> o.jwt(withDefaults()))
    // clé virtuelle ← lookup(claim "team" du JWT) → SetRequestHeader

⚠️ CE N'EST PAS SPRING. C'est la même chaîne d'étapes, écrite pour être
exécutée et testée ici. Le code Spring du cours reste la référence : il n'est
pas compilé dans ce projet, et le README le dit.

LA SEULE CHOSE QUI COMPTE DANS CE FICHIER

    jeton = valider(jwt)                      # qui parle
    cle   = coffre[jeton.equipe]              # avec quel budget
    appel = proxy(cle, ...)                   # SANS le jwt

La passerelle **remplace** le jeton client par la clé virtuelle de l'équipe.
Elle ne l'ajoute pas à côté, et elle ne le transmet pas. Le proxy ne voit
jamais vos utilisateurs, et le client ne voit jamais la clé virtuelle : chaque
maillon ne connaît que le secret du maillon suivant.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .budgets import (BudgetDepasse, CleInconnue, ModeleInterdit,
                      Registre)
from .jetons import JetonInvalide, verifier
from .proxy import Appel, Proxy


class Refuse(Exception):
    """Un refus de la passerelle, avec son code HTTP."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass
class Trace:
    """Une ligne du journal — ce que le tableau de bord agrège."""

    equipe: str
    alias: str
    modele_reel: str
    cout: float
    jetons: int
    latence_ms: float
    bascule: bool
    code: int = 200


@dataclass
class Passerelle:
    proxy: Proxy
    registre: Registre
    secret_jwt: str
    coffre: dict[str, str] = field(default_factory=dict)   # equipe → clé
    journal: list[Trace] = field(default_factory=list)

    async def traiter(self, jwt: str, alias: str, question: str) -> Appel:
        """Le trajet complet d'une requête, dans l'ordre où il coûte le moins.

        L'ordre n'est pas décoratif : vérifier le jeton d'abord, le budget
        ensuite, appeler le fournisseur en dernier. Inverser les deux premiers
        laisserait un jeton invalide consommer une lecture de budget ;
        appeler avant de vérifier le budget ferait payer le refus.
        """
        # TODO : enchainer (1) verifier le jeton, (2) retrouver la cle virtuelle de l'equipe dans le coffre, (3) autoriser aupres du registre, (4) appeler le proxy, (5) imputer le cout reel et journaliser. Chaque echec leve un Refuse avec son code HTTP, et laisse une trace — un refus non journalise est un incident invisible. Onze tests le verifient.
        raise Refuse(500, "a ecrire")

    def _tracer(self, equipe: str, alias: str, code: int) -> None:
        self.journal.append(Trace(equipe=equipe, alias=alias, modele_reel="",
                                  cout=0.0, jetons=0, latence_ms=0.0,
                                  bascule=False, code=code))

    # -- ce que la passerelle transmet, et ce qu'elle retient --------

    def entetes_sortants(self, jwt: str) -> dict[str, str]:
        """Les en-têtes que le proxy reçoit réellement.

        Le jeton client n'y est PAS. C'est la propriété qu'un test vérifie :
        laisser passer l'Authorization d'origine « au cas où » donnerait au
        proxy — et à ses journaux — l'identité de chaque utilisateur final.
        """
        jeton = verifier(jwt, self.secret_jwt)
        return {"Authorization": f"Bearer {self.coffre[jeton.equipe]}"}
