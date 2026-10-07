# L'image du bac a sable — la DERNIERE ligne de defense.
#
# ⚠️ Elle est auditee par `fr.portail.bac.AuditImage`, que le chapitre 4
# lance sur CE FICHIER. Retirez une ligne, relancez le chapitre : il le dit.
#
#   docker build -t runner:jobportal-script -f deploiement/Dockerfile target
#
# Le contexte de construction est `target` : l'image ne recoit QUE les
# classes compilees. Ni les sources, ni le pom, ni le depot Git.

# Minimale : un JRE, pas un JDK. Pas de compilateur, pas d'outils,
# pas de gestionnaire de paquets a detourner.
FROM eclipse-temurin:25-jre-alpine

# ⚠️ LA LIGNE QU'ON OUBLIE. Sans `USER`, le code du candidat tourne en root
# DANS le conteneur. Ce n'est pas le root de la machine — mais c'est le point
# de depart de toute evasion, et cela annule l'interet de `--cap-drop`.
RUN adduser --disabled-password --uid 1000 execute
USER 1000:1000

WORKDIR /travail
COPY --chown=1000:1000 classes /travail/classes

# Forme exec : PID 1 est la JVM elle-meme, pas un shell.
# Avec la forme shell, PID 1 serait `/bin/sh -c ...`, qui ne transmet pas les
# signaux — `docker stop` attendrait dix secondes avant de tuer.
#
# ⚠️ AUCUN ARGUMENT DE SCRIPT. Le script arrive sur l'ENTREE STANDARD.
# Passe en argument, il serait lisible dans `ps`, dans `docker inspect` et
# dans les journaux du demon — c'est-a-dire archive.
ENTRYPOINT ["java", \
            "-XX:+ExitOnOutOfMemoryError", \
            "-XX:ActiveProcessorCount=1", \
            "-Dfile.encoding=UTF-8", \
            "-cp", "/travail/classes", \
            "fr.portail.bac.Executeur"]
