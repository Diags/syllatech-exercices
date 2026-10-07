"""Chapitre 5 — Kubernetes avance.

    uv run python chapitres/chapitre_5_avance.py

Les `requests` placent, les `limits` tuent, les sondes decident du trafic,
et la mise a jour progressive se deroule tick par tick. Le clou du
chapitre : un deploiement casse qui se bloque sans jamais couper le
service.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                       # noqa: E402
from jobportal import kubernetes as k8s              # noqa: E402

RACINE = Path(__file__).resolve().parent.parent
MANIFESTES = RACINE / "manifestes"
DEPLOIEMENT = (MANIFESTES / "deployment.yaml").read_text(encoding="utf-8")


def cluster_neuf() -> k8s.Cluster:
    return k8s.Cluster([k8s.noeud("noeud-1", 2, 4),
                        k8s.noeud("noeud-2", 2, 4)])


def deja_deploye() -> k8s.Cluster:
    cluster = cluster_neuf()
    cluster.appliquer(DEPLOIEMENT)
    cluster.stabiliser()
    return cluster


def main() -> None:
    console.utf8()
    _requests_et_limits()
    _les_classes_de_qualite()
    _les_sondes()
    _la_mise_a_jour()
    _le_deploiement_bloque()


def _requests_et_limits() -> None:
    print("1. `requests` PLACE, `limits` TUE\n")
    cluster = cluster_neuf()
    print("   Les deux noeuds, tels que Kubernetes les voit :\n")
    for nom, machine in sorted(cluster.noeuds.items()):
        print(f"      {nom}  {machine.cpu} m CPU   "
              f"{k8s.lisible(machine.memoire)} de memoire ALLOUABLE")
    print(f"\n   (une machine de 4 Gio en declare "
          f"{k8s.lisible(cluster.noeuds['noeud-1'].memoire)} : le kubelet, le")
    print("   moteur de conteneurs et le seuil d'eviction prennent le")
    print("   reste. La capacite n'est pas l'allouable.)\n")

    cluster.appliquer(
        (MANIFESTES / "deployment-gourmand.yaml").read_text(encoding="utf-8"))
    cluster.stabiliser()
    print("   Quatre repliques qui demandent 2 Gi chacune :\n")
    for ligne in k8s.rendre_pods(cluster):
        print(f"      {ligne}")
    print()
    for nom in sorted(cluster.noeuds):
        cpu, memoire = cluster.reste(nom)
        print(f"      {nom} : il reste {cpu} m CPU et "
              f"{k8s.lisible(memoire)}")
    print("\n   Deux pods places, deux `Pending` — pour toujours. Le total")
    print("   libre du cluster depasse pourtant 2 Gi : un pod ne se coupe")
    print("   pas en deux, il lui faut la place SUR UN NOEUD.")
    print("\n   ⚠️ `requests` n'est pas une estimation, c'est une")
    print("   RESERVATION. L'ordonnanceur ne regarde jamais la memoire")
    print("   reellement consommee : il additionne les `requests`. Un")
    print("   chiffre pose « pour etre tranquille » immobilise donc de la")
    print("   memoire que personne n'utilise, et fait tomber en panne un")
    print("   deploiement qui serait passe.")

    print("\n   `limits`, lui, ne place rien — il TUE :\n")
    gourmand = cluster_neuf()
    gourmand.appliquer(DEPLOIEMENT.replace(
        "jobportal:1.0", "jobportal:1.3-gourmande"))
    gourmand.stabiliser(30)
    image = k8s.connue("registry.exemple.fr/jobportal:1.3-gourmande")
    limite = gourmand.par_deploiement("jobportal")[0].conteneurs[0]
    print(f"      limite declaree     : {k8s.lisible(limite.memoire_limite)}")
    print(f"      memoire reellement utilisee : "
          f"{k8s.lisible(image.memoire_utilisee)}\n")
    for ligne in k8s.rendre_pods(gourmand):
        print(f"      {ligne}")
    print("\n   Le conteneur est tue et redemarre, en boucle. Le pod reste")
    print("   `Running` — c'est le CONTENEUR qui meurt — et le compteur de")
    print("   redemarrages est le seul signe visible dans `kubectl get")
    print("   pods`. Un `OOMKilled` ne laisse aucune trace dans les")
    print("   journaux de l'application : elle est tuee par le noyau, sans")
    print("   preavis et sans pouvoir ecrire quoi que ce soit.")


def _les_classes_de_qualite() -> None:
    print("\n\n2. LES CLASSES DE QUALITE, ET L'ORDRE D'EVICTION\n")
    cluster = cluster_neuf()
    cluster.appliquer(DEPLOIEMENT)
    cluster.appliquer((MANIFESTES / "deployment-sans-sondes.yaml").read_text(
        encoding="utf-8"))
    cluster.stabiliser()

    print(f"   {'DEPLOIEMENT':<24} {'requests':<14} {'limits':<14} QoS")
    for nom in sorted(cluster.deploiements):
        pod = cluster.par_deploiement(nom)[0]
        conteneur = pod.conteneurs[0]
        demandes = (f"{conteneur.cpu_demande}m / "
                    f"{k8s.lisible(conteneur.memoire_demandee)}"
                    if conteneur.cpu_demande else "aucune")
        limites = (f"{conteneur.cpu_limite}m / "
                   f"{k8s.lisible(conteneur.memoire_limite)}"
                   if conteneur.cpu_limite else "aucune")
        print(f"   {nom:<24} {demandes:<14} {limites:<14} {pod.qos}")

    print("\n   Trois classes, et elles se deduisent — on ne les ecrit")
    print("   jamais :\n")
    print("      Guaranteed   requests == limits sur TOUS les conteneurs")
    print("      Burstable    des requests, mais pas egales aux limits")
    print("      BestEffort   ni requests ni limits\n")
    print("   ⚠️ Quand un noeud manque de memoire, le kubelet evince dans")
    print("   cet ordre : BestEffort d'abord, Burstable ensuite,")
    print("   Guaranteed en dernier. Un manifeste sans `resources` n'est")
    print("   donc pas « neutre » : il se declare volontaire pour mourir")
    print("   le premier, et il le fait au pire moment — quand le noeud")
    print("   est deja sous pression.")
    print("\n   C'est le defaut le plus repandu des manifestes ecrits vite,")
    print("   et le plus facile a corriger : trois lignes de `resources`.")


def _les_sondes() -> None:
    print("\n\n3. CE QUE LA READINESS CHANGE, TICK PAR TICK\n")
    avec = cluster_neuf()
    avec.appliquer(DEPLOIEMENT)
    sans = cluster_neuf()
    sans.appliquer((MANIFESTES / "deployment-sans-sondes.yaml").read_text(
        encoding="utf-8"))
    sans.appliquer(
        '{"apiVersion": "v1", "kind": "Service"}'.replace("{", "").replace("}", "")
        if False else """apiVersion: v1
