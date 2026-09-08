"""Diagnostic : compare les colonnes attendues (column_mapping.py) aux
colonnes réellement présentes dans les tables Fichiers Fonciers, pour
détecter rapidement un écart de nomenclature avant de lancer une commande.
"""

from . import column_mapping as cm
from .db import PgConnection
from .sql_templates import referentiels


def diagnose(connection_name, millesime):
    conn = PgConnection(connection_name)
    refs = referentiels(millesime)

    expected = {
        "parcelle": set(cm.PARCELLE_COLUMNS.values()),
        "suf": set(cm.SUF_COLUMNS.values()),
        "proprietaire": set(cm.PROPRIETAIRE_COLUMNS.values()),
    }

    report = []
    for key in ("parcelle", "suf", "proprietaire"):
        # refs[key] est déjà un identifiant qualifié et échappé, ex: "schema"."table"
        schema_quoted, table_quoted = refs[key].split(".", 1)
        schema = schema_quoted.strip('"').replace('""', '"')
        table = table_quoted.strip('"').replace('""', '"')
        rows = conn.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = {schema} AND table_name = {table}".format(
                schema=_sql_literal(schema), table=_sql_literal(table)
            )
        )
        actual = {r[0] for r in rows}
        missing = sorted(expected[key] - actual)
        report.append((key, refs[key], sorted(actual), missing))
    return report


def _sql_literal(value):
    """Échappe une chaîne comme littéral SQL (guillemets simples doublés).
    Utilisé uniquement pour des valeurs déjà validées comme identifiants
    (voir identifiers.validate_identifier), jamais pour du texte libre."""
    return "'" + value.replace("'", "''") + "'"
