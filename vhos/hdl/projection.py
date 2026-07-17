"""Heuristics projection — the published mapping table, v0.

Spec Part II: "Each prose verb maps to projection slots via a published
mapping table maintained alongside the vocabulary."  This module IS
that table for compiler vhosc-0.1.0.  A reviewer can retrace any
projection value to the prose statements that produced it, and from
there to the sources — traceability is non-negotiable, so every derived
slot records its contributing statement lines.

Slot semantics (all axes low->high in [0,1], 0.5 = no evidence):
    decision_style.deliberation           impulsive -> deliberate
    decision_style.intuition_vs_analysis  intuitive -> analytical
    decision_style.risk_tolerance         averse -> seeking
    decision_style.novelty_appetite       familiar -> novel
    decision_style.horizon                short -> long
    decision_style.granularity            detail-first -> pattern-first
    decision_style.consensus_orientation  contrarian -> consensus
    biases.*                              strength of the bias
    influence_susceptibility.*            strength of the channel

Qualitative tokens in authored blocks normalize for comparison:
    short=0.15 long=0.85 detail-first=0.15 pattern-first=0.85
"""

import re

# (verb, object keyword regex or None, [(slot_path, delta)])
RULES = [
    ("DECIDES", r"first principles",
     [("decision_style.intuition_vs_analysis", +0.15),
      ("decision_style.deliberation", +0.15)]),
    ("DECIDES", r"\bquickly\b|\binstinct|\bgut\b",
     [("decision_style.deliberation", -0.15),
      ("decision_style.intuition_vs_analysis", -0.15)]),
    ("WEIGHS", r"coherence|consistency",
     [("decision_style.intuition_vs_analysis", +0.10)]),
    ("WEIGHS", r"constructib|buildab|comput",
     [("decision_style.granularity", -0.10),
      ("decision_style.intuition_vs_analysis", +0.10)]),
    ("PREFERS", r"\bnovel|\bnew\b|untried|unexplored",
     [("decision_style.novelty_appetite", +0.15)]),
    ("PREFERS", r"concrete|mechanical|tangible",
     [("decision_style.granularity", -0.10)]),
    ("RESISTS", r"authority",
     [("influence_susceptibility.authority_signaling", -0.20),
      ("biases.authority", -0.15)]),
    ("RESISTS", r"social pressure|conformity|consensus|convention",
     [("influence_susceptibility.social_proof", -0.15),
      ("decision_style.consensus_orientation", -0.15)]),
    ("DISCOUNTS", r"disapproval|opinion|reputation|standing",
     [("influence_susceptibility.social_proof", -0.15),
      ("decision_style.consensus_orientation", -0.10)]),
    ("DEFAULTS_TO", r"experiment|trial|test",
     [("biases.confirmation", -0.10),
      ("decision_style.novelty_appetite", +0.05)]),
    ("IS_SWAYED_BY", r"emotion|feeling|sentiment",
     [("influence_susceptibility.emotional_appeal", +0.20)]),
    ("IS_SWAYED_BY", r"repetition",
     [("influence_susceptibility.repetition", +0.20)]),
    ("ANCHORS_ON", None,
     [("biases.anchoring", +0.15)]),
    ("TRUSTS", r"evidence|demonstration|data|proof",
     [("biases.authority", -0.10),
      ("decision_style.intuition_vs_analysis", +0.10)]),
    ("REJECTS", r"convention|ceremony|pretense",
     [("decision_style.consensus_orientation", -0.10)]),
]

INTENSITY_FACTOR = {"strongly": 1.5, "always": 1.5, "moderately": 1.0,
                    None: 1.0, "occasionally": 0.7, "weakly": 0.5,
                    "rarely": 0.4}

QUALITATIVE = {"short": 0.15, "long": 0.85,
               "detail-first": 0.15, "pattern-first": 0.85,
               "familiar": 0.15, "novel": 0.85,
               "averse": 0.15, "seeking": 0.85,
               "contrarian": 0.15, "consensus": 0.85,
               "intuitive": 0.15, "analytical": 0.85,
               "impulsive": 0.15, "deliberate": 0.85}

SYNC_TOLERANCE = 0.20   # |derived - authored| above this -> sync report


def derive(statements):
    """Derive the projection from prose statements.  Returns
    {family: {slot: {value, confidence, contributing: [line, ...]}}}."""
    acc = {}   # slot_path -> [ (delta, confidence, line) ]
    for s in statements:
        if s.form != "assertion":
            continue
        for verb, pattern, deltas in RULES:
            if s.verb != verb:
                continue
            if pattern and not re.search(pattern, s.object, re.I):
                continue
            factor = INTENSITY_FACTOR.get(s.intensity, 1.0)
            for slot, delta in deltas:
                acc.setdefault(slot, []).append(
                    (delta * factor * max(s.confidence, 0.0),
                     s.confidence, s.line))
    out = {}
    for slot, hits in acc.items():
        family, name = slot.split(".")
        value = _clamp(0.5 + sum(d for d, _c, _l in hits))
        conf = _clamp(0.9 * sum(c for _d, c, _l in hits) / len(hits))
        out.setdefault(family, {})[name] = {
            "value": round(value, 3),
            "confidence": round(conf, 3),
            "contributing_lines": sorted({l for _d, _c, l in hits}),
        }
    return out


def merge(authored, derived):
    """Merge authored block (wins where present) with derived slots.

    Returns (merged, sync_report).  Both forms travel together and the
    compiler keeps them in sync by REPORTING divergence, never by
    silently rewriting the authored numbers (self-authority extends to
    the authored projection block)."""
    merged = {}
    report = []
    families = set(list(authored.keys()) + list(derived.keys()))
    for fam in sorted(families):
        if fam.startswith("_") or fam == "subject_id":
            continue
        a_slots = authored.get(fam, {}) if isinstance(authored.get(fam, {}), dict) else {}
        d_slots = derived.get(fam, {})
        for slot in sorted(set(list(a_slots.keys()) + list(d_slots.keys()))):
            a = a_slots.get(slot)
            d = d_slots.get(slot)
            if a is not None:
                val = a.get("value") if isinstance(a, dict) else a
                entry = {
                    "value": val,
                    "confidence": (a.get("confidence") if isinstance(a, dict) else None),
                    "provenance": "authored",
                }
                if d is not None:
                    entry["derived_value"] = d["value"]
                    av = QUALITATIVE.get(val, val)
                    if isinstance(av, (int, float)) and \
                            abs(av - d["value"]) > SYNC_TOLERANCE:
                        report.append(
                            "%s.%s: authored %.2f vs derived %.2f "
                            "(gap > %.2f) — review the prose or the block"
                            % (fam, slot, av, d["value"], SYNC_TOLERANCE))
                merged.setdefault(fam, {})[slot] = entry
            else:
                entry = dict(d)
                entry["provenance"] = "derived"
                merged.setdefault(fam, {})[slot] = entry
    return merged, report


def _clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))
