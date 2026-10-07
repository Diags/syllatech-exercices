"""Le lecteur de Dockerfile, et le contexte de construction.

La moitie de ces tests verifie qu'une syntaxe non geree s'arrete ici, avec
un numero de ligne. Un lecteur qui accepte tout ne prouve rien.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from jobportal import contexte
from jobportal.dockerfile import (ErreurDockerfile, analyser,
                                  analyser_fichier, arguments_exec,
                                  forme_exec, sources_et_destination,
                                  tag_de_base)

RACINE = Path(__file__).resolve().parent.parent
CONTEXTE = RACINE / "contexte"


def test_les_etapes_et_leurs_noms():
    fichier = analyser_fichier(CONTEXTE / "Dockerfile")

    assert fichier.multi_etages
    assert [e.designation for e in fichier.etapes] == ["build", "1"]
    assert fichier.etape("build") is not None


def test_la_continuation_de_ligne_recolle_linstruction():
    fichier = analyser("""
    FROM alpine:3.20
    RUN apt-get update \\
        && apt-get install -y curl \\
        && rm -rf /var/lib/apt/lists/*
    """)

    commande = fichier.finale.cherchees("RUN")[0].arguments
    assert commande == ("apt-get update && apt-get install -y curl "
                        "&& rm -rf /var/lib/apt/lists/*")


def test_un_commentaire_dans_une_continuation_est_ignore():
    fichier = analyser("""
    FROM alpine:3.20
    RUN echo un \\
    # un commentaire au milieu
        && echo deux
    """)

    assert fichier.finale.cherchees("RUN")[0].arguments == "echo un && echo deux"


def test_seul_ARG_est_permis_avant_le_premier_FROM():
    fichier = analyser('ARG VERSION=21\nFROM eclipse-temurin:${VERSION}-jre')
    assert len(fichier.arguments_de_tete) == 1

    with pytest.raises(ErreurDockerfile, match="avant le premier"):
        analyser('RUN echo bonjour\nFROM alpine:3.20')


def test_les_formes_exec_et_shell_se_distinguent():
    fichier = analyser("""
    FROM alpine:3.20
    ENTRYPOINT ["java", "-jar", "app.jar"]
    """)
    exec_ = fichier.finale.cherchees("ENTRYPOINT")[0]

    assert forme_exec(exec_)
    assert arguments_exec(exec_) == ["java", "-jar", "app.jar"]

    shell = analyser("FROM alpine:3.20\nCMD java -jar app.jar")
    assert not forme_exec(shell.finale.cherchees("CMD")[0])


def test_les_drapeaux_dun_COPY_sont_lus():
    fichier = analyser("""
    FROM alpine:3.20 AS build
    FROM alpine:3.20
    COPY --from=build --chown=1001:1001 /app/x.jar /app/x.jar
    """)
    copie = fichier.finale.cherchees("COPY")[0]

    assert copie.drapeaux == {"from": "build", "chown": "1001:1001"}
    assert sources_et_destination(copie) == (["/app/x.jar"], "/app/x.jar")


def test_le_dernier_USER_gagne_et_root_est_le_defaut():
    avec = analyser("FROM alpine:3.20\nUSER nobody\nUSER appuser")
    sans = analyser("FROM alpine:3.20\nRUN echo bonjour")

    assert avec.finale.utilisateur == "appuser"
    assert sans.finale.utilisateur == "root"


def test_un_FROM_sans_tag_vaut_latest():
    """⚠️ La ligne qu'un audit releve en premier."""
    fichier = analyser("FROM openjdk\nFROM eclipse-temurin:21-jre")

    assert tag_de_base(fichier.etapes[0]) == "latest"
    assert tag_de_base(fichier.etapes[1]) == "21-jre"


@pytest.mark.parametrize("source, motif", [
    ("RUN echo x", "avant le premier"),
    ("FROM", "sans argument"),
    ("FROM alpine:3.20\nMACHIN x", "instruction inconnue"),
    ("FROM alpine:3.20\nONBUILD RUN x", "ONBUILD"),
    ("FROM alpine:3.20\nRUN --mount=type=cache echo x", "BuildKit"),
    ("# syntax=docker/dockerfile:1\nFROM alpine:3.20", "analyseur"),
    ("FROM alpine:3.20\nCOPY <<EOF /x", "heredoc"),
    ("FROM alpine:3.20\nRUN", "sans argument"),
])
def test_ce_qui_nest_pas_gere_leve(source: str, motif: str):
    with pytest.raises(ErreurDockerfile, match=motif):
        analyser(source)


# ── le contexte ──────────────────────────────────────────────────────────

def test_le_dockerignore_ecarte_et_le_bang_rattrape():
    """⚠️ Le DERNIER motif qui correspond decide."""
    avec = contexte.charger(CONTEXTE)

    assert ".env" in avec.exclus
    assert ".env.exemple" in avec.fichiers          # rattrape par « ! »
    assert "target/jobportal.jar" in avec.exclus
    assert ".git/objects/pack/pack-8f3a9c.pack" in avec.exclus


def test_le_contexte_sans_dockerignore_emporte_tout():
    avec = contexte.charger(CONTEXTE)
    sans = contexte.charger(CONTEXTE, appliquer_dockerignore=False)

    assert len(sans.fichiers) > len(avec.fichiers)
    assert sans.taille > 200_000_000        # le .git et le target
    assert avec.taille < 100_000


def test_lempreinte_dun_COPY_change_avec_le_contenu():
    """⚠️ C'est cette empreinte qui fait, ou defait, le cache."""
    base = contexte.charger(CONTEXTE)
    lu = (CONTEXTE / "README.md").read_bytes()
    modifie = contexte.modifier(base, "README.md", lu + b"\n")

    assert base.empreinte_de(["pom.xml"]) == modifie.empreinte_de(["pom.xml"])
    assert base.empreinte_de(["src"]) == modifie.empreinte_de(["src"])
    assert base.empreinte_de(["."]) != modifie.empreinte_de(["."])


def test_un_fichier_ignore_ne_change_pas_lempreinte():
    base = contexte.charger(CONTEXTE)
    modifie = contexte.modifier(base, "target/jobportal.jar", b"autre chose")

    assert base.empreinte_de(["."]) == modifie.empreinte_de(["."])


def test_letoile_ne_traverse_pas_un_slash():
    """La regle de Go, pas celle du shell."""
    motifs = ["*/cible"]

    assert contexte._ignore("a/cible", motifs)
    assert not contexte._ignore("a/b/cible", motifs)
    assert contexte._ignore("a/b/cible", ["**/cible"])
