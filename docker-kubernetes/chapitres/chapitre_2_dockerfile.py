"""Chapitre 2 — Dockerfile : des images sur mesure.

    uv run python chapitres/chapitre_2_dockerfile.py

Deux Dockerfile construisent la MEME application. L'un reconstruit cinq
couches quand on change un caractere dans un README ; l'autre, zero. Ce
chapitre compte, ligne par ligne, ou part la difference.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                                  # noqa: E402
from jobportal import construction, contexte, dockerfile, image  # noqa: E402

RACINE = Path(__file__).resolve().parent.parent
CONTEXTE = RACINE / "contexte"

CODE = "src/main/java/fr/portail/OffreControleur.java"


def main() -> None:
    console.utf8()
    avec = contexte.charger(CONTEXTE)
    sans = contexte.charger(CONTEXTE, appliquer_dockerignore=False)

    _le_contexte(avec, sans)
    _la_cle_de_cache(avec, sans)
    _lordre_des_couches(avec, sans)
    _le_multi_etages(avec, sans)
    _ce_qui_reste(sans)


def _le_contexte(avec: contexte.Contexte, sans: contexte.Contexte) -> None:
    print("1. LE POINT DE `docker build .` N'EST PAS UN DOSSIER\n")
    print("   C'est le CONTEXTE : tout ce que le client archive et envoie")
    print("   au demon avant que la premiere instruction ne s'execute.\n")
    print(f"   Sans `.dockerignore` : {len(sans.fichiers):>2} fichiers, "
          f"{contexte.octets(sans.taille):>9}")
    print(f"   Avec `.dockerignore` : {len(avec.fichiers):>2} fichiers, "
          f"{contexte.octets(avec.taille):>9}\n")
    print("   Ce que le fichier ecarte :\n")
    for fichier in sorted(avec.exclus.values(), key=lambda f: -f.taille):
        print(f"      {fichier.chemin:<40} {contexte.octets(fichier.taille):>9}")
    print(f"\n   Les motifs, dans l'ordre ou ils sont lus : {avec.ignores}")
    print("\n   ⚠️ C'est le DERNIER motif qui correspond qui l'emporte. Ici,")
    print("   `.env` est exclu par la quatrieme ligne, puis `.env.exemple`")
    print("   est rattrape par la cinquieme — un `!` annule l'exclusion.")
    print("   Inverser les deux lignes ne garderait rien.")
    print("\n   Et le gain n'est pas que du reseau : un fichier ecarte ne")
    print("   compte pas dans l'empreinte des `COPY`. C'est la moitie")
    print("   invisible du probleme, et c'est la section suivante.")


def _la_cle_de_cache(avec: contexte.Contexte, sans: contexte.Contexte) -> None:
    print("\n\n2. LA CLE DE CACHE D'UNE COUCHE\n")
    print("   Elle est calculee a partir de trois choses :\n")
    print("      la cle de la couche PARENTE")
    print("      + le TEXTE de l'instruction")
    print("      + pour un COPY/ADD : l'EMPREINTE des fichiers copies\n")
    print("   Deux consequences, et ce sont les seules a retenir :\n")
    print("      1. une couche qui manque le cache fait manquer TOUTES")
    print("         celles qui la suivent — leur parente a change ;")
    print("      2. un `COPY` depend du CONTENU de ce qu'il copie.\n")
    print("   L'empreinte de ce que chaque `COPY` emporte :\n")
    for titre, ctx in (("avec .dockerignore", avec),
                       ("sans .dockerignore", sans)):
        print(f"      {titre}")
        for sources in (["."], ["pom.xml"], ["src"]):
            fichiers = ctx.correspondants(sources)
            print(f"         COPY {' '.join(sources):<9} → "
                  f"{ctx.empreinte_de(sources)}  "
                  f"({len(fichiers)} fichier(s), "
                  f"{contexte.octets(sum(f.taille for f in fichiers))})")
    print("\n   ⚠️ `COPY . .` emporte 4 fichiers de plus sans le")
    print("   `.dockerignore`, dont le `.git` et le `target`. Son empreinte")
    print("   change donc a chaque commit, meme quand le code n'a pas bouge.")


def _lordre_des_couches(avec: contexte.Contexte,
                        sans: contexte.Contexte) -> None:
    print("\n\n3. LA MESURE QUI TRANCHE : L'ORDRE DES COUCHES\n")
    lu = (CONTEXTE / "README.md").read_bytes()
    lu_code = (CONTEXTE / CODE).read_bytes()

    lignes = []
    for nom, base in (("Dockerfile.naif", sans), ("Dockerfile", avec)):
        fichier = dockerfile.analyser_fichier(CONTEXTE / nom)
        cache = construction.Cache()
        premier = construction.construire(fichier, base, cache)
        rien = construction.construire(fichier, base, cache)
        readme = construction.construire(
            fichier, contexte.modifier(base, "README.md", lu + b"\n"), cache)
        code = construction.construire(
            fichier, contexte.modifier(base, CODE, lu_code + b"\n"), cache)
        lignes.append((nom, premier, rien, readme, code))

    print(f"   {'':<18} {'1er build':>14} {'sans rien':>14} "
          f"{'+1 car. README':>16} {'+1 ligne de code':>18}")
    for nom, premier, rien, readme, code in lignes:
        print(f"   {nom:<18} "
              f"{_case(premier):>14} {_case(rien):>14} "
              f"{_case(readme):>16} {_case(code):>18}")
    print("\n   (« n c » = n couches reconstruites)\n")

    naif = lignes[0][3]
    bon = lignes[1][3]
    print(f"   Changer UN caractere dans le README :")
    print(f"      Dockerfile.naif  → {naif.couches_reconstruites} couches, "
          f"{naif.secondes:.1f} s")
    print(f"      Dockerfile       → {bon.couches_reconstruites} couches, "
          f"{bon.secondes:.1f} s")
    print("\n   Le README n'a aucune influence sur le binaire produit. Il")
    print("   coute pourtant, dans la version naive, le retelechargement")
    print("   complet des dependances Maven — parce que `COPY . .` est")
    print("   place AVANT le `RUN mvn dependency:go-offline`.\n")
    print("   Le detail du build naif apres cette modification :\n")
    for ligne in construction.rendre(naif):
        print(f"   {ligne}")
    print("\n   Et le meme, dans la version ordonnee :\n")
    for ligne in construction.rendre(bon):
        print(f"   {ligne}")
    print("\n   ⚠️ La regle tient en une phrase : du plus STABLE au plus")
    print("   VOLATIL. La liste des dependances change une fois par mois,")
    print("   le code dix fois par jour — donc `COPY pom.xml` d'abord, le")
    print("   telechargement ensuite, `COPY src` en dernier.")
    code_naif, code_bon = lignes[0][4], lignes[1][4]
    print(f"\n   Et quand le code change VRAIMENT, l'ecart reste :")
    print(f"      Dockerfile.naif  → {code_naif.couches_reconstruites} couches, "
          f"{code_naif.secondes:.1f} s")
    print(f"      Dockerfile       → {code_bon.couches_reconstruites} couches, "
          f"{code_bon.secondes:.1f} s")
    print("   Le telechargement des dependances, lui, n'est pas rejoue.")


def _case(resultat: construction.Construction) -> str:
    return f"{resultat.couches_reconstruites} c / {resultat.secondes:.0f}s"


def _le_multi_etages(avec: contexte.Contexte, sans: contexte.Contexte) -> None:
    print("\n\n4. LE MULTI-ETAGES : CE QUI NE MONTE PAS DANS L'IMAGE\n")
    bon = dockerfile.analyser_fichier(CONTEXTE / "Dockerfile")
    naif = dockerfile.analyser_fichier(CONTEXTE / "Dockerfile.naif")
    print(f"   Dockerfile       {len(bon.etapes)} etapes  "
          f"{[e.designation for e in bon.etapes]}")
    print(f"   Dockerfile.naif  {len(naif.etapes)} etape   "
          f"{[e.designation for e in naif.etapes]}\n")

    resultats = {}
    for nom, fichier, base in (("Dockerfile", bon, avec),
                               ("Dockerfile.naif", naif, sans)):
        resultats[nom] = construction.construire(
            fichier, base, construction.Cache(), nom)

    print("   Le contenu de chaque image finale :\n")
    for nom, resultat in resultats.items():
        print(f"      {nom}")
        for chemin, fichier in sorted(resultat.image.fichiers().items()):
            print(f"         {chemin:<46} {image.octets(fichier.taille):>9}")
        print(f"         {'':<46} {'─' * 9}")
        print(f"         {'TOTAL TRANSFERE':<46} "
              f"{image.octets(resultat.image.taille):>9}\n")

    bonne = resultats["Dockerfile"].image
    naive = resultats["Dockerfile.naif"].image
    facteur = naive.taille / bonne.taille
    print(f"   {image.octets(naive.taille)} contre "
          f"{image.octets(bonne.taille)} — un facteur {facteur:.1f}.\n")
    print("   Ce qui n'est PAS dans l'image finale ordonnee : Maven, le")
    print("   JDK complet, le depot `.m2`, les sources, les tests, le")
    print("   `.git`, le `.env`. Non pas parce qu'ils ont ete effaces —")
    print("   on a vu au chapitre 1 que cela ne sert a rien — mais parce")
    print("   qu'ils n'ont jamais ete poses dans un calque de CETTE image.")
    print("\n   L'etage de construction, lui, a bien telecharge ses 212 Mo")
    print("   de dependances. Il reste dans le cache du constructeur, ou il")
    print("   sert au build suivant, et ne part sur aucun registre.")
    print("\n   ⚠️ Et la surface d'attaque suit la taille : pas de")
    print("   compilateur dans l'image finale, donc pas de compilateur")
    print("   disponible a qui parvient a executer du code dedans.")


def _ce_qui_reste(sans: contexte.Contexte) -> None:
    print("\n\n5. LES SIX DEFAUTS DU DOCKERFILE NAIF, ET LEUR VERDICT\n")
    naif = dockerfile.analyser_fichier(CONTEXTE / "Dockerfile.naif")
    bon = dockerfile.analyser_fichier(CONTEXTE / "Dockerfile")
    resultat = construction.construire(naif, sans, construction.Cache())

    bonne = construction.construire(
        bon, contexte.charger(CONTEXTE), construction.Cache())
    controles = [
        ("plusieurs etages de construction",
         bon.multi_etages, naif.multi_etages),
        ("les dependances copiees avant les sources",
         _dependances_avant_les_sources(bon),
         _dependances_avant_les_sources(naif)),
        ("aucun secret dans un calque",
         not bonne.image.fouiller("/app/.env"),
         not resultat.image.fouiller("/app/.env")),
        ("aucun poids mort (`rm` inutile)",
         bonne.image.poids_mort == 0, resultat.image.poids_mort == 0),
        ("un USER non-root",
         bon.finale.utilisateur != "root", naif.finale.utilisateur != "root"),
        ("une commande de demarrage en forme exec",
         dockerfile.forme_exec(bon.finale.cherchees("ENTRYPOINT")[0]),
         dockerfile.forme_exec(naif.finale.cherchees("CMD")[0])),
    ]
    print(f"   {'CONTROLE':<44} {'Dockerfile':>12} {'naif':>6}")
    for libelle, bien, mal in controles:
        print(f"   {libelle:<44} {'oui' if bien else 'NON':>12} "
              f"{'oui' if mal else 'NON':>6}")
    ecarts = sum(1 for _, bien, mal in controles if bien != mal)
    print(f"\n   {len(controles)} controles, {ecarts} ecarts — et le fichier")
    print("   naif construit pourtant une image qui fonctionne. C'est ce")
    print("   qui rend ces defauts durables : rien n'echoue, rien")
    print("   n'avertit, et la facture arrive sous forme de temps de build,")
    print("   de bande passante et de surface d'attaque.")
    print("\n   ⚠️ `contexte/Dockerfile.naif` est une piece a conviction :")
    print("   `tests/test_a_corriger.py` verifie que ces six defauts sont")
    print("   toujours la. Ne le reparez pas.")
    print()


def _dependances_avant_les_sources(fichier: dockerfile.Dockerfile) -> bool:
    """Le motif : un COPY cible, puis un RUN, puis le COPY des sources."""
    for etape in fichier.etapes:
        copies = [i for i in etape.instructions if i.mot == "COPY"]
        runs = [i for i in etape.instructions if i.mot == "RUN"]
        if not copies or not runs:
            continue
        premier = copies[0]
        if premier.arguments.strip().startswith(". "):
            return False
        if any(run.ligne > premier.ligne for run in runs) and len(copies) > 1:
            return True
    return False


if __name__ == "__main__":
    main()
