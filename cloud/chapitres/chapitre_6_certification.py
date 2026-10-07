"""Chapitre 6 — Preparer la certification.

    uv run python chapitres/chapitre_6_certification.py

La mesure du chapitre tient en un tableau : la MEME question, les MEMES
options, et une bonne reponse qui change avec le mot qui tranche.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                       # noqa: E402
from jobportal import examen, questions             # noqa: E402

CRITERES = ["le plus economique", "le plus disponible", "le plus securise",
            "le moins d'administration"]


def main() -> None:
    console.utf8()
    _le_mot_qui_tranche()
    _une_question_quatre_reponses()
    _le_piege_du_moins_cher()
    _lenonce_sans_mot()
    _un_examen_blanc()
    _reviser()


def _le_mot_qui_tranche() -> None:
    print("1. L'EXAMEN NE TESTE PAS VOTRE MEMOIRE\n")
    print("   Il teste votre jugement. Les questions sont des mises en")
    print("   situation ou PLUSIEURS reponses fonctionnent, et une seule")
    print("   optimise le critere demande.\n")
    print("   Ce projet ne stocke aucune bonne reponse. Chaque option est")
    print("   decrite sur quatre axes, et la bonne reponse est CALCULEE :\n")
    for critere, (axe, sens) in sorted(examen.CRITERES.items()):
        verbe = "minimise" if sens < 0 else "maximise"
        print(f"      « {critere:<26} »  →  {verbe} « {axe} »")
    print("\n   Consequence directe, et c'est toute la lecon du chapitre :")
    print("   changer le mot qui tranche change la bonne reponse, sans")
    print("   qu'une virgule de l'enonce ou des options n'ait bouge.")


def _une_question_quatre_reponses() -> None:
    print("\n\n2. LA MESURE QUI TRANCHE : UNE QUESTION, QUATRE VERDICTS\n")
    print(f"   {'QUESTION':<26}" + "".join(
        f"{c.split()[-1][:9]:>11}" for c in CRITERES))
    for cle, question in questions.BANQUE.items():
        ligne = f"   {cle:<26}"
        for critere in CRITERES:
            ligne += f"{question.bonne_reponse(critere).lettre:>11}"
        print(ligne)

    distinctes = {
        cle: len({question.bonne_reponse(c).lettre for c in CRITERES})
        for cle, question in questions.BANQUE.items()}
    print(f"\n   Nombre de reponses DIFFERENTES selon le critere :")
    for cle, combien in sorted(distinctes.items(), key=lambda p: -p[1]):
        print(f"      {cle:<28} {combien} sur {len(CRITERES)}")

    cle = max(distinctes, key=lambda c: distinctes[c])
    question = questions.BANQUE[cle]
    print(f"\n   En detail, « {cle} » :\n")
    print(f"      {question.situation}\n")
    for option in question.options:
        print(f"      {option.lettre}. {option.texte}")
        print(f"         cout {option.cout:g} · disponibilite "
              f"{option.disponibilite:g} · securite {option.securite:g} · "
              f"administration {option.administration:g}")
    print()
    for critere in CRITERES:
        bonne = question.bonne_reponse(critere)
        print(f"      {critere:<28} → {bonne.lettre}  ({bonne.pourquoi})")
    print("\n   ⚠️ C'est exactement ce que font les distracteurs d'un")
    print("   examen : ils sont tous DEFENDABLES. Celui qui lit vite")
    print("   reconnait une bonne pratique et la coche ; celui qui lit le")
    print("   mot qui tranche coche celle qui repond a la question posee.")


def _le_piege_du_moins_cher() -> None:
    print("\n\n3. LE PIEGE LE PLUS INSTRUCTIF : « LE MOINS CHER »\n")
    question = questions.BANQUE["acces-au-bucket"]
    print(f"      {question.situation}\n")
    economique = question.bonne_reponse("le plus economique")
    securise = question.bonne_reponse("le plus securise")
    print(f"      le plus economique → {economique.lettre}. {economique.texte}")
    print(f"      le plus securise   → {securise.lettre}. {securise.texte}\n")
    print("   La reponse la MOINS CHERE est de rendre le stockage public.")
    print("   Elle est exacte sur le critere du cout, et catastrophique.")
    print("\n   ⚠️ Un vrai examen ne poserait jamais cette question avec")
    print("   « le moins cher » : la securite n'y est pas un critere parmi")
    print("   d'autres, c'est un PREREQUIS. Quand l'enonce parle d'acces,")
    print("   de donnees personnelles ou de cles, le moindre privilege")
    print("   l'emporte, quel que soit le mot qui tranche.")
    print("\n   Le projet le montre justement parce que le moteur, lui,")
    print("   applique le critere sans juger. C'est la limite d'un modele")
    print("   a quatre axes — et elle est utile a voir.")


def _lenonce_sans_mot() -> None:
    print("\n\n4. UN ENONCE SANS MOT QUI TRANCHE N'A PAS DE REPONSE\n")
    enonces = [
        "Quelle solution est la plus economique pour ce profil de charge ?",
        "Quelle architecture est la plus resiliente a la perte d'une zone ?",
        "Quelle option demande le moins d'administration a l'equipe ?",
        "Quelle configuration est la plus securisee ?",
        "Quelle solution recommandez-vous ?",
        "Quelle solution est la plus economique ET la plus disponible ?",
    ]
    for enonce in enonces:
        try:
            critere = examen.detecter(enonce)
            print(f"   ✓ {enonce}")
            print(f"       → {critere}")
        except examen.ErreurExamen as erreur:
            print(f"   ✗ {enonce}")
            print(f"       → {erreur}")
    print("\n   Les deux dernieres lignes sont les deux erreurs de lecture")
    print("   classiques : l'enonce ou l'on n'a pas vu le mot, et celui ou")
    print("   l'on a cru en voir deux. Dans les deux cas, la reponse est de")
    print("   RELIRE — pas de deviner.")


def _un_examen_blanc() -> None:
    print("\n\n5. UN EXAMEN BLANC, ET CE QU'IL REND VRAIMENT\n")
    # Les reponses d'un candidat imaginaire, avec le temps passe.
    passage = [
        ("heberger-une-api", "le plus economique", "B", 55),
        ("stocker-des-cv", "le moins d'administration", "B", 40),
        ("base-de-donnees", "le moins d'administration", "B", 62),
        ("acces-au-bucket", "le plus securise", "B", 30),
        ("exposer-la-base", "le plus securise", "B", 35),
        ("environnement-de-test", "le plus economique", "B", 48),
        ("analyse-des-candidatures", "le plus disponible", "C", 90),
        ("repartition-des-zones", "le plus disponible", "B", 410),
    ]
    copie = examen.Copie(
        [examen.Reponse(questions.BANQUE[cle], critere, choisie, secondes)
         for cle, critere, choisie, secondes in passage],
        minutes_autorisees=20)

    print(f"   Note                 : {copie.note * 100:.0f} %")
    print(f"   Temps utilise        : {copie.secondes_utilisees / 60:.1f} min "
          f"sur {copie.minutes_autorisees:.0f} min autorisees")
    print(f"   Budget par question  : {copie.secondes_par_question:.0f} s")
    print(f"   Dans les temps       : "
          f"{'oui' if copie.dans_les_temps else '⚠️ NON'}\n")

    print("   Par domaine :\n")
    for domaine, (justes, total) in copie.par_domaine().items():
        part = justes / total * 100
        marque = "  ⚠️ a revoir" if part < 70 else ""
        print(f"      {domaine:<24} {justes}/{total}  {part:>5.0f} %{marque}")

    chronophages = copie.chronophages()
    print(f"\n   Questions qui ont pris plus du double du budget : "
          f"{len(chronophages)}")
    for reponse in chronophages:
        print(f"      [{reponse.question.domaine}] {reponse.secondes:.0f} s "
              f"— {'juste' if reponse.juste else 'et fausse'}")

    print("\n   ⚠️ La derniere ligne est le vrai enseignement d'un examen")
    print("   blanc. Sept minutes sur UNE question, pour la rater : c'est")
    print("   le temps de trois autres questions que le candidat n'aura")
    print("   pas le temps de lire. Marquer et revenir vaut mieux que")
    print("   s'acharner — et c'est une competence qui se travaille, pas")
    print("   une question de connaissances.")


def _reviser() -> None:
    print("\n\n6. REVISER PAR LA PRATIQUE, PAS PAR LA RELECTURE\n")
    question = questions.BANQUE["base-de-donnees"]
    critere = "le plus disponible"
    copie = examen.Copie([examen.Reponse(question, critere, "B", 45)])
    print("   La correction utile n'est pas « la bonne reponse etait C ».")
    print("   C'est celle-ci :\n")
    for ligne in examen.corriger(copie):
        print(f"      {ligne}")
    print("\n   Pourquoi la bonne est bonne, ET pourquoi chaque autre est")
    print("   mauvaise SUR CE CRITERE. C'est ce second point qui construit")
    print("   le jugement : au prochain enonce, on reconnaitra la forme,")
    print("   pas la reponse.")
    print("\n   Le plan des deux dernieres semaines, qui decoule de ce que")
    print("   la section 5 mesure :")
    print("      • reviser le DOMAINE le plus faible, pas la note globale.")
    print("        Une note de 72 % faite de « 95 % partout sauf 20 % en")
    print("        reseau » et une note de 72 % uniforme demandent deux")
    print("        revisions opposees ;")
    print("      • chronometrer, et regarder les questions chronophages :")
    print("        elles disent ou le jugement n'est pas encore automatique ;")
    print("      • relire UNIQUEMENT les questions ratees, jamais le cours")
    print("        en entier. Relire donne une illusion de maitrise ; se")
    print("        tromper cree un souvenir.")
    print("\n   ⚠️ Et le fond vient des cinq chapitres precedents : les")
    print("   modeles de service, le reseau et l'IAM, les donnees et le")
    print("   FinOps sont exactement les domaines que l'examen recoupe. Ce")
    print("   chapitre n'apprend pas le cloud — il apprend a repondre.")
    print()


if __name__ == "__main__":
    main()
