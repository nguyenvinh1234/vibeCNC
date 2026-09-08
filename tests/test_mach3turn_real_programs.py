import os
import unittest

from vibe_cnc.mach3turn_parser import Mach3TurnGCodeParser
from vibe_cnc.mach3turn_validator import blocks_export, validate_mach3turn


FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "mach3turn")


def load_fixture(name):
    with open(os.path.join(FIXTURE_DIR, name), "r", encoding="utf-8") as handle:
        return handle.read()


class Mach3TurnRealProgramRegressionTests(unittest.TestCase):
    """Regression tests copied from the machine programs supplied by the user."""

    def test_thu1_keeps_t0101_and_has_no_orphan_number_fatal(self):
        code = load_fixture("thu1.nc")

        paths = Mach3TurnGCodeParser(chuck_z=-1000.0).parse(code)
        findings = validate_mach3turn(code)

        self.assertEqual(paths["tool_changes"][0]["tool"], 1)
        self.assertEqual([f for f in findings if f["rule"] == "M3T-SYNTAX-001"], [])
        # The real file intentionally has no explicit modal safety header yet,
        # so it must remain blocked until G18/G21/G90/G94-or-G95 are confirmed.
        self.assertTrue(blocks_export(findings))

    def test_tiep_keeps_t0404_and_g0_10_is_fatal(self):
        code = load_fixture("tiep_invalid.nc")

        paths = Mach3TurnGCodeParser(chuck_z=-1000.0).parse(code)
        findings = validate_mach3turn(code)
        fatal = [f for f in findings if f["rule"] == "M3T-SYNTAX-001"]

        self.assertEqual(paths["tool_changes"][0]["tool"], 4)
        self.assertEqual(len(fatal), 1)
        self.assertEqual(fatal[0]["line"], 11)
        self.assertEqual(fatal[0]["severity"], "FATAL")
        self.assertTrue(blocks_export(findings))

    def test_real_programs_keep_spindle_and_feed_text_unchanged(self):
        thu1 = load_fixture("thu1.nc")
        tiep = load_fixture("tiep_invalid.nc")

        self.assertIn("S350 M4", thu1)
        self.assertIn("F300", thu1)
        self.assertIn("S350 M4", tiep)
        self.assertIn("F350", tiep)


if __name__ == "__main__":
    unittest.main()
