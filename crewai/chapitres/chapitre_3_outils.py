"""Chapitre 3 — Les outils : ce que l'agent voit, et comment il les nomme.

    uv run python chapitres/chapitre_3_outils.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                                        # noqa: E402
from jobportal.donnees import rechercher_offres, salaire_du_marche   # noqa: E402
from jobportal.equipe import chercheur, economiste, equipe_outillee   # noqa: E402
from jobportal.modele import ModeleFactice                           # noqa: E402


def main() -> None:
    console.utf8()

    print("1. UN OUTIL EST UNE FONCTION DECOREE\n")
    for outil in (rechercher_offres, salaire_du_marche):
        print(f"   name        {outil.name}")
        print(f"   description {outil.description[:72]}")
        print(f"   arguments   {list(outil.args_schema.model_fields)}\n")
    print("   Le libelle passe a @tool et la DOCSTRING sont les deux seuls")
    print("   elements qui remontent au modele. Le nom de la fonction Python,")
    print("   lui, ne sort jamais.")

    print("\n2. LE NOM QUE L'AGENT DOIT EMETTRE EST UN TROISIEME NOM\n")
    m = ModeleFactice()
    equipe_outillee(m).kickoff(inputs={"sujet": "DevOps"})
    print(f"   libelle @tool   « {rechercher_offres.name} »")
    print(f"   fonction Python   rechercher_offres")
    print(f"   nom emis          {m.appels[0] if m.appels else '—'}")
    print("\n   CrewAI derive un identifiant du libelle. Emettre le libelle")
    print("   ou le nom Python fait echouer l'action — et l'erreur revient au")
    print("   modele comme une observation ordinaire, donc sans rien")
    print("   interrompre. La reponse finale cite alors le message d'erreur,")
    print("   ce qui a tout l'air d'un resultat.")

    print("\n3. L'AGENT SE SERT-IL DU RETOUR ?\n")
    m = ModeleFactice()
    resultat = equipe_outillee(m).kickoff(inputs={"sujet": "DevOps"})
    reelles = json.loads(rechercher_offres.run(mot_cle="DevOps"))
    citee = any(o.split(" — ")[0] in str(resultat) for o in reelles)
    print(f"   outil appele : {m.appels}")
    print(f"   cite une offre reelle de la base : {'oui' if citee else 'non'}")
    print(f"   {str(resultat)[:100]}")

    print("\n4. LES OUTILS SE DONNENT PAR AGENT, PAS PAR EQUIPAGE\n")
    for agent in (chercheur(m, outils=True), economiste(m)):
        print(f"   {agent.role:<36}{[o.name for o in agent.tools]}")
    print("\n   C'est le moindre privilege applique aux agents : l'economiste")
    print("   n'a pas besoin de la recherche d'offres, et ne l'a pas. Donner")
    print("   vingt outils a tout le monde dilue le choix du modele autant")
    print("   que ca elargit la surface.")

    print("\n5. crewai_tools EST UN AUTRE PAQUET\n")
    try:
        import crewai_tools       # noqa: F401
        print("   installe.")
    except ModuleNotFoundError:
        print("   from crewai_tools import SerperDevTool   → ModuleNotFoundError")
        print("\n   Le chapitre 3 l'importe sans le dire : « crewai » ne le tire")
        print("   pas. Et SerperDevTool demande en plus une cle d'API — deux")
        print("   obstacles pour une ligne d'import.")


if __name__ == "__main__":
    main()
