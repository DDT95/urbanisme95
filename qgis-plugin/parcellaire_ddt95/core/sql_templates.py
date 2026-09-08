"""Construction du SQL pour une commande d'état/plan parcellaire.

Toutes les valeurs interpolées ici sont soit :
  - des identifiants (schéma, commande) validés par validate_identifier()
    puis échappés par quote_ident()/qualified_table() ;
  - un millésime entier validé par validate_millesime() ;
  - des noms de colonnes provenant exclusivement de column_mapping.py
    (jamais saisis librement par l'utilisateur final).
Aucune valeur issue du CSV n'est jamais concaténée dans ces requêtes :
l'import des données du CSV passe par core.csv_import.insert_rows(), qui
utilise le fournisseur PostgreSQL natif de QGIS (attributs liés, pas de
SQL texte).
"""

from . import column_mapping as cm
from .identifiers import qualified_table, quote_ident, validate_identifier, validate_millesime


def referentiels(millesime):
    """Renvoie les tables Fichiers Fonciers/GPA qualifiées pour un millésime
    donné, en supposant le motif standard x_ff<AAAA>_dep. Si un millésime
    futur ne suit pas ce motif, ajustez cette fonction (seul endroit à
    modifier pour changer la convention de nommage par année)."""
    year = validate_millesime(millesime)
    refs = {
        "parcelle": "x_ff{y}_dep.d95_fftp_{y}_pnb10_parcelle".format(y=year),
        "suf": "x_ff{y}_dep.d95_fftp_{y}_pnb21_suf".format(y=year),
        "proprietaire": "x_ff{y}_non_ano_dep.d95_fftp_{y}_proprietaire_droit_non_ano".format(
            y=year
        ),
        "gpa": "r_drieat.gpa_annexe_1",
    }
    qualified = {}
    for key, dotted in refs.items():
        schema, table = dotted.split(".", 1)
        validate_identifier(schema, "schéma référentiel ({})".format(key))
        validate_identifier(table, "table référentiel ({})".format(key))
        qualified[key] = qualified_table(schema, table)
    return qualified


def staging_table_name(commande):
    return "data_parcelle_{}".format(commande)


def etat_table_name(commande):
    return "etat_p_{}".format(commande)


def plan_table_name(commande):
    return "plans_parcellaire_{}".format(commande)


def comparaison_table_name(commande):
    return "comparaison_parcelles_{}".format(commande)


def _check(schema, commande):
    validate_identifier(schema, "schéma")
    validate_identifier(commande, "commande")


def create_staging_table_sql(schema, commande):
    _check(schema, commande)
    table = qualified_table(schema, staging_table_name(commande))
    return """
DROP TABLE IF EXISTS {table};
CREATE TABLE {table} (
    ogc_fid serial PRIMARY KEY,
    id text NOT NULL,
    commune text,
    prefixe text,
    section text,
    numero text,
    contenance text,
    created text,
    updated text,
    layer text
);
""".strip().format(table=table)


def create_etat_parcellaire_sql(schema, commande, millesime):
    _check(schema, commande)
    year = validate_millesime(millesime)
    refs = referentiels(year)
    staging = qualified_table(schema, staging_table_name(commande))
    etat = qualified_table(schema, etat_table_name(commande))

    p = cm.PARCELLE_COLUMNS
    s = cm.SUF_COLUMNS
    pr = cm.PROPRIETAIRE_COLUMNS

    def col(alias, mapping, key):
        return "{}.{}".format(alias, quote_ident(mapping[key]))

    # concat_ws ignore les valeurs NULL (contrairement à ||, qui rendrait
    # toute la concaténation NULL dès qu'une ligne d'adresse est vide).
    adresse_lignes = [
        "NULLIF(trim(coalesce({}, '')), '')".format(
            col("prop", pr, "adresse_ligne{}".format(i))
        )
        for i in range(1, 5)
    ]
    adresse_complete = "concat_ws(E'\\n', {})".format(", ".join(adresse_lignes))

    return """
DROP TABLE IF EXISTS {etat};
CREATE TABLE {etat} AS
SELECT
    row_number() OVER () AS etat_id,
    {year} AS annee_ff,
    {c_idprocpte} AS idprocpte,
    {p_idpar} AS idpar,
    {p_idcom} AS idcom,
    {p_idcomtxt} AS idcomtxt,
    {p_ccosec} AS ccosec,
    {p_dnupla} AS dnupla,
    {s_ccodrotxt} AS ccodrotxt,
    {s_datmut} AS datmut,
    {s_lieudit} AS lieudit,
    {s_natpar} AS natpar,
    {p_surfpar} AS surfpar,
    {s_ccogrmtxt} AS ccogrmtxt,
    {s_ccogrm} AS ccogrm,
    {s_sumsuba} AS sumsuba,
    {c_nom} AS nom,
    {c_dlieunss} AS dlieunss,
    {c_siren} AS siren,
    {c_adr1} AS adresse_ligne1,
    {c_adr2} AS adresse_ligne2,
    {c_adr3} AS adresse_ligne3,
    {c_adr4} AS adresse_ligne4,
    {adresse_complete} AS adresse_complete,
    CASE WHEN gpa.{gpa_col} IS NOT NULL THEN 'oui' ELSE 'non' END AS gpa
FROM {staging} data
JOIN {ref_parcelle} parc ON {p_idpar} = data.id
LEFT JOIN {ref_suf} suf ON {s_idpar} = {p_idpar}
LEFT JOIN {ref_proprietaire} prop ON {c_idprocpte} = {p_idprocpte}
LEFT JOIN {ref_gpa} gpa ON gpa.{gpa_col} = {p_idpar};

ALTER TABLE {etat} ADD PRIMARY KEY (etat_id);
CREATE INDEX ON {etat} (idpar);
""".strip().format(
        etat=etat,
        year=year,
        staging=staging,
        ref_parcelle=refs["parcelle"],
        ref_suf=refs["suf"],
        ref_proprietaire=refs["proprietaire"],
        ref_gpa=refs["gpa"],
        gpa_col=quote_ident(cm.GPA_JOIN_COLUMN),
        p_idpar=col("parc", p, "idpar"),
        p_idprocpte=col("parc", p, "idprocpte"),
        p_idcom=col("parc", p, "idcom"),
        p_idcomtxt=col("parc", p, "idcomtxt"),
        p_ccosec=col("parc", p, "ccosec"),
        p_dnupla=col("parc", p, "dnupla"),
        p_surfpar=col("parc", p, "surfpar"),
        s_idpar=col("suf", s, "idpar"),
        s_ccodrotxt=col("suf", s, "ccodrotxt"),
        s_datmut=col("suf", s, "datmut"),
        s_lieudit=col("suf", s, "lieudit"),
        s_natpar=col("suf", s, "natpar"),
        s_ccogrm=col("suf", s, "ccogrm"),
        s_ccogrmtxt=col("suf", s, "ccogrmtxt"),
        s_sumsuba=col("suf", s, "sumsuba"),
        c_idprocpte=col("prop", pr, "idprocpte"),
        c_nom=col("prop", pr, "nom"),
        c_dlieunss=col("prop", pr, "dlieunss"),
        c_siren=col("prop", pr, "siren"),
        c_adr1=col("prop", pr, "adresse_ligne1"),
        c_adr2=col("prop", pr, "adresse_ligne2"),
        c_adr3=col("prop", pr, "adresse_ligne3"),
        c_adr4=col("prop", pr, "adresse_ligne4"),
        adresse_complete=adresse_complete,
    )


