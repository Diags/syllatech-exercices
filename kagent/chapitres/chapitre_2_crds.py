"""Chapitre 2 — Les CRDs en profondeur.

    uv run python chapitres/chapitre_2_crds.py

Une CRD n'ajoute pas seulement un genre d'objet : elle ajoute un schema que
l'API applique. Ce schema REFUSE ce qui le viole, et ELAGUE en silence ce
qu'il ne connait pas. La seconde moitie est celle qui coute.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                                   # noqa: E402
from jobportal import controleur, crd, schemas, yaml_minimal    # noqa: E402

RACINE = Path(__file__).resolve().parent.parent
MANIFESTES = RACINE / "manifestes"


def main() -> None:
    console.utf8()
    _trois_crds()
    _le_refus_bruyant()
    _lelagage_silencieux()
    _les_defauts()
    _agent_as_code()


def _trois_crds() -> None:
    print("1. TROIS CRDS, TROIS RESPONSABILITES\n")
    for genre, schema in schemas.PAR_GENRE.items():
        specification = schema["properties"]["spec"]
        champs = sorted(specification.get("properties", {}))
        exiges = specification.get("required", [])
        print(f"   {genre}")
        print(f"      champs      : {', '.join(champs)}")
        print(f"      obligatoires: {', '.join(exiges) or '—'}")
        regles = specification.get("x-kubernetes-validations") or []
        if regles:
            print(f"      regles      : {', '.join(regles)}")
        print()

    print("   Le decouplage n'est pas cosmetique. `ModelConfig` isole le")
    print("   fournisseur ET SES SECRETS : la CRD ne porte pas le jeton,")
    print("   elle NOMME un `Secret` Kubernetes.\n")
    api = controleur.Api()
    for document in yaml_minimal.charger_fichier_tous(
            MANIFESTES / "plateforme.yaml"):
        api.appliquer(document)
    modele = api.lire("ModelConfig", "claude-config")
    print(f"      spec du ModelConfig : {modele.spec}")
    print("\n   ⚠️ Cherchez le jeton : il n'y est pas. `apiKeySecret` nomme")
    print("   un objet `Secret`, gere par le RBAC du cluster et chiffre au")
    print("   repos. Le YAML qu'on versionne dans Git ne contient jamais")
    print("   rien de confidentiel — c'est ce decouplage qui rend l'agent")
    print("   « as code » possible.")
    print("\n   Consequence pratique : changer de fournisseur ou de modele")
    print("   se fait en editant un SEUL objet, sans toucher a aucun agent.")


def _le_refus_bruyant() -> None:
    print("\n\n2. CE QUE LE SCHEMA REFUSE — BRUYAMMENT\n")
    api = controleur.Api()
    for document in yaml_minimal.charger_fichier_tous(
            MANIFESTES / "agent-invalide.yaml"):
        verdict = api.appliquer(document)
        print(f"   `kubectl apply -f agent-invalide.yaml` →\n")
        for probleme in verdict.problemes:
            print(f"      error: {probleme}")
        print(f"\n   Objet cree : {'oui' if verdict.valide else 'NON'}")

    print("\n   Un second manifeste, bien type cette fois, et pourtant")
    print("   refuse — par une regle TRANSVERSE :\n")
    sans_corps = {
        "apiVersion": "kagent.dev/v1alpha2", "kind": "Agent",
        "metadata": {"name": "agent-sans-corps"},
        "spec": {"type": "Declarative"},
    }
    for probleme in crd.admettre(schemas.AGENT, sans_corps).problemes:
        print(f"      error: {probleme}")

    print("\n   Deux refus, deux mecanismes :")
    print("      • `type: Declaratif` n'est pas dans l'`enum` du champ —")
    print("        une contrainte LOCALE, portee par le champ lui-meme ;")
    print("      • « un agent Declarative doit porter un bloc declarative »")
    print("        ne peut se verifier qu'en regardant DEUX champs a la")
    print("        fois. C'est ce que Kubernetes ecrit en CEL dans")
    print("        `x-kubernetes-validations`, et c'est la seule facon")
    print("        d'exprimer une union discriminee dans un schema")
    print("        structurel — ou `oneOf` est interdit.")
    print("\n   Les deux s'appliquent a l'ADMISSION, donc avant le stockage.")
    print("   Rien n'est cree, la commande echoue, et le message nomme le")
    print("   champ fautif. C'est le bon comportement — et c'est ce qui")
    print("   rend la section suivante si deroutante.")


def _lelagage_silencieux() -> None:
    print("\n\n3. LA MESURE QUI TRANCHE : CE QUE LE SCHEMA ELAGUE\n")
    api = controleur.Api()
    for nom in ("plateforme.yaml", "agent-faute-de-frappe.yaml"):
        for document in yaml_minimal.charger_fichier_tous(MANIFESTES / nom):
            verdict = api.appliquer(document)
            if document.get("kind") == "Agent":
                envoye = document["spec"]["declarative"]
                print("   Ce que le fichier contient :\n")
                for cle in envoye:
                    print(f"      spec.declarative.{cle}")
                print(f"\n   Verdict de l'API : {verdict}")
                print(f"   Sortie de kubectl : "
                      f"« agent.kagent.dev/assistant-faute-de-frappe "
                      f"configured »\n")
                print("   Ce que l'API a STOCKE :\n")
                for cle, valeur in verdict.objet["spec"]["declarative"].items():
                    apercu = repr(valeur)
                    if len(apercu) > 46:
                        apercu = apercu[:43] + "...'"
                    print(f"      {cle:<16} = {apercu}")
                print("\n   Ce qu'elle a ELAGUE, sans le dire :\n")
                for chemin in verdict.elagues:
                    print(f"      {chemin}")

    controle = controleur.Controleur(api)
    controle.reconcilier()
    print("\n   Et l'agent, lui :\n")
    for ligne in controleur.rendre_statut(
            [api.lire("Agent", "assistant-faute-de-frappe")]):
        print(f"      {ligne}")

    print("\n   ⚠️ DEUX « s » DE TROP, ET L'AGENT TOURNE SANS PROMPT. Il")
    print("   est `Accepted`, il est `Ready`, `kubectl apply` a repondu")
    print("   « configured », et son `systemMessage` est la chaine vide.")
    print("\n   C'est le comportement normal d'un schema structurel : tout")
    print("   champ inconnu est retire avant stockage. Kubernetes le fait")
    print("   pour garantir que l'objet stocke correspond exactement au")
    print("   schema — et le prix est ce silence.")
    print("\n   La parade tient en une habitude : relire l'objet TEL QUE")
    print("   L'API L'A STOCKE.")
    print("      kubectl get agent assistant-faute-de-frappe -o yaml")
    print("   Ce que ce fichier montre est la verite ; ce que vous avez")
    print("   envoye n'est qu'une intention. `kubectl apply --dry-run=server`")
    print("   rend la meme chose sans rien ecrire, et se met dans une CI.")


def _les_defauts() -> None:
    print("\n\n4. CE QUE LE SCHEMA AJOUTE, LUI AUSSI EN SILENCE\n")
    minimal = {
        "apiVersion": "kagent.dev/v1alpha2",
        "kind": "Agent",
        "metadata": {"name": "agent-minimal"},
        "spec": {"type": "Declarative",
                 "declarative": {"modelConfig": "claude-config"}},
    }
    verdict = crd.admettre(schemas.AGENT, minimal)
    print("   Un manifeste reduit au strict minimum :\n")
    print(f"      spec.declarative = {minimal['spec']['declarative']}\n")
    print("   Ce que l'API stocke :\n")
    for cle, valeur in verdict.objet["spec"]["declarative"].items():
        print(f"      {cle:<16} = {valeur!r}")
    print(f"      (namespace       = "
          f"{verdict.objet['metadata']['namespace']!r})")
    print("\n   Les valeurs par defaut du schema sont ecrites dans l'objet.")
    print("   Elles n'apparaissent nulle part dans votre fichier, et elles")
    print("   comptent : `maxIterations` a 10 plafonne le nombre de tours")
    print("   d'outils, `stream` a false change la forme de la reponse.")
    print("\n   ⚠️ Ces defauts appartiennent a la VERSION de la CRD. Une")
    print("   mise a jour de kagent peut les changer, et vos agents")
    print("   changeront de comportement sans qu'une ligne de vos")
    print("   manifestes n'ait bouge. C'est une raison de plus de relire")
    print("   l'objet stocke, et d'ecrire explicitement ce dont on depend.")


def _agent_as_code() -> None:
    print("\n\n5. L'AGENT « AS CODE », ET CE QUE CELA CHANGE VRAIMENT\n")
    fichiers = sorted(MANIFESTES.glob("*.yaml"))
    lignes = sum(len(f.read_text(encoding="utf-8").splitlines())
                 for f in fichiers)
    print(f"   {len(fichiers)} fichiers, {lignes} lignes — et c'est TOUT")
    print("   l'etat de la plateforme d'agents :\n")
    for fichier in fichiers:
        genres = [d.get("kind") for d in
                  yaml_minimal.charger_fichier_tous(fichier)]
        print(f"      {fichier.name:<30} {', '.join(genres)}")

    print("\n   Un changement de prompt devient une pull request : relue,")
    print("   tracee, reversible. L'etat de l'agent est la somme de ses")
    print("   manifestes — pas une configuration cachee dans une interface")
    print("   que personne ne sait reconstituer.")
    print("\n   ⚠️ Avec une limite qu'il faut dire : « as code » ne rend pas")
    print("   l'agent DETERMINISTE. Le manifeste est reproductible, la")
    print("   reponse du modele ne l'est pas. Ce que le versionnement")
    print("   apporte est la reproductibilite de l'ENTREE — ce qui est")
    print("   deja enorme quand il faut expliquer pourquoi l'agent s'est")
    print("   comporte autrement la semaine derniere.")
    print()


if __name__ == "__main__":
    main()
