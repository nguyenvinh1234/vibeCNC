import unittest

from vibe_cnc.machine_profile import MACH3TURN_XHC_MKX_ET, get_machine_profile
from vibe_cnc.mach3turn_validator import blocks_export, validate_mach3turn


class MachineProfileTests(unittest.TestCase):
    def test_ngoc_viet_profile_is_mach3turn_diameter_mode(self):
        profile = get_machine_profile("MACH3TURN_XHC_MKX_ET")

        self.assertEqual(profile.dialect, "mach3turn")
        self.assertEqual(profile.x_mode, "diameter")
        self.assertEqual(profile.tool_count, 8)
        self.assertEqual(profile.required_plane, "G18")
        self.assertEqual(profile.required_units, "G21")


class Mach3TurnValidatorTests(unittest.TestCase):
    def test_clean_explicit_header_is_not_blocked(self):
        code = "G21 G18 G90 G94\nG0 X60. Z10.\nG1 X45. Z-20. F300\nM30"

        findings = validate_mach3turn(code)

        self.assertEqual(findings, [])
        self.assertFalse(blocks_export(findings))

    def test_compact_words_without_spaces_are_valid(self):
        code = "G21G18G90G94\nG0X60.Z10.\nG1X45.Z-20.F300\nM30"

        findings = validate_mach3turn(code)

        self.assertEqual(findings, [])
        self.assertFalse(blocks_export(findings))

    def test_real_style_z_and_feed_can_touch(self):
        code = "G21 G18 G90 G94\nG0 X5. Z0.\nG1 Z-8.5F300"

        findings = validate_mach3turn(code)

        self.assertEqual(findings, [])

    def test_g0_orphan_number_is_fatal_and_never_guessed(self):
        code = "G21 G18 G90 G94\nG0 X60. Z0.\nG0 10.\nM30"

        findings = validate_mach3turn(code)
        syntax = [f for f in findings if f["rule"] == "M3T-SYNTAX-001"]

        self.assertEqual(len(syntax), 1)
        self.assertEqual(syntax[0]["line"], 3)
        self.assertEqual(syntax[0]["severity"], "FATAL")
        self.assertIn("will not guess", syntax[0]["message"])
        self.assertTrue(blocks_export(findings))

    def test_axisless_g0_with_tool_is_warning_not_an_axis_guess(self):
        code = "G21 G18 G90 G94\nG0 T0101\nG0 X60. Z10."

        findings = validate_mach3turn(code)
        motion = [f for f in findings if f["rule"] == "M3T-MOTION-001"]

        self.assertEqual(len(motion), 1)
        self.assertEqual(motion[0]["line"], 2)
        self.assertEqual(motion[0]["severity"], "WARNING")
        self.assertFalse(blocks_export(findings))

    def test_missing_modal_state_blocks_at_first_axis_move(self):
        findings = validate_mach3turn("G0 X10. Z5.\nM30")
        rules = {f["rule"] for f in findings}

        self.assertIn("M3T-MODAL-PLANE", rules)
        self.assertIn("M3T-MODAL-UNITS", rules)
        self.assertIn("M3T-MODAL-DISTANCE", rules)
        self.assertIn("M3T-MODAL-FEED", rules)
        self.assertTrue(blocks_export(findings))

    def test_g91_is_an_allowed_explicit_distance_mode(self):
        findings = validate_mach3turn("G21 G18 G91 G94\nG0 X10. Z5.")

        self.assertNotIn("M3T-MODAL-DISTANCE", [f["rule"] for f in findings])

    def test_g95_is_an_allowed_explicit_feed_mode(self):
        findings = validate_mach3turn("G21 G18 G90 G95\nG1 X10. Z-5. F0.2")

        self.assertNotIn("M3T-MODAL-FEED", [f["rule"] for f in findings])

    def test_wrong_plane_is_blocking(self):
        findings = validate_mach3turn("G21 G17 G90 G94\nG0 X10. Z5.")
        mismatch = [f for f in findings if f["rule"] == "M3T-PLANE-MISMATCH"]

        self.assertEqual(len(mismatch), 1)
        self.assertEqual(mismatch[0]["severity"], "ERROR")
        self.assertTrue(blocks_export(findings))

    def test_comment_does_not_satisfy_modal_header(self):
        findings = validate_mach3turn("(G21 G18 G90 G94)\nG0 X10. Z5.")
        rules = {f["rule"] for f in findings}

        self.assertIn("M3T-MODAL-PLANE", rules)
        self.assertIn("M3T-MODAL-UNITS", rules)

    def test_profile_argument_is_explicit(self):
        findings = validate_mach3turn(
            "G21 G18 G90 G94\nG0 X10. Z5.",
            profile=MACH3TURN_XHC_MKX_ET,
        )

        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