def create_plans_parcellaire_sql(schema, commande, millesime):
    _check(schema, commande)
    year = validate_millesime(millesime)
    refs = referentiels(year)
    staging = qualified_table(schema, staging_table_name(commande))
    plan = qualified_table(schema, plan_table_name(commande))
    p = cm.PARCELLE_COLUMNS

    def col(alias, key):
        return "{}.{}".format(alias, quote_ident(p[key]))

    return """
DROP TABLE IF EXISTS {plan};
CREATE TABLE {plan} AS
SELECT DISTINCT
    row_number() OVER () AS plan_id,
    {p_idpar} AS idpar,
    {p_idcomtxt} AS idcomtxt,
    {p_idcom} AS idcom,
    {p_ccosec} AS section,
    {p_dnupla} AS numero,
    {p_geom} AS geompar
FROM {staging} data
JOIN {ref_parcelle} parc ON {p_idpar} = data.id
WHERE {p_geom} IS NOT NULL;

ALTER TABLE {plan} ADD PRIMARY KEY (plan_id);
ALTER TABLE {plan}
    ALTER COLUMN geompar TYPE geometry(MultiPolygon, {srid})
    USING ST_SetSRID(ST_Multi(geompar), {srid});
CREATE INDEX ON {plan} USING GIST (geompar);
""".strip().format(
        plan=plan,
        staging=staging,
        ref_parcelle=refs["parcelle"],
        srid=cm.SRID,
        p_idpar=col("parc", "idpar"),
        p_idcomtxt=col("parc", "idcomtxt"),
        p_idcom=col("parc", "idcom"),
        p_ccosec=col("parc", "ccosec"),
        p_dnupla=col("parc", "dnupla"),
        p_geom=col("parc", "geometrie"),
    )


def create_comparaison_sql(schema, commande):
    _check(schema, commande)
    staging = qualified_table(schema, staging_table_name(commande))
    etat = qualified_table(schema, etat_table_name(commande))
    plan = qualified_table(schema, plan_table_name(commande))
    comparaison = qualified_table(schema, comparaison_table_name(commande))

    return """
DROP TABLE IF EXISTS {comparaison};
CREATE TABLE {comparaison} AS
SELECT
    row_number() OVER () AS comparaison_id,
    data.id AS idpar,
    'manquant_etat' AS anomalie
FROM {staging} data
WHERE NOT EXISTS (SELECT 1 FROM {etat} e WHERE e.idpar = data.id)

UNION ALL

SELECT
    row_number() OVER () + 1000000 AS comparaison_id,
    data.id AS idpar,
    'manquant_plan' AS anomalie
FROM {staging} data
WHERE NOT EXISTS (SELECT 1 FROM {plan} pl WHERE pl.idpar = data.id)

UNION ALL

SELECT
    row_number() OVER () + 2000000 AS comparaison_id,
    e.idpar AS idpar,
    'hors_csv' AS anomalie
FROM (SELECT DISTINCT idpar FROM {etat}) e
WHERE NOT EXISTS (SELECT 1 FROM {staging} data WHERE data.id = e.idpar);

ALTER TABLE {comparaison} ADD PRIMARY KEY (comparaison_id);
""".strip().format(comparaison=comparaison, staging=staging, etat=etat, plan=plan)
