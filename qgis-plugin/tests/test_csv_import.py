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
    def test_reads_valid_csv_and_rebuilds_id(self):
        # La colonne 'id' du CSV (ici volontairement fausse) doit être
        # ignorée : l'id utilisé est toujours reconstruit depuis
        # commune/prefixe/section/numero.
        path = _write_csv(
            [
                {
                    "id": "CECI_EST_FAUX",
                    "commune": "95510",
                    "prefixe": "",
                    "section": "A",
                    "numero": "327",
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

    def test_works_without_id_or_prefixe_column(self):
        # Cas réel attendu : le CSV ne contient que commune/section/numero.
        path = _write_csv(
            [{"commune": "95510", "section": "A", "numero": "1"}],
            ["commune", "section", "numero"],
        )
        try:
            rows = read_csv_rows(path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["id"], "955100000A0001")
        finally:
            os.remove(path)

    def test_missing_required_column_raises(self):
        path = _write_csv(
            [{"commune": "95510"}],
            ["commune"],
        )
        try:
            with self.assertRaises(CsvFormatError):
                read_csv_rows(path)
        finally:
            os.remove(path)

    def test_incomplete_rows_are_skipped(self):
        path = _write_csv(
            [
                {"commune": "95510", "section": "", "numero": "1"},
                {"commune": "95510", "section": "A", "numero": "1"},
            ],
            ["commune", "section", "numero"],
        )
        try:
            rows = read_csv_rows(path)
            self.assertEqual(len(rows), 1)
        finally:
            os.remove(path)

    def test_all_rows_incomplete_raises(self):
        path = _write_csv(
            [{"commune": "95510", "section": "", "numero": "1"}],
            ["commune", "section", "numero"],
        )
        try:
            with self.assertRaises(CsvFormatError):
                read_csv_rows(path)
        finally:
            os.remove(path)

    def test_combined_section_numero_column_without_comma(self):
        # En-tête réel rencontré : "id,commune,section numero" (virgule
        # manquante avant "numero"), valeurs comme "A 327". La colonne
        # 'id' du CSV est volontairement fausse ici (section AA au lieu
        # de A) pour vérifier qu'elle est bien ignorée.
        fd, path = tempfile.mkstemp(suffix=".csv")
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
            f.write("id,commune,section numero\n")
            f.write("95510000AA0028,95510,A 329\n")
        try:
            rows = read_csv_rows(path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["section"], "A")
            self.assertEqual(rows[0]["numero"], "329")
            self.assertEqual(rows[0]["id"], "955100000A0329")
        finally:
            os.remove(path)

    def test_invalid_numero_raises_with_line_number(self):
        path = _write_csv(
            [{"commune": "95510", "section": "A", "numero": "12A"}],
            ["commune", "section", "numero"],
        )
        try:
            with self.assertRaises(CsvFormatError) as ctx:
                read_csv_rows(path)
            self.assertIn("Ligne 2", str(ctx.exception))
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
