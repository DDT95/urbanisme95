import csv
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from parcellaire_ddt95.core.csv_import import CsvFormatError, read_csv_rows


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


if __name__ == "__main__":
    unittest.main()
