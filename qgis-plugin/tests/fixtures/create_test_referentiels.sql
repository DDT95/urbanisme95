-- Jeu de données FICTIF pour tester le plugin de bout en bout, sans
-- utiliser de vraies données Fichiers Fonciers (aucun nom, adresse ou
-- identifiant réel). À exécuter sur une base PostgreSQL de test/locale,
-- jamais sur la base professionnelle.
--
-- Reproduit la structure réelle confirmée par la requête SQL de
-- production DDT95 (colonnes idpar, jdatat, ssuf, cgrnumdtxt, dqualp,
-- drcsuba...), pour le millésime 2024, avec une commune fictive 95999.

CREATE EXTENSION IF NOT EXISTS postgis;

DROP SCHEMA IF EXISTS x_ff2024_dep CASCADE;
DROP SCHEMA IF EXISTS x_ff2024_non_ano_dep CASCADE;
DROP SCHEMA IF EXISTS r_drieat CASCADE;

CREATE SCHEMA x_ff2024_dep;
CREATE SCHEMA x_ff2024_non_ano_dep;
CREATE SCHEMA r_drieat;

-- Table parcelle -------------------------------------------------------
CREATE TABLE x_ff2024_dep.d95_fftp_2024_pnb10_parcelle (
    idpar text PRIMARY KEY,
    idprocpte text,
    idcom text,
    idcomtxt text,
    ccosec text,
    dnupla text,
    jdatat date,
    dnuvoi text,
    dindic text,
    cconvo text,
    dvoilib text,
    cgrnumdtxt text,
    ssuf numeric,
    geompar geometry(MultiPolygon, 2154)
);

-- Table subdivision fiscale (une parcelle peut avoir plusieurs
-- subdivisions, sommées dans sumsuba) -----------------------------------
CREATE TABLE x_ff2024_dep.d95_fftp_2024_pnb21_suf (
    idpar text,
    drcsuba numeric
);

-- Table propriétaire/droit (non anonymisée, données fictives ici) -------
CREATE TABLE x_ff2024_non_ano_dep.d95_fftp_2024_proprietaire_droit_non_ano (
    idprocpte text,
    ccodrotxt text,
    ccogrmtxt text,
    ccogrm text,
    dqualp text,
    dnomus text,
    dprnus text,
    dformjur text,
    ddenom text,
    jdatnss date,
    dldnss text,
    dsiren text,
    dlign3 text,
    dlign4 text,
    dlign5 text,
    dlign6 text
);

-- Table GPA ---------------------------------------------------------------
CREATE TABLE r_drieat.gpa_annexe_1 (
    "cleSIG" text,
    commentaire text
);

-- Données fictives --------------------------------------------------------
-- Parcelle 1 : propriétaire personne physique (dqualp renseigné), avec
-- GPA, et 2 subdivisions fiscales (pour vérifier le SUM/GROUP BY).
INSERT INTO x_ff2024_dep.d95_fftp_2024_pnb10_parcelle VALUES (
    '959990000A0001', 'CPT0001', '95999', 'COMMUNE TEST', '0A', '0001',
    '2020-01-15', '3', 'BIS', 'RUE', 'DE TEST', 'S', 1150,
    ST_Multi(ST_GeomFromText(
        'POLYGON((650000 6860000, 650010 6860000, 650010 6860010, 650000 6860010, 650000 6860000))',
        2154
    ))
);
INSERT INTO x_ff2024_dep.d95_fftp_2024_pnb21_suf VALUES
    ('959990000A0001', 800),
    ('959990000A0001', 350);
INSERT INTO x_ff2024_non_ano_dep.d95_fftp_2024_proprietaire_droit_non_ano VALUES (
    'CPT0001', 'PP', 'AB', 'Terre', 'M', 'DUPONT (FICTIF)', 'JEAN', NULL, NULL,
    '1980-05-01', 'PARIS (FICTIF)', NULL,
    '3 RUE DE TEST', '', '95999 COMMUNE TEST', 'FRANCE'
);
INSERT INTO r_drieat.gpa_annexe_1 VALUES ('959990000A0001', 'Zone test GPA');

-- Parcelle 2 : propriétaire personne morale (dqualp NULL), sans GPA.
INSERT INTO x_ff2024_dep.d95_fftp_2024_pnb10_parcelle VALUES (
    '959990000A0002', 'CPT0002', '95999', 'COMMUNE TEST', '0A', '0002',
    '2018-06-01', '5', '', 'RUE', 'DE TEST', 'S', 780,
    ST_Multi(ST_GeomFromText(
        'POLYGON((650020 6860000, 650030 6860000, 650030 6860010, 650020 6860010, 650020 6860000))',
        2154
    ))
);
INSERT INTO x_ff2024_dep.d95_fftp_2024_pnb21_suf VALUES ('959990000A0002', 780);
INSERT INTO x_ff2024_non_ano_dep.d95_fftp_2024_proprietaire_droit_non_ano VALUES (
    'CPT0002', 'PP', 'AB', 'Terre', NULL, NULL, NULL, 'SCI', 'TEST IMMO (FICTIF)',
    NULL, NULL, '000000002',
    '5 RUE DE TEST', '', '95999 COMMUNE TEST', 'FRANCE'
);

-- Parcelle 3 : volontairement absente des tables sources, pour vérifier
-- que le plugin la signale comme "manquant_etat" et "manquant_plan"
-- (elle sera présente dans le CSV de test mais pas ici).
