-- Jeu de données FICTIF pour tester le plugin de bout en bout, sans
-- utiliser de vraies données Fichiers Fonciers (aucun nom, adresse ou
-- identifiant réel). À exécuter sur une base PostgreSQL de test/locale,
-- jamais sur la base professionnelle.
--
-- Reproduit la structure attendue par
-- parcellaire_ddt95/core/column_mapping.py pour le millésime 2024,
-- avec une commune fictive 95999.

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
    dcntpa numeric,
    geompar geometry(MultiPolygon, 2154)
);

-- Table subdivision fiscale ---------------------------------------------
CREATE TABLE x_ff2024_dep.d95_fftp_2024_pnb21_suf (
    idpar text,
    ccodrotxt text,
    datmut date,
    dlieujoi text,
    cnatsp text,
    ccogrm text,
    ccogrmtxt text,
    sumsuba numeric
);

-- Table propriétaire (non anonymisée, données fictives ici) -------------
CREATE TABLE x_ff2024_non_ano_dep.d95_fftp_2024_proprietaire_droit_non_ano (
    idprocpte text,
    ddenom text,
    dsiren text,
    dlieunss text,
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
-- Parcelle 1 : trouvée dans l'état, dans le plan, avec GPA
INSERT INTO x_ff2024_dep.d95_fftp_2024_pnb10_parcelle VALUES (
    '959990000A0001', 'CPT0001', '95999', 'COMMUNE TEST', '0A', '0001', 1200,
    ST_Multi(ST_GeomFromText(
        'POLYGON((650000 6860000, 650010 6860000, 650010 6860010, 650000 6860010, 650000 6860000))',
        2154
    ))
);
INSERT INTO x_ff2024_dep.d95_fftp_2024_pnb21_suf VALUES (
    '959990000A0001', 'PP', '2020-01-15', 'Lieu-dit Test', 'S', 'AB', 'Terre', 1150
);
INSERT INTO x_ff2024_non_ano_dep.d95_fftp_2024_proprietaire_droit_non_ano VALUES (
    'CPT0001', 'DUPONT JEAN (FICTIF)', '000000001', 'FICTIF',
    '3 RUE DE TEST', '', '95999 COMMUNE TEST', 'FRANCE'
);
INSERT INTO r_drieat.gpa_annexe_1 VALUES ('959990000A0001', 'Zone test GPA');

-- Parcelle 2 : trouvée dans l'état et le plan, sans GPA
INSERT INTO x_ff2024_dep.d95_fftp_2024_pnb10_parcelle VALUES (
    '959990000A0002', 'CPT0002', '95999', 'COMMUNE TEST', '0A', '0002', 800,
    ST_Multi(ST_GeomFromText(
        'POLYGON((650020 6860000, 650030 6860000, 650030 6860010, 650020 6860010, 650020 6860000))',
        2154
    ))
);
INSERT INTO x_ff2024_dep.d95_fftp_2024_pnb21_suf VALUES (
    '959990000A0002', 'PP', '2018-06-01', 'Lieu-dit Test 2', 'S', 'AB', 'Terre', 780
);
INSERT INTO x_ff2024_non_ano_dep.d95_fftp_2024_proprietaire_droit_non_ano VALUES (
    'CPT0002', 'MARTIN ALICE (FICTIF)', '000000002', 'FICTIF',
    '5 RUE DE TEST', '', '95999 COMMUNE TEST', 'FRANCE'
);

-- Parcelle 3 : volontairement absente des tables sources, pour vérifier
-- que le plugin la signale comme "manquant_etat" et "manquant_plan"
-- (elle sera présente dans le CSV de test mais pas ici).
