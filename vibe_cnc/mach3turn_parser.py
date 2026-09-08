"""Mach3Turn-aware wrapper around the upstream Fanuc lathe parser.

The upstream parser intentionally treats X/Z as absolute and U/W as
incremental.  Mach3Turn programs can also switch G90/G91, so this wrapper
normalizes G91 X/Z targets into absolute coordinates before passing the program
to the proven geometry parser.  The original source text is never modified on
disk.
"""
from dataclasses import dataclass
import re
from typing import Dict, List, Optional

from .gcode_parser import GCodeParser, NON_MOTION_CODES
from .machine_profile import MACH3TURN_XHC_MKX_ET, MachineProfile


NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)"


@dataclass(frozen=True)
class ModalState:
    plane: Optional[str]
    units: Optional[str]
    distance_mode: Optional[str]
    feed_mode: Optional[str]
    compensation: str
    motion: Optional[str]


class Mach3TurnGCodeParser:
    """Mach3Turn modal front-end with the existing geometry parser as backend."""

    def __init__(
        self,
        chuck_z: float = -5.0,
        chuck_diameter: float = None,
        profile: MachineProfile = MACH3TURN_XHC_MKX_ET,
    ):
        self.profile = profile
        self.backend = GCodeParser(chuck_z=chuck_z, chuck_diameter=chuck_diameter)
        self.modal_history: Dict[int, ModalState] = {}
        self.normalized_code = ""
        self.warnings: List[dict] = []
        self.reset()

    def reset(self):
        self.plane = None
        self.units = None
        self.distance_mode = None
        self.feed_mode = None
        self.compensation = "G40"
        self.motion = None
        self.x = 0.0
        self.z = 0.0
        self.modal_history = {}
        self.normalized_code = ""
        self.warnings = []

    @staticmethod
    def _strip_comments(line: str) -> str:
        line = re.sub(r"\(.*?\)", "", line)
        return re.sub(r";.*", "", line).strip()

    @staticmethod
    def _g_codes(line: str) -> List[int]:
        # G-code words may be adjacent (for example G21G18G90G94).
        return [int(value) for value in re.findall(r"G0*(\d+)", line, re.IGNORECASE)]

    @staticmethod
    def _replace_axis(line: str, axis: str, value: float) -> str:
        pattern = re.compile(rf"{axis}{NUMBER}", re.IGNORECASE)
        return pattern.sub(f"{axis}{value:.12g}", line, count=1)

    def _snapshot(self) -> ModalState:
        return ModalState(
            plane=self.plane,
            units=self.units,
            distance_mode=self.distance_mode,
            feed_mode=self.feed_mode,
            compensation=self.compensation,
            motion=self.motion,
        )

    def _normalize_distance_modes(self, gcode: str) -> str:
        out: List[str] = []

        for line_num, raw_line in enumerate(gcode.splitlines(), 1):
            code_line = self._strip_comments(raw_line)
            g_codes = self._g_codes(code_line)

            for g in g_codes:
                if g in (0, 1, 2, 3):
                    self.motion = f"G{g:02d}"
                elif g in (17, 18, 19):
                    self.plane = f"G{g}"
                elif g in (20, 21):
                    self.units = f"G{g}"
                elif g in (90, 91):
                    self.distance_mode = f"G{g}"
                elif g in (94, 95):
                    self.feed_mode = f"G{g}"
                elif g in (40, 41, 42):
                    self.compensation = f"G{g}"

            self.modal_history[line_num] = self._snapshot()

            # Parameter blocks must retain X/Z as parameters.  Converting them
            # into coordinates would recreate the exact class of false moves the
            # upstream parser carefully avoids.
            if any(g in NON_MOTION_CODES for g in g_codes):
                out.append(code_line)
                continue

            x_match = re.search(rf"X({NUMBER})", code_line, re.IGNORECASE)
            z_match = re.search(rf"Z({NUMBER})", code_line, re.IGNORECASE)
            # Normalization is parser-only, so comments are intentionally omitted
            # while line count is preserved.  This prevents an X/Z written inside
            # a comment from being replaced as if it were executable code.
            transformed = code_line

            if self.distance_mode == "G91":
                if x_match:
                    self.x += float(x_match.group(1))
                    transformed = self._replace_axis(transformed, "X", self.x)
                if z_match:
                    self.z += float(z_match.group(1))
                    transformed = self._replace_axis(transformed, "Z", self.z)
            else:
                # Unknown mode is left geometrically compatible with the
                # upstream absolute parser.  The safety validator blocks export
                # until G90/G91 is explicit, so this fallback is for viewing only.
                if x_match:
                    self.x = float(x_match.group(1))
                if z_match:
                    self.z = float(z_match.group(1))

            out.append(transformed)

        return "\n".join(out)

    def parse(self, gcode: str) -> dict:
        self.reset()
        self.normalized_code = self._normalize_distance_modes(gcode)
        paths = self.backend.parse(self.normalized_code)
        self.warnings.extend(self.backend.warnings)
        # Final coordinates come from the geometry backend so arcs/cycles remain
        # authoritative when they are involved.
        self.x = self.backend.x
        self.z = self.backend.z
        return paths
