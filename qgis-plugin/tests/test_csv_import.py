import csv
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from parcellaire_ddt95.core.csv_import import CsvFormatError, insert_rows, read_csv_rows


def _write_csv(rows, fieldnames):
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


class TestReadCsvRows(unittest.TestCase):
    def test_reads_valid_csv(self):
        path = _write_csv(
            [
                {
                    "id": "955100000A0327",
                    "commune": "95510",
                    "prefixe": "",
                    "section": "A",
                    "numero": "0327",
                    "contenance": "1200",
                }
            ],
            ["id", "commune", "prefixe", "section", "numero", "contenance"],
        )
        try:
            rows = read_csv_rows(path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["id"], "955100000A0327")
            self.assertEqual(rows[0]["created"], "")
        finally:
            os.remove(path)

    def test_missing_required_column_raises(self):
        path = _write_csv(
            [{"id": "1", "commune": "95510"}],
            ["id", "commune"],
        )
        try:
            with self.assertRaises(CsvFormatError):
                read_csv_rows(path)
        finally:
            os.remove(path)

    def test_empty_id_rows_are_skipped(self):
        path = _write_csv(
            [
                {
                    "id": "",
                    "commune": "95510",
                    "prefixe": "",
                    "section": "A",
                    "numero": "1",
                    "contenance": "100",
                },
                {
                    "id": "955100000A0001",
                    "commune": "95510",
                    "prefixe": "",
                    "section": "A",
                    "numero": "1",
                    "contenance": "100",
                },
            ],
            ["id", "commune", "prefixe", "section", "numero", "contenance"],
        )
        try:
            rows = read_csv_rows(path)
            self.assertEqual(len(rows), 1)
        finally:
            os.remove(path)

    def test_all_rows_empty_id_raises(self):
        path = _write_csv(
            [
                {
                    "id": "",
                    "commune": "95510",
                    "prefixe": "",
                    "section": "A",
                    "numero": "1",
                    "contenance": "100",
                }
            ],
            ["id", "commune", "prefixe", "section", "numero", "contenance"],
        )
        try:
            with self.assertRaises(CsvFormatError):
                read_csv_rows(path)
        finally:
            os.remove(path)


class _FakeConn:
    """Simule core.db.PgConnection : accumule les instructions SQL passées
    à execute(), sans dépendance QGIS, pour tester insert_rows() seule."""

    def __init__(self):
        self.statements = []

    def execute(self, sql):
        self.statements.append(sql)


class TestInsertRows(unittest.TestCase):
    def test_uses_single_connection_no_separate_provider(self):
        # insert_rows ne doit plus ouvrir de QgsVectorLayer/connexion
        # séparée : tout passe par conn.execute() sur la connexion fournie
        # (sinon : blocage si la table est encore verrouillée dans la
        # transaction en cours sur l'autre connexion).
        conn = _FakeConn()
        rows = [{"id": "1", "commune": "95510", "prefixe": "", "section": "A",
                 "numero": "1", "contenance": "100", "created": "", "updated": "", "layer": ""}]
        total = insert_rows(conn, "q_26_01_4825", "data_parcelle_wk", rows)
        self.assertEqual(total, 1)
        self.assertEqual(len(conn.statements), 1)
        self.assertIn('INSERT INTO "q_26_01_4825"."data_parcelle_wk"', conn.statements[0])

    def test_escapes_single_quotes_in_values(self):
        conn = _FakeConn()
        rows = [{"id": "1", "commune": "95510", "prefixe": "", "section": "A",
                 "numero": "1", "contenance": "100", "created": "note d'import",
                 "updated": "", "layer": ""}]
        insert_rows(conn, "q_26_01_4825", "data_parcelle_wk", rows)
        self.assertIn("note d''import", conn.statements[0])
        self.assertNotIn("note d'import'", conn.statements[0])

    def test_batches_large_row_counts(self):
        conn = _FakeConn()
        rows = [
            {"id": str(i), "commune": "95510", "prefixe": "", "section": "A",
             "numero": str(i), "contenance": "100", "created": "", "updated": "", "layer": ""}
            for i in range(1200)
        ]
        total = insert_rows(conn, "q_26_01_4825", "data_parcelle_wk", rows)
        self.assertEqual(total, 1200)
        self.assertEqual(len(conn.statements), 3)  # 500 + 500 + 200


if __name__ == "__main__":
    unittest.main()
