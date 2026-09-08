import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from parcellaire_ddt95.core.idpar import IdparFormatError, build_idpar


class TestBuildIdpar(unittest.TestCase):
    def test_single_letter_section_is_left_padded(self):
        # Exemple réel confirmé en base : 955100000A0001
        self.assertEqual(build_idpar("95510", "", "A", "1"), "955100000A0001")
        self.assertEqual(build_idpar("95510", "000", "A", "0001"), "955100000A0001")

    def test_two_letter_section_kept_as_is(self):
        self.assertEqual(build_idpar("95510", "", "AA", "28"), "95510000AA0028")

    def test_missing_prefixe_defaults_to_zeros(self):
        self.assertEqual(build_idpar("95510", None, "A", "1"), "955100000A0001")

    def test_commune_left_padded_if_short(self):
        self.assertEqual(build_idpar("510", "", "A", "1"), "005100000A0001")

    def test_rejects_non_numeric_commune(self):
        with self.assertRaises(IdparFormatError):
            build_idpar("9551X", "", "A", "1")

    def test_rejects_non_numeric_numero(self):
        with self.assertRaises(IdparFormatError):
            build_idpar("95510", "", "A", "12A")

    def test_rejects_section_too_long(self):
        with self.assertRaises(IdparFormatError):
            build_idpar("95510", "", "ABC", "1")

    def test_rejects_empty_commune(self):
        with self.assertRaises(IdparFormatError):
            build_idpar("", "", "A", "1")

    def test_section_lowercase_is_uppercased(self):
        self.assertEqual(build_idpar("95510", "", "a", "1"), "955100000A0001")


if __name__ == "__main__":
    unittest.main()
