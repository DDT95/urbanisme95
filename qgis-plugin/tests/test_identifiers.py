import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from parcellaire_ddt95.core.identifiers import (
    InvalidIdentifierError,
    qualified_table,
    quote_ident,
    validate_identifier,
    validate_millesime,
)


class TestValidateIdentifier(unittest.TestCase):
    def test_accepts_simple_names(self):
        self.assertEqual(validate_identifier("q_26_01_4825"), "q_26_01_4825")
        self.assertEqual(validate_identifier("wk"), "wk")

    def test_rejects_uppercase(self):
        with self.assertRaises(InvalidIdentifierError):
            validate_identifier("WK")

    def test_rejects_leading_digit(self):
        with self.assertRaises(InvalidIdentifierError):
            validate_identifier("1wk")

    def test_rejects_sql_injection_attempt(self):
        with self.assertRaises(InvalidIdentifierError):
            validate_identifier("wk; DROP TABLE foo; --")

    def test_rejects_quote_characters(self):
        with self.assertRaises(InvalidIdentifierError):
            validate_identifier('wk"; SELECT 1')

    def test_rejects_empty(self):
        with self.assertRaises(InvalidIdentifierError):
            validate_identifier("")

    def test_rejects_non_string(self):
        with self.assertRaises(InvalidIdentifierError):
            validate_identifier(None)


class TestQuoteIdent(unittest.TestCase):
    def test_wraps_in_double_quotes(self):
        self.assertEqual(quote_ident("wk"), '"wk"')

    def test_escapes_internal_double_quotes(self):
        self.assertEqual(quote_ident('a"b'), '"a""b"')

    def test_qualified_table(self):
        self.assertEqual(
            qualified_table("q_26_01_4825", "etat_p_wk"),
            '"q_26_01_4825"."etat_p_wk"',
        )


class TestValidateMillesime(unittest.TestCase):
    def test_accepts_valid_year(self):
        self.assertEqual(validate_millesime(2024), 2024)
        self.assertEqual(validate_millesime("2025"), 2025)

    def test_rejects_out_of_range(self):
        with self.assertRaises(InvalidIdentifierError):
            validate_millesime(1999)

    def test_rejects_non_numeric(self):
        with self.assertRaises(InvalidIdentifierError):
            validate_millesime("wk")


if __name__ == "__main__":
    unittest.main()
