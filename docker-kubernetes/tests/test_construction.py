"""Le cache de couches, et ce qu'une image transporte.

Le test central est `test_le_readme_ne_coute_rien_au_bon_dockerfile` : il
fige la mesure que le chapitre 2 imprime.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from jobportal import construction, contexte, dockerfile

RACINE = Path(__file__).resolve().parent.parent
CONTEXTE = RACINE / "contexte"
CODE = "src/main/java/fr/portail/OffreControleur.java"


@pytest.fixture
def avec() -> contexte.Contexte:
    return contexte.charger(CONTEXTE)


@pytest.fixture
def sans() -> contexte.Contexte:
    return contexte.charger(CONTEXTE, appliquer_dockerignore=False)


def _construire(nom: str, ctx: contexte.Contexte,
                cache: construction.Cache | None = None):
    return construction.construire(
        dockerfile.analyser_fichier(CONTEXTE / nom), ctx,
        cache if cache is not None else construction.Cache())


def test_le_premier_build_ne_reutilise_rien(avec):
    resultat = _construire("Dockerfile", avec)

    assert resultat.couches_reutilisees == 0
    assert resultat.couches_reconstruites == 8
    assert resultat.secondes > 100


def test_le_second_build_ne_reconstruit_rien(avec):
    cache = construction.Cache()
    _construire("Dockerfile", avec, cache)
    second = _construire("Dockerfile", avec, cache)

    assert second.couches_reconstruites == 0
    assert second.secondes == 0.0


def test_le_readme_ne_coute_rien_au_bon_dockerfile(avec, sans):
    """⚠️ LA MESURE DU CHAPITRE 2 : 0 couche contre 5.

    Le README n'a aucune influence sur le binaire produit. Dans la version
    naive, il coute pourtant le retelechargement complet des dependances.
    """
    lu = (CONTEXTE / "README.md").read_bytes()

    resultats = {}
    for nom, base in (("Dockerfile", avec), ("Dockerfile.naif", sans)):
        cache = construction.Cache()
        _construire(nom, base, cache)
        modifie = contexte.modifier(base, "README.md", lu + b"\n")
        resultats[nom] = construction.construire(
            dockerfile.analyser_fichier(CONTEXTE / nom), modifie, cache)

    assert resultats["Dockerfile"].couches_reconstruites == 0
    assert resultats["Dockerfile"].secondes == 0.0
    assert resultats["Dockerfile.naif"].couches_reconstruites == 5
    assert resultats["Dockerfile.naif"].secondes > 100


def test_une_modification_du_code_ne_rejoue_pas_le_telechargement(avec):
    cache = construction.Cache()
    _construire("Dockerfile", avec, cache)
    lu = (CONTEXTE / CODE).read_bytes()
    resultat = construction.construire(
        dockerfile.analyser_fichier(CONTEXTE / "Dockerfile"),
        contexte.modifier(avec, CODE, lu + b"\n"), cache)

    rejouees = [pas.instruction.texte for pas in resultat.pas
                if pas.couche is not None and not pas.en_cache]
    assert resultat.couches_reconstruites == 3
    assert not any("go-offline" in texte for texte in rejouees)
    assert any("COPY src" in texte for texte in rejouees)


def test_une_couche_manquee_fait_manquer_toutes_les_suivantes(avec):
    """Dans une etape, un echec de cache contamine toute la suite.

    ⚠️ Mais PAS l'etape d'apres : le `FROM` d'un second etage repart de
    zero, et sa couche de base reste en cache. C'est ce que montre la
    seconde assertion, et c'est une raison de plus de separer les etages.
    """
    cache = construction.Cache()
    _construire("Dockerfile", avec, cache)
    modifie = contexte.modifier(avec, "pom.xml", b"<project/>")
    resultat = construction.construire(
        dockerfile.analyser_fichier(CONTEXTE / "Dockerfile"), modifie, cache)

    build = [pas for pas in resultat.pas
             if pas.etape == "build" and pas.couche is not None]
    premier_echec = next(rang for rang, pas in enumerate(build)
                         if not pas.en_cache)
    assert all(not pas.en_cache for pas in build[premier_echec:])
    assert build[0].en_cache                      # le FROM tient

    finale = [pas for pas in resultat.pas
              if pas.etape == "1" and pas.couche is not None]
    assert finale[0].en_cache                     # le FROM du second etage


def test_le_multi_etages_laisse_maven_dehors(avec, sans):
    bonne = _construire("Dockerfile", avec).image
    naive = _construire("Dockerfile.naif", sans).image

    assert "/usr/share/maven" not in bonne.fichiers()
    assert "/usr/share/maven" in naive.fichiers()
    assert bonne.taille < naive.taille / 3


def test_un_rm_ne_fait_pas_maigrir_limage(sans):
    """⚠️ La propriete la plus contre-intuitive d'une image."""
    naive = _construire("Dockerfile.naif", sans).image

    assert naive.lire("/root/.m2/repository") is None     # invisible
    assert naive.poids_mort > 200_000_000                 # et transporte
    assert naive.taille > naive.taille_visible


def test_un_secret_efface_reste_extractible(sans):
    naive = _construire("Dockerfile.naif", sans).image

    assert naive.lire("/app/.env") is None
    trouves = naive.fouiller("/app/.env")
    assert len(trouves) == 1
    assert b"DB_PASSWORD" in (trouves[0][1].contenu or b"")


def test_le_bon_dockerfile_nembarque_aucun_secret(avec):
    bonne = _construire("Dockerfile", avec).image

    assert bonne.fouiller("/app/.env") == []
    assert bonne.poids_mort == 0


def test_le_cache_distingue_deux_textes_equivalents(avec):
    cache = construction.Cache()
    premier = analyser_en_ligne("FROM alpine:3.20\nRUN echo  bonjour")
    second = analyser_en_ligne("FROM alpine:3.20\nRUN echo bonjour")

    construction.construire(premier, avec, cache)
    resultat = construction.construire(second, avec, cache)

    assert resultat.couches_reconstruites == 1     # le FROM est reutilise


def analyser_en_ligne(source: str):
    return dockerfile.analyser(source)


def test_un_from_inconnu_est_signale_sans_faire_echouer(avec):
    resultat = construction.construire(
        analyser_en_ligne("FROM alpine:3.20\nRUN faire-quelque-chose"),
        avec, construction.Cache())

    assert resultat.inconnues == ["faire-quelque-chose"]


def test_un_copy_from_dune_etape_inexistante_leve(avec):
    with pytest.raises(construction.ErreurConstruction, match="--from"):
        construction.construire(
            analyser_en_ligne('FROM alpine:3.20\nCOPY --from=absente /a /b'),
            avec, construction.Cache())
