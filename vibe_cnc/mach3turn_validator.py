"""Deterministic safety checks for the Mach3Turn/XHC profile.

This module is deliberately independent from PyQt and AI providers.  It must be
possible to run it in CI and before every export.  Findings are plain dicts so
they can be merged with the existing :mod:`lint_engine` output.
"""
import re
from typing import Dict, List, Optional

from .machine_profile import MACH3TURN_XHC_MKX_ET, MachineProfile


SEVERITIES = ("INFO", "WARNING", "ERROR", "FATAL")
BLOCKING_SEVERITIES = frozenset({"ERROR", "FATAL"})
MOTION_CODES = frozenset({0, 1, 2, 3})
NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)"
# G-code words are allowed to touch: X0.37Z-8.5F300 is valid lexical input.
# Therefore these expressions intentionally do not require word boundaries
# between an address value and the following address letter.
AXIS_WORD_RE = re.compile(rf"([XZUW])({NUMBER})", re.IGNORECASE)
WORD_RE = re.compile(rf"[A-Z]{NUMBER}", re.IGNORECASE)
ORPHAN_NUMBER_RE = re.compile(r"(?<![A-Z])(?<![\d.])[-+]?\d+(?:\.\d*)?(?![\d.])", re.IGNORECASE)


def _strip_comments(line: str) -> str:
    line = re.sub(r"\(.*?\)", "", line)
    line = re.sub(r";.*", "", line)
    return line.strip()


def _finding(line: int, rule: str, message: str, severity: str) -> Dict:
    if severity not in SEVERITIES:
        raise ValueError(f"Unsupported severity: {severity}")
    return {
        "line": int(line),
        "rule": rule,
        "message": message,
        "severity": severity,
    }


def _g_codes(code_line: str) -> List[int]:
    return [int(value) for value in re.findall(r"G0*(\d+)", code_line, re.IGNORECASE)]


def _orphan_numbers(code_line: str) -> List[str]:
    """Return numeric literals that are not attached to a G-code address word.

    ``G0 10.`` therefore returns ``["10."]`` while ``G0 X10.``, ``G0X10.`` and
    ``G0 T0101`` return an empty list.  Program numbers such as ``O001`` and
    sequence numbers such as ``N10`` are normal address words and are removed.
    """

    without_words = WORD_RE.sub(" ", code_line.upper())
    # '%' and common punctuation are harmless after the address words are gone.
    without_words = without_words.replace("%", " ")
    return [match.group(0) for match in ORPHAN_NUMBER_RE.finditer(without_words)]


def validate_mach3turn(
    code: str,
    profile: MachineProfile = MACH3TURN_XHC_MKX_ET,
) -> List[Dict]:
    """Validate modal state and malformed motion blocks for Mach3Turn.

    The validator never guesses a missing axis.  Ambiguous numeric motion such
    as ``G0 10.`` is FATAL because deciding whether it meant X10 or Z10 would be
    unsafe on a real lathe.
    """

    findings: List[Dict] = []
    plane: Optional[str] = None
    units: Optional[str] = None
    distance_mode: Optional[str] = None
    feed_mode: Optional[str] = None
    modal_motion: Optional[int] = None
    first_axis_motion_seen = False

    for line_num, raw_line in enumerate(code.splitlines(), 1):
        line = _strip_comments(raw_line)
        if not line or line == "%":
            continue

        g_codes = _g_codes(line)
        explicit_motion = next((g for g in g_codes if g in MOTION_CODES), None)

        # A number with no address letter in an explicit motion block is never
        # repaired automatically.  It is exactly the dangerous `G0 10.` class.
        orphan_numbers = _orphan_numbers(line) if explicit_motion is not None else []
        if orphan_numbers:
            values = ", ".join(orphan_numbers)
            findings.append(_finding(
                line_num,
                "M3T-SYNTAX-001",
                f"Ambiguous motion block contains number(s) without an address: {values}. "
                "Specify X/Z explicitly; the validator will not guess.",
                "FATAL",
            ))

        # Update modal groups in block order.  The last code from a modal group
        # on one block wins, matching how the rest of the simulator treats G-codes.
        for g in g_codes:
            if g in MOTION_CODES:
                modal_motion = g
            elif g in (17, 18, 19):
                plane = f"G{g}"
            elif g in (20, 21):
                units = f"G{g}"
            elif g in (90, 91):
                distance_mode = f"G{g}"
            elif g in (94, 95):
                feed_mode = f"G{g}"

        has_axis = AXIS_WORD_RE.search(line) is not None

        # `G0 T0101` is not silently treated as a move.  It is suspicious but
        # not the same as the malformed orphan-number case above.
        if explicit_motion is not None and not has_axis and not orphan_numbers:
            # G02/G03 can describe a full circle with centre/radius words and no
            # X/Z end point, so do not flag those as axisless here.
            has_arc_geometry = bool(re.search(rf"[IKR]{NUMBER}", line, re.IGNORECASE))
            if explicit_motion in (0, 1) or not has_arc_geometry:
                findings.append(_finding(
                    line_num,
                    "M3T-MOTION-001",
                    "Explicit motion mode has no X/Z/U/W target. Keep modal setup separate from tool/spindle commands.",
                    "WARNING",
                ))

        if not has_axis or modal_motion is None:
            continue

        # Modal state is checked at the point it first matters, not merely by
        # searching the whole file.  A G21 placed after a move does not make the
        # earlier move safe.
        if not first_axis_motion_seen:
            first_axis_motion_seen = True
            if plane is None:
                findings.append(_finding(
                    line_num, "M3T-MODAL-PLANE",
                    f"{profile.required_plane} must be explicit before the first axis move.",
                    "ERROR"))
            if units is None:
                findings.append(_finding(
                    line_num, "M3T-MODAL-UNITS",
                    f"{profile.required_units} units must be explicit before the first axis move.",
                    "ERROR"))
            if profile.require_explicit_distance_mode and distance_mode is None:
                findings.append(_finding(
                    line_num, "M3T-MODAL-DISTANCE",
                    "G90 or G91 must be explicit before the first axis move.",
                    "ERROR"))
            if profile.require_explicit_feed_mode and feed_mode is None:
                findings.append(_finding(
                    line_num, "M3T-MODAL-FEED",
                    "G94 or G95 must be explicit before the first axis move.",
                    "ERROR"))

        if plane is not None and plane != profile.required_plane:
            findings.append(_finding(
                line_num, "M3T-PLANE-MISMATCH",
                f"{plane} is active; profile {profile.profile_id} requires {profile.required_plane} (X-Z plane).",
                "ERROR"))

        if units is not None and units != profile.required_units:
            findings.append(_finding(
                line_num, "M3T-UNITS-MISMATCH",
                f"{units} is active; profile {profile.profile_id} requires {profile.required_units} metric units.",
                "ERROR"))

    # Stable program order makes the lint pane and tests deterministic.
    findings.sort(key=lambda item: (item["line"], SEVERITIES.index(item["severity"])))
    return findings


def blocks_export(findings: List[Dict]) -> bool:
    """True when deterministic validation says a production export must stop."""

    return any(item.get("severity", "WARNING") in BLOCKING_SEVERITIES for item in findings)
