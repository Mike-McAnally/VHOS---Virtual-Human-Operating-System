"""Integration: compile the shipped Alan Turing subject and run the
affect pipeline over the result.  This is the end-to-end conformance
check for Contract 2 outputs plus the tuning layer."""

import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from vhos import COMPILER_VERSION
from vhos.hdl.compiler import compile_subject
from vhos.vocabulary import Vocabulary
from vhos.soma.dynamics import SomaEngine
from vhos.soma.appraisal import appraise
from vhos.soma.state import ChannelParams
from vhos.affect import read_soma, apply_tuning
from vhos.runtime import assemble_system_prompt

SUBJECT = os.path.join(ROOT, "subjects", "alan_turing")


class TestTuringPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.report, cls.issues = compile_subject(SUBJECT)
        derived = os.path.join(SUBJECT, "derived", COMPILER_VERSION)
        with open(os.path.join(derived, "statements.json")) as f:
            cls.statements = json.load(f)["statements"]
        with open(os.path.join(derived, "affect.json")) as f:
            cls.fingerprint = json.load(f)["fingerprint"]
        with open(os.path.join(derived, "heuristics.json")) as f:
            cls.heuristics = json.load(f)
        cls.vocab = Vocabulary()

    def test_compiles_clean(self):
        self.assertEqual(self.report["status"], "ok",
                         self.report["issues"])
        self.assertEqual(self.report["statement_count"], 31)

    def test_contract2_fields_present(self):
        required = ("$schema", "subject_id", "form", "verb", "object",
                    "stimulus", "chain", "chain_sides", "intensity",
                    "layer", "author", "confidence", "sources", "as_of",
                    "affect_refs", "note", "reviewed")
        for s in self.statements:
            for k in required:
                self.assertIn(k, s)
            self.assertTrue(0.0 <= s["confidence"] <= 1.0)
            self.assertTrue(s["sources"])

    def test_temporal_modeling_pair(self):
        """The 1932 spirit belief must survive, dated, alongside the
        1950 operational-test belief — the @AS_OF rule in action."""
        as_ofs = {s["as_of"] for s in self.statements if s["verb"] == "BELIEVES"}
        self.assertIn("1932", as_ofs)
        self.assertIn("1950", as_ofs)

    def test_heuristics_authored_wins_with_derived_recorded(self):
        auth = self.heuristics["projection"]["biases"]["authority"]
        self.assertEqual(auth["provenance"], "authored")
        self.assertLess(auth["value"], 0.2)
        self.assertIn("derived_value", auth)

    def _stressed_affect(self):
        engine = SomaEngine(seed=3)
        engine.params["tension"] = ChannelParams(baseline=0.45, tau=300.0,
                                                 gain=1.0, noise=0.0)
        engine.step(impulses=appraise(["threat", "social_exposure"]))
        coarse = read_soma(engine.state, engine.params)
        return apply_tuning(coarse, self.fingerprint, self.vocab,
                            context_tags=["disclosing", "persecution",
                                          "friends"])

    def test_divergence_fires_in_context(self):
        affect = self._stressed_affect()
        self.assertTrue(affect.divergences,
                        "divergence map should fire for this context")
        self.assertIn("amused", affect.divergences[0])
        # the personal tuning delta for distress should surface
        joined = " ".join(affect.expression_bias)
        self.assertIn("drily", joined)

    def test_assembled_prompt_carries_disclosure_and_affect(self):
        engine = SomaEngine(seed=3)
        engine.step(impulses=appraise(["blocked_goal"]))
        coarse = read_soma(engine.state, engine.params)
        affect = apply_tuning(coarse, self.fingerprint, self.vocab)
        prompt = assemble_system_prompt("Alan Turing", self.statements,
                                        affect_state=affect,
                                        interoception="(test intero)")
        self.assertIn("modeled approximation", prompt)   # Part VIII disclosure
        self.assertIn("first principles", prompt)
        self.assertIn("Characteristic sequences", prompt)
        # B1 regression: @AS_OF must reach the persona (temporal modeling)
        self.assertIn("As of 1932:", prompt)
        self.assertIn("As of 1950:", prompt)

    def test_divergence_carries_embodiment_guard(self):
        affect = self._stressed_affect()
        prompt = assemble_system_prompt("Alan Turing", self.statements,
                                        affect_state=affect)
        self.assertIn("Embody this; never state it.", prompt)    # B3
        if affect.naming_preference:
            self.assertIn("If asked what you feel", prompt)      # B2

    def test_immutability_absent_for_historical_subject(self):
        # No self/instance statements in the Turing file — and the
        # count must say so (a living subject's file will differ).
        self.assertEqual(self.report["immutable_count"], 0)


if __name__ == "__main__":
    unittest.main()
