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
    # 2018-2020 : parcelle/suf disponibles au niveau départemental (schéma
    # x_ffAAAA_dep, tables d95_...), mais PAS la table propriétaire non
    # anonymisée à ce niveau-là ces années-là : on utilise donc le schéma
    # national x_ffAAAA (non préfixé d95_) pour "proprietaire" uniquement,
    # ce qui reste correct (la jointure se fait par idprocpte, la
    # restriction au 95 vient déjà de la table parcelle).
    2018: {
        "parcelle": ("x_ff2018_dep", "d95_fftp_2018_pnb10_parcelle"),
        "suf": ("x_ff2018_dep", "d95_fftp_2018_pnb21_suf"),
        "proprietaire": ("x_ff2018", "fftp_2018_proprietaire_droit_non_ano"),
        "gpa": ("r_drieat", "gpa_annexe_1"),
    },
    2019: {
        "parcelle": ("x_ff2019_dep", "d95_fftp_2019_pnb10_parcelle"),
        "suf": ("x_ff2019_dep", "d95_fftp_2019_pnb21_suf"),
        "proprietaire": ("x_ff2019", "fftp_2019_proprietaire_droit_non_ano"),
        "gpa": ("r_drieat", "gpa_annexe_1"),
    },
    2020: {
        "parcelle": ("x_ff2020_dep", "d95_fftp_2020_pnb10_parcelle"),
        "suf": ("x_ff2020_dep", "d95_fftp_2020_pnb21_suf"),
        "proprietaire": ("x_ff2020", "fftp_2020_proprietaire_droit_non_ano"),
        "gpa": ("r_drieat", "gpa_annexe_1"),
    },
    # 2021-2023 : la table propriétaire non anonymisée existe cette fois
    # directement dans le schéma départemental x_ffAAAA_dep.
    2021: {
        "parcelle": ("x_ff2021_dep", "d95_fftp_2021_pnb10_parcelle"),
        "suf": ("x_ff2021_dep", "d95_fftp_2021_pnb21_suf"),
        "proprietaire": ("x_ff2021_dep", "d95_fftp_2021_proprietaire_droit_non_ano"),
        "gpa": ("r_drieat", "gpa_annexe_1"),
    },
    2022: {
        "parcelle": ("x_ff2022_dep", "d95_fftp_2022_pnb10_parcelle"),
        "suf": ("x_ff2022_dep", "d95_fftp_2022_pnb21_suf"),
        "proprietaire": ("x_ff2022_dep", "d95_fftp_2022_proprietaire_droit_non_ano"),
        "gpa": ("r_drieat", "gpa_annexe_1"),
    },
    2023: {
        "parcelle": ("x_ff2023_dep", "d95_fftp_2023_pnb10_parcelle"),
        "suf": ("x_ff2023_dep", "d95_fftp_2023_pnb21_suf"),
        "proprietaire": ("x_ff2023_dep", "d95_fftp_2023_proprietaire_droit_non_ano"),
        "gpa": ("r_drieat", "gpa_annexe_1"),
    },
    2024: {
        "parcelle": ("x_ff2024_dep", "d95_fftp_2024_pnb10_parcelle"),
        "suf": ("x_ff2024_dep", "d95_fftp_2024_pnb21_suf"),
        "proprietaire": ("x_ff2024_non_ano_dep", "d95_fftp_2024_proprietaire_droit_non_ano"),
        "gpa": ("r_drieat", "gpa_annexe_1"),
    },
    # Confirmé par information_schema.tables sur la base réelle : un seul
    # schéma (pas de split dep/non_ano), tables suffixées par l'année
    # plutôt que préfixées, pas de préfixe départemental d95_.
    2025: {
        "parcelle": ("x_ff2025_non_ano", "fftp_pnb10_parcelle_2025"),
        "suf": ("x_ff2025_non_ano", "fftp_pnb21_suf_2025"),
        "proprietaire": ("x_ff2025_non_ano", "fftp_proprietaire_droit_non_ano_2025"),
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
