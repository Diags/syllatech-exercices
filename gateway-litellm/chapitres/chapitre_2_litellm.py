"""Chapitre 2 — LiteLLM : un proxy, 100+ modèles.

    uv run python chapitres/chapitre_2_litellm.py

Tout ce qui suit passe par le vrai `litellm.Router`, monté depuis le vrai
`config/passerelle.yaml`. Ce qui est substitué est le seul champ
`mock_response` — un champ **de litellm** : le proxy fait tout son travail,
compte les jetons, calcule le coût, et rend la réponse annoncée au lieu
d'appeler le réseau.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal.commun import config, ligne, titre, utf8    # noqa: E402
from jobportal.proxy import Proxy, charger                 # noqa: E402


async def main() -> None:
    utf8()
    proxy = Proxy.depuis(config())

    titre(1, "UN SEUL FORMAT, TROIS FOURNISSEURS")
    print("   L'application envoie toujours la meme chose : le format")
    print("   /v1/chat/completions d'OpenAI. LiteLLM le traduit vers l'API")
    print("   native de chacun — Messages chez Anthropic, l'API Gemini chez")
    print("   Google, l'API d'Ollama en local.\n")
    for alias in proxy.alias:
        appel = await proxy.appeler(alias, "Trois offres pour un profil Java ?")
        ligne(f"model=\"{alias}\"",
              f"{appel.modele_reel:<26}{appel.jetons:>3} jetons  "
              f"{appel.cout:.6f} $", 18)
    print()
    print("   Trois fournisseurs, un seul appel cote application. Les couts")
    print("   different parce que les tarifs different — et c'est litellm qui")
    print("   les connait, pas ce projet.")

    titre(2, "L'ALIAS DECOUPLE LE CODE DU FOURNISSEUR")
    declaration = charger(config())
    print(f"   {'ce que l application ecrit':<32}ce qui repond")
    for entree in declaration["model_list"]:
        ligne(f"model=\"{entree['model_name']}\"",
              entree["litellm_params"]["model"], 32)
    print()
    print("   Remplacer « anthropic/claude-sonnet-4-5 » par « ollama/llama3 »")
    print("   dans le YAML change le fournisseur pour toutes les applications")
    print("   sans qu'aucune ne soit redeployee. C'est la raison d'etre de la")
    print("   colonne de gauche : elle est un CONTRAT, pas un nom de modele.")

    titre(3, "LE COUT VIENT DE LA TABLE DE litellm")
    from litellm import model_cost

    def tarif(modele: str):
        """La cle de la table n'est pas toujours celle du YAML.

        « claude-sonnet-4-5 » y est, « anthropic/claude-sonnet-4-5 » non ;
        « ollama/llama3 » y est, « llama3 » non. Chercher d'un seul cote
        declare absents des modeles qui ont un prix — ou l'inverse.
        """
        return model_cost.get(modele) or model_cost.get(modele.split("/")[-1])

    print(f"   {'modele du config.yaml':<32}{'cle trouvee':<22}tarif")
    for modele in ("anthropic/claude-sonnet-4-5", "openai/gpt-4o-mini",
                   "ollama/llama3", "openai/modele-maison-v3"):
        infos = tarif(modele)
        trouvee = ("(aucune)" if infos is None else
                   modele if modele in model_cost else modele.split("/")[-1])
        if infos is None:
            etat = "ABSENT → facture 0,00 $ en silence"
        else:
            e = (infos.get("input_cost_per_token") or 0) * 1_000_000
            s = (infos.get("output_cost_per_token") or 0) * 1_000_000
            etat = (f"{e:>6.2f} / {s:>6.2f} $ par M jetons"
                    if e or s else "0,00 $ — et c'est EXACT (modele local)")
        print(f"   {modele:<32}{trouvee:<22}{etat}")
    print()
    print("   Deux facons tres differentes de couter zero :")
    print()
    print("   · « ollama/llama3 » est DANS la table, a 0,00 $. Un modele qui")
    print("     tourne chez vous ne coute effectivement rien au jeton.")
    print("   · « openai/modele-maison-v3 » n'y est PAS. litellm ne leve rien")
    print("     pour un modele qu'il ne connait pas : il le facture zero.")
    print()
    print("   Le tableau de bord est alors juste pour tous les autres et faux")
    print("   pour celui-la, sans qu'aucune ligne ne l'indique. C'est ainsi")
    print("   qu'un cout disparait d'un budget — et « model_info » dans le")
    print("   config.yaml est la facon de le declarer.")

    titre(4, "LES CLES NE SONT JAMAIS DANS LE YAML")
    for entree in declaration["model_list"]:
        params = entree["litellm_params"]
        valeur = params.get("api_key")
        ligne(entree["model_name"],
              "aucune cle (modele local, api_base)" if valeur is None
              else f"{valeur}  → lue au demarrage", 12)
    print()
    print("   « os.environ/NOM » est resolu par le proxy au demarrage. La")
    print("   valeur n'est donc ni dans git, ni dans l'image du conteneur, et")
    print("   sa rotation ne demande aucun redeploiement.")
    print()
    print("   Et « api_base » ouvre la porte a l'auto-heberge : le meme proxy")
    print("   sert le cloud et l'on-premise, avec le meme contrat.")
    for entree in declaration["model_list"]:
        base = entree["litellm_params"].get("api_base")
        if base:
            ligne(f"   {entree['model_name']}", f"api_base: {base}", 15)

    titre(5, "CE QUE L'APPLICATION NE VOIT PAS")
    appel = await proxy.appeler("claude", "Bonjour")
    for quoi, valeur in (("le fournisseur reel", appel.modele_reel),
                         ("le cout de l'appel", f"{appel.cout:.6f} $"),
                         ("les jetons", appel.jetons),
                         ("la latence", f"{appel.latence_ms:.0f} ms"),
                         ("une bascule eventuelle", appel.bascule)):
        ligne(quoi, str(valeur), 26)
    print()
    print("   Elle recoit une reponse au format OpenAI, et rien d'autre. Tout")
    print("   ce tableau existe cote proxy : c'est ce qui rend la passerelle")
    print("   utile, et c'est aussi ce qu'il faut journaliser — sans quoi il")
    print("   n'existe nulle part.")

    print("\n   Au chapitre suivant : qui a le droit d'appeler.\n")


if __name__ == "__main__":
    asyncio.run(main())
