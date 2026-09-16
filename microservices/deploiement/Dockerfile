# ============================================================
# L'image du service des offres — multi-etapes, et non-root.
# ============================================================
# Deux etages : on compile dans une image lourde, on n'embarque
# que le resultat dans une image legere. Le chapitre 4 mesure ce
# que chaque etage pese et ce qui finit reellement dans l'image.

# ── etage 1 : la compilation ────────────────────────────────
FROM maven:3-eclipse-temurin-25 AS construction
WORKDIR /source
# ⚠️ L'ORDRE DES COUCHES EST UNE DECISION DE PERFORMANCE.
# Le pom change rarement, le code souvent. En copiant le pom
# SEUL puis en telechargeant les dependances, on obtient une
# couche que Docker reutilise tant que le pom ne bouge pas.
# L'inverse — COPY . . en premier — invalide le cache a chaque
# modification d'une ligne de code, et retelecharge tout.
COPY pom.xml .
RUN mvn -B -q dependency:go-offline
COPY src ./src
RUN mvn -B -q package -DskipTests

# ── etage 2 : l'execution ───────────────────────────────────
FROM eclipse-temurin:25-jre
WORKDIR /application
# ⚠️ UN UTILISATEUR NON PRIVILEGIE. Par defaut, un conteneur
# tourne en root : une evasion, et l'attaquant est root sur
# l'hote. Trois lignes suffisent a l'eviter.
RUN groupadd --system portail && useradd --system --gid portail portail
COPY --from=construction /source/target/*.jar application.jar
RUN chown portail:portail application.jar
USER portail
EXPOSE 8080
# La forme EXEC : le processus Java est PID 1 et recoit SIGTERM.
# En forme shell, c'est /bin/sh qui est PID 1, et l'arret propre
# n'arrive jamais jusqu'a la JVM.
ENTRYPOINT ["java", "-jar", "application.jar"]
