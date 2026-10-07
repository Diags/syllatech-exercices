"""Les gardes — autour de `tools.approval` et `tools.skills_guard` de Hermes.

Deux gardes, deux natures :

  · **`tools.approval`** regarde une COMMANDE avant de l'exécuter. 70 motifs
    « dangereux » (demander confirmation) et 12 « hardline » (refuser).
  · **`tools.skills_guard`** regarde un FICHIER avant de l'installer. 121
    motifs de menace, 17 caractères invisibles, et des plafonds de taille.

Aucune commande n'est exécutée par ce module : on demande son avis à la
garde, on lit sa réponse. C'est tout ce qu'il faut pour mesurer ce qu'elle
attrape — et ce qu'elle laisse passer.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tools import approval, skills_guard


@dataclass
class Verdict:
    commande: str
    dangereuse: bool
    raison_dangereuse: str
    hardline: bool
    raison_hardline: str

    @property
    def issue(self) -> str:
        """Ce qui arrive vraiment à la commande.

        Les trois issues ne sont pas graduées de la même façon : « hardline »
        est un REFUS, « dangereuse » est une DEMANDE. La seconde dépend donc
        de quelqu'un pour répondre — et en cron, personne ne répond.
        """
        if self.hardline:
            return "REFUS"
        if self.dangereuse:
            return "demande"
        return "passe"


def juger(commande: str) -> Verdict:
    # ⚠️ Les deux détecteurs ne rendent PAS la même forme :
    #   detect_dangerous_command -> (bool, raison, categorie)   — 3 valeurs
    #   detect_hardline_command  -> (bool, raison)              — 2 valeurs
    # Les dépaqueter pareil lève un ValueError au premier appel. C'est
    # visible tout de suite ; le piège serait de n'en appeler qu'un.
    # TODO : interroger les deux detecteurs de tools.approval et rendre un Verdict. ⚠️ Ils n'ont PAS la meme forme : detect_dangerous_command rend trois valeurs (bool, raison, categorie), detect_hardline_command en rend deux. Les depaqueter pareil leve un ValueError. Douze tests le verifient.
    return Verdict(commande, False, "", False, "")


def compteurs() -> dict[str, int]:
    return {
        "motifs_dangereux": len(approval.DANGEROUS_PATTERNS),
        "motifs_hardline": len(approval.HARDLINE_PATTERNS),
        "motifs_de_menace": len(skills_guard.THREAT_PATTERNS),
        "caracteres_invisibles": len(skills_guard.INVISIBLE_CHARS),
        "fichiers_max": skills_guard.MAX_FILE_COUNT,
        "ko_par_fichier": skills_guard.MAX_SINGLE_FILE_KB,
        "ko_au_total": skills_guard.MAX_TOTAL_SIZE_KB,
    }


# ----------------------------------------------- le scanner de skills

def scanner(chemin: Path):
    """`skills_guard.scan_file` sur un vrai fichier."""
    return skills_guard.scan_file(chemin)


def empreinte(texte: str) -> str:
    return skills_guard.content_hash(texte)


def depots_de_confiance() -> list[str]:
    return sorted(skills_guard.TRUSTED_REPOS)


def invisibles(texte: str) -> list[str]:
    """Les caractères invisibles présents dans un texte.

    ⚠️ C'est un vecteur d'injection réel : un caractère de direction ou une
    espace de largeur nulle sépare visuellement deux mots qui n'en font
    qu'un pour le modèle, ou cache une consigne au relecteur humain. Le
    fichier a l'air propre à l'écran, et ne l'est pas.
    """
    return sorted({hex(ord(c)) for c in texte
                   if c in skills_guard.INVISIBLE_CHARS})
