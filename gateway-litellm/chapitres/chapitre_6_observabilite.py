"""Chapitre 6 — Observabilité et production.

    uv run python chapitres/chapitre_6_observabilite.py

`success_callback: ["prometheus", "langfuse"]` instancie un `CustomLogger` de
litellm. Ce chapitre en branche un vrai, sans serveur, et montre ce que
Prometheus et Langfuse reçoivent — puis les deux façons de ne rien recevoir.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal.commun import (RACINE, SECRET_JWT, config, ligne,
                              monter, titre, utf8)  # noqa: E402
from jobportal.jetons import signer                                          # noqa: E402
from jobportal.observabilite import (Sonde, TableauDeBord, brancher,
                                     sondes_branchees)           # noqa: E402
from jobportal.passerelle import Refuse                                      # noqa: E402
from jobportal.proxy import Proxy                                            # noqa: E402
from outils.verifier_config import verifier                                  # noqa: E402
from jobportal.proxy import charger                                          # noqa: E402

TRAFIC = [("data", "claude"), ("data", "claude"), ("data", "rapide"),
          ("rh", "rapide"), ("rh", "rapide"), ("rh", "claude"),
          ("data", "local"), ("finance", "claude")]


async def main() -> None:
    utf8()

    titre(1, "CE QUE LE RAPPEL REÇOIT")
    sonde = brancher(Sonde())
    passerelle = monter()
    for equipe, alias in TRAFIC:
        jwt = signer(f"{equipe}@exemple.fr", equipe, SECRET_JWT)
        try:
            await passerelle.traiter(jwt, alias, "Trois offres ?")
        except Refuse:
            pass
    await asyncio.sleep(0.3)          # les rappels sont asynchrones

    print(f"   {len(TRAFIC)} requetes envoyees, "
          f"{len(sonde.mesures)} mesures recues.\n")
    print(f"   {'modele':<22}{'appels':>7}{'jetons':>8}{'cout':>12}")
    for modele, ligne_ in sorted(sonde.par_modele().items()):
        print(f"   {modele:<22}{ligne_['appels']:>7}{ligne_['jetons']:>8}"
              f"{ligne_['cout']:>12.6f}")
    print(f"   {'':<22}{'':>7}{'':>8}{sonde.cout_total:>12.6f}  $")
    print()
    print("   Huit requetes, moins de mesures : les refus ne sont pas des")
    print("   appels reussis, donc le rappel ne les voit jamais. Un tableau")
    print("   de bord bati sur le seul success_callback affiche donc un taux")
    print("   d'erreur de zero, quoi qu'il arrive.")

    titre(2, "CE QUE litellm NE SAIT PAS : L'EQUIPE")
    tableau = TableauDeBord(journal=passerelle.journal)
    print(f"   {'equipe':<12}{'appels':>7}{'refus':>7}{'bascules':>10}"
          f"{'cout':>12}{'latence moy.':>14}")
    for equipe, l in sorted(tableau.par_equipe().items()):
        print(f"   {equipe:<12}{l['appels']:>7}{l['refus']:>7}"
              f"{l['bascules']:>10}{l['cout']:>12.6f}"
              f"{l['latence_moyenne_ms']:>12.0f} ms")
    print()
    print("   litellm ne connait que des MODELES. L'equipe est une notion de")
    print("   la passerelle, portee par la cle virtuelle. Recoller les deux")
    print("   est tout le travail du proxy reel avec sa base PostgreSQL — et")
    print("   c'est cette table-la qui permet de refacturer.")

    titre(3, "CHANGER DE SONDE NE CHANGE PAS DE SONDE")
    print("   « litellm.callbacks » est de l'etat GLOBAL, et litellm en derive")
    print("   une liste interne qu'il ne reconstruit pas. Mesurer cela depuis")
    print("   ce chapitre serait faux : la section 1 a deja branche une sonde.")
    print("   outils/mesurer_doublon.py le fait donc dans un processus NEUF.\n")
    mesure = json.loads(subprocess.run(
        [sys.executable, str(RACINE / "outils" / "mesurer_doublon.py")],
        capture_output=True, text=True, check=True).stdout)

    naif, propre = mesure["naif"], mesure["propre"]
    print("   Deux appels, deux « litellm.callbacks = [nouvelle] » naifs :\n")
    ligne("sondes reellement appelees", str(naif["sondes_appelees"]), 32)
    ligne("la PREMIERE sonde", f"{naif['premiere_mesures']} mesures, "
                               f"{naif['premiere_cout']:.6f} $", 32)
    ligne("la SECONDE sonde", f"{naif['seconde_mesures']} mesure", 32)
    print()
    ligne("avec brancher(), qui purge",
          f"{propre['sondes_appelees']} sonde, {propre['mesures']} mesure, "
          f"{propre['cout']:.6f} $", 32)
    print()
    print("   La seconde sonde ne recoit RIEN, et la premiere continue de")
    print("   tout recevoir. On remplace son exportateur, on deploie, le")
    print("   nouveau tableau de bord reste vide — et l'ancien, parfois un")
    print("   bouchon de test, tourne toujours. Les deux moities du probleme")
    print("   sont muettes.")
    print()
    print("   Selon le moment ou l'on reassigne, la nouvelle sonde est tantot")
    print("   AJOUTEE a l'ancienne — et tout est compte deux fois — tantot")
    print("   IGNOREE, comme ici. Le point commun est le seul qui compte :")
    print("   l'assignation seule n'est pas un remplacement. brancher() purge")
    print("   les listes derivees, et le resultat redevient previsible.")
    proxy = Proxy.depuis(config())

    titre(4, "LA PREMIERE FACON DE NE RIEN VOIR : LA SIGNATURE")
    print("   litellm appelle les quatre parametres PAR MOT-CLE :\n")
    print("      async def async_log_success_event(self, kwargs, response_obj,")
    print("                                        start_time, end_time)\n")
    print("   Une signature qui les nomme autrement leve un TypeError… que")
    print("   litellm rattrape et journalise en « [Non-Blocking] Exception")
    print("   occurred while success logging ».\n")

    class SondeCassee(Sonde):
        """Le seul defaut est le NOM des deux derniers parametres."""

        async def async_log_success_event(self, kwargs, response_obj,
                                          start, end):      # noms errones
            self.mesures.append(kwargs)

    # On passe par brancher() : la sonde est donc REELLEMENT enregistree, et
    # les zeros qui suivent ne peuvent venir que de la signature.
    cassee = brancher(SondeCassee())
    # Le TypeError part dans le journal de litellm a chaque appel. On le tait
    # ici pour garder le chapitre lisible — en production, personne ne le tait
    # et personne ne le lit : c'est la meme chose.
    import logging

    journal = logging.getLogger("LiteLLM")
    niveau = journal.level
    journal.setLevel(logging.CRITICAL)
    for _ in range(3):
        await proxy.appeler("rapide", "bonjour")
    await asyncio.sleep(0.3)
    journal.setLevel(niveau)
    ligne("sondes enregistrees", str(sondes_branchees()), 26)
    ligne("appels passes", "3", 26)
    ligne("mesures recues", str(len(cassee.mesures)), 26)
    ligne("code de retour des appels", "200, tous", 26)
    print()
    print("   L'application marche parfaitement. Le tableau de bord reste a")
    print("   zero. Rien ne relie les deux, sauf une ligne d'erreur noyee au")
    print("   demarrage — et c'est la panne la plus discrete du cours. Elle a")
    print("   ete rencontree en ecrivant ce projet.")

    titre(5, "LA SECONDE : UN MODELE SANS PRIX")
    sonde2 = brancher(Sonde())
    maison = Proxy({"model_list": [
        {"model_name": "maison",
         "litellm_params": {"model": "openai/modele-maison-v3",
                            "api_key": "factice", "mock_response": "ok"}},
        {"model_name": "rapide",
         "litellm_params": {"model": "openai/gpt-4o-mini",
                            "api_key": "factice", "mock_response": "ok"}}]})
    for alias in ("maison", "maison", "rapide"):
        await maison.appeler(alias, "bonjour")
    await asyncio.sleep(0.3)
    for modele, l in sorted(sonde2.par_modele().items()):
        ligne(modele, f"{l['appels']} appels, {l['jetons']} jetons, "
                      f"{l['cout']:.6f} $", 24)
    print(f"\n   Modeles factures 0,00 $ malgre des jetons : "
          f"{', '.join(sonde2.gratuits()) or 'aucun'}")
    print()
    print("   Le tableau de bord est juste pour « gpt-4o-mini » et faux pour")
    print("   « modele-maison-v3 », sans qu'aucune ligne ne l'indique. Une")
    print("   sonde qui compare les jetons au cout attrape le cas : des")
    print("   jetons consommes pour zero dollar est un signal, pas un cadeau.")

    titre(6, "CE QUE LE VERIFICATEUR DIT DES DEUX CONFIGURATIONS")
    for nom in ("passerelle", "a-corriger"):
        soucis = verifier(charger(config(nom)))
        erreurs = sum(1 for s in soucis if s.gravite == "erreur")
        ligne(f"config/{nom}.yaml",
              f"{erreurs} erreur(s), {len(soucis) - erreurs} avertissement(s)",
              26)
    print()
    print("   Les erreurs de la seconde demarrent toutes sans broncher :")
    print("   une cle en clair, un alias declare deux fois, une bascule vers")
    print("   un alias inexistant, un modele sans prix, une cle maitre en")
    print("   clair. Le proxy repond, les applications marchent.")

    titre(7, "LA PRODUCTION, EN QUATRE SERVICES")
    for service, role in (
            ("gateway", "JWT, debit, substitution de la cle"),
            ("litellm", "traduction, bascule, imputation"),
            ("postgres", "cles virtuelles, budgets, historique"),
            ("redis", "cache et compteurs de debit partages")):
        ligne(service, role, 12)
    print()
    print("   Sans Redis, deux repliques du proxy comptent chacune leur")
    print("   moitie du debit : la limite reelle est le double de celle")
    print("   annoncee. Sans Postgres, les budgets repartent de zero a chaque")
    print("   redemarrage. Ce ne sont pas des options de confort.")
    print()
    print("   Et « import litellm » prend une trentaine de secondes : reglez")
    print("   la sonde de vivacite en consequence.")

    print("\n   Fin du parcours. outils/verifier_config.py s'utilise sur")
    print("   votre propre config.yaml.\n")


if __name__ == "__main__":
    asyncio.run(main())
