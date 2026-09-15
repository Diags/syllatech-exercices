"""Chapitre 6 — Production : observabilité et sécurité.

    uv run python chapitres/chapitre_6_production.py

Les cinq chapitres précédents ont pris les briques une par une. Celui-ci
regarde ce qui reste quand tout est branché : ce que les journaux contiennent,
ce qui sort du système sans qu'on l'ait voulu, et ce qu'un vérificateur peut
attraper avant le déploiement.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import agent, agent_a_corriger                   # noqa: E402
from jobportal.commun import ligne, silence, titre, utf8        # noqa: E402
from jobportal.contrat import appeler                           # noqa: E402
from outils.verifier_agent import verifier                      # noqa: E402


def journal_de(app, charge, session=None):
    """Capture ce que le SDK journalise pour UN appel — TEL QU'IL L'ECRIT.

    ⚠️ Un handler de capture ordinaire ne suffit pas : `requestId` et
    `sessionId` ne sont pas des attributs de l'enregistrement, c'est le
    `RequestContextFormatter` du SDK qui les ajoute au moment de formater.
    Une capture posee AVANT le formatage rend donc des lignes sans session —
    et l'on conclurait a tort que le SDK ne les trace pas.

    On reutilise donc SON formateur, sur un flux a nous. Ce qui suit est
    exactement ce que CloudWatch recevrait.
    """
    import io
    import logging

    logger = logging.getLogger("bedrock_agentcore.app")
    formateur = next((h.formatter for h in logger.handlers if h.formatter), None)

    tampon = io.StringIO()
    piege = logging.StreamHandler(tampon)
    piege.setFormatter(formateur)
    logger.addHandler(piege)
    origine, logger.handlers = logger.handlers, [piege]
    try:
        reponse = appeler(app, charge, session=session)
    finally:
        logger.handlers = origine

    lignes = []
    for brute in tampon.getvalue().splitlines():
        try:
            lignes.append(json.loads(brute))
        except json.JSONDecodeError:
            lignes.append({"message": brute})
    return lignes, reponse


def main() -> None:
    utf8()

    titre(1, "CE QUE LE SDK JOURNALISE, SANS RIEN CONFIGURER")
    lignes, reponse = journal_de(agent.app, {"prompt": "DevOps a Lyon"},
                                 session="s-77")
    for entree in lignes:
        for cle in ("level", "message", "requestId", "sessionId"):
            if entree.get(cle):
                print(f"   {cle:<12} {entree[cle]}")
    print()
    print("   Un identifiant de requete, une duree, un identifiant de")
    print("   session — en JSON, sur la sortie standard. C'est ce que")
    print("   CloudWatch ingere, et c'est deja une trace exploitable sans")
    print("   qu'on ait rien instrumente.")
    print()
    print("   « Aucun changement de code » du cours est donc exact pour les")
    print("   traces d'invocation. Ce qui n'y est PAS : vos etapes metier,")
    print("   les outils appeles, les jetons consommes. Cela, il faut le")
    print("   journaliser soi-meme — ou brancher un traceur.")

    titre(2, "CE QUI SORT DU SYSTEME QUAND ON NE L'ATTRAPE PAS")
    print("   Le meme appel, sur l'agent a corriger : son entrypoint n'a")
    print("   aucun « try », et le champ « prompt » n'a pas de garde.\n")
    with silence():
        casse = appeler(agent_a_corriger.app, {})
    ligne("code", str(casse.code), 16)
    ligne("corps", casse.texte[:70], 16)
    print()
    with silence():
        sain = appeler(agent.app, {})
    ligne("l'agent corrige", f"{sain.code}  {sain.texte[:52]}", 16)
    print()
    print("   Le premier renvoie le message de son exception. Ici c'est une")
    print("   KeyError anodine ; sur une vraie panne, c'est le nom d'un hote")
    print("   interne, un chemin de fichier ou un morceau de requete SQL.")
    print("   Le second rend une phrase neutre, et met le detail au journal.")

    titre(3, "L'ISOLATION PAR SESSION, VUE DES JOURNAUX")
    for session in ("s-alice", "s-bob"):
        lignes, _ = journal_de(agent.app, {"prompt": "offres"}, session=session)
        trace = next((e for e in lignes
                      if "completed" in e.get("message", "")), None)
        ligne(session, f"sessionId = {trace.get('sessionId')!r}   "
                       f"requestId = {str(trace.get('requestId'))[:8]}…"
              if trace else "(rien)", 12)
    print()
    print("   Deux sessions, deux traces separees. C'est ce qui permet de")
    print("   repondre a « qu'a fait cet utilisateur ? » sans lire le journal")
    print("   entier — et c'est pourquoi l'entrypoint doit prendre `context` :")
    print("   sans lui, les deux lignes seraient indiscernables.")

    titre(4, "LE VERIFICATEUR, SUR LES DEUX AGENTS")
    for nom, module in (("jobportal.agent", agent),
                        ("jobportal.agent_a_corriger", agent_a_corriger)):
        soucis = verifier(module.app, module)
        erreurs = sum(1 for s in soucis if s.gravite == "erreur")
        ligne(nom, f"{erreurs} erreur(s), "
                   f"{len(soucis) - erreurs} avertissement(s)", 32)
    print()
    for souci in verifier(agent_a_corriger.app, agent_a_corriger):
        marque = "ERREUR   " if souci.gravite == "erreur" else "attention"
        print(f"   {marque} {souci.ou}")
    print()
    print("   Les cinq defauts de agent_a_corriger.py se deploient sans un")
    print("   mot : « agentcore configure && agentcore launch » reussit,")
    print("   l'endpoint repond 200, et les tests d'integration passent.")

    titre(5, "LE DEFAUT QUE LE VERIFICATEUR A FAILLI MANQUER")
    print("   La premiere version du test « l'entrypoint attrape-t-il ses")
    print("   exceptions ? » etait :\n")
    print('      if "try" not in inspect.getsource(fonction): …\n')
    print("   Elle ne s'est JAMAIS declenchee. `getsource` inclut la ligne du")
    print("   decorateur, et « @app.en-TRY-point » contient la sous-chaine.")
    print("   Le test passait sur tous les agents, y compris ceux sans aucun")
    print("   bloc try.")
    print()
    print("   Un test qui passe toujours vaut exactement un test absent, et")
    print("   il est plus difficile a voir. La version actuelle lit l'arbre")
    print("   syntaxique, ou un « try » est un nœud et pas trois lettres.")

    titre(6, "LES QUATRE CLOISONS, ET CE QU'ELLES SEPARENT")
    for cloison, separe, defaut in (
            ("session (Runtime)", "deux conversations",
             "un en-tete absent en local"),
            ("sandbox (Code Interpreter)", "le code genere et votre machine",
             "aucun — elle est jetable par construction"),
            ("acteur (Memory)", "deux utilisateurs",
             "un actor_id oublie melange tout"),
            ("jeton (Identity)", "deux delegations",
             "un compte de service partage n'en separe aucune")):
        print(f"   {cloison}")
        print(f"      separe   {separe}")
        print(f"      defaut   {defaut}")
    print()
    print("   Les quatre repondent a la meme question posee a des echelles")
    print("   differentes : qu'est-ce qui ne doit PAS se melanger ? La")
    print("   reponse d'AgentCore est la meme a chaque fois — un identifiant,")
    print("   et un environnement par identifiant.")

    titre(7, "CE QUE CE PROJET NE PROUVE PAS")
    for limite in (
            "aucun appel AWS n'est fait. Le Runtime est reel et exercable",
            "  ici ; les sandboxes, la Gateway et Memory sont des doubles",
            "  locaux qui gardent la forme de l'API ;",
            "l'isolation d'AgentCore n'est pas mesuree — un dictionnaire",
            "  Python separe des variables, pas des privileges ;",
            "la recherche semantique de la Gateway utilise des plongements",
            "  vectoriels ; celle d'ici compte les mots partages ;",
            "l'extraction de Memory utilise un modele ; celle d'ici, des",
            "  expressions regulieres."):
        print(f"   · {limite}" if not limite.startswith("  ") else f"   {limite}")
    print()
    print("   Ce qui EST prouve tient en une ligne : le contrat du Runtime,")
    print("   et les sept comportements du chapitre 1 — tous mesures sur le")
    print("   vrai BedrockAgentCoreApp, sans compte AWS.")

    print("\n   uv run python outils/verifier_agent.py <votre.module>\n")


if __name__ == "__main__":
    main()
