"""Lecture du CSV de parcelles et import dans la table de staging PostgreSQL.

read_csv_rows() est pur Python (aucune dépendance QGIS) et donc testable
sans QGIS installé. insert_rows() insère les lignes via des instructions
INSERT (valeurs échappées par sql_string_literal, jamais d'identifiant
utilisateur concaténé) exécutées sur la MÊME connexion PostgreSQL que le
reste du traitement (core.db.PgConnection.execute) — pas de connexion
séparée : une connexion distincte ouverte pendant que la connexion
principale tient encore un verrou sur la table de staging (créée dans la
même transaction, pas encore validée) resterait bloquée indéfiniment en
attente de ce verrou. C'est exactement ce qui provoquait un blocage
silencieux de QGIS à cette étape.

IMPORTANT : l'idpar utilisé pour la jointure avec le référentiel n'est
JAMAIS pris tel quel dans une éventuelle colonne 'id' du CSV (souvent
absente, ou héritée d'un ancien export qui ne correspond plus au
millésime courant — c'est ce qui provoquait des parcelles "manquantes"
alors que le format semblait correct). Il est reconstruit à chaque fois
à partir de commune/préfixe/section/numéro via core.idpar.build_idpar().
"""

import csv

from .identifiers import qualified_table, sql_string_literal
from .idpar import IdparFormatError, build_idpar

REQUIRED_FIELDS = ("commune", "section", "numero")
OPTIONAL_FIELDS = ("id", "prefixe", "contenance", "created", "updated", "layer")
ALL_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS

# Nombre de lignes par instruction INSERT (évite une requête unique
# démesurée sur un très gros CSV, sans multiplier les allers-retours réseau).
BATCH_SIZE = 500


class CsvFormatError(ValueError):
    pass


def read_csv_rows(path, encoding="utf-8-sig"):
    """Lit le CSV et renvoie une liste de dict avec les colonnes ALL_FIELDS.
    La colonne 'id' du résultat est toujours reconstruite à partir de
    commune/préfixe/section/numéro (une éventuelle colonne 'id' du CSV
    source est ignorée). Ignore les lignes sans commune/section/numéro.
    Lève CsvFormatError si le fichier est vide, si des colonnes
    obligatoires manquent, ou si un idpar ne peut pas être construit."""
    with open(path, newline="", encoding=encoding) as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise CsvFormatError("Le fichier CSV est vide.")
        missing = [c for c in REQUIRED_FIELDS if c not in reader.fieldnames]
        if missing:
            raise CsvFormatError(
                "Colonnes manquantes dans le CSV : " + ", ".join(missing)
            )
        rows = []
        for line_no, raw_row in enumerate(reader, start=2):  # 1 = en-tête
            row = {field: (raw_row.get(field) or "").strip() for field in ALL_FIELDS}
            if not (row["commune"] and row["section"] and row["numero"]):
                continue
            try:
                row["id"] = build_idpar(
                    row["commune"], row.get("prefixe", ""), row["section"], row["numero"]
                )
            except IdparFormatError as exc:
                raise CsvFormatError("Ligne {} du CSV : {}".format(line_no, exc)) from exc
            rows.append(row)

    if not rows:
        raise CsvFormatError(
            "Aucune ligne exploitable (commune/section/numéro) n'a été trouvée."
        )
    return rows


def insert_rows(conn, schema, table, rows, progress=None):
    """Insère les lignes lues du CSV dans la table de staging, par lots,
    sur `conn` (core.db.PgConnection) déjà utilisée pour le reste du
    traitement — dans la même transaction, sans connexion séparée."""
    target = qualified_table(schema, table)
    columns = ", ".join(ALL_FIELDS)
    total = 0
    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start : start + BATCH_SIZE]
        values_sql = ",\n".join(
            "({})".format(
                ", ".join(
                    sql_string_literal(row[field]) if row[field] else "NULL"
                    for field in ALL_FIELDS
                )
            )
            for row in batch
        )
        conn.execute(
            "INSERT INTO {table} ({columns}) VALUES\n{values};".format(
                table=target, columns=columns, values=values_sql
            )
        )
        total += len(batch)
        if progress:
            progress(total, len(rows))
    return total
