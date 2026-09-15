# Le Dockerfile du portail de l'emploi — la version qu'on garde.
#
# Deux etages. Le premier compile, le second execute. Ce qui distingue ce
# fichier de `Dockerfile.naif`, ligne pour ligne, tient en trois choix :
#
#   1. le `pom.xml` est copie AVANT les sources, et les dependances sont
#      telechargees entre les deux : une modification du code source ne
#      touche donc pas la couche du telechargement ;
#   2. l'image finale repart d'un JRE et ne recupere QUE le jar : ni Maven,
#      ni javac, ni sources, ni depot `.m2` ;
#   3. elle tourne sous un utilisateur non-root, et son `ENTRYPOINT` est
#      en forme exec — le programme est donc PID 1 et recoit le SIGTERM.

FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /app

# ⚠️ L'ORDRE EST LA SEULE CHOSE QUI COMPTE ICI. Ces deux lignes forment le
# motif a retenir : la liste des dependances, puis leur telechargement.
COPY pom.xml .
RUN mvn dependency:go-offline -B

# Les sources arrivent apres. Elles changent dix fois par jour ; la couche
# precedente, elle, ne bouge qu'a la modification du pom.
COPY src ./src
RUN mvn package -DskipTests -B

# ── L'image finale : elle ne connait rien du premier etage ──────────────
FROM eclipse-temurin:21-jre
RUN useradd -r -u 1001 appuser
USER appuser
WORKDIR /app

COPY --from=build /app/target/jobportal.jar app.jar

EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
