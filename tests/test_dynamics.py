import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vhos.soma.state import ChannelParams
from vhos.soma.dynamics import SomaEngine
from vhos.soma.render import (render_interoception, generation_params,
                              length_hint)
from vhos.soma.appraisal import appraise
from vhos.substrate.contract import GenParams
from vhos.affect.general_model import read_soma


def quiet_params():
    """No noise, no coupling ambiguity — pure dynamics for testing."""
    return {
        "arousal": ChannelParams(baseline=0.35, tau=120.0, gain=1.0, noise=0.0),
        "tension": ChannelParams(baseline=0.30, tau=300.0, gain=1.0, noise=0.0),
        "fatigue": ChannelParams(baseline=0.25, tau=1800.0, gain=1.0, noise=0.0),
        "warmth":  ChannelParams(baseline=0.40, tau=600.0, gain=1.0, noise=0.0),
    }


class TestDynamics(unittest.TestCase):

    def test_impulse_raises_channel(self):
        e = SomaEngine(params=quiet_params(), seed=1)
        before = e.state.values["arousal"]
        e.step(impulses={"arousal": +0.4})
        self.assertGreater(e.state.values["arousal"], before + 0.3)

    def test_homeostatic_return(self):
        e = SomaEngine(params=quiet_params(), seed=1)
        e.step(impulses={"arousal": +0.5})
        e.run(1200)  # 10x tau
        self.assertAlmostEqual(e.state.values["arousal"], 0.35, delta=0.03)

    def test_bounded_under_extreme_impulses(self):
        e = SomaEngine(params=quiet_params(), seed=1)
        e.step(impulses={"arousal": +50, "tension": +50})
        for v in e.state.values.values():
            self.assertLessEqual(v, 1.0)
        e.step(impulses={"arousal": -50, "warmth": -50})
        for v in e.state.values.values():
            self.assertGreaterEqual(v, 0.0)

    def test_gain_scales_response(self):
        p1, p2 = quiet_params(), quiet_params()
        p2["arousal"] = ChannelParams(baseline=0.35, tau=120.0, gain=2.0, noise=0.0)
        e1, e2 = SomaEngine(params=p1), SomaEngine(params=p2)
        e1.step(impulses={"arousal": +0.2})
        e2.step(impulses={"arousal": +0.2})
        d1 = e1.state.values["arousal"] - 0.35
        d2 = e2.state.values["arousal"] - 0.35
        self.assertAlmostEqual(d2 / d1, 2.0, delta=0.05)

    def test_deterministic_with_seed(self):
        a = SomaEngine(seed=7)
        b = SomaEngine(seed=7)
        for _ in range(50):
            a.step()
            b.step()
        self.assertEqual(a.state.values, b.state.values)

    def test_arousal_accrues_fatigue(self):
        e = SomaEngine(params=quiet_params())
        e.step(impulses={"arousal": +0.5})
        f0 = e.state.values["fatigue"]
        e.run(300)
        self.assertGreater(e.state.values["fatigue"], f0)


class TestCoupling(unittest.TestCase):

    def _stressed_engine(self):
        e = SomaEngine(params=quiet_params())
        e.step(impulses=appraise(["threat", "blocked_goal"]))
        return e

    def test_interoception_mentions_bracing_under_tension(self):
        e = self._stressed_engine()
        text = render_interoception(e.state, e.params)
        self.assertTrue("braced" in text or "tightness" in text, text)
        # Tier 1 rule: sensation only, no emotion labels
        for label in ("anxious", "afraid", "angry", "distressed"):
            self.assertNotIn(label, text.lower())

    def test_tension_narrows_top_p(self):
        e = self._stressed_engine()
        g = generation_params(e.state, e.params, base=GenParams())
        self.assertLess(g.top_p, GenParams().top_p)

    def test_fatigue_shortens_output(self):
        # max_tokens is safety headroom, not a length signal: shrinking
        # it truncated thinking models mid-reasoning (chat runtime bug
        # #1, 2026-07-15). Fatigue-driven brevity now rides in the
        # prompt via length_hint(); the cap passes through untouched.
        e = SomaEngine(params=quiet_params())
        e.step(impulses={"fatigue": +0.5})
        g = generation_params(e.state, e.params, base=GenParams())
        self.assertEqual(g.max_tokens, GenParams().max_tokens)
        self.assertTrue(length_hint(e.state, e.params))
        rested = SomaEngine(params=quiet_params())
        self.assertEqual(length_hint(rested.state, rested.params), "")

    def test_general_model_reads_stress_as_distress(self):
        e = self._stressed_engine()
        coarse = read_soma(e.state, e.params)
        self.assertLess(coarse.valence, 0)
        self.assertIn("high-energy distressing", coarse.categories)
        self.assertIn("activated", coarse.categories)

    def test_general_model_reads_warmth_as_uplifting(self):
        e = SomaEngine(params=quiet_params())
        e.step(impulses=appraise(["social_warmth", "achievement"]))
        coarse = read_soma(e.state, e.params)
        self.assertGreater(coarse.valence, 0)


if __name__ == "__main__":
    unittest.main()
