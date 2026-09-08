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
from .identifiers import (
    InvalidIdentifierError,
    qualified_table,
    quote_ident,
    validate_identifier,
    validate_millesime,
)


def referentiels(millesime):
    """Renvoie les tables Fichiers Fonciers/GPA qualifiées pour un millésime
    donné, à partir de column_mapping.REFERENTIELS_PAR_MILLESIME (le
    nommage des schémas/tables FF n'étant pas régulier d'une année sur
    l'autre, il n'est pas déduit automatiquement)."""
    year = validate_millesime(millesime)
    par_millesime = cm.REFERENTIELS_PAR_MILLESIME.get(year)
    if par_millesime is None:
        disponibles = ", ".join(str(y) for y in sorted(cm.REFERENTIELS_PAR_MILLESIME))
        raise InvalidIdentifierError(
            "Millésime {} non configuré dans column_mapping."
            "REFERENTIELS_PAR_MILLESIME (millésimes disponibles : {}). "
            "Ajoutez les noms de schéma/table de ce millésime dans "
            "core/column_mapping.py.".format(year, disponibles or "aucun")
        )
    qualified = {}
    for key, (schema, table) in par_millesime.items():
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


# Vues stables, toujours au même nom quelle que soit la commande. Le projet
# QGIS (couche virtuelle atlas_com, filtre d'atlas de plans_parcellaire)
# les référence une fois pour toutes ; le plugin les repointe vers les
# tables de la commande courante à chaque génération, si bien qu'aucune
# mise en page ni couche virtuelle n'a jamais besoin d'être retouchée.
ETAT_VUE_COURANTE = "etat_p_courant"
PLAN_VUE_COURANTE = "plans_parcellaire_courant"
COMPARAISON_VUE_COURANTE = "comparaison_parcelles_courant"


def _check(schema, commande):
    validate_identifier(schema, "schéma")
    validate_identifier(commande, "commande")


