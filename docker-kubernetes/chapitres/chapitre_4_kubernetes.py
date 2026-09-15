"""Chapitre 4 — Kubernetes : les fondamentaux.

    uv run python chapitres/chapitre_4_kubernetes.py

`kubectl apply` n'execute rien. Ce chapitre fait tourner la boucle de
reconciliation tick par tick, supprime un pod pour le voir revenir, et
montre le Service qui ne repond jamais parce qu'il lui manque une lettre.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                       # noqa: E402
from jobportal import kubernetes as k8s              # noqa: E402

RACINE = Path(__file__).resolve().parent.parent
MANIFESTES = RACINE / "manifestes"


def cluster_neuf() -> k8s.Cluster:
    """Deux noeuds de 2 coeurs et 4 Gio."""
    return k8s.Cluster([k8s.noeud("noeud-1", 2, 4),
                        k8s.noeud("noeud-2", 2, 4)])


def main() -> None:
    console.utf8()
    cluster = cluster_neuf()
    manifeste = (MANIFESTES / "deployment.yaml").read_text(encoding="utf-8")

    _la_boucle(cluster, manifeste)
    _le_trio(cluster)
    _lauto_guerison(cluster)
    _le_selecteur(cluster)
    _lidempotence(cluster, manifeste)


def _la_boucle(cluster: k8s.Cluster, manifeste: str) -> None:
    print("1. `kubectl apply` N'EXECUTE RIEN\n")
    objets = cluster.appliquer(manifeste)
    print(f"   Objets ecrits dans l'API : {objets}")
    print(f"   Pods existants juste apres l'apply : {len(cluster.pods)}\n")
    print("   Rien n'a demarre. `apply` a ecrit un ETAT VOULU, et c'est")
    print("   tout. Ce qui suit est le travail des controleurs, qui")
    print("   comparent en boucle le voulu au reel :\n")

    depart = cluster.tick
    duree = cluster.stabiliser()
    for evenement in cluster.journal_depuis(depart):
        print(f"      {evenement}")
    print(f"\n   Stabilise en {duree} ticks d'une seconde.\n")
    for ligne in k8s.rendre_pods(cluster):
        print(f"      {ligne}")
    print("\n   Quatre controleurs se sont relayes, dans cet ordre :")
    print("      1. celui du Deployment a cree un ReplicaSet ;")
    print("      2. celui du ReplicaSet a cree trois Pods ;")
    print("      3. l'ordonnanceur les a places sur des noeuds ;")
    print("      4. le kubelet les a demarres, puis sonde jusqu'a ce que")
    print("         la readiness passe — cinq ticks plus tard.")
    print("\n   ⚠️ Aucun de ces controleurs ne sait ce que les autres font.")
    print("   Chacun regarde l'etat, fait UN pas, et recommence. C'est ce")
    print("   qui rend le systeme robuste — et c'est aussi pourquoi une")
    print("   panne s'y diagnostique en lisant l'etat, jamais en cherchant")
    print("   « qui a lance la commande ».")


def _le_trio(cluster: k8s.Cluster) -> None:
    print("\n\n2. DEPLOYMENT → REPLICASET → POD\n")
    deploiement = cluster.deploiements["jobportal"]
    print(f"   Deployment  {deploiement.nom:<22} replicas voulus : "
          f"{deploiement.voulus}   revision : {deploiement.revision}")
    for replicaset in cluster.replicasets.values():
        print(f"   ReplicaSet  {replicaset.nom:<22} voulus : "
              f"{replicaset.voulus}   empreinte : {replicaset.empreinte}")
    for pod in cluster.par_deploiement("jobportal"):
        print(f"   Pod         {pod.nom:<22} "
              f"etiquettes : {pod.etiquettes}")

    print("\n   Trois objets, trois roles distincts :\n")
    print("      • le Deployment porte l'INTENTION : « je veux 3 repliques")
    print("        de cette image, mises a jour de cette facon » ;")
    print("      • le ReplicaSet porte un GABARIT FIGE et compte ses pods.")
    print("        Il ne sait rien des mises a jour ;")
    print("      • le Pod est l'unite qui tourne. Il est jetable, et son")
    print("        nom change a chaque recreation.\n")
    print("   L'etiquette `pod-template-hash` est la charniere : elle vaut")
    print(f"   {deploiement.gabarit.empreinte}, c'est-a-dire l'empreinte du")
    print("   gabarit. Changer l'image change l'empreinte, donc cree un")
    print("   NOUVEAU ReplicaSet — et c'est comme cela qu'une mise a jour")
    print("   progressive fonctionne, sans qu'aucun code ne « migre » quoi")
    print("   que ce soit.")
    print("\n   ⚠️ Corollaire a retenir pour le chapitre 6 : si le gabarit")
    print("   ne change pas, l'empreinte ne change pas, et Kubernetes ne")
    print("   fait RIEN. Deux deploiements identiques ne redemarrent aucun")
    print("   pod, meme si l'image derriere le tag a change.")


def _lauto_guerison(cluster: k8s.Cluster) -> None:
    print("\n\n3. L'AUTO-GUERISON N'EST PAS UNE OPTION\n")
    victime = cluster.par_deploiement("jobportal")[0]
    print(f"   Pods prets avant : {cluster.disponibles('jobportal')}")
    print(f"   `kubectl delete pod {victime.nom}`\n")
    depart = cluster.tick
    cluster.supprimer_pod(victime.nom)
    cluster.stabiliser()
    for evenement in cluster.journal_depuis(depart):
        print(f"      {evenement}")
    print(f"\n   Pods prets apres : {cluster.disponibles('jobportal')}\n")
    for ligne in k8s.rendre_pods(cluster, cluster.par_deploiement("jobportal")):
        print(f"      {ligne}")
    print("\n   Le pod supprime n'est pas revenu : un AUTRE a ete cree, avec")
    print("   un nom different. C'est exactement ce que dit « le pod est")
    print("   ephemere et remplacable » — il n'a pas d'identite, pas de")
    print("   disque, pas d'adresse stable.")
    print("\n   ⚠️ Pour une base de donnees, cette propriete est un")
    print("   probleme, pas une qualite : il faut un `StatefulSet`, qui")
    print("   donne aux pods un nom stable (`db-0`, `db-1`) et un volume")
    print("   qui les suit. Un `Deployment` ne convient qu'aux services")
    print("   SANS etat — c'est la premiere question a se poser devant un")
    print("   manifeste.")


def _le_selecteur(cluster: k8s.Cluster) -> None:
    print("\n\n4. LE SERVICE QUI NE REPOND JAMAIS\n")
    casse = (MANIFESTES / "service-mauvais-selecteur.yaml").read_text(
        encoding="utf-8")
    cluster.appliquer(casse)

    print(f"   {'SERVICE':<22} {'SELECTEUR':<26} ENDPOINTS")
    for service in cluster.services.values():
        endpoints = cluster.endpoints(service.nom)
        liste = ", ".join(p.nom for p in endpoints) if endpoints else "<none>"
        print(f"   {service.nom:<22} {str(service.selecteur):<26} "
              f"{len(endpoints)}  {liste if len(liste) < 40 else ''}")

    print("\n   Les etiquettes que portent les pods :")
    for pod in cluster.par_deploiement("jobportal")[:1]:
        print(f"      {pod.etiquettes}")

    print("\n   ⚠️ `app: jobporta` contre `app: jobportal`. Une lettre.")
    print("   Le manifeste est valide, `kubectl apply` l'accepte, le")
    print("   Service recoit une IP et un nom DNS. Il ne repond jamais —")
    print("   et RIEN ne le signale.")
    print("\n   Kubernetes ne verifie pas qu'un selecteur corresponde a")
    print("   quelque chose, et il a raison : un Service est souvent cree")
    print("   AVANT les pods qu'il servira. Le seul signe est")
    print("   `kubectl get endpoints`, qui affiche `<none>`.")
    print("\n   C'est le premier reflexe devant un service qui rend des")
    print("   erreurs de connexion : pas les journaux de l'application,")
    print("   pas le DNS — les endpoints. Un `<none>` fait gagner une")
    print("   heure.")


def _lidempotence(cluster: k8s.Cluster, manifeste: str) -> None:
    print("\n\n5. APPLIQUER DEUX FOIS NE FAIT RIEN\n")
    avant = {pod.nom: pod.age for pod in cluster.par_deploiement("jobportal")}
    depart = cluster.tick
    cluster.appliquer(manifeste)
    cluster.stabiliser()
    apres = {pod.nom: pod.age for pod in cluster.par_deploiement("jobportal")}

    print(f"   Pods avant le second apply : {sorted(avant)}")
    print(f"   Pods apres                 : {sorted(apres)}")
    print(f"   Pods recrees               : "
          f"{len(set(apres) - set(avant))}")
    print(f"   ReplicaSets                : {len(cluster.replicasets)}")
    evenements = [e for e in cluster.journal_depuis(depart)
                  if "pod/" in e.quoi]
    print(f"   Evenements sur les pods    : {len(evenements)}\n")

    print("   Le second `apply` a reecrit exactement le meme etat voulu.")
    print("   Les controleurs ont compare, n'ont rien trouve a faire, et")
    print("   se sont rendormis. C'est l'idempotence, et c'est ce qui rend")
    print("   possible le GitOps : une boucle qui reapplique le depot")
    print("   toutes les trois minutes ne redemarre rien.")
    print("\n   ⚠️ Avec une reserve, et elle est de taille : `kubectl apply`")
    print("   fusionne, il ne remplace pas. Un champ retire de votre")
    print("   fichier n'est pas efface du cluster — il reste tel qu'il")
    print("   etait, parce que `apply` ne connait que ce que vous lui")
    print("   envoyez. C'est la raison d'etre des annotations de")
    print("   `last-applied-configuration`, et du mode `--server-side`.")
    print("   Pour partir d'une page blanche, il faut `kubectl replace`")
    print("   ou supprimer l'objet.")
    print()


if __name__ == "__main__":
    main()
