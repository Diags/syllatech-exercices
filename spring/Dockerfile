# Le portail de l'emploi, en deux etapes.
#
# ⚠️ `-Djarmode=layertools`, que citent la plupart des tutoriels, a ete
# RETIRE de Spring Boot 4. Il est remplace par `-Djarmode=tools`, qui fait
# davantage : extraire les couches (`--layers`), et poser le lanceur a cote
# (`--launcher`) pour demarrer sans reconstruire de jar. Un Dockerfile copie
# d'un article de 2023 echoue donc ici, avec un message qui ne dit pas
# pourquoi. Le chapitre 6 lance les deux commandes et montre la difference.
#
# Construire et lancer :
#   mvn -q package -DskipTests
#   docker build -t portail-emploi .
#   docker run --rm -p 8080:8080 portail-emploi

FROM eclipse-temurin:25-jre AS extraction
WORKDIR /extrait
COPY target/spring-portail-1.0.0.jar app.jar
RUN java -Djarmode=tools -jar app.jar extract --layers --launcher

# L'image finale ne contient ni Maven, ni le code source, ni le jar
# d'origine : seulement ce qui tourne.
FROM eclipse-temurin:25-jre
WORKDIR /app

# L'ORDRE DE CES QUATRE LIGNES EST TOUTE L'OPTIMISATION. Docker empile une
# couche par COPY et n'invalide que celles qui suivent la premiere qui a
# change. Les dependances, qui ne bougent qu'au changement du pom, viennent
# donc en premier ; notre code, qui change a chaque commit, en dernier.
COPY --from=extraction /extrait/app/dependencies/ ./
COPY --from=extraction /extrait/app/spring-boot-loader/ ./
COPY --from=extraction /extrait/app/snapshot-dependencies/ ./
COPY --from=extraction /extrait/app/application/ ./

# Ne pas tourner en root. Rien dans cette application n'en a besoin, et une
# faille dans une dependance vaut alors les droits d'un utilisateur sans
# privileges plutot que ceux de l'administrateur du conteneur.
RUN useradd --create-home --uid 10001 portail
USER portail

EXPOSE 8080

# La configuration vient de l'environnement, jamais de l'image :
#   docker run -e SPRING_PROFILES_ACTIVE=prod -e DB_URL=... portail-emploi
ENV SPRING_PROFILES_ACTIVE=prod

# ⚠️ La forme « exec » (un tableau JSON) et non une chaine : sans elle,
# Docker lance un shell qui devient le processus 1, et le signal d'arret ne
# parvient jamais a la JVM — le conteneur est alors tue au bout du delai de
# grace, sans arret propre.
ENTRYPOINT ["java", "org.springframework.boot.loader.launch.JarLauncher"]
