-- ============================================================
-- V1 — le schema initial du portail
-- ============================================================
-- ⚠️ CE FICHIER EST LA SOURCE DE VERITE DU SCHEMA, pas les annotations
-- JPA. `spring.jpa.hibernate.ddl-auto` est a `validate` : Hibernate
-- VERIFIE que les entites correspondent, il ne cree rien. Une entite qui
-- derive du schema fait echouer le demarrage — ce qui est exactement ce
-- qu'on veut, et ce que `update` ne fait jamais.

CREATE TABLE entreprise (
    id   BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
    nom  VARCHAR(120) NOT NULL,
    ville VARCHAR(80) NOT NULL
);

CREATE TABLE offre (
    id            BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
    titre         VARCHAR(160) NOT NULL,
    pile          VARCHAR(40)  NOT NULL,
    salaire_ke    INT          NOT NULL,
    entreprise_id BIGINT       NOT NULL,
    CONSTRAINT fk_offre_entreprise
        FOREIGN KEY (entreprise_id) REFERENCES entreprise (id)
);

CREATE TABLE compte (
    id             BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
    identifiant    VARCHAR(60)  NOT NULL UNIQUE,
    -- ⚠️ 60 caracteres : la longueur exacte d'une empreinte BCrypt. Une
    -- colonne trop courte tronque en silence et rend TOUS les mots de
    -- passe acceptes ou refuses selon la base — un grand classique.
    mot_de_passe   VARCHAR(60)  NOT NULL,
    roles          VARCHAR(120) NOT NULL,
    actif          BOOLEAN      NOT NULL DEFAULT TRUE
);

CREATE INDEX idx_offre_pile ON offre (pile);
