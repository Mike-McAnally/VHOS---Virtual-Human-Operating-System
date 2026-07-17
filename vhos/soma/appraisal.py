"""SOMA v0.1 — appraisal: events -> body impulses.

The general (subject-independent) appraisal table.  Tags are coarse
event classes; values are impulse pushes to soma channels.  This is
the General Human Affect Model's input side: how situations generally
land in a body.  The PERSONAL layer enters as per-channel gain
multipliers taken from the subject's soma_calibration (a reactive
subject amplifies; a phlegmatic one damps).

v0 appraisal is a rule table by design: transparent, testable,
substrate-free.  A future minor version may add an LLM-as-appraiser
through the Abstraction Contract's reason() call — the table remains
the fallback and the test oracle.
"""

from dataclasses import dataclass, field
from typing import Dict, List

APPRAISAL_TABLE = {
    # tag                arousal  tension  fatigue  warmth
    "threat":          {"arousal": +0.40, "tension": +0.35},
    "loss":            {"arousal": +0.10, "fatigue": +0.25, "warmth": -0.20},
    "blocked_goal":    {"arousal": +0.20, "tension": +0.30},
    "novelty":         {"arousal": +0.20, "tension": -0.05},
    "achievement":     {"arousal": +0.15, "warmth": +0.25, "tension": -0.15},
    "social_warmth":   {"warmth": +0.30, "tension": -0.10},
    "social_exposure": {"arousal": +0.25, "tension": +0.20},
    "unfair_dismissal": {"arousal": +0.20, "tension": +0.15},
    "absurdity":       {"arousal": +0.10, "warmth": +0.10, "tension": -0.10},
    "rest":            {"fatigue": -0.30, "tension": -0.15},
    "exertion":        {"arousal": +0.20, "fatigue": +0.20, "tension": -0.25},
}


@dataclass
class Event:
    t: float
    description: str
    tags: List[str]
    magnitude: float = 1.0
    source: str = "runtime"

    def impulses(self, gains=None):
        return appraise(self.tags, self.magnitude, gains)


def appraise(tags, magnitude=1.0, gains=None):
    """Combine table rows for all tags; scale by magnitude and by the
    subject's per-channel gains (personal tuning of the body)."""
    gains = gains or {}
    out: Dict[str, float] = {}
    for tag in tags:
        row = APPRAISAL_TABLE.get(tag)
        if row is None:
            continue
        for channel, push in row.items():
            out[channel] = out.get(channel, 0.0) + push * magnitude
    for channel in list(out):
        out[channel] *= gains.get(channel, 1.0)
    return out