def create_vues_courantes_sql(schema, commande):
    """(Re)crée les 3 vues à nom fixe pointant vers les tables de la
    commande courante. CREATE OR REPLACE VIEW échoue si la liste de
    colonnes change de façon incompatible (rare ici, tables recréées à
    l'identique à chaque fois) : le message d'erreur PostgreSQL reste
    clair dans ce cas."""
    _check(schema, commande)
    etat = qualified_table(schema, etat_table_name(commande))
    plan = qualified_table(schema, plan_table_name(commande))
    comparaison = qualified_table(schema, comparaison_table_name(commande))
    etat_vue = qualified_table(schema, ETAT_VUE_COURANTE)
    plan_vue = qualified_table(schema, PLAN_VUE_COURANTE)
    comparaison_vue = qualified_table(schema, COMPARAISON_VUE_COURANTE)
    return (
        "DROP VIEW IF EXISTS {etat_vue} CASCADE;\n"
        "CREATE VIEW {etat_vue} AS SELECT * FROM {etat};\n"
        "DROP VIEW IF EXISTS {plan_vue} CASCADE;\n"
        "CREATE VIEW {plan_vue} AS SELECT * FROM {plan};\n"
        "DROP VIEW IF EXISTS {comparaison_vue} CASCADE;\n"
        "CREATE VIEW {comparaison_vue} AS SELECT * FROM {comparaison};"
    ).format(
        etat_vue=etat_vue,
        etat=etat,
        plan_vue=plan_vue,
        plan=plan,
        comparaison_vue=comparaison_vue,
        comparaison=comparaison,
    )


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
    """Reproduit fidèlement la requête de production DDT95 (schéma
    q_26_01_4825, fournie par un collègue) : jointures strictes (JOIN, pas
    LEFT JOIN) sur la subdivision fiscale et le propriétaire, agrégation
    SUM(drcsuba) par regroupement de subdivisions, distinction
    personne physique / personne morale via dqualp pour le nom, la date
    de naissance et le SIREN."""
    _check(schema, commande)
    year = validate_millesime(millesime)
    refs = referentiels(year)
    staging = qualified_table(schema, staging_table_name(commande))
    etat = qualified_table(schema, etat_table_name(commande))

    p = cm.PARCELLE_COLUMNS
    s = cm.SUF_COLUMNS
    pr = cm.PROPRIETAIRE_COLUMNS

    def pcol(key):
        return "parc.{}".format(quote_ident(p[key]))

    def scol(key):
        return "pnb21.{}".format(quote_ident(s[key]))

    def prcol(key):
        return "proprio.{}".format(quote_ident(pr[key]))

    lieudit = "CONCAT({}, {}, ' ', {}, ' ', {})".format(
        pcol("dnuvoi"), pcol("dindic"), pcol("cconvo"), pcol("dvoilib")
    )

    nom = (
        "CASE WHEN {dqualp} IS NOT NULL "
        "THEN CONCAT({dqualp}, ' ', {dnomus}, ' ', {dprnus}) "
        "ELSE CONCAT({dformjur}, ' ', {ddenom}) END"
    ).format(
        dqualp=prcol("dqualp"),
        dnomus=prcol("dnomus"),
        dprnus=prcol("dprnus"),
        dformjur=prcol("dformjur"),
        ddenom=prcol("ddenom"),
    )

    dlieunss = (
        "CASE WHEN {dqualp} IS NOT NULL "
        "THEN CONCAT(' né(e) le ', {jdatnss}, ' à ', {dldnss}) ELSE '' END"
    ).format(dqualp=prcol("dqualp"), jdatnss=prcol("jdatnss"), dldnss=prcol("dldnss"))

    siren = "CASE WHEN {dqualp} IS NULL THEN {dsiren} ELSE '' END".format(
        dqualp=prcol("dqualp"), dsiren=prcol("dsiren")
    )

    adr = [prcol("adresse_ligne{}".format(i)) for i in range(1, 5)]
    # concat_ws ignore les valeurs NULL (contrairement à ||, qui rendrait
    # toute la concaténation NULL dès qu'une ligne d'adresse est vide).
    adresse_complete = "concat_ws(E'\\n', {})".format(", ".join(adr))

    gpa_col = quote_ident(cm.GPA_JOIN_COLUMN)

    group_by = ", ".join(
        [
            pcol("idpar"),
            pcol("idprocpte"),
            pcol("idcom"),
            pcol("idcomtxt"),
            pcol("ccosec"),
            pcol("dnupla"),
            prcol("ccodrotxt"),
            pcol("datmut"),
            pcol("dnuvoi"),
            pcol("dindic"),
            pcol("cconvo"),
            pcol("dvoilib"),
            pcol("natpar"),
            pcol("surfpar"),
            prcol("ccogrmtxt"),
            prcol("ccogrm"),
            prcol("dqualp"),
            prcol("dnomus"),
            prcol("dprnus"),
            prcol("dformjur"),
            prcol("ddenom"),
            prcol("jdatnss"),
            prcol("dldnss"),
            prcol("dsiren"),
        ]
        + adr
        + ["gpa.{}".format(gpa_col)]
    )

    return """
DROP TABLE IF EXISTS {etat};
CREATE TABLE {etat} AS
SELECT
    row_number() OVER () AS etat_id,
    {year} AS annee_ff,
    {p_idprocpte} AS idprocpte,
    {p_idpar} AS idpar,
    {p_idcom} AS idcom,
    {p_idcomtxt} AS idcomtxt,
    {p_ccosec} AS ccosec,
    {p_dnupla} AS dnupla,
    {pr_ccodrotxt} AS ccodrotxt,
    {p_datmut} AS datmut,
    {lieudit} AS lieudit,
    {p_natpar} AS natpar,
    {p_surfpar} AS surfpar,
    {pr_ccogrmtxt} AS ccogrmtxt,
    {pr_ccogrm} AS ccogrm,
    SUM({s_drcsuba}) AS sumsuba,
    {nom} AS nom,
    {dlieunss} AS dlieunss,
    {siren} AS siren,
    {adr1} AS adresse_ligne1,
    {adr2} AS adresse_ligne2,
    {adr3} AS adresse_ligne3,
    {adr4} AS adresse_ligne4,
    {adresse_complete} AS adresse_complete,
    CASE WHEN gpa.{gpa_col} IS NOT NULL THEN 'oui' ELSE 'non' END AS gpa
FROM {staging} data
JOIN {ref_parcelle} parc ON {p_idpar} = data.id
JOIN {ref_suf} pnb21 ON {s_idpar} = {p_idpar}
JOIN {ref_proprietaire} proprio ON {p_idprocpte} = {pr_idprocpte}
LEFT JOIN {ref_gpa} gpa ON gpa.{gpa_col} = {p_idpar}
GROUP BY {group_by}
ORDER BY {p_idprocpte}, {p_idcom}, {p_ccosec}, {p_dnupla};

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
        gpa_col=gpa_col,
        p_idpar=pcol("idpar"),
        p_idprocpte=pcol("idprocpte"),
        p_idcom=pcol("idcom"),
        p_idcomtxt=pcol("idcomtxt"),
        p_ccosec=pcol("ccosec"),
        p_dnupla=pcol("dnupla"),
        p_datmut=pcol("datmut"),
        p_natpar=pcol("natpar"),
        p_surfpar=pcol("surfpar"),
        pr_ccodrotxt=prcol("ccodrotxt"),
        pr_ccogrmtxt=prcol("ccogrmtxt"),
        pr_ccogrm=prcol("ccogrm"),
        pr_idprocpte=prcol("idprocpte"),
        s_idpar=scol("idpar"),
        s_drcsuba=scol("drcsuba"),
        lieudit=lieudit,
        nom=nom,
        dlieunss=dlieunss,
        siren=siren,
        adr1=adr[0],
        adr2=adr[1],
        adr3=adr[2],
        adr4=adr[3],
        adresse_complete=adresse_complete,
        group_by=group_by,
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
