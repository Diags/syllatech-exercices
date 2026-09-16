"""Le Flow du chapitre 5 — l'orchestration evenementielle.

UN CREW N'EST PAS UN FLOW, et c'est la distinction du chapitre.

Un `Crew` execute des taches : sequentiellement, ou sous la conduite d'un
manager. L'enchainement est decide PAR LE MODELE, ou par l'ordre de la liste.

Un `Flow` est du CODE : des methodes Python, un etat partage, et des
branchements ecrits par vous. `@router` decide, `@listen` reagit. Rien n'y est
laisse au modele — ce qui le rend testable, reproductible, et gratuit sur les
branches qui n'appellent aucun agent.

La regle qui en decoule : **ce qui doit etre fiable va dans le Flow, ce qui
demande du jugement va dans le Crew.**
"""

from __future__ import annotations

from crewai.flow.flow import Flow, listen, router, start

from .equipe import equipe_outillee, equipe_typee


class VeilleFlow(Flow):
    """Collecter, evaluer, puis publier — ou resoumettre.

    La branche `resoumettre` ne coute RIEN : elle n'appelle aucun agent. C'est
    tout l'interet d'un routeur ecrit en Python — dans un crew, la meme
    decision serait prise par un modele, donc payee et parfois mal prise.
    """

    def __init__(self, modele=None, sujet: str = "DevOps",
                 collecte_vide: bool = False, **kw) -> None:
        super().__init__(**kw)
        self._modele = modele
        self._sujet = sujet
        # Un routeur dont une seule branche est jamais parcourue n'est pas un
        # routeur : c'est une ligne droite avec un « if » decoratif. Ce
        # parametre sert a emprunter l'autre branche, et un test l'exige.
        #
        # ⚠️ Ne PAS le faire en heritant et en redefinissant `collecter` : le
        # decorateur @start() est enregistre a la creation de la classe, et
        # une redefinition dans une sous-classe le perd — le flux s'arrete
        # apres la premiere etape, sans erreur.
        self._collecte_vide = collecte_vide
        self.journal: list[str] = []

    @start()
    def collecter(self):
        self.journal.append("collecter")
        if self._collecte_vide:
            self.state["rapport"] = None
            return None
        resultat = equipe_typee(self._modele).kickoff(inputs={"sujet": self._sujet})
        self.state["rapport"] = resultat.pydantic
        return resultat.pydantic

    @router(collecter)
    def evaluer(self, rapport=None):
        self.journal.append("evaluer")
        rapport = rapport or self.state.get("rapport")
        # TODO : rendre « publier » si le rapport porte au moins une tendance, « resoumettre » sinon. Le seuil est du CODE : il ne varie pas d'une execution a l'autre et se teste sans modele. Trois tests le verifient, dont un qui exige que les DEUX branches soient empruntees.
        return "publier"

    # ⚠️ LE NOM DU HANDLER NE PEUT PAS ETRE CELUI DE L'EVENEMENT.
    #
    # Le chapitre 5 ecrit :
    #
    #     @listen("publier")
    #     def publier(self): ...
    #
    # CrewAI 1.x le REFUSE a la construction du flux : « a listener triggered
    # by its own completion creates an infinite loop ». La classe ne se cree
    # meme pas. Le handler doit donc porter un autre nom que l'evenement qu'il
    # ecoute — d'ou `envoyer_newsletter` ci-dessous.
    @listen("publier")
    def envoyer_newsletter(self):
        self.journal.append("publier")
        rapport = self.state.get("rapport")
        return f"newsletter envoyee : {getattr(rapport, 'resume', '')[:60]}"

    @listen("resoumettre")
    def signaler_le_vide(self):
        self.journal.append("resoumettre")
        return "rapport vide — aucune newsletter, aucun agent relance"
