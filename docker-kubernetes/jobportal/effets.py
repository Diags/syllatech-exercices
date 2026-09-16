"""Ce que coute chaque commande — des ENTREES declarees, pas des mesures.

⚠️ LISEZ CE PARAGRAPHE AVANT DE CITER UN CHIFFRE DE CE PROJET.

Aucune image n'est construite ici : il n'y a ni demon Docker, ni reseau. Les
durees et les tailles ci-dessous sont donc des **entrees du modele**,
relevees une fois sur une construction reelle du portail de l'emploi
(Maven 3.9 / Temurin 21, liaison fibre, cache de depot vide) et notees a la
main. Elles ne sont pas remesurees a chaque execution, et elles varieront
chez vous.

Ce que le projet MESURE, en revanche, est ce qu'il calcule a partir de ces
entrees : **quelles couches sont reconstruites**, et pourquoi. C'est
l'algorithme du cache, et lui est exact — c'est celui de Docker.

Autrement dit : si vous changez un chiffre ci-dessous, les secondes
affichees par les chapitres changent ; le NOMBRE de couches reconstruites,
lui, ne bouge pas d'un pouce. C'est ce nombre qui enseigne quelque chose.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Effet:
    """Ce qu'une commande coute, et ce qu'elle laisse derriere elle."""

    secondes: float
    produit: dict[str, int] = field(default_factory=dict)   # chemin -> octets
    efface: tuple[str, ...] = ()
    commentaire: str = ""


# Le cout d'un `FROM` : le telechargement de l'image de base.
BASES: dict[str, Effet] = {
    "maven:3.9-eclipse-temurin-21": Effet(
        secondes=31.0,
        produit={"/usr/share/maven": 11_000_000,
                 "/opt/java/openjdk": 331_000_000,
                 "/usr/bin": 8_000_000},
        commentaire="JDK complet + Maven : une chaine de compilation entiere"),
    "eclipse-temurin:21-jre": Effet(
        secondes=9.0,
        produit={"/opt/java/openjdk": 178_000_000, "/usr/bin": 8_000_000},
        commentaire="JRE seul : ni javac, ni Maven, ni sources"),
    "eclipse-temurin:21-jre-alpine": Effet(
        secondes=5.0,
        produit={"/opt/java/openjdk": 178_000_000, "/usr/bin": 3_000_000},
        commentaire="la meme, sur Alpine — ⚠️ musl, pas glibc"),
    "openjdk": Effet(
        secondes=34.0,
        produit={"/usr/local/openjdk": 470_000_000, "/usr/bin": 8_000_000},
        commentaire="⚠️ sans tag : c'est « latest », et l'image bouge"),
}

# Le cout d'un `RUN`, par texte EXACT de commande.
#
# ⚠️ La cle est le texte, pas l'intention. C'est exactement ainsi que
# Docker raisonne pour son cache : deux commandes equivalentes ecrites
# differemment sont deux couches differentes.
COMMANDES: dict[str, Effet] = {
    "mvn dependency:go-offline -B": Effet(
        secondes=74.0,
        produit={"/root/.m2/repository": 212_000_000},
        commentaire="le telechargement qu'on veut garder en cache"),
    "mvn package -DskipTests -B": Effet(
        secondes=38.0,
        produit={"/app/target/classes": 2_100_000,
                 "/app/target/jobportal.jar": 47_000_000,
                 "/app/target/maven-status": 90_000},
        commentaire="la compilation : elle depend des sources, donc elle rejoue"),
    "rm -rf /root/.m2": Effet(
        secondes=1.0, efface=("/root/.m2",),
        commentaire="⚠️ n'enleve RIEN de l'image — voir image.py"),
    "rm /app/.env": Effet(
        secondes=0.1, efface=("/app/.env",),
        commentaire="⚠️ le secret reste dans la couche precedente"),
    "useradd -r -u 1001 appuser": Effet(
        secondes=0.4, produit={"/etc/passwd": 2_400},
        commentaire="l'utilisateur non-root de l'image finale"),
    "apt-get update && apt-get install -y curl": Effet(
        secondes=22.0,
        produit={"/var/lib/apt/lists": 41_000_000, "/usr/bin/curl": 260_000},
        commentaire="⚠️ les listes apt pesent plus que curl"),
    "apt-get update && apt-get install -y curl "
    "&& rm -rf /var/lib/apt/lists/*": Effet(
        secondes=22.0, produit={"/usr/bin/curl": 260_000},
        commentaire="la meme, dans UNE couche : les listes n'existent jamais"),
}

# Ce qu'on applique a une commande qu'on ne connait pas. Le projet le dit
# plutot que d'inventer un chiffre credible.
INCONNUE = Effet(secondes=0.5, commentaire="commande hors du catalogue")


def pour_la_base(image: str) -> Effet:
    return BASES.get(image, Effet(
        secondes=10.0, produit={"/": 100_000_000},
        commentaire="image de base hors du catalogue"))


def pour_la_commande(commande: str) -> Effet:
    return COMMANDES.get(commande.strip(), INCONNUE)


def connue(commande: str) -> bool:
    return commande.strip() in COMMANDES
