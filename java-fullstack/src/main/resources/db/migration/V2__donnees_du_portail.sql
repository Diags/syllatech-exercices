-- ============================================================
-- V2 — les donnees du portail
-- ============================================================
-- ⚠️ ENTREE DECLAREE. Six offres, trois entreprises, deux comptes : ce
-- que les chapitres mesurent — le nombre de requetes SQL d'un N+1, ce
-- qu'un DTO cache, ce qu'un role autorise — se DEDUIT de ces lignes.

INSERT INTO entreprise (nom, ville) VALUES
    ('Clauger',        'Lyon'),
    ('Nantes Digital', 'Nantes'),
    ('Cap Bordeaux',   'Bordeaux');

INSERT INTO offre (titre, pile, salaire_ke, entreprise_id) VALUES
    ('Developpeur Java Spring',          'java',   48, 1),
    ('Ingenieur plateforme Kubernetes',  'devops', 62, 1),
    ('Developpeur Java / Kafka',         'java',   52, 2),
    ('SRE astreinte',                    'devops', 58, 2),
    ('Developpeur front React',          'front',  44, 3),
    ('Architecte cloud',                 'devops', 78, 3);

-- Les empreintes sont de VRAIES empreintes BCrypt du mot de passe
-- « motdepasse », posees par la migration V3 au demarrage : une empreinte
-- ecrite en dur ici serait un secret commite, et le cours dit de ne
-- jamais le faire.
