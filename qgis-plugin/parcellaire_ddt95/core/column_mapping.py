"""Correspondance entre les colonnes produites dans l'état/plan parcellaire
et les colonnes réellement présentes dans vos tables Fichiers Fonciers.

C'EST LE SEUL FICHIER À MODIFIER si les noms de colonnes de votre base
PostgreSQL diffèrent de ceux supposés ci-dessous (nomenclature MAJIC
standard). Utilisez le bouton « Diagnostiquer les tables sources » du
plugin pour comparer ces noms avec les colonnes réellement présentes
dans votre base avant la première exécution en production.

Alias utilisés dans les requêtes générées :
  parc  -> table parcelle (x_ff<AAAA>_dep.d95_fftp_<AAAA>_pnb10_parcelle)
  suf   -> table subdivision fiscale (..._pnb21_suf)
  prop  -> table propriétaire non anonymisé (..._proprietaire_droit_non_ano)
  gpa   -> r_drieat.gpa_annexe_1
"""

# Système de coordonnées des géométries cadastrales (Lambert-93 par défaut).
SRID = 2154

# Colonne de jointure entre la table GPA et la table parcelle.
GPA_JOIN_COLUMN = "cleSIG"

PARCELLE_COLUMNS = {
    "idpar": "idpar",
    "idprocpte": "idprocpte",
    "idcom": "idcom",
    "idcomtxt": "idcomtxt",
    "ccosec": "ccosec",
    "dnupla": "dnupla",
    "surfpar": "dcntpa",
    "geometrie": "geompar",
}

SUF_COLUMNS = {
    "idpar": "idpar",
    "ccodrotxt": "ccodrotxt",
    "datmut": "datmut",
    "lieudit": "dlieujoi",
    "natpar": "cnatsp",
    "ccogrm": "ccogrm",
    "ccogrmtxt": "ccogrmtxt",
    "sumsuba": "sumsuba",
}

PROPRIETAIRE_COLUMNS = {
    "idprocpte": "idprocpte",
    "nom": "ddenom",
    "siren": "dsiren",
    "dlieunss": "dlieunss",
    "adresse_ligne1": "dlign3",
    "adresse_ligne2": "dlign4",
    "adresse_ligne3": "dlign5",
    "adresse_ligne4": "dlign6",
}
