import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from parcellaire_ddt95.core.identifiers import InvalidIdentifierError
from parcellaire_ddt95.core import sql_templates as tpl


class TestSqlTemplates(unittest.TestCase):
    def test_rejects_malicious_schema(self):
        with self.assertRaises(InvalidIdentifierError):
            tpl.create_staging_table_sql("q_26; DROP TABLE users; --", "wk")

    def test_rejects_malicious_commande(self):
        with self.assertRaises(InvalidIdentifierError):
            tpl.create_etat_parcellaire_sql("q_26_01_4825", "wk'; DROP TABLE etat_p_wk; --", 2024)

    def test_staging_table_sql_contains_quoted_identifiers(self):
        sql = tpl.create_staging_table_sql("q_26_01_4825", "wk")
        self.assertIn('"q_26_01_4825"."data_parcelle_wk"', sql)
        self.assertIn("PRIMARY KEY", sql)

    def test_etat_parcellaire_sql_references_expected_tables(self):
        sql = tpl.create_etat_parcellaire_sql("q_26_01_4825", "wk", 2024)
        self.assertIn('"q_26_01_4825"."etat_p_wk"', sql)
        self.assertIn("x_ff2024_dep", sql)
        self.assertIn("x_ff2024_non_ano_dep", sql)
        self.assertIn("r_drieat", sql)
        self.assertIn("gpa", sql.lower())
        self.assertIn("annee_ff", sql)
        self.assertIn("2024 AS annee_ff", sql)

    def test_adresse_complete_uses_concat_ws_not_plain_concat(self):
        # concat_ws ignore les valeurs NULL ; avec ||, une seule ligne
        # d'adresse vide (NULLIF -> NULL) rendrait toute l'adresse NULL.
        sql = tpl.create_etat_parcellaire_sql("q_26_01_4825", "wk", 2024)
        self.assertIn("concat_ws(E'\\n'", sql)
        self.assertNotIn("'\\n' || NULLIF", sql)

    def test_plans_parcellaire_sql_has_gist_index_and_srid(self):
        sql = tpl.create_plans_parcellaire_sql("q_26_01_4825", "wk", 2024)
        self.assertIn('"q_26_01_4825"."plans_parcellaire_wk"', sql)
        self.assertIn("USING GIST", sql)
        self.assertIn("2154", sql)
        self.assertIn("PRIMARY KEY", sql)

    def test_comparaison_sql_covers_both_directions(self):
        sql = tpl.create_comparaison_sql("q_26_01_4825", "wk")
        self.assertIn("manquant_etat", sql)
        self.assertIn("manquant_plan", sql)
        self.assertIn("hors_csv", sql)

    def test_referentiels_follow_year_pattern(self):
        refs = tpl.referentiels(2025)
        self.assertIn("x_ff2025_dep", refs["parcelle"])
        self.assertIn("d95_fftp_2025_pnb10_parcelle", refs["parcelle"])
        self.assertIn("x_ff2025_non_ano_dep", refs["proprietaire"])

    def test_referentiels_rejects_invalid_millesime(self):
        with self.assertRaises(InvalidIdentifierError):
            tpl.referentiels("abcd")


if __name__ == "__main__":
    unittest.main()
