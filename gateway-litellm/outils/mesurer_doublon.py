#!/usr/bin/env python3
"""Combien de fois un appel est-il journalise ? — dans un processus NEUF.

    uv run python outils/mesurer_doublon.py

POURQUOI UN PROCESSUS A PART

Ce qu'on mesure ici est de l'etat GLOBAL de litellm : la liste de rappels
qu'il derive de `litellm.callbacks`. Un processus qui a deja branche une
sonde — ce que fait le chapitre 6 des sa premiere section — n'est plus dans
l'etat ou la question se pose. La mesure serait alors fausse dans un sens
comme dans l'autre.

C'est pourquoi le chapitre 6 appelle ce script au lieu de faire la mesure
lui-meme : la seule facon honnete de mesurer un etat global est de partir
d'un etat propre.

La sortie est du JSON, pour que le chapitre n'ait rien a reanalyser.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

MODELE = [{"model_name": "rapide",
           "litellm_params": {"model": "openai/gpt-4o-mini",
                              "api_key": "factice", "mock_response": "ok"}}]


async def mesurer() -> dict:
    import litellm
    from litellm import Router

    from jobportal.observabilite import Sonde, brancher, sondes_branchees

    litellm.suppress_debug_info = True
    routeur = Router(model_list=MODELE)

    async def un_appel():
        await routeur.acompletion(model="rapide",
                                  messages=[{"role": "user", "content": "x"}])
        await asyncio.sleep(0.3)

    # 1. Le geste naturel : on reassigne la liste.
    premiere = Sonde()
    litellm.callbacks = [premiere]
    await un_appel()

    # 2. On croit remplacer la premiere.
    seconde = Sonde()
    litellm.callbacks = [seconde]
    await un_appel()

    naif = {"sondes_appelees": sondes_branchees(),
            "premiere_mesures": len(premiere.mesures),
            "premiere_cout": round(premiere.cout_total, 6),
            "seconde_mesures": len(seconde.mesures),
            "cout_reel_des_2_appels": round(seconde.cout_total
                                            + premiere.cout_total / 2, 6)}

    # 3. Le meme geste, avec brancher() qui purge les listes derivees.
    troisieme = brancher(Sonde())
    await un_appel()
    propre = {"sondes_appelees": sondes_branchees(),
              "mesures": len(troisieme.mesures),
              "cout": round(troisieme.cout_total, 6)}

    return {"naif": naif, "propre": propre}


if __name__ == "__main__":
    print(json.dumps(asyncio.run(mesurer()), indent=2))
