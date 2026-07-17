import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vhos.vocabulary import Vocabulary, SIDES


class TestVocabulary(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.v = Vocabulary()

    def test_entry_count_matches_spec(self):
        # Appendix A: 220 entries (193 from v0.2 + 27 added by the author)
        self.assertEqual(len(self.v.entries), 220)

    def test_every_mapping_valid(self):
        for word, maps in self.v.entries.items():
            for m in maps:
                self.assertIn(m["side"], SIDES, word)
                self.assertIn(m["category"], self.v.categories[m["side"]], word)

    def test_intensity_split_ashamed(self):
        # default (no weakening modifier) -> high-intensity mapping
        cats = {m["category"] for m in self.v.lookup("ashamed")}
        self.assertIn("high-energy distressing", cats)
        self.assertNotIn("low-energy distressing", cats)
        # weakly -> low-intensity mapping
        cats_weak = {m["category"] for m in self.v.lookup("ashamed", "weakly")}
        self.assertIn("low-energy distressing", cats_weak)
        self.assertNotIn("high-energy distressing", cats_weak)
        # self-focused thinking side survives either way
        self.assertIn("thinking_states", self.v.sides("ashamed", "weakly"))

    def test_intensity_split_unhappy(self):
        self.assertEqual(
            [m["category"] for m in self.v.lookup("unhappy", "rarely")],
            ["low-energy distressing"])

    def test_patient_three_rows(self):
        self.assertEqual(len(self.v.entries["patient"]), 3)

    def test_chain_side_checks(self):
        # AMUSED is internal-only: fine to FEEL, wrong to ACT
        self.assertIsNone(self.v.check_chain_link("feel", "amused"))
        self.assertIsNotNone(self.v.check_chain_link("act", "amused"))
        # RESERVED is external: fine to ACT
        self.assertIsNone(self.v.check_chain_link("act", "reserved"))
        # ALERT lives on body+thinking: fine to BECOME
        self.assertIsNone(self.v.check_chain_link("become", "alert"))

    def test_multiword_entries(self):
        for w in ("at ease", "burned out", "on edge", "worn out", "grief-stricken"):
            self.assertIn(w, self.v)


if __name__ == "__main__":
    unittest.main()
