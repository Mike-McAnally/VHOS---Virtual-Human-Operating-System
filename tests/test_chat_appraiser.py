"""Tests for the chat runtime's lexical message appraiser.

Regression suite for the test-3 finding (2026-07-15): plain substring
matching fired a *threat* impulse from "war" inside "software" and
spiked tension to 0.77 on an innocuous message about software. Single
words must match whole words; phrases still match as substrings.
"""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from chat_turing import appraise_message                    # noqa: E402


class TestWordBoundaries(unittest.TestCase):

    def test_software_is_not_war(self):
        # the exact test-3 false positive
        tags = appraise_message(
            "a software was able to pear into the cognitive number cloud")
        self.assertNotIn("threat", tags)

    def test_wonderful_is_not_won(self):
        tags = appraise_message("what a wonderful audience")
        self.assertNotIn("achievement", tags)
        self.assertIn("social_warmth", tags)     # "wonderful" itself

    def test_real_war_still_lands(self):
        tags = appraise_message("the war changed everything")
        self.assertIn("threat", tags)

    def test_inflected_forms_land(self):
        self.assertIn("threat", appraise_message("he died in 1954"))
        self.assertIn("novelty", appraise_message("two new machines"))

    def test_phrases_match_as_substrings(self):
        self.assertIn("social_warmth",
                      appraise_message("so good to see you again"))
        self.assertIn("threat",
                      appraise_message("they want to shut down the lab"))

    def test_neutral_message_is_silent(self):
        self.assertEqual(appraise_message("hello there"), [])


if __name__ == "__main__":
    unittest.main()
