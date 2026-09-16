"""Chapitre 5 — Multi-plateforme & automatisations.

    uv run python chapitres/chapitre_5_automatisations.py

Les tâches planifiées de ce chapitre sont créées par `cron.jobs.create_job` —
le vrai. Elles sont écrites dans un `HERMES_HOME` temporaire, jamais dans le
vôtre, et aucun ordonnanceur n'est démarré : on regarde ce que Hermes ÉCRIT,
pas ce qu'il exécute.

Le fil du chapitre est le suivant : un agent qui travaille sans personne
devant change la nature de tous les risques des chapitres précédents.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal.commun import ligne, titre, utf8          # noqa: E402


def main() -> None:
    utf8()
    logging.disable(logging.CRITICAL)
    os.environ["HERMES_HOME"] = tempfile.mkdtemp(prefix="hermes-cours-")

    from cron import jobs, scheduler
    from cron.blueprint_catalog import CATALOG

    jobs.ensure_dirs()

    titre(1, "UNE TACHE PLANIFIEE, TELLE QUE HERMES L'ECRIT")
    tache = jobs.create_job(
        prompt="Relance les candidatures envoyees il y a plus de 7 jours.",
        schedule="0 9 * * 1-5", name="relances-matin",
        skills=["relancer-candidat"], deliver="email")
    for cle in ("name", "schedule_display", "next_run_at", "state",
                "deliver", "skills", "enabled_toolsets"):
        ligne(cle, json.dumps(tache.get(cle), ensure_ascii=False), 22)
    print()
    print("   Remarquez « enabled_toolsets : null ». Une tache sans ensemble")
    print("   declare recoit le catalogue par defaut — celui du chapitre 4,")
    print("   a ~10 000 jetons. Une tache qui tourne toutes les 15 minutes")
    print("   paie ce catalogue 96 fois par jour, pour trois lignes de")
    print("   travail.")

    titre(2, "LE CALENDRIER EST RESOLU, PAS STOCKE EN TEXTE")
    for expression, quoi in (("0 9 * * 1-5", "chaque matin ouvre"),
                             ("*/15 * * * *", "tous les quarts d'heure"),
                             ("0 0 1 * *", "le 1er de chaque mois")):
        horaire = {"kind": "cron", "expr": expression, "display": expression}
        ligne(f"{expression:<14} {quoi}",
              str(jobs.compute_next_run(horaire)), 38)
    print()
    print("   ⚠️ `compute_next_run` prend un DICTIONNAIRE, pas la chaine cron.")
    print("   Lui passer « 0 9 * * 1-5 » directement rend None — sans lever.")
    print("   Une tache dont le prochain lancement est None ne se declenche")
    print("   jamais, et rien ne le signale : elle reste « scheduled ».")

    titre(3, "LES MODELES DE TACHES LIVRES")
    ligne("blueprints au catalogue", str(len(CATALOG)), 26)
    for entree in list(CATALOG)[:5]:
        identifiant = getattr(entree, "id", None) or getattr(entree, "key", "?")
        titre_ = (getattr(entree, "title", None)
                  or getattr(entree, "name", None)
                  or getattr(entree, "description", ""))
        print(f"      {str(identifiant)[:24]:<26}{str(titre_)[:46]}")
    print()
    print("   Ce sont des automatisations pretes a remplir. Leur interet")
    print("   n'est pas de gagner du temps : c'est que les creneaux a")
    print("   remplir sont NOMMES, donc qu'on ne laisse pas un champ vide")
    print("   par distraction — comme « enabled_toolsets ».")

    titre(4, "UN AGENT QUI TOURNE SANS PERSONNE DEVANT")
    print("   Le cas particulier de cron n'est pas l'horaire : c'est que")
    print("   l'agent s'y execute en AUTO-APPROBATION. Il n'y a personne")
    print("   pour repondre « non » a une demande d'approbation.\n")
    ligne("marqueur de tache silencieuse", repr(scheduler.SILENT_MARKER), 32)
    ligne("exception dediee", scheduler.CronPromptInjectionBlocked.__name__, 32)
    print()
    print("   Hermes a une exception rien que pour cela. Sa docstring dit ce")
    print("   qui a ete corrige, et c'est instructif :\n")
    for ligne_ in (scheduler.CronPromptInjectionBlocked.__doc__ or "").strip().splitlines():
        print(f"      {ligne_.strip()}")

    titre(5, "CE QUE CETTE DOCSTRING RACONTE")
    print("   Au depart, le scanner d'injection tournait a la CREATION de la")
    print("   tache, sur le champ « prompt » fourni par l'utilisateur.")
    print()
    print("   Mais une tache peut charger des SKILLS a l'execution — ici,")
    print("   « relancer-candidat ». Le contenu de la skill n'etait pas")
    print("   scanne. Une skill malveillante installee depuis un depot")
    print("   public arrivait donc intacte dans un agent auto-approuve, qui")
    print("   tourne a 9 h du matin sans personne pour lire ce qu'il fait.")
    print()
    print("   La correction : scanner le prompt ASSEMBLE, skills comprises,")
    print("   au moment de construire la requete. Les trois chapitres se")
    print("   rejoignent ici — une skill (ch. 3) devient dangereuse parce")
    print("   qu'elle est chargee sans surveillance (ch. 5), et c'est le")
    print("   scanner du chapitre 6 qui l'arrete.")

    titre(6, "LES CANAUX : LE MEME AGENT, PLUSIEURS PORTES")
    from gateway import channel_directory

    fonctions = [n for n in dir(channel_directory) if not n.startswith("_")
                 and callable(getattr(channel_directory, n))]
    ligne("gateway.channel_directory", ", ".join(fonctions[:4]), 28)
    import pkgutil
    import gateway
    ligne("modules du gateway",
          str(len(list(pkgutil.iter_modules(gateway.__path__)))), 28)
    print()
    print("   Le gateway est un processus SEPARE de l'agent. C'est ce qui")
    print("   permet a Discord, Slack ou un courriel d'atteindre le meme")
    print("   agent, avec la meme memoire et les memes skills — et c'est")
    print("   aussi ce qui fait que le redemarrer ne coupe pas les canaux.")
    print()
    print("   La consequence a retenir : votre agent devient joignable")
    print("   depuis l'exterieur. Tout ce qui arrive par un canal est une")
    print("   entree non fiable, au meme titre qu'une page web.")

    titre(7, "CE QUE CE CHAPITRE NE PROUVE PAS")
    for limite in (
            "aucun ordonnanceur n'est demarre : les taches sont ecrites,",
            "  pas executees — les executer demande un modele ;",
            "aucun canal n'est branche : Discord, Slack et les autres",
            "  demandent des jetons et un service joignable ;",
            "la livraison (`deliver`) et son registre ne sont pas testes."):
        print(f"   · {limite}" if not limite.startswith("  ") else f"   {limite}")
    print()
    print(f"   Les taches de ce chapitre sont dans {os.environ['HERMES_HOME']}")
    print("   et disparaitront avec le dossier temporaire.")

    print("\n   Au chapitre suivant : les gardes, et ce qu'elles arretent.\n")


if __name__ == "__main__":
    main()
