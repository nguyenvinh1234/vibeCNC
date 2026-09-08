"""Machine profiles for controller/dialect-specific safety rules.

The profile is intentionally declarative.  It describes what the validator is
allowed to assume about a machine; it never talks to Mach3, NcEther.dll or any
physical I/O.
"""
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class MachineProfile:
    """Deterministic machine/dialect policy used by parsers and validators."""

    profile_id: str
    dialect: str
    x_mode: str
    tool_count: int
    required_plane: str = "G18"
    required_units: str = "G21"
    allowed_distance_modes: Tuple[str, ...] = ("G90", "G91")
    preferred_distance_mode: str = "G90"
    allowed_feed_modes: Tuple[str, ...] = ("G94", "G95")
    preferred_feed_mode: str = "G94"
    require_explicit_distance_mode: bool = True
    require_explicit_feed_mode: bool = True


MACH3TURN_XHC_MKX_ET = MachineProfile(
    profile_id="MACH3TURN_XHC_MKX_ET",
    dialect="mach3turn",
    # The current Ngoc Viet programs use X as a diameter value.  This is a
    # profile-level fact, not something the parser is allowed to guess per file.
    x_mode="diameter",
    tool_count=8,
    required_plane="G18",
    required_units="G21",
    allowed_distance_modes=("G90", "G91"),
    preferred_distance_mode="G90",
    allowed_feed_modes=("G94", "G95"),
    preferred_feed_mode="G94",
)


PROFILES = {
    MACH3TURN_XHC_MKX_ET.profile_id: MACH3TURN_XHC_MKX_ET,
}


def get_machine_profile(profile_id: str) -> MachineProfile:
    """Return a known profile or raise a clear error for an unknown id."""

    try:
        return PROFILES[profile_id]
    except KeyError as exc:
        raise ValueError(f"Unknown machine profile: {profile_id}") from exc
