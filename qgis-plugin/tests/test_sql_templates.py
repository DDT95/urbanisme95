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

    def test_vues_courantes_point_to_commande_tables(self):
        sql = tpl.create_vues_courantes_sql("q_26_01_4825", "wk")
        self.assertIn('CREATE VIEW "q_26_01_4825"."etat_p_courant" AS SELECT * FROM "q_26_01_4825"."etat_p_wk"', sql)
        self.assertIn(
            'CREATE VIEW "q_26_01_4825"."plans_parcellaire_courant" AS SELECT * FROM "q_26_01_4825"."plans_parcellaire_wk"',
            sql,
        )
        self.assertIn(
            'CREATE VIEW "q_26_01_4825"."comparaison_parcelles_courant" AS SELECT * FROM "q_26_01_4825"."comparaison_parcelles_wk"',
            sql,
        )

    def test_vues_courantes_rejects_malicious_commande(self):
        with self.assertRaises(InvalidIdentifierError):
            tpl.create_vues_courantes_sql("q_26_01_4825", "wk; DROP SCHEMA public CASCADE; --")

    def test_comparaison_sql_covers_both_directions(self):
        sql = tpl.create_comparaison_sql("q_26_01_4825", "wk")
        self.assertIn("manquant_etat", sql)
        self.assertIn("manquant_plan", sql)
        self.assertIn("hors_csv", sql)

    def test_referentiels_2024_matches_production_query(self):
        refs = tpl.referentiels(2024)
        self.assertEqual(refs["parcelle"], '"x_ff2024_dep"."d95_fftp_2024_pnb10_parcelle"')
        self.assertEqual(refs["suf"], '"x_ff2024_dep"."d95_fftp_2024_pnb21_suf"')
        self.assertEqual(
            refs["proprietaire"],
            '"x_ff2024_non_ano_dep"."d95_fftp_2024_proprietaire_droit_non_ano"',
        )
        self.assertEqual(refs["gpa"], '"r_drieat"."gpa_annexe_1"')

    def test_referentiels_rejects_invalid_millesime(self):
        with self.assertRaises(InvalidIdentifierError):
            tpl.referentiels("abcd")

    def test_referentiels_rejects_unconfigured_millesime(self):
        # Le nommage FF n'étant pas régulier d'un millésime à l'autre, un
        # millésime non explicitement ajouté à REFERENTIELS_PAR_MILLESIME
        # doit échouer clairement plutôt que deviner un nom de table.
        with self.assertRaises(InvalidIdentifierError):
            tpl.referentiels(2025)

    def test_etat_parcellaire_uses_strict_joins_and_sum(self):
        # La requête de production utilise JOIN (pas LEFT JOIN) sur la
        # subdivision fiscale et le propriétaire, avec SUM(drcsuba).
        sql = tpl.create_etat_parcellaire_sql("q_26_01_4825", "wk", 2024)
        self.assertIn('JOIN "x_ff2024_dep"."d95_fftp_2024_pnb21_suf" pnb21', sql)
        self.assertIn(
            'JOIN "x_ff2024_non_ano_dep"."d95_fftp_2024_proprietaire_droit_non_ano" proprio',
            sql,
        )
        # Une seule jointure externe : gpa (les autres sont strictes).
        self.assertEqual(sql.count("LEFT JOIN"), 1)
        self.assertIn('SUM(pnb21."drcsuba")', sql)
        self.assertIn('proprio."dqualp"', sql)
        self.assertIn("GROUP BY", sql)


if __name__ == "__main__":
    unittest.main()
