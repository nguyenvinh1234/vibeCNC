import unittest

from vibe_cnc.mach3turn_parser import Mach3TurnGCodeParser


class Mach3TurnModalParserTests(unittest.TestCase):
    def test_g91_xz_are_incremental(self):
        parser = Mach3TurnGCodeParser(chuck_z=-1000.0)

        paths = parser.parse("\n".join([
            "G21 G18 G90 G94",
            "G00 X10. Z5.",
            "G91",
            "G01 X5. Z-2. F300",
        ]))

        self.assertEqual(paths["cut"], [[(10.0, 5.0), (15.0, 3.0), 4]])
        self.assertAlmostEqual(parser.x, 15.0)
        self.assertAlmostEqual(parser.z, 3.0)

    def test_compact_g91_z_word_with_feed_is_incremental(self):
        parser = Mach3TurnGCodeParser(chuck_z=-1000.0)

        paths = parser.parse("\n".join([
            "G21G18G90G94",
            "G0X10.Z5.",
            "G91",
            "G1Z-2.F300",
        ]))

        self.assertEqual(paths["cut"], [[(10.0, 5.0), (10.0, 3.0), 4]])
        self.assertAlmostEqual(parser.z, 3.0)

    def test_g90_and_g91_do_not_produce_the_same_target(self):
        absolute = Mach3TurnGCodeParser(chuck_z=-1000.0).parse("\n".join([
            "G21 G18 G90 G94",
            "G00 X10. Z5.",
            "G01 X5. Z-2. F300",
        ]))
        incremental = Mach3TurnGCodeParser(chuck_z=-1000.0).parse("\n".join([
            "G21 G18 G90 G94",
            "G00 X10. Z5.",
            "G91",
            "G01 X5. Z-2. F300",
        ]))

        self.assertEqual(absolute["cut"][0][1], (5.0, -2.0))
        self.assertEqual(incremental["cut"][0][1], (15.0, 3.0))
        self.assertNotEqual(absolute["cut"][0][1], incremental["cut"][0][1])

    def test_switching_back_to_g90_restores_absolute_targets(self):
        parser = Mach3TurnGCodeParser(chuck_z=-1000.0)

        paths = parser.parse("\n".join([
            "G21 G18 G90 G94",
            "G00 X10. Z5.",
            "G91",
            "G01 X5. Z-2. F300",
            "G90",
            "G01 X20. Z-10.",
        ]))

        self.assertEqual(paths["cut"][0][1], (15.0, 3.0))
        self.assertEqual(paths["cut"][1][1], (20.0, -10.0))

    def test_modal_state_tracks_feed_and_plane(self):
        parser = Mach3TurnGCodeParser()

        parser.parse("G21 G18 G90 G95\nG00 X10. Z5.")
        state = parser.modal_history[2]

        self.assertEqual(state.units, "G21")
        self.assertEqual(state.plane, "G18")
        self.assertEqual(state.distance_mode, "G90")
        self.assertEqual(state.feed_mode, "G95")
        self.assertEqual(state.motion, "G00")

    def test_non_motion_parameter_xz_are_not_rewritten_in_g91(self):
        parser = Mach3TurnGCodeParser()

        parser.parse("G91\nG50 X100. Z50.")

        self.assertIn("G50 X100. Z50.", parser.normalized_code)
        self.assertAlmostEqual(parser.x, 0.0)
        self.assertAlmostEqual(parser.z, 0.0)


if __name__ == "__main__":
    unittest.main()
