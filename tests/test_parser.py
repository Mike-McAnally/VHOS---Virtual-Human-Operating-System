import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vhos.hdl.parser import parse_hdl, ParseError
from vhos.hdl import validator
from vhos.vocabulary import Vocabulary

# The spec's own worked example (Part II), verbatim fragments.
EINSTEIN = '''HDL_VERSION 0.4
SUBJECT_ID "albert_einstein"
PRIMARY_AUTHOR_MODE ai
LAST_COMPILED 2026-06-09

THIS SUBJECT VALUES understanding nature deeply.
  @LAYER drives  @AUTHOR ai  @CONFIDENCE 0.95
  @SOURCES [writings/autobiographical-notes-1949.txt#para_3]

THIS SUBJECT REJECTS militarism as a path to human security.
  @LAYER social  @AUTHOR ai  @CONFIDENCE 0.92
  @SOURCES [correspondence/einstein-freud-why-war-1933.txt,
             statements/manifesto-to-europeans-1914.txt]

THIS SUBJECT WEIGHS internal coherence strongly.
  @LAYER heuristics  @AUTHOR ai  @CONFIDENCE 0.90
  @SOURCES [essay/physics-and-reality-1936.txt]

WHEN THIS SUBJECT learns of war or atrocity,
  they FEEL distressed,
  THEN BECOME reflective,
  THEN ACT defiant.
  @LAYER social  @AUTHOR ai  @CONFIDENCE 0.80
  @SOURCES [biography/isaacson-2007.ch_14]
  @CHAIN [distressed -> reflective -> defiant]
'''

SELF_AUTHORED = '''HDL_VERSION 0.4
SUBJECT_ID "subject_x"
PRIMARY_AUTHOR_MODE self

WHEN THIS SUBJECT is interrupted mid-thought,
  they FEEL irritated weakly.
  @LAYER drives  @AUTHOR self  @CONFIDENCE 1.00
  @SOURCES [self-attestation/2026-06-09]
'''


class TestParser(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.vocab = Vocabulary()

    def test_einstein_fragment_parses(self):
        doc = parse_hdl(EINSTEIN)
        self.assertEqual(doc.header["SUBJECT_ID"], "albert_einstein")
        self.assertEqual(len(doc.statements), 4)

        s0 = doc.statements[0]
        self.assertEqual((s0.form, s0.verb), ("assertion", "VALUES"))
        self.assertEqual(s0.object, "understanding nature deeply")  # 'deeply' is object text
        self.assertIsNone(s0.intensity)
        self.assertAlmostEqual(s0.confidence, 0.95)

        s1 = doc.statements[1]
        self.assertEqual(len(s1.sources), 2)  # wrapped @SOURCES list

        s2 = doc.statements[2]
        self.assertEqual(s2.intensity, "strongly")
        self.assertEqual(s2.object, "internal coherence")

        s3 = doc.statements[3]
        self.assertEqual(s3.form, "chain")
        self.assertEqual(s3.chain, ["distressed", "reflective", "defiant"])
        self.assertEqual(s3.chain_sides, ["feel", "become", "act"])
        self.assertEqual(s3.chain_annotation, s3.chain)

        issues = validator.validate(doc, self.vocab)
        self.assertFalse(validator.has_errors(issues),
                         [str(i) for i in issues])

    def test_chain_mismatch_is_error(self):
        bad = EINSTEIN.replace("[distressed -> reflective -> defiant]",
                               "[distressed -> defiant]")
        doc = parse_hdl(bad)
        issues = validator.validate(doc, self.vocab)
        self.assertTrue(any(i.code == "E007" for i in issues))

    def test_unknown_chain_word_is_error(self):
        bad = EINSTEIN.replace("they FEEL distressed,",
                               "they FEEL discombobulated,") \
                      .replace("[distressed -> reflective -> defiant]",
                               "[discombobulated -> reflective -> defiant]")
        doc = parse_hdl(bad)
        issues = validator.validate(doc, self.vocab)
        self.assertTrue(any(i.code == "E006" for i in issues))

    def test_wrong_side_chain_word_is_warning(self):
        # ACT amused: amused has no external_behavior side -> W001
        odd = EINSTEIN.replace("THEN ACT defiant.", "THEN ACT amused.") \
                      .replace("[distressed -> reflective -> defiant]",
                               "[distressed -> reflective -> amused]")
        doc = parse_hdl(odd)
        issues = validator.validate(doc, self.vocab)
        self.assertTrue(any(i.code == "W001" for i in issues))
        self.assertFalse(validator.has_errors(issues))

    def test_self_authority_immutable_flag(self):
        doc = parse_hdl(SELF_AUTHORED)
        s = doc.statements[0]
        self.assertTrue(s.immutable)
        self.assertEqual(s.form, "conditional")
        self.assertEqual(s.chain, ["irritated"])
        self.assertEqual(s.intensity, "weakly")

    def test_conditional_requires_feel(self):
        with self.assertRaises(ParseError):
            parse_hdl("WHEN THIS SUBJECT is poked, they explode.\n"
                      "  @LAYER drives @AUTHOR ai @CONFIDENCE 0.5 @SOURCES [x]\n")

    def test_confidence_out_of_range(self):
        bad = EINSTEIN.replace("@CONFIDENCE 0.95", "@CONFIDENCE 1.95")
        doc = parse_hdl(bad)
        issues = validator.validate(doc, self.vocab)
        self.assertTrue(any(i.code == "E002" for i in issues))


if __name__ == "__main__":
    unittest.main()
