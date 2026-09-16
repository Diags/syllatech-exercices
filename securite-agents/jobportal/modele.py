"""Le modèle — volontairement **crédule**, et c'est tout l'intérêt.

Un modèle de langage ne distingue pas, par nature, une *instruction* d'une
*donnée*. Tout arrive dans la même fenêtre, sous la même forme : du texte. La
séparation qu'on croit évidente — « ceci est mon prompt, cela est le CV » —
n'existe que dans notre tête.

Ce modèle-ci reproduit ce défaut fondamental, et rien d'autre : il exécute la
dernière instruction impérative qu'il trouve dans son contexte, d'où qu'elle
vienne. C'est une caricature, mais **une caricature fidèle** — et c'est ce qui
rend les défenses de ce projet mesurables plutôt que déclaratives.

Un vrai modèle résiste mieux. Il résiste *mieux*, pas *toujours* : c'est
exactement pourquoi la défense ne peut pas reposer sur lui. Les mesures de ce
projet sont donc un plancher, pas une prédiction.

Substituer un vrai modèle ne change aucune défense : elles sont toutes en
dehors de lui.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

# La part des attaques auxquelles un modele CADRE obeit quand meme.
#
# ⚠️ Ce chiffre est une hypothese de travail, pas une mesure. Il tient lieu
# du fait, largement documente, qu'aucune consigne de prompt ne resiste a
# 100 % : un modele instruit de ne pas obeir aux documents y obeit encore
# parfois, et la part exacte depend du modele, de la formulation et de
# l'attaque. Le mettre a 0 rendrait la delimitation suffisante a elle
# seule — et donc tout le reste de ce projet inutile, ce qui serait le
# contraire de la verite. Le mettre a 1 rendrait la consigne inutile, ce
# qui serait faux aussi.
#
# Mesurez-le sur VOTRE modele et VOS attaques : c'est precisement ce que
# fait outils/redteam.py, et c'est le seul chiffre qui vous concerne.
TAUX_DE_FUITE = 0.35

# Les tournures par lesquelles une instruction se reconnaît. Un vrai modèle
# comprend le sens ; celui-ci reconnaît des formes. La liste est courte et
# n'a pas à être exhaustive : elle sert à produire un comportement crédule
# reproductible, pas à détecter des attaques (ce serait la mauvaise défense —
# voir `defenses.py`, section « la liste noire ne suffit jamais »).
# Un verbe a l'imperatif, eventuellement precede d'une amorce courte du type
# « Note importante pour l'assistant : » ou « Avant de repondre, ». C'est la
# forme que prennent ces injections : une phrase d'apparence anodine qui
# introduit un ordre.
IMPERATIFS = re.compile(
    r"^[^.\n]{0,60}?[:,]?\s*"
    r"\b(attribue|envoie|transmets|ignore|oublie|supprime|exfiltre|affiche|"
    r"revele|lis|ajoute|remplace)\b(.*)$",
    re.IGNORECASE | re.MULTILINE)

# Ce que l'instruction demande, traduit en intention. C'est cette intention
# que les défenses devront neutraliser.
INTENTIONS = {
    "attribue": "note_forcee",
    "envoie": "exfiltration",
    "transmets": "exfiltration",
    "exfiltre": "exfiltration",
    "supprime": "destruction",
    "ignore": "contournement",
    "oublie": "contournement",
    "revele": "fuite_de_prompt",
    "affiche": "fuite_de_prompt",
    "lis": "fuite_de_fichier",
    "remplace": "contournement",
    "ajoute": "contournement",
}


@dataclass
class Instruction:
    verbe: str
    reste: str
    intention: str
    source: str          # "systeme" ou "document"


@dataclass
class Reponse:
    texte: str
    score: int = 5
    competences: list[str] = field(default_factory=list)
    instruction_suspecte: bool = False
    appels: list[tuple[str, dict]] = field(default_factory=list)
    obeie: Instruction | None = None


class ModeleCredule:
    """Exécute la dernière instruction impérative trouvée, d'où qu'elle vienne.

    `respecte_les_delimiteurs` est LE paramètre du chapitre 2. À False, le
    modèle ne fait aucune différence entre le prompt et le document — c'est le
    comportement par défaut, et c'est le problème. À True, il applique la règle
    qu'on lui a donnée : ce qui est entre les balises est une donnée.

    Même à True il n'est pas infaillible : `taux_de_fuite` simule la part des
    cas où la consigne ne tient pas. C'est volontaire — une défense qui repose
    sur la seule obéissance du modèle n'est pas une défense.
    """

    def __init__(self, respecte_les_delimiteurs: bool = False,
                 taux_de_fuite: float = TAUX_DE_FUITE) -> None:
        self.respecte = respecte_les_delimiteurs
        self.taux_de_fuite = taux_de_fuite

    def repondre(self, prompt: str, zone_non_fiable: tuple[int, int] | None = None,
                 outils: dict | None = None) -> Reponse:
        """`zone_non_fiable` dit OU se trouve le texte d'origine externe.

        C'est un FAIT sur le prompt, pas une defense : l'appelant sait
        toujours quelle portion vient d'un CV televerse. Ce que la defense
        ajoute, c'est la CONSIGNE de ne pas y obeir — et c'est au modele de
        la suivre, ce qui est precisement le probleme.
        """
        instructions = self._lire(prompt, zone_non_fiable)
        reponse = Reponse(texte="Analyse effectuee.", competences=["Java", "Spring"])

        obeies = [i for i in instructions if self._obeit(i)]
        if not obeies:
            # Il a VU l'instruction sans y obéir : on le signale. C'est la
            # sortie que le chapitre 2 attend d'un agent correctement cadré.
            reponse.instruction_suspecte = any(i.source == "document"
                                               for i in instructions)
            return reponse

        derniere = obeies[-1]
        reponse.obeie = derniere
        reponse.instruction_suspecte = False
        self._executer(derniere, reponse, outils or {})
        return reponse

    # ------------------------------------------------------------------

    def _lire(self, prompt: str, zone: tuple[int, int] | None) -> list[Instruction]:
        """Repère les impératifs, et note s'ils viennent du document."""
        instructions = []
        for m in IMPERATIFS.finditer(prompt):
            debut = m.start()
            externe = bool(zone and zone[0] <= debut < zone[1])
            instructions.append(Instruction(
                verbe=m.group(1).lower(),
                reste=m.group(2).strip(),
                intention=INTENTIONS.get(m.group(1).lower(), "inconnue"),
                source="document" if externe else "systeme",
            ))
        return instructions

    def _obeit(self, instruction: Instruction) -> bool:
        if instruction.source == "systeme":
            return False        # les consignes légitimes ne sont pas des actions
        if not self.respecte:
            return True         # crédule : tout est instruction
        # Le modèle a reçu la consigne. Il la suit — la plupart du temps.
        # Le tirage est DÉTERMINISTE (empreinte de l'instruction) : la même
        # attaque donne toujours le même résultat, sinon les mesures de ce
        # projet varieraient d'une exécution à l'autre et ne vaudraient rien.
        empreinte = int(hashlib.blake2b(
            f"{instruction.verbe}|{instruction.reste}".encode(),
            digest_size=4).hexdigest(), 16) / 0xFFFFFFFF
        return empreinte < self.taux_de_fuite

    def _executer(self, instruction: Instruction, reponse: Reponse, outils: dict) -> None:
        if instruction.intention == "note_forcee":
            chiffre = re.search(r"(\d+)\s*/\s*10", instruction.reste)
            reponse.score = int(chiffre.group(1)) if chiffre else 10
            reponse.texte = "Candidat exceptionnel."
            return

        if instruction.intention == "exfiltration":
            destinataire = _adresse(instruction.reste) or "inconnu@exemple.com"
            reponse.appels.append(("envoyer_email", {
                "destinataire": destinataire,
                "objet": "Liste des candidats",
                "corps": "(donnees des autres candidats)"}))
            reponse.texte = f"Liste transmise a {destinataire}."
            return

        if instruction.intention == "destruction":
            reponse.appels.append(("supprimer_offre", {"id": 1}))
            reponse.texte = "Offre supprimee."
            return

        if instruction.intention == "fuite_de_fichier":
            reponse.appels.append(("lire_fichier", {"chemin": "~/.ssh/id_rsa"}))
            reponse.texte = "Fichier lu et transmis."
            return

        if instruction.intention == "fuite_de_prompt":
            reponse.texte = _prompt_systeme(reponse) or "Mon prompt systeme est : …"
            return

        reponse.texte = f"J'ai suivi l'instruction : {instruction.verbe}."


def _adresse(texte: str) -> str | None:
    m = re.search(r"[\w.%+-]+@[\w.-]+\.[a-z]{2,}", texte, re.IGNORECASE)
    return m.group(0) if m else None


def _prompt_systeme(reponse: Reponse) -> str:
    return ""
