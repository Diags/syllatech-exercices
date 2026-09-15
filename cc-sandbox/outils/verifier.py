#!/usr/bin/env python3
"""Le verificateur de configuration de bac a sable.

    python outils/verifier.py configs/a-corriger.json [--portee projet]

Il relit une configuration et signale ce qui NE MARCHERA PAS — sans qu'aucune
erreur ne soit levee au demarrage, sans qu'aucun champ soit mal orthographie,
sans que `claude doctor` ait forcement quelque chose a dire.

LES DEUX FAMILLES DE DEFAUTS SILENCIEUX

  · LA PORTEE. Cinq cles ne sont honorees que depuis les reglages
    utilisateur, geres ou --settings. Dans le .claude/settings.json d'un
    depot, elles sont ignorees. Le resolveur les enleve : on verifie donc la
    configuration TELLE QU'ELLE S'APPLIQUE, pas telle qu'elle est ecrite.

  · LA COMBINAISON. Une cle juste, seule, ne fait rien : un « mask » sans
    tlsTerminate, un injectHosts hors de allowedDomains, un allowWrite sur un
    chemin protege, un joker au mauvais endroit.

Une erreur signalee ici ne casse rien au demarrage. C'est precisement ce qui
la rend chere : elle se decouvre le jour ou elle aurait du proteger.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from outils.resolveur import (CLES_PRIVILEGIEES, Config,  # noqa: E402
                              PORTEES_PRIVILEGIEES, _domaine, appliquee,
                              motif_inerte, protege)

for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except Exception:      # noqa: BLE001
        pass


@dataclass
class Souci:
    gravite: str          # "erreur" ou "attention"
    ou: str
    message: str


def verifier(config: Config) -> list[Souci]:
    soucis: list[Souci] = []

    if not config.enabled:
        soucis.append(Souci("erreur", "sandbox.enabled",
                            "le bac a sable est DESACTIVE : tout le reste de "
                            "cette configuration est decoratif"))
        return soucis

    # -------------------------------------------------- 1. la portee
    #
    # On verifie ensuite la configuration APPLIQUEE. Verifier celle qui est
    # ECRITE donnerait la bonne reponse a la mauvaise question : on validerait
    # des regles qui ne s'executent pas.
    # >>> depart: appeler appliquee(config) et signaler CHAQUE cle jetee comme une erreur, en citant sa consequence et la raison de la restriction. Puis verifier la configuration EFFECTIVE, pas celle qui est ecrite : valider des regles qui ne s'executent pas donnerait la bonne reponse a la mauvaise question. Trois tests le verifient.
    #     effective, ignorees = config, []
    effective, ignorees = appliquee(config)
    for perdue in ignorees:
        soucis.append(Souci(
            "erreur", perdue.cle,
            f"ecrite mais IGNOREE en portee « {perdue.portee} » — "
            f"{perdue.consequence}. Pourquoi : {perdue.pourquoi}. Deplacez-la "
            f"dans les reglages utilisateur, geres, ou --settings."))
    # <<<

    # -------------------------- 2. un allowWrite sur un chemin protege
    #
    # Sauf si filesystem.disabled s'applique : la couche entiere est coupee,
    # donc l'entree n'est plus inerte — elle est superflue. Signaler
    # « protege » la serait faux, et un verificateur qui ment sur un cas rend
    # suspects tous les autres. L'avertissement filesystem.disabled les liste.
    proteges_ouverts = [c for c in effective.filesystem.get("allowWrite", [])
                        if protege(c)]
    if not effective.filesystem.get("disabled"):
        for chemin in proteges_ouverts:
            soucis.append(Souci("erreur", f"allowWrite / {chemin}",
                                f"« {protege(chemin)} » est protege QUOI "
                                "QU'ON ECRIVE. Cet allowWrite ne leve pas la "
                                "protection — il ne fait rien, et rien ne le "
                                "dit."))

    # ----------------------------------- 3. un masque sans terminaison TLS
    masques = [e for e in effective.credentials.get("envVars", [])
               if e.get("mode") == "mask"]
    masques_fichiers = [e for e in effective.credentials.get("files", [])
                        if e.get("mode") == "mask"]
    # >>> depart: signaler un mask sans network.tlsTerminate. Le proxy doit dechiffrer pour reconnaitre la sentinelle et y remettre la vraie valeur ; sans terminaison TLS il ne peut pas, donc la sentinelle part telle quelle et l'authentification rate. Rien ne fuit, mais rien ne marche. Deux tests le verifient.
    #     pass
    if (masques or masques_fichiers) and not effective.network.get("tlsTerminate"):
        noms = ", ".join([e["name"] for e in masques]
                         + [e["path"] for e in masques_fichiers])
        soucis.append(Souci("erreur", "credentials / tlsTerminate",
                            f"« {noms} » en mode mask, sans "
                            "network.tlsTerminate : le masquage ECHOUE. Le "
                            "proxy ne dechiffre pas, donc il ne peut pas "
                            "remplacer la sentinelle par la vraie valeur — "
                            "l'authentification rate, sans rien exposer."))
    # <<<

    # ------------------------- 4. un injectHosts hors de la liste des domaines
    for entree in masques + masques_fichiers:
        nom = entree.get("name") or entree.get("path", "?")
        for hote in entree.get("injectHosts", []):
            if not any(_domaine(hote, m)
                       for m in effective.network.get("allowedDomains", [])):
                soucis.append(Souci("erreur", f"injectHosts / {nom}",
                                    f"« {hote} » n'est pas joignable "
                                    "(allowedDomains). Le proxy n'injecte que "
                                    "sur les connexions que la liste admet : "
                                    "la vraie valeur n'arrivera jamais."))
            if hote.startswith("["):
                soucis.append(Souci("erreur", f"injectHosts / {nom}",
                                    f"« {hote} » est crochete. allowedDomains "
                                    "veut la forme crochetee, injectHosts "
                                    "veut l'adresse NUE : les deux listes ont "
                                    "chacune leur analyseur."))

    # ------------------------------------- 5. un joker au mauvais endroit
    for liste in ("allowedDomains", "deniedDomains"):
        for motif in effective.network.get(liste, []):
            if motif_inerte(motif):
                soucis.append(Souci("erreur", f"{liste} / {motif}",
                                    "le bac a sable n'honore que « *.exemple."
                                    "com » et « * ». Un joker ailleurs agit "
                                    "encore sur WebFetch, et sur les "
                                    "commandes sandboxees il ne fait RIEN."))

    # ------------------------------ 6. un mask qui va retomber en deny
    for entree in masques_fichiers:
        chemin = entree["path"]
        if "*" in chemin or chemin.endswith("/"):
            soucis.append(Souci("erreur", f"credentials.files / {chemin}",
                                "mask ne s'applique qu'a UN fichier. Sur un "
                                "glob ou un dossier, Claude Code retombe sur "
                                "deny : la lecture est bloquee au lieu d'etre "
                                "masquee, et l'outil qui lit ce fichier casse "
                                "au lieu de marcher."))

    # --------------------------------------------- 7. ce qui est simplement risque
    if effective.allowUnsandboxedCommands:
        soucis.append(Souci("attention", "allowUnsandboxedCommands",
                            "a true (defaut) : quand une commande echoue sous "
                            "le bac a sable, Claude peut proposer de la "
                            "rejouer dehors. Passez-le a false pour un mode "
                            "strict."))
    if not effective.failIfUnavailable:
        soucis.append(Souci("attention", "failIfUnavailable",
                            "a false (defaut) : si le bac a sable ne peut pas "
                            "demarrer — Windows natif, bubblewrap absent — "
                            "Claude Code avertit et CONTINUE sans. Vous "
                            "croirez etre protege."))
    if effective.filesystem.get("disabled"):
        ouverts = (" Y compris « " + ", ".join(proteges_ouverts) + " »."
                   if proteges_ouverts else "")
        soucis.append(Souci("attention", "filesystem.disabled",
                            "l'isolation des fichiers est coupee, chemins "
                            "proteges compris." + ouverts + " Restent le "
                            "reseau, les envVars, et les masques de fichiers "
                            "— qui ne dependent pas de cette couche."))
    if not effective.network.get("allowedDomains"):
        soucis.append(Souci("attention", "network.allowedDomains",
                            "vide : aucun domaine n'est pre-autorise, donc le "
                            "premier acces a chacun sera DEMANDE. C'est sur, "
                            "et c'est ce qui fait desactiver le bac a sable."))
    return soucis


def main() -> int:
    arguments = [a for a in sys.argv[1:] if not a.startswith("--")]
    portee = "projet"
    if "--portee" in sys.argv:
        portee = sys.argv[sys.argv.index("--portee") + 1]
    chemin = arguments[0] if arguments else "configs/atelier.json"

    config = Config.fichier(chemin, portee=portee)
    soucis = verifier(config)
    erreurs = [s for s in soucis if s.gravite == "erreur"]

    marque = "" if portee in PORTEES_PRIVILEGIEES else \
        f"   ({len(CLES_PRIVILEGIEES)} cles n'y sont pas honorees)"
    print(f"\n  {chemin}  —  portee « {portee} »{marque}\n")
    for s in soucis:
        etiquette = "ERREUR    " if s.gravite == "erreur" else "attention "
        print(f"  {etiquette} {s.ou}")
        for ligne in _plier(s.message, 66):
            print(f"             {ligne}")
    if not soucis:
        print("  Aucun probleme detecte.")
    print(f"\n  {len(erreurs)} erreur(s), "
          f"{len(soucis) - len(erreurs)} avertissement(s)\n")
    return 1 if erreurs else 0


def _plier(texte: str, largeur: int) -> list[str]:
    lignes, courante = [], ""
    for mot in texte.split():
        if len(courante) + len(mot) + 1 > largeur:
            lignes.append(courante)
            courante = mot
        else:
            courante = f"{courante} {mot}".strip()
    if courante:
        lignes.append(courante)
    return lignes


if __name__ == "__main__":
    sys.exit(main())
