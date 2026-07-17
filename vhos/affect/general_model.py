"""The General Human Affect Model — reference implementation, v0.

Reads the simulated body into core affect (valence, arousal) plus the
coarse shared vocabulary categories.  This is the prior trained on
humanity at large (spec Part I): how interior weather generally reads.
It knows nothing about any particular subject — the Personal Tuning
Layer (tuning.py) supplies X' minus X.

Deliberately substrate-free (pure stdlib math): the affect subsystem
must survive engine swaps.  A substrate MAY accelerate this call
(Contract 3 read_soma) but is never required.

v0 readout was linear-with-clamps; v0.2 replaces the clamp with tanh
per TR-001 issue I-1 / spec v4.0 Part IX calibration notes: the linear
readout saturated at -1.0 in every distressed run, erasing gradation
exactly where the tuning layer needs room.  Floors should be
reachable, not resident.  Still a transparent baseline the evaluation
harness can beat with learned models later (soma doc §9).
"""

import math

from ..substrate.contract import CoarseAffect


def read_soma(state, params):
    d = state.deviation(params)
    a = d.get("arousal", 0.0)
    t = d.get("tension", 0.0)
    f = d.get("fatigue", 0.0)
    w = d.get("warmth", 0.0)

    # valence: warmth pulls up; tension and fatigue pull down; very
    # high arousal on top of tension reads unpleasant (racing, braced).
    # tanh keeps compound stress graded instead of pinned at the floor
    # (the TR-001 stressed arm now reads ~-0.86 instead of -1.00).
    raw = 1.8 * w - 2.0 * t - 1.2 * f - 0.8 * max(0.0, a - 0.15)
    valence = math.tanh(raw)

    arousal_level = state.values.get("arousal", 0.0)

    categories = []
    # internal quadrant
    if arousal_level >= 0.5:
        categories.append("high-energy distressing" if valence < 0
                          else "high-energy uplifting")
    else:
        categories.append("low-energy distressing" if valence < 0
                          else "low-energy uplifting")
    # body categories
    if arousal_level >= 0.6 or state.values.get("tension", 0.0) >= 0.62:
        categories.append("activated")
    if state.values.get("fatigue", 0.0) >= 0.6:
        categories.append("drained")
    # thinking categories (coarse)
    if state.values.get("tension", 0.0) >= 0.55 and arousal_level >= 0.55:
        categories.append("overloaded")

    return CoarseAffect(valence=round(valence, 3),
                        arousal=round(arousal_level, 3),
                        categories=categories)
