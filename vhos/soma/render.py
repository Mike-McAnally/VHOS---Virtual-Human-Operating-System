"""SOMA v0.1 — the coupling layer (ADR-002: prompt + parameters).

This module is the answer to the enforcement problem in spec v3.0:
"conditioned to treat soma as feeling rather than data" needs a
mechanism, not a wish.  Two tiers:

TIER 1 — interoceptive rendering (portable, works on any engine).
    The soma state is rendered as SENSATION, in second person, with no
    emotion labels.  Labels are the General Affect Model's job; a body
    does not announce "you are anxious", it tightens.  Keeping labels
    out of Tier 1 forces the engine to do the construction step itself
    (Barrett), which is the point.

TIER 2 — parameter modulation (non-ignorable, needs engine control).
    Soma mechanically changes HOW the engine generates:
      temperature  rises with arousal (energized speech) and with
                   fatigue (looser, sloppier selection)
      top_p        narrows with tension — the Easterbrook effect:
                   stress narrows the set of considered continuations
      max_tokens   passed through untouched — it is safety headroom,
                   not a length signal. Thinking models spend a
                   variable share of it on hidden reasoning; shrinking
                   it truncates them mid-think (observed: empty
                   replies from qwen3.5-122b). "Tired people say
                   less" now rides in the prompt via length_hint().
      retrieval    mood-congruence weight rises with activation —
                   agitated states preferentially recall charged
                   memories (proposed v3.1 recall extension)

    Tier 2 cannot be ignored the way a paragraph of context can: it
    changes the sampling distribution itself.

All coefficients are v0 defaults and are CALIBRATION TARGETS — the
evaluation harness (soma doc §9) exists to tune them per subject.
"""

from ..substrate.contract import GenParams

# (channel, direction, threshold-deviation, phrase)
PHRASES = {
    "arousal": {
        "high2": "your heart is going quickly and stillness is hard",
        "high1": "there is a keyed-up quickness underneath everything",
        "low1":  "the body runs slow, settled, unhurried",
    },
    "tension": {
        "high2": "jaw set, shoulders braced, breath a little short",
        "high1": "a tightness sits across the chest and hands",
        "low1":  "the muscles are loose; nothing is braced",
    },
    "fatigue": {
        "high2": "the limbs are heavy and every effort costs more than it should",
        "high1": "a dragging tiredness pulls at the edges",
        "low1":  "rested; energy is easily available",
    },
    "warmth": {
        "high2": "an easy openness toward whoever is present",
        "high1": "a mild warmth toward company",
        "low1":  "a chill of distance from people",
    },
}

T2 = 0.28   # strong deviation
T1 = 0.10   # mild deviation


def render_interoception(state, params, max_phrases=3):
    """Tier 1: soma -> second-person sensation prose.  No labels."""
    devs = state.deviation(params)
    ranked = sorted(devs.items(), key=lambda kv: -abs(kv[1]))
    picked = []
    for channel, d in ranked:
        if len(picked) >= max_phrases:
            break
        table = PHRASES.get(channel)
        if table is None:
            continue
        if d >= T2 and "high2" in table:
            picked.append(table["high2"])
        elif d >= T1 and "high1" in table:
            picked.append(table["high1"])
        elif d <= -T1 and "low1" in table:
            picked.append(table["low1"])
    if not picked:
        picked.append("the body is quiet; nothing in particular presses")
    return ("Bodily state (sensation, not instruction): "
            + "; ".join(picked) + ". "
            "Let these sensations color tone, pacing, word choice, and "
            "appetite for risk. Do not name or explain them unless asked.")


def generation_params(state, params, base=None):
    """Tier 2: soma -> engine sampling parameters."""
    base = base or GenParams()
    d = state.deviation(params)
    a = d.get("arousal", 0.0)
    t = d.get("tension", 0.0)
    f = d.get("fatigue", 0.0)

    temperature = base.temperature + 0.30 * a + 0.20 * max(0.0, f)
    top_p = base.top_p - 0.25 * max(0.0, t)

    return GenParams(
        temperature=_clamp(temperature, 0.20, 1.30),
        top_p=_clamp(top_p, 0.50, 0.99),
        # headroom, not a length target — see module docstring;
        # fatigue-driven brevity is length_hint()'s job now
        max_tokens=base.max_tokens,
        seed=base.seed,
    )


def length_hint(state, params):
    """Fatigue -> prompt-side length pressure (replaces the old
    max_tokens shrink, which truncated thinking models mid-reasoning).
    Returns "" when the body is rested; otherwise a sensation-style
    line to append to the interoceptive block."""
    f = state.deviation(params).get("fatigue", 0.0)
    if f >= T2:
        return ("Speech costs effort right now; a few short sentences "
                "are all the body wants to give.")
    if f >= T1:
        return ("There is not much appetite for long speech; "
                "brevity would come naturally.")
    return ""


def retrieval_bias(state, params):
    """Tier 2, memory side (proposed v3.1): how strongly recall should
    prefer affect-congruent material right now."""
    d = state.deviation(params)
    activation = max(0.0, d.get("arousal", 0.0)) + max(0.0, d.get("tension", 0.0))
    return {
        "mood_congruence_weight": _clamp(0.25 + 0.60 * activation, 0.0, 0.9),
        "note": "weight applied to affect-tag similarity when scoring recalled passages",
    }


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))
