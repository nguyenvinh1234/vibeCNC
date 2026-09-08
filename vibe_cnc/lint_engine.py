import re
from typing import List, Dict

from .mach3turn_validator import validate_mach3turn
from .machine_profile import MACH3TURN_XHC_MKX_ET


class LintEngine:
    # Rule labels for the codes the parser records. The UI shows this string,
    # so it has to read like the hand-written rules above it.
    PARSER_RULES = {
        "ARC_R_TOO_SMALL": "Arc R",
        "ARC_R_ZERO_CHORD": "Arc R",
        "ARC_NO_CENTER": "Arc",
        "ARC_COMP_TOO_TIGHT": "G41/G42",
        "CYCLE_NO_PASS": "Cycle",
        "CYCLE_NO_DEPTH": "Cycle",
        "CYCLE_NO_CONTOUR": "Cycle",
        "CYCLE_BLOCKS_MISSING": "Cycle",
    }

    # Conservative severity for upstream rules. Controller-specific validators
    # may return their own explicit severity (including FATAL).
    RULE_SEVERITY = {
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

    # How many code-bearing lines count as "the header". Comments and the
    # tape-start '%' do not count: a program that explains itself in a comment
    # block up top still has a header, it just starts further down.
    HEADER_LINES = 5

    def __init__(self, cfg):
        self.cfg = cfg
        p = cfg.data.get("policies", {})
        self.required = p.get("require_header_codes", ["G18", "G40", "G80", "G97"])
        self.req_units = p.get("require_units", "G21")
        self.req_origin = p.get("require_origin", "G54")
        self.protected_m = set(p.get("protected_m_codes", []))
        self.machine_profile_id = cfg.data.get("machine", {}).get("profile")

    def run_all(self, code: str) -> List[Dict]:
        lines = code.splitlines()
        finds = []
        # 1) Header presence.
        #
        # Whole words on stripped code only. A substring search over the raw
        # first five lines accepted "G18" inside "G180" and inside a comment
        # saying the opposite ("kein G18 noetig"), and it missed the header
        # entirely whenever a comment block pushed it past line five.
        header = self._header(lines)
        for token in self.required:
            if not self._has_word(header, token):
                finds.append(self._f(1, "Header", f"{token} expected in header."))
        if self.req_units and not self._has_word(header, self.req_units):
            finds.append(self._f(1, "Units", f"{self.req_units} (mm) expected."))
        if self.req_origin and not self._has_word(header, self.req_origin):
            finds.append(self._f(1, "Origin", f"{self.req_origin} expected."))

        # 2) G50 before G96
        first_g50 = self._first_index(lines, r"\bG50\b")
        first_g96 = self._first_index(lines, r"\bG96\b")
        if first_g96 != -1 and (first_g50 == -1 or first_g50 > first_g96):
            line_num = first_g96 + 1 if first_g96 != -1 else 1
            finds.append(self._f(line_num, "CSS", "G50 must precede first G96."))

        # 3) Protected M-codes must not be commented out.
        #
        # Whether one was removed cannot be decided from a single line; that
        # needs a before/after comparison. What can be decided is that one is
        # still in the file but commented out, which is the form removing it
        # usually takes. The old override rule fired on any line carrying more
        # than one M-code, so a perfectly normal "M62 M08" was reported.
        for i, line in enumerate(lines):
            code_line = self._strip_comments(line)
            for m_code in sorted(self.protected_m):
                pattern = rf"\bM0?{m_code}\b"
                if re.search(pattern, line, re.IGNORECASE) and not re.search(
                    pattern, code_line, re.IGNORECASE
                ):
                    finds.append(
                        self._f(
                            i + 1,
                            "M-Invariant",
                            f"M{m_code} is commented out (invariant).",
                        )
                    )

        # 4) End-of-program retract
        end_idx = max(len(lines) - 3, 0)
        end_block = " ".join(lines[end_idx:])
        # G28 is the reference return and retracts both axes by itself; U/W are
        # the incremental words a Fanuc lathe uses for exactly this move, so
        # looking only for X and Z missed the most common correct ending.
        retracted = (
            re.search(r"\bG28\b", end_block)
            or (
                re.search(r"\b[ZW][-+]?\d", end_block)
                and re.search(r"\b[XU][-+]?\d", end_block)
            )
        )
        if "M30" in end_block and not retracted:
            finds.append(
                self._f(
                    len(lines),
                    "Retract",
                    "Before M30: Move Z to safe plane, then retract X.",
                )
            )

        # 5) G7x sanity (rough)
        for i, line in enumerate(lines):
            if re.search(r"\bG7(0|1|2)\b", line):
                # Read the number rather than pattern-match it. F0.25 is a
                # normal turning feed, not a zero feed.
                feed = self._feed_value(line)
                if feed is not None and feed <= 0.0:
                    finds.append(
                        self._f(i + 1, "G7x", "Feed F must not be 0 or negative.")
                    )
            if re.search(r"\bG76\b", line):
                if not re.search(r"\b[FRS]\d", line):
                    finds.append(
                        self._f(
                            i + 1,
                            "G76",
                            "Threading: Check F/S/R parameters (heuristic).",
                        )
                    )

        # 6) G41/G42 – simple checks (Fanuc TNR)
        comp_active = False
        current_tool = None
        tool_map = {}
        nose_numbers = set()
        tool_table_loaded = False
        try:
            # tool_data needs no GUI stack, so this works on a bare interpreter.
            from .tool_data import NOSE_OFFSETS, load_tools_json

            nose_numbers = set(NOSE_OFFSETS)
            tool_json = load_tools_json()
            for item in tool_json.get("tool_table", []):
                try:
                    tool_map[int(item.get("t", 0))] = item
                except Exception:
                    pass
            tool_table_loaded = True
        except Exception:
            tool_map = {}

        for i, line in enumerate(lines):
            # Skip comments for simple search
            code_line = re.sub(r"\(.*?\)", "", line)
            # Tool change
            tool_match = re.search(r"\bT(\d+)\b", code_line)
            if tool_match:
                try:
                    current_tool = int(tool_match.group(1)) // 100
                except Exception:
                    current_tool = None
                if comp_active:
                    finds.append(
                        self._f(i + 1, "G41/G42", "Cancel G40 before tool change.")
                    )

            # Compensation on/off
            if re.search(r"\bG0?41\b", code_line) or re.search(
                r"\bG0?42\b", code_line
            ):
                comp_active = True
                # Tool radius exists?
                if current_tool is not None and tool_table_loaded:
                    tool = tool_map.get(current_tool, {})
                    radius = self._insert_radius(tool)
                    if radius <= 0.0:
                        finds.append(
                            self._f(
                                i + 1,
                                "G41/G42",
                                f"Tool T{current_tool:02d}: insert_radius_mm missing (tools.json).",
                            )
                        )
                    elif tool.get("nose_direction") not in nose_numbers:
                        finds.append(
                            self._f(
                                i + 1,
                                "G41/G42",
                                f"Tool T{current_tool:02d}: nose_direction missing (tools.json) "
                                "— compensation assumes 0 (nose point = centre).",
                            )
                        )
                # Check lead-in for next move (next line with movement)
                for j in range(i + 1, min(i + 6, len(lines))):
                    nxt = re.sub(r"\(.*?\)", "", lines[j])
                    if re.search(r"\bX[-+]?\d", nxt) or re.search(
                        r"\bZ[-+]?\d", nxt
                    ):
                        if re.search(r"\bG0?0\b", nxt):
                            finds.append(
                                self._f(
                                    j + 1,
                                    "G41/G42",
                                    "Lead-in must not use G00 — use G01.",
                                )
                            )
                        if re.search(r"\bG0?[23]\b", nxt):
                            finds.append(
                                self._f(
                                    j + 1,
                                    "G41/G42",
                                    "Avoid arcs directly after G41/G42 (use linear lead-in).",
                                )
                            )
                        break
            if re.search(r"\bG0?40\b", code_line):
                comp_active = False

        # Open compensation at program end
        if comp_active:
            finds.append(
                self._f(len(lines), "G41/G42", "Set G40 before program end.")
            )

        # 7) Geometry the parser could not make sense of
        finds.extend(self._parser_findings(code))

        # 8) Controller-specific deterministic rules. Only activate them when a
        # machine profile explicitly opts into Mach3Turn so upstream Fanuc users
        # do not suddenly inherit controller-specific blocking rules.
        if self.machine_profile_id == MACH3TURN_XHC_MKX_ET.profile_id:
            finds.extend(validate_mach3turn(code, MACH3TURN_XHC_MKX_ET))

        # Every finding has a severity, including legacy upstream rules.
        finds = [self._ensure_severity(item) for item in finds]

        # One list, in program order, without exact repeats.
        finds = self._dedupe(finds)
        finds.sort(key=lambda finding: finding["line"])
        return finds

    def _header(self, lines) -> str:
        """The first HEADER_LINES lines that carry code, comments removed."""
        code_lines = []
        for line in lines:
            stripped = self._strip_comments(line).lstrip("%").strip()
            if not stripped:
                continue
            code_lines.append(stripped)
            if len(code_lines) >= self.HEADER_LINES:
                break
        return " ".join(code_lines)

    @staticmethod
    def _strip_comments(line: str) -> str:
        return re.sub(r";.*", "", re.sub(r"\(.*?\)", "", line)).strip()

    @staticmethod
    def _has_word(haystack: str, token: str) -> bool:
        return re.search(
            rf"\b{re.escape(token)}\b", haystack, re.IGNORECASE
        ) is not None

    @staticmethod
    def _insert_radius(tool: dict) -> float:
        """The nose radius of one tool record, 0.0 when unusable."""
        try:
            return float(tool.get("insert_radius_mm", 0.0) or 0.0)
        except (AttributeError, TypeError, ValueError):
            return 0.0

    @staticmethod
    def _feed_value(line: str):
        """The F word of a line as a number. None if absent or unparsable."""
        match = re.search(r"\bF([-+]?\d*\.?\d*)", line, re.IGNORECASE)
        if not match:
            return None
        try:
            return float(match.group(1))
        except ValueError:
            return None

    @classmethod
    def _ensure_severity(cls, finding: Dict) -> Dict:
        item = dict(finding)
        item.setdefault("severity", cls.RULE_SEVERITY.get(item.get("rule"), "WARNING"))
        return item

    @staticmethod
    def _dedupe(finds: List[Dict]) -> List[Dict]:
        seen, unique = set(), []
        for finding in finds:
            key = (
                finding["line"],
                finding["rule"],
                finding["message"],
                finding.get("severity"),
            )
            if key not in seen:
                seen.add(key)
                unique.append(finding)
        return unique

    def _parser_findings(self, code: str) -> List[Dict]:
        """Warnings the parser records while building the toolpaths."""
        try:
            from .gcode_parser import GCodeParser

            parser = GCodeParser()
            parser.parse(code)
        except Exception:
            # Linting must never fail because the parser choked on something.
            return []

        return [
            self._f(
                warning["line"],
                self.PARSER_RULES.get(warning["code"], "Geometry"),
                warning["message"],
            )
            for warning in parser.warnings
        ]

    def _first_index(self, lines, pattern):
        regex = re.compile(pattern)
        for i, line in enumerate(lines):
            if regex.search(line):
                return i
        return -1

    def _f(self, line: int, rule: str, msg: str, severity: str = None):
        return {
            "line": line,
            "rule": rule,
            "message": msg,
            "severity": severity or self.RULE_SEVERITY.get(rule, "WARNING"),
        }
