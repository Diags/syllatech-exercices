# ============================================================
# Le Dockerfile multi-stage du portail — front et back, une image
# ============================================================
#
# ⚠️ IL EST AUDITE PAR `fr.portail.deploiement.AuditImage`, que le
# chapitre 6 lance sur CE FICHIER. Retirez une ligne, relancez : il le dit.
#
#   docker build -t portail:1.0.0 -f deploiement/Dockerfile .

# --- Etape 1 : construire le front ---------------------------------
# Node et ses centaines de megaoctets de dependances sont necessaires pour
# COMPILER React. Ils ne le sont pas pour SERVIR le resultat.
FROM node:22-alpine AS front
WORKDIR /front
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# --- Etape 2 : construire le back ----------------------------------
FROM maven:3-eclipse-temurin-25 AS back
WORKDIR /build
COPY pom.xml .
# ⚠️ Les dependances AVANT les sources : cette couche ne change que lorsque
# le `pom.xml` change. Copier tout d'un coup retelecharge Maven a chaque
# modification d'une ligne de Java.
RUN mvn -B -q dependency:go-offline
COPY src/ src/
RUN mvn -B -q package -DskipTests

# --- Etape 3 : l'image finale --------------------------------------
# ⚠️ UN JRE, PAS UN JDK. Pas de compilateur, pas de Maven, pas de Node :
# l'outillage reste dans les etapes precedentes. Moins de megaoctets, et
# surtout moins de surface d'attaque.
FROM eclipse-temurin:25-jre-alpine

# ⚠️ LA LIGNE QU'ON OUBLIE. Sans `USER`, l'application tourne en root DANS
# le conteneur — le point de depart de toute evasion.
RUN addgroup -S portail && adduser -S -G portail portail
USER portail

WORKDIR /app
COPY --from=back  --chown=portail:portail /build/target/*.jar /app/app.jar
COPY --from=front --chown=portail:portail /front/dist        /app/static

# ⚠️ AUCUN SECRET ICI. Ni `ENV PORTAIL_JWT_CLE=…`, ni fichier de mots de
# passe copie : une variable posee dans une image est visible par
# `docker history`, et elle part avec l'image dans chaque registre.
# La configuration arrive au LANCEMENT.
ENV SPRING_PROFILES_ACTIVE=production
EXPOSE 8080

# ⚠️ Un controle de sante, pour que l'orchestrateur sache si le conteneur
# REPOND — et pas seulement s'il tourne.
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s \
    CMD wget -q -O- http://localhost:8080/actuator/health || exit 1

# Forme exec : PID 1 est la JVM, qui recoit donc les signaux. Avec la forme
# shell, PID 1 serait `/bin/sh -c`, et `docker stop` attendrait dix
# secondes avant de tuer.
ENTRYPOINT ["java", "-XX:MaxRAMPercentage=75", "-jar", "/app/app.jar"]
