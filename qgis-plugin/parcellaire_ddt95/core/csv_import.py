"""Lecture du CSV de parcelles et import dans la table de staging PostgreSQL.

read_csv_rows() est pur Python (aucune dépendance QGIS) et donc testable
sans QGIS installé. insert_rows() utilise le fournisseur PostgreSQL natif
de QGIS (QgsVectorLayer / addFeatures) : les valeurs du CSV sont passées
comme attributs de feature, jamais concaténées dans du texte SQL, ce qui
élimine tout risque d'injection sur les données importées.
"""

import csv

REQUIRED_FIELDS = ("id", "commune", "prefixe", "section", "numero", "contenance")
OPTIONAL_FIELDS = ("created", "updated", "layer")
ALL_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS


class CsvFormatError(ValueError):
    pass


def read_csv_rows(path, encoding="utf-8-sig"):
    """Lit le CSV et renvoie une liste de dict avec les colonnes ALL_FIELDS.
    Ignore les lignes sans identifiant 'id'. Lève CsvFormatError si le
    fichier est vide ou si des colonnes obligatoires manquent."""
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
        for raw_row in reader:
            row = {field: (raw_row.get(field) or "").strip() for field in ALL_FIELDS}
            if row["id"]:
                rows.append(row)

    if not rows:
        raise CsvFormatError("Aucune ligne avec un identifiant 'id' n'a été trouvée.")
    return rows


def insert_rows(pg_connection, schema, table, rows):
    """Insère les lignes lues du CSV dans la table de staging PostgreSQL
    via le fournisseur QGIS natif. pg_connection est un core.db.PgConnection
    déjà ouvert sur la connexion PostgreSQL choisie par l'utilisateur."""
    from qgis.core import QgsDataSourceUri, QgsFeature, QgsVectorLayer

    from .db import DbError

    uri = QgsDataSourceUri(pg_connection.uri())
    uri.setDataSource(schema, table, "", "", "ogc_fid")
    layer = QgsVectorLayer(uri.uri(False), "staging_tmp", "postgres")
    if not layer.isValid():
        raise DbError(
            "Impossible d'ouvrir la table de staging {}.{} pour l'import.".format(
                schema, table
            )
        )

    fields = layer.fields()
    features = []
    for row in rows:
        feat = QgsFeature(fields)
        for key, value in row.items():
            idx = fields.indexOf(key)
            if idx >= 0:
                feat.setAttribute(idx, value if value else None)
        features.append(feat)

    provider = layer.dataProvider()
    ok, _ = provider.addFeatures(features)
    if not ok:
        raise DbError(
            "Échec de l'import CSV dans {}.{} : {}".format(
                schema, table, provider.lastError().message()
            )
        )
    return len(features)
