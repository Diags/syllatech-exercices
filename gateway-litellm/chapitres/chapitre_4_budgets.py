"""Chapitre 4 — Budgets, clés virtuelles et fallbacks.

    uv run python chapitres/chapitre_4_budgets.py

Trois mesures, pas trois affirmations :

  · ce qu'une bascule coûte en latence, selon `num_retries` ;
  · de combien un budget peut être dépassé, et pourquoi ce n'est pas zéro ;
  · ce que fait vraiment un alias déclaré deux fois.
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal.budgets import BudgetDepasse, Registre, depassement_possible  # noqa: E402
from jobportal.commun import SECRET_JWT, ligne, monter, titre, utf8          # noqa: E402
from jobportal.jetons import signer                                          # noqa: E402
from jobportal.passerelle import Refuse                                      # noqa: E402
from jobportal.proxy import Proxy                                            # noqa: E402


def modele(alias: str, vrai: str, reponse: str) -> dict:
    return {"model_name": alias,
            "litellm_params": {"model": vrai, "api_key": "factice",
                               "mock_response": reponse}}


PANNE = "litellm.RateLimitError"


async def main() -> None:
    utf8()

    titre(1, "UNE CLE VIRTUELLE N'EST PAS UN ALIAS DE VOTRE CLE")
    registre = Registre()
    data = registre.generer("data", budget_max=1.00, rpm=60)
    rh = registre.generer("rh", budget_max=0.02, modeles=("rapide",))
    for cle in (data, rh):
        ligne(f"{cle.cle}  ({cle.equipe})",
              f"budget {cle.budget_max:>5.2f} $   "
              f"modeles : {', '.join(cle.modeles) or 'tous'}", 24)
    print()
    print("   Revoquer « rh » ne touche ni « data » ni la cle Anthropic de")
    print("   l'entreprise. C'est une IDENTITE, pas un alias : elle porte un")
    print("   budget, une liste de modeles, un debit — et elle se jette.")

    titre(2, "LE BUDGET SE VERIFIE AVANT, S'IMPUTE APRES")
    print("   Entre les deux, le cout n'est pas encore connu.\n")
    petite = registre.generer("essai", budget_max=0.0005)
    print(f"   Avant le premier appel, avec un plafond de "
          f"{petite.budget_max:.5f} $ et")
    print(f"   un appel le plus cher a 0,05 $, le depassement possible est de")
    print(f"   {depassement_possible(petite, 0.05):.2f} $ — soit "
          f"{0.05 / petite.budget_max:.0f}× le plafond.\n")
    for tour in range(1, 4):
        try:
            registre.autoriser(petite.cle, "claude")
            registre.imputer(petite.cle, 0.00033)
            ligne(f"appel {tour}", f"passe — depense {petite.depense:.5f} $ "
                                   f"sur {petite.budget_max:.5f} $", 12)
        except BudgetDepasse as erreur:
            ligne(f"appel {tour}", f"REFUSE — {erreur}", 12)
    print()
    depasse = petite.depense - petite.budget_max
    print(f"   Depassement constate : {depasse:+.5f} $ sur un plafond de "
          f"{petite.budget_max:.5f} $")
    print(f"   — parce que le deuxieme appel a ete AUTORISE (la depense etait")
    print("   encore sous le plafond) puis impute a son cout reel.")
    print()
    print("   Refuser sur une ESTIMATION ramenerait ce depassement a zero, et")
    print("   refuserait des appels legitimes a chaque fois que l'estimation")
    print("   est haute. Le choix de LiteLLM est de laisser passer le dernier")
    print("   appel : il faut donc un plafond, et une marge.")

    titre(3, "LA BASCULE, MESUREE")
    print("   « claude » tombe. Combien de temps avant que « rapide » reponde,")
    print("   selon num_retries ?\n")
    mesures = []
    for reessais in (0, 1, 2):
        proxy = Proxy({
            "model_list": [modele("claude", "anthropic/claude-sonnet-4-5", PANNE),
                           modele("rapide", "openai/gpt-4o-mini", "reponse")],
            "litellm_settings": {"fallbacks": [{"claude": ["rapide"]}],
                                 "num_retries": reessais}})
        debut = time.perf_counter()
        appel = await proxy.appeler("claude", "bonjour")
        duree = (time.perf_counter() - debut) * 1000
        mesures.append((reessais, duree, appel))
        ligne(f"num_retries = {reessais}",
              f"{duree:>7.0f} ms   a repondu : {appel.modele_reel}   "
              f"bascule : {appel.bascule}", 20)
    base = mesures[0][1]
    print(f"\n   Deux reessais coutent {mesures[-1][1] / base:.0f}× le temps de")
    print("   la bascule seule. Ils servent quand la panne est BREVE — un 429")
    print("   qui passe. Ils nuisent quand elle dure : on paie l'attente, puis")
    print("   on bascule quand meme. Le config.yaml de ce projet est donc a")
    print("   num_retries: 0, et c'est un choix a assumer par fournisseur.")

    titre(4, "L'APPLICATION NE VOIT QU'UNE REPONSE REUSSIE")
    _, _, appel = mesures[0]
    ligne("ce que l'application a demande", appel.alias, 32)
    ligne("ce qui a repondu", appel.modele_reel, 32)
    ligne("ce qu'elle recoit", "200, une reponse au format OpenAI", 32)
    print()
    print("   C'est exactement le but d'une bascule — et exactement pourquoi")
    print("   il faut la journaliser. Sans la colonne « bascule », un")
    print("   fournisseur peut etre en panne une semaine sans que personne ne")
    print("   le sache : les couts changent, les reponses changent, et le")
    print("   taux d'erreur reste a zero.")

    titre(5, "LE MEME ALIAS DEUX FOIS N'ECRASE RIEN")
    deux = Proxy({"model_list": [
        modele("rapide", "openai/gpt-4o", "depuis gpt-4o"),
        modele("rapide", "openai/gpt-4o-mini", "depuis gpt-4o-mini")]})
    vus: dict[str, int] = {}
    cout = 0.0
    for _ in range(10):
        appel = await deux.appeler("rapide", "bonjour")
        vus[appel.modele_reel] = vus.get(appel.modele_reel, 0) + 1
        cout += appel.cout
    for nom, combien in sorted(vus.items()):
        ligne(nom, f"{combien} appels sur 10", 20)
    print(f"\n   cout des 10 appels : {cout:.6f} $")
    print()
    print("   On croit remplacer la premiere entree ; LiteLLM y voit deux")
    print("   DEPLOIEMENTS du meme alias et repartit la charge entre eux")
    print("   (simple-shuffle par defaut). La moitie des requetes part donc")
    print("   vers l'autre modele, avec l'autre prix et l'autre qualite — et")
    print("   rien ne le signale. outils/verifier_config.py l'attrape.")

    titre(6, "LE TRAJET COMPLET, AVEC SES REFUS")
    passerelle = monter()
    for equipe, alias in (("data", "claude"), ("rh", "claude"),
                          ("rh", "rapide"), ("finance", "claude")):
        jwt = signer(f"{equipe}@exemple.fr", equipe, SECRET_JWT)
        try:
            appel = await passerelle.traiter(jwt, alias, "Trois offres ?")
            ligne(f"{equipe} → {alias}",
                  f"200  {appel.cout:.6f} $  ({appel.modele_reel})", 22)
        except Refuse as refus:
            ligne(f"{equipe} → {alias}", f"{refus.code}  {refus}", 22)
    print()
    print("   « finance » recoit 403 et non 401 : l'utilisateur est bien")
    print("   authentifie, c'est son equipe qui n'a pas de cle. Renvoyer 401")
    print("   l'enverrait se reconnecter en boucle.")

    print("\n   Au chapitre suivant : ou un secret fuit si l'on saute une")
    print("   etape.\n")


if __name__ == "__main__":
    asyncio.run(main())
