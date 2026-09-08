"""Composite deterministic safety gate for vibeCNC.

This keeps the existing upstream linter intact while adding controller-specific
validation and a single export decision.  AI output must pass through this
engine before a production export is allowed.
"""
from typing import Dict, List

from .lint_engine import LintEngine
from .mach3turn_validator import BLOCKING_SEVERITIES, SEVERITIES, validate_mach3turn
from .machine_profile import MACH3TURN_XHC_MKX_ET


# Conservative defaults for upstream lint rules when running a production
# Mach3Turn profile.  The existing linter did not have severities, so the wrapper
# adds them without changing its API or risking upstream test regressions.
BASE_RULE_SEVERITY = {
    "Header": "ERROR",
    "Units": "ERROR",
    "Origin": "ERROR",
    "CSS": "ERROR",
    "M-Invariant": "ERROR",
    "Retract": "ERROR",
    "G7x": "ERROR",
    "G76": "WARNING",
    "G41/G42": "ERROR",
    "Arc R": "ERROR",
    "Arc": "ERROR",
    "Cycle": "ERROR",
    "Geometry": "ERROR",
}


class SafetyEngine:
    """Run upstream lint plus the selected machine-profile validator."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.base_linter = LintEngine(cfg)
        machine = cfg.data.get("machine", {}) if hasattr(cfg, "data") else {}
        self.profile_id = machine.get("profile")

    @staticmethod
    def _with_severity(finding: Dict) -> Dict:
        item = dict(finding)
        item.setdefault("severity", BASE_RULE_SEVERITY.get(item.get("rule"), "WARNING"))
        return item

    @staticmethod
    def _dedupe(findings: List[Dict]) -> List[Dict]:
        # If two validators report the same rule/message, keep the more severe
        # one rather than presenting duplicate lines to the operator.
        rank = {name: index for index, name in enumerate(SEVERITIES)}
        by_key = {}
        for finding in findings:
            item = dict(finding)
            item.setdefault("severity", "WARNING")
            key = (item.get("line"), item.get("rule"), item.get("message"))
            old = by_key.get(key)
            if old is None or rank[item["severity"]] > rank[old["severity"]]:
                by_key[key] = item
        return sorted(
            by_key.values(),
            key=lambda item: (item.get("line", 0), rank.get(item.get("severity"), 1)),
        )

    def run_all(self, code: str) -> List[Dict]:
        findings = [self._with_severity(item) for item in self.base_linter.run_all(code)]

        if self.profile_id == MACH3TURN_XHC_MKX_ET.profile_id:
            findings.extend(validate_mach3turn(code, MACH3TURN_XHC_MKX_ET))

        return self._dedupe(findings)

    @staticmethod
    def blocks_export(findings: List[Dict]) -> bool:
        return any(item.get("severity", "WARNING") in BLOCKING_SEVERITIES for item in findings)

    def can_export(self, code: str) -> bool:
        return not self.blocks_export(self.run_all(code))
