"""Emotion vocabulary loader.

``vocabulary.json`` is GENERATED from Appendix A of the unified spec
(220 words, 286 side-rows).  The appendix is canonical; the JSON is a
derived projection and is never edited by hand (spec Part II).

Implements the Contract 2 intensity-split rule: for split entries
(ASHAMED, UNHAPPY) the low-intensity mapping applies only when the
statement carries a weakening modifier (weakly, rarely); otherwise the
high-intensity mapping applies.
"""

import json
import os

SIDES = ("internal_feelings", "body_states", "thinking_states", "external_behavior")

# Verb-to-side expectations for chain links (design decision, v0):
# FEEL links should resolve to internal_feelings, ACT links to
# external_behavior; BECOME resolves to thinking_states or body_states
# (a word living on both contributes both, per spec Part II).
CHAIN_SIDE_EXPECTATION = {
    "feel": ("internal_feelings",),
    "become": ("thinking_states", "body_states"),
    "act": ("external_behavior",),
}

WEAKENING_MODIFIERS = ("weakly", "rarely")
INTENSITY_MODIFIERS = ("strongly", "moderately", "weakly",
                       "rarely", "occasionally", "always")

_DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "vocabulary.json")


class Vocabulary:
    """The shared emotion vocabulary, plus optional subject-specific
    additions (which never pollute the shared file, per spec)."""

    def __init__(self, path=None, custom_path=None):
        with open(path or _DEFAULT_PATH, encoding="utf-8") as f:
            data = json.load(f)
        self.name = data.get("name", "vhos-core")
        self.version = data.get("version", "?")
        self.categories = data.get("sides", {})
        self.entries = {k.lower(): v for k, v in data["entries"].items()}
        self.custom = {}
        if custom_path and os.path.exists(custom_path):
            with open(custom_path, encoding="utf-8") as f:
                cdata = json.load(f)
            self.custom = {k.lower(): v for k, v in cdata.get("entries", {}).items()}

    # ------------------------------------------------------------------
    def __contains__(self, word):
        w = _norm(word)
        return w in self.entries or w in self.custom

    def __len__(self):
        return len(self.entries) + len(self.custom)

    def lookup(self, word, intensity=None):
        """Resolve a word to its side/category mappings, applying the
        Contract 2 intensity-split rule.  Returns a list of mapping
        dicts, or None if the word is not in the vocabulary."""
        w = _norm(word)
        maps = self.entries.get(w)
        if maps is None:
            maps = self.custom.get(w)
        if maps is None:
            return None
        weak = intensity in WEAKENING_MODIFIERS
        resolved = []
        for m in maps:
            cond = m.get("condition")
            if cond == "low_intensity" and not weak:
                continue
            if cond == "high_intensity" and weak:
                continue
            resolved.append(m)
        return resolved

    def sides(self, word, intensity=None):
        maps = self.lookup(word, intensity)
        if maps is None:
            return None
        return sorted({m["side"] for m in maps})

    def check_chain_link(self, verb, word, intensity=None):
        """Return None if the word suits the chain verb's side, else a
        human-readable warning string (validator emits it as W001)."""
        sides = self.sides(word, intensity)
        if sides is None:
            return "word '%s' is not in the vocabulary" % word
        expected = CHAIN_SIDE_EXPECTATION[verb.lower()]
        if not any(s in sides for s in expected):
            return ("word '%s' has sides %s but chain verb %s expects one of %s"
                    % (word, sides, verb.upper(), list(expected)))
        return None


def _norm(word):
    return word.lower().strip().replace("_", " ")
