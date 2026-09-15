"""Chapitre 6 — Production : Helm et CI/CD.

    uv run python chapitres/chapitre_6_production.py

Un chart est un generateur de texte. Ce chapitre rend le meme chart pour
deux environnements, fait echouer un rendu sans valeur obligatoire, puis
mesure ce que le tag `latest` fait — et ne fait pas — quand la CI le pousse
deux fois de suite.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                       # noqa: E402
from jobportal import helm                          # noqa: E402
from jobportal import kubernetes as k8s              # noqa: E402

RACINE = Path(__file__).resolve().parent.parent
CHART = RACINE / "chart"
PRODUCTION = CHART / "values-production.yaml"


def cluster_neuf() -> k8s.Cluster:
    return k8s.Cluster([k8s.noeud("noeud-1", 2, 4),
                        k8s.noeud("noeud-2", 2, 4)])


def main() -> None:
    console.utf8()
    chart = helm.charger(CHART)
    _un_generateur_de_texte(chart)
    _la_fusion_des_valeurs(chart)
    _required(chart)
    _le_tag_latest(chart)
    _le_retour_arriere(chart)
    _ce_qui_reste()


def _un_generateur_de_texte(chart: helm.Chart) -> None:
    print("1. UN CHART EST UN GENERATEUR DE TEXTE\n")
    print(f"   Chart « {chart.nom} » version {chart.version}")
    print(f"      gabarits    : {sorted(chart.gabarits)}")
    print(f"      definitions : {sorted(chart.definitions)}\n")
    valeurs = helm.valeurs_de(chart, set_=["image.tag=1.0"])
    rendus = helm.rendre(chart, valeurs, "jobportal")
    print("   `helm template` sur les valeurs par defaut — extrait :\n")
    for ligne in rendus["deployment.yaml"].splitlines()[:8]:
        print(f"      {ligne}")
    print("      …")
    print("\n   Rien n'a parle a Kubernetes. Helm a lu des fichiers,")
    print("   remplace des `{{ … }}` et rendu du YAML. C'est tout ce qu'un")
    print("   chart fait — et c'est pour cela qu'un `helm template` se")
    print("   relit, se versionne et se compare comme n'importe quel")
    print("   fichier.")
    print("\n   ⚠️ Consequence directe : une erreur de valeur ne produit")
    print("   pas une erreur Helm, elle produit un YAML different. Le")
    print("   controle doit donc se faire AVANT — c'est la section 3.")


def _la_fusion_des_valeurs(chart: helm.Chart) -> None:
    print("\n\n2. TROIS COUCHES DE VALEURS, DANS CET ORDRE\n")
    par_defaut = chart.valeurs
    avec_prod = helm.valeurs_de(chart, [PRODUCTION])
    complete = helm.valeurs_de(chart, [PRODUCTION], ["image.tag=a1b2c3d"])

    lignes = [
        ("replicas", "replicas"),
        ("image.repository", "image.repository"),
        ("image.tag", "image.tag"),
        ("ressources.cpu", "ressources.cpu"),
        ("ressources.memoire", "ressources.memoire"),
        ("ingress.actif", "ingress.actif"),
        ("ingress.hote", "ingress.hote"),
    ]
    print(f"   {'CHEMIN':<22} {'values.yaml':<20} "
          f"{'+ production':<20} + --set")
    for libelle, chemin in lignes:
        print(f"   {libelle:<22} {str(_lire(par_defaut, chemin)):<20} "
              f"{str(_lire(avec_prod, chemin)):<20} "
              f"{_lire(complete, chemin)}")

    print("\n   La fusion est PROFONDE : `values-production.yaml` ne redit")
    print("   pas `image.repository`, et celui-ci survit. Seul ce qui est")
    print("   ecrit est remplace.")
    print("\n   ⚠️ Avec une exception qui surprend tout le monde une fois :")
    print("   une LISTE est remplacee en entier, jamais fusionnee element")
    print("   par element. Surcharger un seul port d'une liste de ports")
    print("   demande donc de reecrire la liste complete.")
    print("\n   Et l'ordre compte : `--set` passe apres tout le reste.")
    print("   C'est ce qui permet a la CI de poser le tag de l'image sans")
    print("   toucher au moindre fichier — `--set image.tag=$SHA`.")


def _lire(valeurs: dict, chemin: str):
    courant = valeurs
    for morceau in chemin.split("."):
        if not isinstance(courant, dict):
            return "—"
        courant = courant.get(morceau)
    return courant if courant not in (None, "") else "(vide)"


def _required(chart: helm.Chart) -> None:
    print("\n\n3. `required` : ECHOUER AU RENDU PLUTOT QU'EN PRODUCTION\n")
    print("   Le gabarit ecrit :\n")
    for ligne in chart.gabarits["deployment.yaml"].splitlines():
        if "image:" in ligne:
            print(f"      {ligne.strip()}")
    print()
    try:
        helm.rendre(chart, helm.valeurs_de(chart, [PRODUCTION]))
        print("      rendu sans `image.tag` → passe (!)")
    except helm.ErreurHelm as erreur:
        print(f"      rendu sans `image.tag` → ECHEC : {erreur}")

    sans_required = chart.gabarits["deployment.yaml"].replace(
        'required "image.tag est obligatoire : posez-le avec '
        '--set image.tag=$SHA" .Values.image.tag', ".Values.image.tag")
    nu = helm.Chart(chart.nom, chart.version, chart.valeurs,
                    {"deployment.yaml": sans_required}, chart.definitions)
    rendu = helm.rendre(nu, helm.valeurs_de(chart, [PRODUCTION]))
    ligne = [l for l in rendu["deployment.yaml"].splitlines()
             if "image:" in l][0]
    print(f"      le meme gabarit SANS `required` →")
    print(f"         {ligne.strip()}")
    print("\n   ⚠️ Le YAML produit reste valide. Il part vers le cluster,")
    print("   Kubernetes cree le Deployment, et les pods echouent en")
    print("   `ErrImagePull` — six minutes plus tard, avec un message qui")
    print("   ne parle pas de votre `values.yaml`.")
    print("\n   `required` est la seule facon de faire echouer le RENDU. Il")
    print("   coute une ligne et deplace la panne de la production vers la")
    print("   pull request. Posez-le sur tout ce qui n'a pas de valeur par")
    print("   defaut raisonnable : le tag de l'image, le nom d'hote, les")
    print("   references de secrets.")


def _le_tag_latest(chart: helm.Chart) -> None:
    print("\n\n4. LA MESURE QUI TRANCHE : `latest` NE DEPLOIE RIEN\n")
    print("   Deux fusions sur `main`, donc deux `helm upgrade`. Une fois")
    print("   avec le tag `latest`, une fois avec le SHA du commit.\n")

    for titre, tags in (("--set image.tag=latest", ["latest", "latest"]),
                        ("--set image.tag=$SHA", ["a1b2c3d", "9f8e7d6"])):
        publication = helm.Publication("jobportal", chart)
        cluster = cluster_neuf()
        for tag in tags:
            valeurs = helm.valeurs_de(chart, [PRODUCTION],
                                      [f"image.tag={tag}"])
            revision = publication.mettre_a_jour(valeurs)
            cluster.appliquer(publication.manifeste(revision.numero))
            cluster.stabiliser()

        pods = cluster.par_deploiement("jobportal")
        print(f"   ── {titre}\n")
        print(f"      manifestes des revisions 1 et 2 identiques : "
              f"{publication.identiques(1, 2)}")
        print(f"      ReplicaSets crees  : {len(cluster.replicasets)}")
        print(f"      revision Deployment: "
              f"{cluster.deploiements['jobportal'].revision}")
        print(f"      ages des pods      : {sorted(p.age for p in pods)}")
        print(f"      images servies     : "
              f"{sorted({p.conteneurs[0].image for p in pods})}\n")

    print("   Avec `latest`, le manifeste rendu est OCTET POUR OCTET le")
    print("   meme. Kubernetes compare l'etat voulu a l'etat reel, ne")
    print("   trouve aucune difference, ne cree aucun ReplicaSet, et ne")
    print("   redemarre aucun pod. L'image que vous venez de construire et")
    print("   de pousser ne part jamais.")
    print("\n   ⚠️ Et le pire : rien n'echoue. `helm upgrade` rend")
    print("   « STATUS: deployed », la CI est verte, le tableau de bord est")
    print("   vert. La version en production est celle d'avant, et")
    print("   personne ne le sait avant le premier rapport d'anomalie sur")
    print("   un bogue deja corrige.")
    print("\n   Avec le SHA du commit, le gabarit de pod change, donc son")
    print("   `pod-template-hash` change, donc un NOUVEAU ReplicaSet est")
    print("   cree — et la mise a jour progressive du chapitre 5 se")
    print("   deroule. Les ages des pods le montrent : ils ont ete")
    print("   remplaces l'un apres l'autre.")
    print("\n   C'est la raison technique — et non stylistique — pour")
    print("   laquelle un tag de deploiement doit etre IMMUABLE.")


def _le_retour_arriere(chart: helm.Chart) -> None:
    print("\n\n5. L'HISTORIQUE, ET CE QUE `rollback` REJOUE\n")
    publication = helm.Publication("jobportal", chart)
    publication.installer(helm.valeurs_de(
        chart, [PRODUCTION], ["image.tag=a1b2c3d"]))
    publication.mettre_a_jour(helm.valeurs_de(
        chart, [PRODUCTION], ["image.tag=9f8e7d6", "replicas=5"]))
    publication.annuler(1)

    print(f"   {'REVISION':<10} {'ACTION':<18} {'IMAGE':<44} REPLICAS")
    for revision in publication.revisions:
        texte = revision.manifestes["deployment.yaml"]
        image = _extraire(texte, "image:")
        replicas = _extraire(texte, "replicas:")
        print(f"   {revision.numero:<10} {revision.action:<18} "
              f"{image:<44} {replicas}")

    print("\n   La revision 3 a repris l'image ET le nombre de repliques de")
    print("   la revision 1. Ce n'est pas le chart qui a ete rejoue : ce")
    print("   sont les MANIFESTES RENDUS de la revision 1, conserves tels")
    print("   quels dans l'historique de la release.")
    print("\n   ⚠️ C'est ce qui rend le retour arriere fiable — il ne depend")
    print("   ni du chart d'aujourd'hui, ni de votre `values.yaml`")
    print("   d'aujourd'hui. Et c'est ce qui le rend trompeur si on")
    print("   l'oublie : un `helm rollback` suivi d'un `helm upgrade` avec")
    print("   les valeurs courantes ramene exactement ce qu'on venait")
    print("   d'annuler.")
    print("\n   Ce que Helm ne fait PAS non plus : revenir sur une")
    print("   migration de base de donnees. Le retour arriere est celui")
    print("   des manifestes, jamais celui des donnees — d'ou la regle de")
    print("   n'ecrire que des migrations compatibles avec la version")
    print("   precedente.")


def _extraire(texte: str, cle: str) -> str:
    for ligne in texte.splitlines():
        if cle in ligne:
            return ligne.split(cle, 1)[1].strip()
    return "—"


def _ce_qui_reste() -> None:
    print("\n\n6. CE QU'UNE CHAINE DE PRODUCTION AJOUTE ENCORE\n")
    print("   Le pipeline que ce chapitre modelise tient en quatre pas :\n")
    print("      build → tag(SHA) → push → helm upgrade --set image.tag=$SHA\n")
    print("   Une vraie chaine y ajoute cinq choses, et aucune n'est")
    print("   optionnelle :\n")
    print("      • `helm lint` et `helm template | kubectl apply")
    print("        --dry-run=server` : le rendu et la validation par l'API")
    print("        AVANT de toucher au cluster ;")
    print("      • une analyse de l'image (Trivy, Grype) : les CVE des")
    print("        paquets systeme de l'image de base, qu'aucun test")
    print("        unitaire ne verra ;")
    print("      • la signature de l'image (cosign) et une politique")
    print("        d'admission qui refuse les images non signees — sans")
    print("        quoi « tag immuable » ne protege que des distraits ;")
    print("      • `kubectl rollout status --timeout` apres l'upgrade :")
    print("        sans lui, la CI est verte alors que le deploiement est")
    print("        bloque, comme au chapitre 5 ;")
    print("      • l'observabilite : journaux centralises, metriques, et")
    print("        une alerte sur le taux d'erreur. Un deploiement qui")
    print("        passe tous les controles peut quand meme degrader le")
    print("        service, et c'est la seule facon de le voir.\n")
    print("   ⚠️ Et une regle qui n'est pas technique : les identifiants de")
    print("   la CI n'ont de droits que sur leur `namespace`. Un")
    print("   `cluster-admin` unique transforme chaque erreur de pipeline")
    print("   en incident global.")
    print("\n   Ce que ce projet ne fait pas, et qu'il faut savoir : il n'y")
    print("   a ni registre, ni reseau, ni volumes persistants, ni")
    print("   `StatefulSet`, ni `Ingress`, ni HPA. Le HPA, en particulier,")
    print("   exige un `metrics-server` et des `requests` — sans")
    print("   `requests`, il n'a aucun denominateur pour calculer un")
    print("   pourcentage d'utilisation, et il ne fait rien. C'est la")
    print("   troisieme raison, apres l'ordonnancement et les classes de")
    print("   qualite, de toujours les declarer.")
    print()


if __name__ == "__main__":
    main()
