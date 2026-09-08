"""Correspondance entre les colonnes produites dans l'état/plan parcellaire
et les colonnes des tables Fichiers Fonciers, reprise directement de la
requête SQL de production fournie par la DDT95 (schéma q_26_01_4825,
millésime 2024).

Alias utilisés dans les requêtes générées :
  parc   -> table parcelle (x_ff<AAAA>_dep.d95_fftp_<AAAA>_pnb10_parcelle)
  pnb21  -> table subdivision fiscale (..._pnb21_suf)
  proprio-> table propriétaire non anonymisé (..._proprietaire_droit_non_ano)
  gpa    -> r_drieat.gpa_annexe_1

⚠️ Le nommage des schémas/tables Fichiers Fonciers n'est PAS strictement
régulier d'un millésime à l'autre (constaté sur votre base : 2024 utilise
x_ff2024_dep / x_ff2024_non_ano_dep avec des tables préfixées d95_, alors
que 2025 semble suivre un autre schéma). REFERENTIELS_PAR_MILLESIME
liste donc explicitement, année par année, les tables à utiliser plutôt
que de les deviner à partir d'un motif. Ajoutez une entrée quand vous
passez à un nouveau millésime.
"""

# Système de coordonnées des géométries cadastrales (Lambert-93, confirmé
# dans le projet QGIS de la DDT95 : EPSG:2154 - RGF93 v1 / Lambert-93).
SRID = 2154

# Colonne de jointure entre la table GPA et la table parcelle.
GPA_JOIN_COLUMN = "cleSIG"

# Tables référentielles Fichiers Fonciers/GPA, par millésime. Seul 2024 est
# confirmé (requête de production DDT95). Ajoutez une entrée par nouveau
# millésime au lieu de déduire le nom automatiquement.
REFERENTIELS_PAR_MILLESIME = {
    2024: {
        "parcelle": ("x_ff2024_dep", "d95_fftp_2024_pnb10_parcelle"),
        "suf": ("x_ff2024_dep", "d95_fftp_2024_pnb21_suf"),
        "proprietaire": ("x_ff2024_non_ano_dep", "d95_fftp_2024_proprietaire_droit_non_ano"),
        "gpa": ("r_drieat", "gpa_annexe_1"),
    },
}

PARCELLE_COLUMNS = {
    "idpar": "idpar",
    "idprocpte": "idprocpte",
    "idcom": "idcom",
    "idcomtxt": "idcomtxt",
    "ccosec": "ccosec",
    "dnupla": "dnupla",
    "datmut": "jdatat",
    "dnuvoi": "dnuvoi",
    "dindic": "dindic",
    "cconvo": "cconvo",
    "dvoilib": "dvoilib",
    "natpar": "cgrnumdtxt",
    "surfpar": "ssuf",
    "geometrie": "geompar",
}

SUF_COLUMNS = {
    "idpar": "idpar",
    "drcsuba": "drcsuba",
}

PROPRIETAIRE_COLUMNS = {
    "idprocpte": "idprocpte",
    "ccodrotxt": "ccodrotxt",
    "ccogrmtxt": "ccogrmtxt",
    "ccogrm": "ccogrm",
    "dqualp": "dqualp",
    "dnomus": "dnomus",
    "dprnus": "dprnus",
    "dformjur": "dformjur",
    "ddenom": "ddenom",
    "jdatnss": "jdatnss",
    "dldnss": "dldnss",
    "dsiren": "dsiren",
    "adresse_ligne1": "dlign3",
    "adresse_ligne2": "dlign4",
    "adresse_ligne3": "dlign5",
    "adresse_ligne4": "dlign6",
}
