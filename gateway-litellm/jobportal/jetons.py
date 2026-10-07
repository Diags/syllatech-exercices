"""Les jetons — écrits à la main, parce que c'est là que la chaîne casse.

Le cours montre le côté Spring :

    .oauth2ResourceServer(o -> o.jwt(withDefaults()))

Une ligne, et tout est fait. C'est excellent en production et inutilisable
pour apprendre : ce qu'elle vérifie n'apparaît nulle part. Ce module écrit la
même chose en trente lignes, pour que les quatre refus soient visibles et
testables.

Un JWT est trois parties séparées par des points, chacune en base64url :

    en-tête . charge utile . signature
    {"alg":"HS256"} . {"team":"data","exp":…} . HMAC(secret, les deux premières)

Rien n'y est chiffré : la charge utile se lit sans le secret. Le secret ne
sert qu'à prouver que personne ne l'a modifiée.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass

ALGORITHME = "HS256"


class JetonInvalide(Exception):
    """Un seul type d'erreur pour les quatre refus.

    Distinguer « signature fausse » de « jeton expiré » dans le message rendu
    au client renseignerait un attaquant sur ce qu'il doit corriger. Le détail
    part dans les journaux ; le client reçoit un refus.
    """


@dataclass
class Jeton:
    sujet: str
    equipe: str
    expire_le: float

    @property
    def expire(self) -> bool:
        return time.time() >= self.expire_le


def _b64(donnees: bytes) -> str:
    return base64.urlsafe_b64encode(donnees).rstrip(b"=").decode()


def _deb64(texte: str) -> bytes:
    return base64.urlsafe_b64decode(texte + "=" * (-len(texte) % 4))


def signer(sujet: str, equipe: str, secret: str, duree: int = 3600,
           algorithme: str = ALGORITHME) -> str:
    entete = {"alg": algorithme, "typ": "JWT"}
    charge = {"sub": sujet, "team": equipe, "exp": time.time() + duree}
    debut = f"{_b64(json.dumps(entete).encode())}." \
            f"{_b64(json.dumps(charge).encode())}"
    if algorithme == "none":
        # Un jeton « alg: none » n'a pas de signature. Il est parfaitement
        # bien formé, et c'est tout le problème : une bibliothèque qui lit
        # l'algorithme DANS le jeton pour décider comment le vérifier accepte
        # celui-ci sans secret. La faille est vieille, et elle ressort à
        # chaque réimplémentation.
        return f"{debut}."
    signature = hmac.new(secret.encode(), debut.encode(), hashlib.sha256)
    return f"{debut}.{_b64(signature.digest())}"


def verifier(jeton: str, secret: str) -> Jeton:
    """Les quatre refus, dans l'ordre où ils doivent arriver."""
    morceaux = jeton.split(".")
    if len(morceaux) != 3:
        raise JetonInvalide("un JWT a trois parties")
    entete_b64, charge_b64, signature_b64 = morceaux

    try:
        entete = json.loads(_deb64(entete_b64))
        charge = json.loads(_deb64(charge_b64))
    except Exception as erreur:                  # noqa: BLE001
        raise JetonInvalide("base64 ou JSON illisible") from erreur

    # TODO : refuser (1) tout algorithme autre que HS256 — l'algorithme ATTENDU est celui du serveur, jamais celui que le jeton annonce, sinon « alg: none » passe ; (2) une signature fausse, comparee avec compare_digest pour ne pas fuir sa longueur par le temps de reponse ; (3) un jeton expire ; (4) un jeton sans claim « team ». Huit tests le verifient.
    raise JetonInvalide("a ecrire")


def lire_sans_verifier(jeton: str) -> dict:
    """Ce que n'importe qui peut lire d'un JWT, sans le secret.

    Utile pour le montrer une fois : un JWT n'est pas un coffre. Y mettre une
    donnée confidentielle revient à la publier.
    """
    return json.loads(_deb64(jeton.split(".")[1]))
