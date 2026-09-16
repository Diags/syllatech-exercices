"""Le graphe de connaissance temporel — le cœur de Zep, écrit en entier.

POURQUOI L'ÉCRIRE PLUTÔT QUE D'APPELER ZEP

`zep-cloud` demande une clé et un service distant. On ne peut donc ni
l'exécuter chez soi, ni — et c'est le plus gênant — **regarder ce qu'il fait**.
Or ce que le cours enseigne n'est pas l'API en quatre appels : c'est le
mécanisme temporel, et il est invisible depuis l'extérieur.

Ce module l'implémente. Les faits portent une validité, un fait nouveau peut
en **invalider** un ancien, et le bloc de contexte ne montre que ce qui est
vrai *maintenant*. C'est exactement ce que Zep fait, et c'est ici inspectable
ligne à ligne.

CE QUI EST SUBSTITUÉ

L'extraction de faits. Zep utilise un modèle ; ici, des motifs. Un vrai
extracteur trouve plus de choses et se trompe autrement — mais la STRUCTURE
qu'il produit est la même, et c'est elle qui décide du comportement de
l'assistant.

LA DIFFÉRENCE AVEC UN RAG, ET ELLE EST STRUCTURELLE

Un RAG cherche des *documents* et rend les plus proches. Un graphe temporel
garde des *faits datés* et sait qu'un fait en a remplacé un autre. Sur
« je cherchais à Paris » puis « finalement, plutôt Lyon », un RAG rend les deux
— et l'assistant propose Paris une fois sur deux.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone


def maintenant() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Fait:
    """Une arête du graphe : un fait, et sa fenêtre de validité.

    `invalid_at` est ce qui distingue Zep d'un magasin de souvenirs. Un fait
    n'est pas supprimé quand il devient faux : il est **fermé**. On peut donc
    répondre à « que croyait-on en mars ? », et surtout ne pas resservir en
    juillet ce qui était vrai en mars.
    """

    sujet: str
    predicat: str          # la catégorie : "lieu", "contrat", "salaire"…
    objet: str
    texte: str
    valid_at: datetime = field(default_factory=maintenant)
    invalid_at: datetime | None = None
    source: str = "message"

    @property
    def valide(self) -> bool:
        return self.invalid_at is None

    def fermer(self, quand: datetime | None = None) -> None:
        self.invalid_at = quand or maintenant()

    def __str__(self) -> str:
        fin = (self.invalid_at.date().isoformat() if self.invalid_at
               else "present")
        return f"{self.texte}  [{self.valid_at.date().isoformat()} → {fin}]"


# ------------------------------------------------------------- extraction

def _plat(texte: str) -> str:
    sans = unicodedata.normalize("NFD", texte)
    return "".join(c for c in sans if unicodedata.category(c) != "Mn").lower()


# Chaque motif produit un fait. Le PRÉDICAT est ce qui compte : deux faits de
# même sujet et même prédicat ne peuvent pas être vrais en même temps, et
# c'est ce qui déclenche l'invalidation.
MOTIFS: list[tuple[str, str, str]] = [
    # La ville, avec ou SANS préposition. Exiger « à Lyon » ferait rater
    # « finalement je préfère Lyon » — et c'est exactement la phrase qui doit
    # invalider la précédente. Un extracteur trop strict ne se trompe pas : il
    # ne trouve rien, ce qui est pire, parce que rien ne le signale.
    ("lieu", r"\b(lyon|paris|nantes|bordeaux|lille|toulouse)\b",
     "{sujet} cherche un poste a {objet}"),
    ("teletravail", r"\b(teletravail complet|full remote|100 ?% remote)\b",
     "{sujet} veut du teletravail complet"),
    ("teletravail", r"\b(sur site|presentiel|au bureau)\b",
     "{sujet} veut travailler sur site"),
    ("contrat", r"\b(cdi|cdd|freelance|alternance)\b",
     "{sujet} cherche un {objet}"),
    ("salaire", r"\b(\d{2})\s*(?:k|000)\b",
     "{sujet} vise {objet}k euros"),
    ("metier", r"\b(devops|python|java|data|cloud|kubernetes)\b",
     "{sujet} s'interesse au {objet}"),
]


def extraire(sujet: str, texte: str, quand: datetime | None = None,
             source: str = "message") -> list[Fait]:
    """Tire des faits d'un message.

    Volontairement simple : ce n'est pas un extracteur, c'est un gabarit. Mais
    il produit la même STRUCTURE qu'un vrai — sujet, prédicat, objet, date —
    et c'est cette structure qui décide de tout le reste.
    """
    plat = _plat(texte)
    faits = []
    for predicat, motif, gabarit in MOTIFS:
        m = re.search(motif, plat)
        if not m:
            continue
        objet = m.group(1)
        faits.append(Fait(sujet=sujet, predicat=predicat, objet=objet,
                          texte=gabarit.format(sujet=sujet, objet=objet),
                          valid_at=quand or maintenant(), source=source))
    return faits


# ----------------------------------------------------------------- graphe

class Graphe:
    """Les faits d'un utilisateur, avec leur histoire."""

    def __init__(self) -> None:
        self.faits: list[Fait] = []

    # -- écriture ---------------------------------------------------

    def ajouter(self, fait: Fait) -> list[Fait]:
        """Ajoute un fait, et FERME ceux qu'il contredit.

        C'est la seule ligne qui compte de tout ce module. Deux faits de même
        sujet et même prédicat ne peuvent pas être vrais en même temps : le
        nouveau ferme l'ancien, à la date où le nouveau commence.

        Un fait IDENTIQUE ne ferme rien — sinon répéter une préférence la
        remettrait à zéro, et l'on perdrait depuis quand elle tient.
        """
        # TODO : fermer les faits que celui-ci contredit — meme sujet, meme predicat, objet DIFFERENT. Un fait identique ne ferme rien, sinon repeter une preference la remettrait a zero. Et si le fait arrive EN RETARD (valid_at plus ancien), c'est LUI qu'on ferme, sinon on produit un intervalle inverse. Six tests le verifient.
        self.faits.append(fait); return []

    def ajouter_message(self, sujet: str, texte: str,
                        quand: datetime | None = None) -> list[Fait]:
        nouveaux = []
        for fait in extraire(sujet, texte, quand):
            self.ajouter(fait)
            nouveaux.append(fait)
        return nouveaux

    def ajouter_donnee(self, sujet: str, donnee: dict,
                       quand: datetime | None = None) -> Fait:
        """Un fait MÉTIER, qui ne vient d'aucune conversation.

        C'est `graph.add(type="json", ...)` du chapitre 5, et c'est ce qui
        sépare une mémoire conversationnelle d'une mémoire tout court : une
        candidature envoyée est un fait, et l'assistant doit le savoir sans
        que personne ne le lui ait dit.
        """
        fait = Fait(sujet=sujet, predicat=donnee.get("event_type", "evenement"),
                    objet=str(donnee.get("offre", "")),
                    texte=_texte_metier(sujet, donnee),
                    valid_at=quand or maintenant(), source="json")
        self.ajouter(fait)
        return fait

    # -- lecture ----------------------------------------------------

    def valides(self, sujet: str | None = None) -> list[Fait]:
        return [f for f in self.faits
                if f.valide and (sujet is None or f.sujet == sujet)]

    def historique(self, sujet: str, predicat: str) -> list[Fait]:
        return [f for f in self.faits
                if f.sujet == sujet and f.predicat == predicat]

    def a_la_date(self, sujet: str, quand: datetime) -> list[Fait]:
        """Ce qu'on croyait à une date donnée.

        Impossible avec une mémoire qui supprime. C'est ce que la fenêtre de
        validité achète, et c'est ce qui permet de répondre à « pourquoi
        m'as-tu proposé Paris en mars ? ».
        """
        # TODO : rendre les faits du sujet qui etaient VALIDES a cette date — ouverts avant, et pas encore fermes. Deux tests le verifient.
        return []

    def chercher(self, sujet: str, requete: str,
                 combien: int = 5) -> list[Fait]:
        """La recherche du chapitre 5, sur les faits VALIDES.

        Chercher dans les faits fermés donnerait des réponses périmées avec
        l'assurance du présent — exactement ce que le graphe temporel évite.
        """
        mots = set(re.findall(r"\w{4,}", _plat(requete)))
        notes = []
        for fait in self.valides(sujet):
            cible = set(re.findall(r"\w{4,}", _plat(fait.texte)))
            note = len(mots & cible)
            if note:
                notes.append((note, fait))
        notes.sort(key=lambda x: -x[0])
        return [f for _, f in notes[:combien]]


def _texte_metier(sujet: str, donnee: dict) -> str:
    evenement = donnee.get("event_type", "evenement")
    if evenement == "candidature_envoyee":
        salaire = donnee.get("salaire_propose")
        montant = f" ({salaire // 1000} k EUR)" if salaire else ""
        return f"{sujet} a postule a « {donnee.get('offre', '?')} »{montant}"
    return f"{sujet} : {evenement} — {donnee.get('offre', '')}"