kind: Service
metadata:
  name: jobportal-sans-sondes
spec:
  selector: { app: jobportal-sans-sondes }
  ports: [{ port: 80, targetPort: 8080 }]
""")

    print(f"   {'tick':<6} {'avec readinessProbe':<24} sans sonde")
    for tick in range(1, 9):
        avec.reconcilier()
        sans.reconcilier()
        gauche = (f"{avec.disponibles('jobportal')} pod(s) dans le Service")
        droite = (f"{sans.disponibles('jobportal-sans-sondes')} "
                  f"pod(s) dans le Service")
        print(f"   t={tick:<4} {gauche:<24} {droite}")

    print("\n   Sans sonde, les trois pods entrent dans le Service au")
    print("   deuxieme tick : Kubernetes considere qu'un conteneur qui")
    print("   TOURNE est PRET. L'application, elle, met encore cinq")
    print("   secondes a charger son contexte Spring.")
    print("\n   ⚠️ Pendant ces cinq secondes, le Service envoie du trafic a")
    print("   des pods qui repondent par des erreurs de connexion. C'est")
    print("   la source des 502 que l'on observe au debut de chaque")
    print("   deploiement, et qu'on met souvent sur le compte du reseau.")
    print("\n   Les trois sondes, et ce que chacune decide :\n")
    print("      readiness   le pod recoit-il du TRAFIC ?  (retire des")
    print("                  endpoints s'il echoue — le pod n'est pas tue)")
    print("      liveness    le pod est-il BLOQUE ?  (le conteneur est")
    print("                  redemarre s'il echoue)")
    print("      startup     couvre un demarrage LENT ; tant qu'elle n'a")
    print("                  pas reussi, les deux autres sont suspendues\n")
    print("   ⚠️ L'erreur classique est une `liveness` sans `startup` sur")
    print("   une application longue a demarrer : la sonde echoue pendant")
    print("   le demarrage, Kubernetes redemarre le conteneur, qui")
    print("   recommence a demarrer — une boucle parfaite, ou rien")
    print("   n'indique que le probleme vient de la sonde.")


def _la_mise_a_jour() -> None:
    print("\n\n4. LA MISE A JOUR PROGRESSIVE, TICK PAR TICK\n")
    prudente = DEPLOIEMENT
    brutale = DEPLOIEMENT.replace(
        "rollingUpdate: { maxSurge: 1, maxUnavailable: 0 }",
        "rollingUpdate: { maxSurge: 0, maxUnavailable: 3 }")

    for titre, manifeste in (("maxSurge 1 / maxUnavailable 0", prudente),
                             ("maxSurge 0 / maxUnavailable 3", brutale)):
        cluster = cluster_neuf()
        cluster.appliquer(manifeste)
        cluster.stabiliser()
        cluster.appliquer(manifeste.replace("jobportal:1.0", "jobportal:1.1"))
        print(f"   ── {titre}\n")
        print(f"      {'tick':<7} {'pods':<6} {'prets':<7} endpoints")
        minimum = 99
        for _ in range(40):
            cluster.reconcilier()
            pods = cluster.par_deploiement("jobportal")
            prets = cluster.disponibles("jobportal")
            minimum = min(minimum, prets)
            print(f"      t={cluster.tick:<5} {len(pods):<6} {prets:<7} "
                  f"{len(cluster.endpoints('jobportal'))}")
            neuves = all(p.conteneurs[0].image.endswith("1.1") for p in pods)
            if neuves and prets == 3 and len(pods) == 3:
                break
        print(f"\n      → minimum de pods prets pendant la bascule : "
              f"{minimum}\n")

    print("   Les deux bornes ne portent pas sur la meme chose :\n")
    print("      maxSurge        plafonne le nombre TOTAL de pods")
    print("      maxUnavailable  plancherise le nombre de pods PRETS\n")
    print("   Avec `maxSurge: 1, maxUnavailable: 0`, le controleur ajoute")
    print("   un pod, attend qu'il soit PRET, puis en retire un ancien.")
    print("   Le nombre de pods prets ne descend jamais sous 3 : aucune")
    print("   requete ne tombe.")
    print("\n   ⚠️ Avec `maxSurge: 0, maxUnavailable: 3`, il retire les")
    print("   trois anciens AVANT de creer les nouveaux. Le service est")
    print("   injoignable pendant tout le demarrage des remplacants. Ce")
    print("   reglage existe pour les cas ou deux versions ne peuvent pas")
    print("   coexister — une migration de schema, par exemple — et il")
    print("   s'assume comme une coupure, pas comme une optimisation.")
    print("\n   Et la contrepartie de la version prudente : pendant la")
    print("   bascule, DEUX versions de votre application repondent en")
    print("   meme temps. Votre code doit donc tolerer que la version")
    print("   d'a cote lise la meme base — c'est la vraie contrainte des")
    print("   deploiements sans coupure, et elle est dans le code, pas")
    print("   dans le manifeste.")


def _le_deploiement_bloque() -> None:
    print("\n\n5. UN DEPLOIEMENT CASSE NE COUPE RIEN\n")
    cluster = cluster_neuf()
    cluster.appliquer(DEPLOIEMENT)
    cluster.stabiliser()
    avant = sorted(p.nom for p in cluster.par_deploiement("jobportal"))

    cluster.appliquer(DEPLOIEMENT.replace(
        "jobportal:1.0", "jobportal:1.2-cassee"))
    print("   L'image 1.2 demarre, et ne passe JAMAIS sa readiness.\n")
    print(f"      {'tick':<7} {'pods':<6} {'prets':<7} {'endpoints':<11} "
          f"condition")
    for _ in range(40):
        cluster.reconcilier()
        if cluster.tick % 5 == 0 or cluster.deploiements["jobportal"].condition:
            deploiement = cluster.deploiements["jobportal"]
            print(f"      t={cluster.tick:<5} "
                  f"{len(cluster.par_deploiement('jobportal')):<6} "
                  f"{cluster.disponibles('jobportal'):<7} "
                  f"{len(cluster.endpoints('jobportal')):<11} "
                  f"{deploiement.condition}")
        if cluster.deploiements["jobportal"].condition:
            break

    print()
    for ligne in k8s.rendre_pods(cluster, cluster.par_deploiement("jobportal")):
        print(f"      {ligne}")
    print(f"\n      ReplicaSets : "
          f"{ {rs.nom: rs.voulus for rs in cluster.replicasets.values()} }")

    print("\n   ⚠️ C'EST LA MESURE LA PLUS UTILE DU CHAPITRE. Le")
    print("   deploiement est bloque, il le DIT")
    print("   (`ProgressDeadlineExceeded`), et le service a repondu sans")
    print("   interruption du debut a la fin : les trois anciens pods")
    print("   n'ont jamais ete retires, parce que le plancher de")
    print("   `maxUnavailable: 0` l'interdisait.")
    print("\n   Un `maxUnavailable` a zero n'est donc pas une precaution")
    print("   de confort : c'est ce qui transforme « la production est")
    print("   tombee » en « le deploiement n'est pas passe ». La")
    print("   difference, a trois heures du matin, est entiere.")

    apres = sorted(p.nom for p in cluster.par_deploiement("jobportal"))
    survivants = [nom for nom in apres if nom in avant]
    print(f"\n   Pods d'origine encore en place : {len(survivants)} sur 3")

    revision = cluster.annuler("jobportal")
    cluster.stabiliser()
    print(f"\n   `kubectl rollout undo` → retour a la revision {revision}\n")
    for ligne in k8s.rendre_pods(cluster, cluster.par_deploiement("jobportal")):
        print(f"      {ligne}")
    print(f"\n      images : "
          f"{sorted({p.conteneurs[0].image for p in cluster.par_deploiement('jobportal')})}")
    print("\n   Le retour arriere est immediat parce que l'ancien")
    print("   ReplicaSet n'a jamais ete supprime : Kubernetes en garde")
    print("   dix par defaut (`revisionHistoryLimit`). Annuler, c'est")
    print("   simplement le remonter a trois et redescendre l'autre a")
    print("   zero.")
    print()


if __name__ == "__main__":
    main()
