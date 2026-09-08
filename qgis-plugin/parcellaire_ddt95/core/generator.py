"""Orchestration complète d'une commande : lecture CSV, import, création
des trois tables, dans une seule transaction PostgreSQL (tout ou rien)."""

from . import sql_templates as tpl
from .csv_import import insert_rows, read_csv_rows
from .db import DbError, PgConnection
from .identifiers import qualified_table, validate_identifier, validate_millesime


class GenerationResult:
    def __init__(self):
        self.steps = []
        self.csv_count = 0
        self.etat_count = 0
        self.plan_count = 0
        self.comparaison_count = 0
        self.comparaison_rows = []

    def log(self, message):
        self.steps.append(message)


def existing_result_tables(connection_name, schema, commande):
    """Renvoie la liste des tables de résultat qui existent déjà pour cette
    commande (pour demander confirmation avant de les écraser)."""
    validate_identifier(schema, "schéma")
    validate_identifier(commande, "commande")
    conn = PgConnection(connection_name)
    candidates = [
        tpl.etat_table_name(commande),
        tpl.plan_table_name(commande),
        tpl.comparaison_table_name(commande),
    ]
    return [name for name in candidates if conn.table_exists(schema, name)]


def generate(connection_name, schema, commande, millesime, csv_path, progress=None):
    """Exécute la procédure complète pour une commande. Toutes les étapes
    PostgreSQL s'exécutent dans une seule transaction : succès complet ou
    annulation totale en cas d'erreur. Renvoie (connexion, résultat)."""
    validate_identifier(schema, "schéma")
    validate_identifier(commande, "commande")
    validate_millesime(millesime)

    result = GenerationResult()

    def log(message):
        result.log(message)
        if progress:
            progress(message)

    log("Lecture du CSV : {}".format(csv_path))
    rows = read_csv_rows(csv_path)
    result.csv_count = len(rows)
    log("{} parcelle(s) lue(s) dans le CSV.".format(result.csv_count))

    conn = PgConnection(connection_name)

    with conn.transaction():
        log("Création de la table de staging...")
        conn.execute(tpl.create_staging_table_sql(schema, commande))

        log("Import des identifiants dans PostgreSQL...")
        insert_rows(conn, schema, tpl.staging_table_name(commande), rows)
        log("{} parcelle(s) importée(s) dans PostgreSQL.".format(len(rows)))

        log("Construction de l'état parcellaire...")
        conn.execute(tpl.create_etat_parcellaire_sql(schema, commande, millesime))

        log("Construction du plan parcellaire...")
        conn.execute(tpl.create_plans_parcellaire_sql(schema, commande, millesime))

        log("Construction de la comparaison...")
        conn.execute(tpl.create_comparaison_sql(schema, commande))

        log("Mise à jour des vues courantes (utilisées par les mises en page)...")
        conn.execute(tpl.create_vues_courantes_sql(schema, commande))

    _fill_bilan(conn, schema, commande, result)
    log(
        "Terminé : {} parcelle(s) au départ, {} ligne(s) d'état, "
        "{} parcelle(s) au plan, {} anomalie(s).".format(
            result.csv_count,
            result.etat_count,
            result.plan_count,
            result.comparaison_count,
        )
    )
    return conn, result


def verify(connection_name, schema, commande):
    """Recalcule uniquement la table de comparaison et le bilan, sans
    toucher au staging ni relancer l'import CSV. Utile après une
    modification manuelle des données sources."""
    validate_identifier(schema, "schéma")
    validate_identifier(commande, "commande")
    conn = PgConnection(connection_name)
    with conn.transaction():
        conn.execute(tpl.create_comparaison_sql(schema, commande))

    result = GenerationResult()
    _fill_bilan(conn, schema, commande, result)
    try:
        result.csv_count = _count(conn, schema, tpl.staging_table_name(commande))
    except DbError:
        result.csv_count = 0
    return result


def _fill_bilan(conn, schema, commande, result):
    result.etat_count = _count(conn, schema, tpl.etat_table_name(commande))
    result.plan_count = _count(conn, schema, tpl.plan_table_name(commande))
    result.comparaison_rows = _fetch_comparaison(conn, schema, commande)
    result.comparaison_count = len(result.comparaison_rows)


def _count(conn, schema, table):
    rows = conn.execute("SELECT count(*) FROM {}".format(qualified_table(schema, table)))
    return rows[0][0] if rows else 0


def _fetch_comparaison(conn, schema, commande):
    table = qualified_table(schema, tpl.comparaison_table_name(commande))
    rows = conn.execute(
        "SELECT idpar, anomalie FROM {} ORDER BY anomalie, idpar".format(table)
    )
    return [(r[0], r[1]) for r in rows]
