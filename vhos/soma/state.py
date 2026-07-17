"""SOMA v0.1 — state schema.

The simulated body: synthetic interior signals the cognitive core is
conditioned to treat as its own bodily feedback (spec Part I).  Spec
v3.0 declared SOMA foundational but gave it no schema; this module is
the schema, per docs/soma-design-v0.1.md.

Four core channels, each in [0,1], chosen from the spec's own list of
analogues ("arousal, tension, fatigue, the autonomic weather"):

    arousal   sympathetic activation      observable analog: heart rate
    tension   muscular/postural bracing   observable analog: jaw, shoulders, EMG
    fatigue   depleted capacity           observable analog: actigraphy, HRV drift
    warmth    social-safety / parasympathetic ease
              observable analog: vocal warmth, facial openness

The visceral end of the build-order gradient (gut, breath, pain) is
RESERVED, not implemented: the spec says defer the visceral end until
SOMA and multimodal capture are mature.  Reserving the names now keeps
future minor versions additive.

Per-channel parameters are exactly what a subject's soma_calibration
section must supply — this is the missing link between the fingerprint
block in HDL Part III and running dynamics:

    baseline  homeostatic set point            (e.g. arousal_baseline_hr)
    tau       return time-constant, seconds    (recovery speed)
    gain      appraisal sensitivity multiplier (reactivity)
    noise     autonomic weather amplitude
"""

from dataclasses import dataclass, field
from typing import Dict

CORE_CHANNELS = ("arousal", "tension", "fatigue", "warmth")
RESERVED_CHANNELS = ("gut", "breath", "pain")


@dataclass
class ChannelParams:
    baseline: float = 0.35
    tau: float = 300.0
    gain: float = 1.0
    noise: float = 0.008


def default_params() -> Dict[str, ChannelParams]:
    """Population prior — the General Human Affect Model's body.  A
    subject's soma_calibration overrides these per channel."""
    return {
        "arousal": ChannelParams(baseline=0.35, tau=120.0, gain=1.0, noise=0.010),
        "tension": ChannelParams(baseline=0.30, tau=300.0, gain=1.0, noise=0.008),
        "fatigue": ChannelParams(baseline=0.25, tau=1800.0, gain=1.0, noise=0.004),
        "warmth":  ChannelParams(baseline=0.40, tau=600.0, gain=1.0, noise=0.006),
    }


@dataclass
class SomaState:
    """A snapshot of the simulated body at time t (seconds)."""
    t: float
    values: Dict[str, float] = field(default_factory=dict)

    def deviation(self, params):
        """Signed deviation of each channel from its baseline."""
        return {c: self.values[c] - params[c].baseline for c in self.values}

    def copy(self):
        return SomaState(t=self.t, values=dict(self.values))
