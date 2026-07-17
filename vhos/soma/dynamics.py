"""SOMA v0.1 — dynamics.

Each channel is a leaky integrator with homeostatic return:

    dx/dt = -(x - baseline) / tau  +  gain * impulse(t)  +  weather

discretized with a forward Euler step and clamped to [0,1].
``weather`` is small Gaussian noise scaled by sqrt(dt) — the autonomic
weather the spec names: the body is never perfectly still.

Two cross-couplings copy gross physiology and are deliberately the
only ones in v0.1 (more couplings = more ways to be wrong):

    arousal above baseline slowly ACCRUES fatigue   (activation costs)
    warmth above baseline slowly RELEASES tension   (safety un-braces)

Provable properties, unit-tested in tests/test_dynamics.py:
    * bounded: every value stays in [0,1] under any impulse sequence
    * homeostatic: with no input and no noise, decays to baseline
    * proportional: impulse response scales with channel gain
    * deterministic: same seed, same trajectory
"""

import math
import random

from .state import SomaState, CORE_CHANNELS, default_params

# (source_channel, destination_channel, coefficient per second)
COUPLINGS = (
    ("arousal", "fatigue", +0.0006),
    ("warmth",  "tension", -0.0008),
)


class SomaEngine:

    def __init__(self, params=None, seed=None, dt=1.0):
        self.params = params or default_params()
        self.dt = dt
        self.rng = random.Random(seed)
        self.state = SomaState(
            t=0.0, values={c: self.params[c].baseline for c in self.params})
        self.history = [self.state.copy()]

    # ------------------------------------------------------------------
    def step(self, impulses=None, dt=None):
        """Advance the body by dt seconds.  ``impulses`` is a dict of
        channel -> instantaneous push (output of appraisal)."""
        dt = dt or self.dt
        impulses = impulses or {}
        v = self.state.values
        new = {}
        for c, p in self.params.items():
            x = v[c]
            # homeostatic decay
            dx = -(x - p.baseline) / p.tau * dt
            # appraised input
            if c in impulses:
                dx += p.gain * impulses[c]
            # autonomic weather
            if p.noise:
                dx += p.noise * self.rng.gauss(0.0, 1.0) * math.sqrt(dt)
            new[c] = x + dx
        # cross-couplings (use pre-step values; per-second coefficients)
        for src, dst, k in COUPLINGS:
            if src in v and dst in new:
                new[dst] += k * (v[src] - self.params[src].baseline) * dt
        # clamp
        for c in new:
            new[c] = max(0.0, min(1.0, new[c]))
        self.state = SomaState(t=self.state.t + dt, values=new)
        self.history.append(self.state.copy())
        return self.state

    def run(self, seconds, events=None):
        """Run for ``seconds``, applying ``events`` — a dict mapping
        time-offset (s) -> impulse dict.  Returns the final state."""
        events = events or {}
        steps = int(seconds / self.dt)
        t0 = self.state.t
        fired = set()
        for _ in range(steps):
            due = None
            for offset in events:
                if offset not in fired and t0 + offset <= self.state.t + self.dt:
                    due = offset
                    break
            if due is not None:
                fired.add(due)
                self.step(impulses=events[due])
            else:
                self.step()
        return self.state
