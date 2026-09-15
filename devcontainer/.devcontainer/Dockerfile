# Un Dockerfile multi-etapes : la meme base pour le developpement et la
# production, augmentee des outils du cote « dev ». C'est ce qui evite deux
# fichiers qui divergent en six mois.
ARG VARIANT=21-bookworm
FROM maven:3-eclipse-temurin-${VARIANT} AS base
WORKDIR /workspace

FROM base AS dev
RUN apt-get update \
 && apt-get install -y --no-install-recommends postgresql-client jq \
 && rm -rf /var/lib/apt/lists/*

FROM base AS prod
# Le contexte est la RACINE du depot (build.context: ".."), pas
# .devcontainer/ : c'est pourquoi pom.xml et src/ sont visibles ici.
COPY pom.xml .
COPY src ./src
RUN mvn -q -B package -DskipTests
