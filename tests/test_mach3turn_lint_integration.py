import unittest
from types import SimpleNamespace

from vibe_cnc.lint_engine import LintEngine


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


class Mach3TurnLintIntegrationTests(unittest.TestCase):
    def test_profile_linter_surfaces_g0_10_as_fatal(self):
        engine = LintEngine(make_cfg())
        code = "G21 G18 G90 G94\nG0 X60. Z0.\nG0 10."

        findings = engine.run_all(code)
        fatal = [f for f in findings if f["rule"] == "M3T-SYNTAX-001"]

        self.assertEqual(len(fatal), 1)
        self.assertEqual(fatal[0]["severity"], "FATAL")
        self.assertEqual(fatal[0]["line"], 3)

    def test_legacy_lint_findings_have_severity(self):
        engine = LintEngine(make_cfg(profile=None, require_header_codes=["G40"]))

        findings = engine.run_all("G00 X10. Z5.")
        header = [f for f in findings if f["rule"] == "Header"]

        self.assertEqual(len(header), 1)
        self.assertEqual(header[0]["severity"], "ERROR")

    def test_no_machine_profile_keeps_mach3turn_rules_off(self):
        engine = LintEngine(make_cfg(profile=None))

        findings = engine.run_all("G0 10.")

        self.assertFalse(any(f["rule"].startswith("M3T-") for f in findings))


if __name__ == "__main__":
    unittest.main()
