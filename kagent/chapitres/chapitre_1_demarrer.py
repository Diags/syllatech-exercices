"""Chapitre 1 — Demarrer avec kagent.

    uv run python chapitres/chapitre_1_demarrer.py

Un agent est un objet declaratif reconcilie par un controleur. Ce chapitre
applique de vrais manifestes, montre que `kubectl apply` ne demarre rien, et
mesure ce qui arrive quand une reference manque.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                                   # noqa: E402
from jobportal import cluster as grappe                         # noqa: E402
from jobportal import controleur, moteur, yaml_minimal          # noqa: E402

RACINE = Path(__file__).resolve().parent.parent
MANIFESTES = RACINE / "manifestes"


def poser(api: controleur.Api, *fichiers: str) -> list:
    """`kubectl apply -f` sur un ou plusieurs fichiers."""
    verdicts = []
    for nom in fichiers:
        for document in yaml_minimal.charger_fichier_tous(MANIFESTES / nom):
            verdicts.append((nom, document, api.appliquer(document)))
    return verdicts


def main() -> None:
    console.utf8()
    _un_objet_declaratif()
    _les_quatre_composants()
    _lordre_na_pas_dimportance()
    _la_reference_manquante()


def _un_objet_declaratif() -> None:
    print("1. `kubectl apply` NE DEMARRE RIEN\n")
    api = controleur.Api()
    for nom, document, verdict in poser(api, "plateforme.yaml",
                                        "agent-sre.yaml"):
        genre = document.get("kind")
        objet = (document.get("metadata") or {}).get("name")
        print(f"   {nom:<20} {genre:<18} {objet:<18} → {verdict}")

    agent = api.lire("Agent", "assistant-sre")
    print(f"\n   Objets stockes dans l'API : {len(api.objets)}")
    print(f"   Conditions de l'agent     : {agent.conditions or 'aucune'}")
    print("\n   L'objet existe, et il n'a aucun statut. `apply` a valide un")
    print("   manifeste et l'a ECRIT — c'est tout ce qu'il fait. Ce qui")
    print("   suit est le travail du controleur.\n")

    controle = controleur.Controleur(api)
    controle.reconcilier()
    print("   Apres un passage du controleur :\n")
    for ligne in controleur.rendre_statut(api.lister("Agent")):
        print(f"      {ligne}")
    print("\n   Deux conditions, et elles ne disent pas la meme chose :")
    print("      Accepted   le manifeste est coherent avec ce qui existe")
    print("      Ready      l'agent est reellement invocable")
    print("\n   ⚠️ C'est exactement le modele d'un `Deployment` : on decrit")
    print("   un etat voulu, un controleur boucle, et le STATUT dit ou en")
    print("   est la convergence. Tout ce que vous savez de Kubernetes")
    print("   s'applique — GitOps, RBAC, `Secret`, sondes, quotas — sans")
    print("   qu'une plateforme a part ait ete inventee.")


def _les_quatre_composants() -> None:
    print("\n\n2. QUATRE COMPOSANTS, QUATRE ROLES\n")
    composants = [
        ("controller", "observe les `Agent` et les reconcilie",
         "jobportal/controleur.py"),
        ("engine", "execute la conversation et les appels d'outils",
         "jobportal/moteur.py"),
        ("tool server", "expose les outils cloud-native",
         "jobportal/outils.py"),
        ("CLI / dashboard", "cree, invoque, inspecte", "les chapitres"),
    ]
    print(f"   {'COMPOSANT':<18} {'ROLE':<46} DANS CE PROJET")
    for nom, role, ou in composants:
        print(f"   {nom:<18} {role:<46} {ou}")
    print("\n   Le decoupage compte : le controleur ne parle jamais au")
    print("   modele, et le moteur ne connait pas Kubernetes. C'est ce qui")
    print("   permet de redemarrer l'un sans l'autre, et de les mettre a")
    print("   l'echelle separement.")
    print("\n   ⚠️ Et cela explique une confusion frequente : un agent")
    print("   `Ready` n'a encore RIEN execute. `Ready` dit que le")
    print("   controleur a resolu ses references — pas que le modele")
    print("   repond, ni que la cle d'API est valide. Ces deux-la ne se")
    print("   decouvrent qu'a la premiere invocation.")


def _lordre_na_pas_dimportance() -> None:
    print("\n\n3. L'ORDRE D'APPLICATION N'A PAS D'IMPORTANCE\n")
    api = controleur.Api()
    controle = controleur.Controleur(api)

    print("   On applique l'AGENT en premier, son modele n'existe pas encore :\n")
    poser(api, "agent-sre.yaml")
    controle.reconcilier()
    for ligne in controleur.rendre_statut(api.lister("Agent")):
        print(f"      {ligne}")

    print("\n   Puis le `ModelConfig` arrive :\n")
    poser(api, "plateforme.yaml")
    controle.reconcilier()
    for ligne in controleur.rendre_statut(api.lister("Agent")):
        print(f"      {ligne}")

    print(f"\n   Passages du controleur : {controle.passages}")
    print("\n   Aucune commande n'a ete rejouee, aucun ordre n'a ete impose.")
    print("   Le controleur a simplement reconstate. C'est toute la")
    print("   difference entre declaratif et imperatif — et c'est ce qui")
    print("   rend le GitOps possible : un dossier de manifestes s'applique")
    print("   dans n'importe quel ordre, autant de fois qu'on veut.")


def _la_reference_manquante() -> None:
    print("\n\n4. LA MESURE : UNE REFERENCE MANQUANTE NE FAIT PAS ECHOUER\n")
    api = controleur.Api()
    controle = controleur.Controleur(api)
    poser(api, "plateforme.yaml", "agent-sre.yaml", "agent-sans-modele.yaml")
    controle.reconcilier()

    print("   Ce que `kubectl apply` a repondu :\n")
    for evenement in api.evenements:
        print(f"      {evenement}")

    print("\n   Ce que `kubectl get agents` montre :\n")
    for ligne in controleur.rendre_statut(api.lister("Agent")):
        print(f"      {ligne}")

    orphelin = api.lire("Agent", "assistant-orphelin")
    print("\n   Et le detail, dans `status.conditions` :\n")
    for condition in orphelin.conditions:
        print(f"      {condition}")
        if condition.message:
            print(f"         {condition.message}")

    print("\n   ⚠️ L'agent a ete CREE. `apply` a repondu « configure ». Il")
    print("   n'est pas invocable, et rien ne vous l'a dit.")
    print("\n   Ce n'est pas un defaut : l'admission ne peut pas verifier")
    print("   une reference, puisqu'en declaratif l'objet reference peut")
    print("   arriver APRES — la section 3 vient de le montrer. Le prix de")
    print("   cette liberte est que l'erreur se lit dans le statut, jamais")
    print("   dans la sortie de la commande.")
    print("\n   D'ou le reflexe, et il est le meme que pour un Service sans")
    print("   endpoints : devant un agent qui ne repond pas, on regarde")
    print("   `kubectl get agent <nom> -o yaml` AVANT les journaux.")

    print("\n   Preuve que l'agent existe et n'est pas utilisable :\n")
    m = moteur.Moteur(api, grappe.avec_incident())
    session = m.invoquer("assistant-orphelin", "Diagnostique l'incident")
    print(f"      invocation → {len(session.outils_appeles)} outil(s), "
          f"reponse de memoire :")
    print(f"      « {session.reponse[:72]}… »")
    print("\n   Le moteur l'execute quand meme, sans outils et sans prompt")
    print("   utile. En production, le controleur refuserait de router vers")
    print("   un agent qui n'est pas `Ready` — et c'est precisement ce que")
    print("   sert a decider une condition.")
    print()


if __name__ == "__main__":
    main()
