"""Chapitre 5 — Scores et datasets : la seule mesure qui decide.

    uv run python chapitres/chapitre_5_evaluation.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console, donnees                          # noqa: E402
from jobportal.assistant import repondre                        # noqa: E402
from jobportal.collecteur import brancher                       # noqa: E402
from jobportal.evaluation import (JEU_METIER, Registre, executer,  # noqa: E402
                                  score_juge, score_regle,
                                  score_utilisateur)


def assistant_v1(question: str) -> str:
    """La premiere version : elle rend les offres, sans plus."""
    return " ; ".join(donnees.query(donnees.mot_cle(question))) or "Rien."


def assistant_v2(question: str) -> str:
    """La seconde : elle dit quand elle ne trouve rien."""
    offres = donnees.query(donnees.mot_cle(question))
    if not offres:
        return "Aucune offre ne correspond a cette recherche."
    return f"{len(offres)} offre(s) : " + " ; ".join(offres)


def main() -> None:
    console.utf8()
    client, collecteur = brancher()
    registre = Registre()

    print("1. TROIS SORTES DE SCORE, ET ELLES NE SE REMPLACENT PAS\n")
    reponse = assistant_v2("Quelles offres DevOps ?")
    for nom, valeur, quoi in (
            ("utilisateur", score_utilisateur(True), "un avis humain, rare et fiable"),
            ("regle", score_regle(reponse, "DevOps"), "deterministe, gratuit, limite"),
            ("juge", score_juge(reponse, "Quelles offres DevOps ?"),
             "un modele : il coute et il VARIE")):
        print(f"   {nom:<14}{valeur:<6}{quoi}")

    print("\n   ⚠️ Le juge est ici SIMULE par des heuristiques. Un vrai juge")
    print("   est un modele, qu'il faut CALIBRER contre des notes humaines")
    print("   avant de lui faire confiance. Un juge non calibre donne un")
    print("   chiffre rassurant et faux — et un chiffre faux est pire que")
    print("   pas de chiffre.")

    print("\n2. LE SCORE UTILISATEUR : sa limite n'est pas la qualite\n")
    print('   get_client().create_score(trace_id=…, name="feedback",')
    print('                             value=1, data_type="BOOLEAN")')
    print("\n   On en obtient sur 1 a 3 % des reponses, et ce sont rarement")
    print("   les cas moyens : on note ce qui a tres bien ou tres mal marche.")
    print("   Un taux de satisfaction calcule la-dessus mesure les extremes.")

    print("\n3. LE DATASET : la non-regression\n")
    for cas in JEU_METIER:
        print(f"   {cas.entree:<44}doit contenir « {cas.attendu} »")

    print("\n4. DEUX VERSIONS, LE MEME JEU DE CAS\n")
    v1 = executer("v1", assistant_v1)
    v2 = executer("v2", assistant_v2)
    for execution in (v1, v2):
        detail = " ".join("ok" if s else "KO" for s in execution.scores)
        print(f"   {execution.nom}   {execution.moyenne:.0%}   {detail}")
    print(f"\n   v1 → v2 : {v1.moyenne:.0%} → {v2.moyenne:.0%}")
    print("\n   Le cas qui change est le dernier : « soudure sous-marine ».")
    print("   v1 rend « Rien. », v2 rend une phrase qui contient « Aucune ».")
    print("   C'est exactement ce qu'un dataset attrape et qu'une relecture")
    print("   manque : un cas limite, sur cinq.")

    print("\n5. CE QU'ON COMPARE N'EST PAS UNE REPONSE\n")
    print("   C'est une MOYENNE, a la precedente. Une reponse peut empirer")
    print("   sans que la moyenne bouge, et c'est la moyenne qui decide si")
    print("   l'on deploie. Le seuil se pose une fois — « on ne descend pas")
    print("   sous 0,8 » — et il tient lieu de test de non-regression.")

    print("\n6. LA BOUCLE COMPLETE\n")
    collecteur.vider()
    for cas in JEU_METIER[:3]:
        texte = repondre(cas.entree, "diaguily", "s-eval")
        registre.create_score(trace_id=cas.entree, name="regle",
                              value=score_regle(texte, cas.attendu))
    client.flush()
    print(f"   {len(collecteur.racines)} traces, {len(registre.scores)} scores")
    print(f"   moyenne « regle » : {registre.moyenne('regle'):.0%}")
    print("\n   Trace, score, dataset : les trois se rejoignent sur le")
    print("   trace_id. C'est ce qui permet, devant une moyenne qui baisse,")
    print("   d'ouvrir les traces qui ont mal note — et non de deviner.")


if __name__ == "__main__":
    main()
