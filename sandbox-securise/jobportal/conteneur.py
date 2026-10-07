"""Le quatrième niveau : généré et **vérifié**, pas exécuté ici.

Docker, gVisor et Firecracker demandent un noyau Linux. Ce module ne prétend
donc pas les simuler — il fait ce qui est réellement utile et réellement
vérifiable sans eux : **construire la ligne de commande, et relire celle que
vous avez écrite**.

Ce n'est pas un lot de consolation. Une commande `docker run` de durcissement
fait douze drapeaux ; elle se copie d'un article, se raccourcit au premier
problème, et le drapeau retiré « le temps de déboguer » y reste. `verifier()`
attrape exactement cela, et il tourne partout.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass

# Chaque drapeau, ce qu'il retire, et l'évasion du corpus qu'il neutralise.
# La troisième colonne est ce qui manque le plus souvent : un drapeau dont on
# ne sait pas ce qu'il empêche est un drapeau qu'on retire.
OBLIGATOIRES = {
    "--network=none": ("toute la pile reseau", "ouverture d'une socket"),
    "--read-only": ("l'ecriture sur le systeme de fichiers", "ecriture sur le disque"),
    "--cap-drop=ALL": ("toutes les capabilities", "elevation de privileges"),
    "--security-opt=no-new-privileges": ("setuid et consorts", "elevation de privileges"),
    "--pids-limit": ("la creation illimitee de processus", "fork bomb"),
    "--memory": ("la memoire illimitee", "explosion memoire"),
    "--cpus": ("le CPU illimite", "boucle infinie"),
    "--rm": ("la persistance du conteneur", "accumulation de conteneurs morts"),
}

RECOMMANDES = {
    "--user": "sans lui, le conteneur tourne en ROOT — le defaut de Docker",
    "--tmpfs": "un scratch jetable : sans lui, --read-only casse les programmes "
               "qui ecrivent legitimement dans /tmp",
    "--security-opt seccomp": "le filtre d'appels systeme ; sans profil, celui "
                              "de Docker s'applique — mieux que rien, loin d'un "
                              "profil dedie",
}


@dataclass
class Souci:
    gravite: str        # "erreur" ou "attention"
    drapeau: str
    message: str


def commande(image: str, code: str, runtime: str | None = None,
             memoire: str = "256m", cpus: str = "0.5") -> list[str]:
    """La commande durcie du chapitre 2, construite plutôt que recopiée.

    `runtime="runsc"` bascule sur gVisor : un noyau en espace utilisateur qui
    intercepte les appels système au lieu de les laisser atteindre le noyau
    hôte. C'est le chapitre 3, et c'est une ligne — d'où l'intérêt de la
    construire ici plutôt que de maintenir deux commandes.
    """
    args = ["docker", "run", "--rm"]
    if runtime:
        args += [f"--runtime={runtime}"]
    args += [
        "--network=none",
        "--read-only",
        "--tmpfs", "/tmp:size=64m,noexec",
        "--user", "1000:1000",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--pids-limit=64",
        f"--memory={memoire}",
        f"--cpus={cpus}",
        image, "python", "-c", code,
    ]
    return args


def verifier(ligne: str | list[str]) -> list[Souci]:
    """Relit une commande `docker run` et dit ce qui manque.

    À brancher sur la CI, au même titre qu'un linter : la commande de
    durcissement vit dans un script, un Makefile ou un manifeste, et elle se
    modifie comme du code — sans relecture, parce que « ce n'est qu'une
    commande ».
    """
    args = shlex.split(ligne) if isinstance(ligne, str) else list(ligne)
    texte = " ".join(args)
    soucis: list[Souci] = []

    # >>> depart: signaler chaque drapeau OBLIGATOIRES absent de la commande, en NOMMANT ce qu'il retire et l'evasion qu'il neutralise. Un drapeau dont on ignore ce qu'il empeche est un drapeau qu'on retire au premier probleme. Un test parametre par drapeau le verifie.
    #     pass
    for drapeau, (retire, evasion) in OBLIGATOIRES.items():
        racine = drapeau.split("=")[0]
        if racine not in texte:
            soucis.append(Souci("erreur", drapeau,
                                f"absent : {retire} reste accessible "
                                f"(evasion « {evasion} »)"))
    # <<<

    for drapeau, pourquoi in RECOMMANDES.items():
        if drapeau.split()[0] not in texte:
            soucis.append(Souci("attention", drapeau, pourquoi))

    # Les contresens : un drapeau présent mais neutralisé. Le plus difficile
    # à voir en relecture, parce que la commande A L'AIR durcie.
    # >>> depart: signaler les quatre contresens : --user root, --privileged, --network=host, et un montage -v sans « :ro ». Quatre tests parametres le verifient.
    #     pass
    if re.search(r"--user\s+(root|0:0|0\b)", texte):
        soucis.append(Souci("erreur", "--user",
                            "--user root annule tout le reste : root dans le "
                            "conteneur reste root si l'isolation cede"))
    if "--privileged" in texte:
        soucis.append(Souci("erreur", "--privileged",
                            "--privileged desactive la quasi-totalite de "
                            "l'isolation. Aucun autre drapeau ne compense."))
    if re.search(r"--network(=|\s+)(host|bridge)", texte):
        soucis.append(Souci("erreur", "--network",
                            "--network=host donne la pile reseau de l'HOTE au "
                            "code non fiable"))
    for montage in re.findall(r"(?:-v|--volume)[ =]([^\s]+)", texte):
        if ":ro" not in montage:
            soucis.append(Souci("erreur", "-v",
                                f"montage « {montage} » en ecriture : la "
                                f"persistance revient par la"))
    # <<<
    if re.search(r"--pids-limit[= ](\d+)", texte):
        n = int(re.search(r"--pids-limit[= ](\d+)", texte).group(1))
        if n > 512:
            soucis.append(Souci("attention", "--pids-limit",
                                f"{n} processus autorises : une fork bomb y "
                                f"tient largement"))
    return soucis


def durcie(**kwargs) -> str:
    return " ".join(shlex.quote(a) for a in commande(**kwargs))
