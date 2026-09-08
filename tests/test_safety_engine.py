import unittest
from types import SimpleNamespace

from vibe_cnc.safety_engine import SafetyEngine


def make_cfg(profile="MACH3TURN_XHC_MKX_ET", **policy_overrides):
    policies = {
        "require_header_codes": [],
        "require_units": None,
        "require_origin": None,
        "protected_m_codes": [],
    }
    policies.update(policy_overrides)
    machine = {"profile": profile} if profile else {}
    return SimpleNamespace(data={"machine": machine, "policies": policies})


class SafetyEngineTests(unittest.TestCase):
    def test_mach3turn_fatal_blocks_export(self):
        engine = SafetyEngine(make_cfg())
        code = "G21 G18 G90 G94\nG0 X60. Z0.\nG0 10."

        findings = engine.run_all(code)

        fatal = [f for f in findings if f["severity"] == "FATAL"]
        self.assertEqual(len(fatal), 1)
        self.assertFalse(engine.can_export(code))

    def test_clean_mach3turn_program_can_pass_core_gate(self):
        engine = SafetyEngine(make_cfg())
        code = "G21 G18 G90 G94\nG0 X60. Z10.\nG1 X45. Z-20. F300"

        findings = engine.run_all(code)

        self.assertEqual(findings, [])
        self.assertTrue(engine.can_export(code))

    def test_upstream_lint_findings_receive_severity(self):
        engine = SafetyEngine(make_cfg(require_header_codes=["G40"]))

        findings = engine.run_all("G21 G18 G90 G94\nG0 X10. Z5.")
        header = [f for f in findings if f["rule"] == "Header"]

        self.assertEqual(len(header), 1)
        self.assertEqual(header[0]["severity"], "ERROR")
        self.assertFalse(engine.can_export("G21 G18 G90 G94\nG0 X10. Z5."))

    def test_no_profile_does_not_inject_mach3turn_rules(self):
        engine = SafetyEngine(make_cfg(profile=None))

        findings = engine.run_all("G0 10.")

        self.assertEqual([f for f in findings if f["rule"].startswith("M3T-")], [])


if __name__ == "__main__":
    unittest.main()
