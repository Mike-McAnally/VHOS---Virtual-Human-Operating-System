"""The Personal Tuning Layer — reference implementation, v0.

Warps the General Affect Model's coarse readout into THIS subject's
fingerprint: the X'-minus-X corrections, the divergence signatures,
the subject's own emotion words (Barrett: the construction step is
individual, so this layer is where the person appears).

Input: CoarseAffect + the compiled affect.json fingerprint + optional
context tags describing the current situation.
Output: AffectState carrying
    naming_preference  the vocabulary words this subject actually uses
    expression_bias    how states surface in this subject (X')
    divergences        felt-vs-shown warnings for the current context

v0 matching is lexical (categories and context keywords).  Honest
limitation: a learned tuning layer needs synchronized capture data
that exists only for living subjects; for historical subjects this
layer runs on biography-derived entries at reduced confidence.
"""

from ..substrate.contract import AffectState


def apply_tuning(coarse, fingerprint, vocabulary, context_tags=()):
    fp = fingerprint or {}
    context_words = {w.lower() for w in context_tags}

    naming = []
    repertoire = _get(fp, "concept_repertoire", "frequent")
    if isinstance(repertoire, list):
        # keep only repertoire words whose vocabulary category matches
        # the current coarse readout — the subject's likely self-labels
        for word in repertoire:
            maps = vocabulary.lookup(str(word))
            if not maps:
                continue
            cats = {m["category"] for m in maps}
            if cats & set(coarse.categories):
                naming.append(str(word))

    expression = []
    deltas = fp.get("tuning_deltas", {})
    if isinstance(deltas, dict):
        for word, entry in deltas.items():
            if not isinstance(entry, dict):
                continue
            maps = vocabulary.lookup(word)
            cats = {m["category"] for m in (maps or [])}
            if cats & set(coarse.categories):
                personal = entry.get("personal")
                if isinstance(personal, dict):
                    personal = personal.get("value")
                if personal:
                    expression.append("%s, in this subject: %s" % (word, personal))

    divergences = []
    for item in fp.get("divergence_map", []) or []:
        if not isinstance(item, dict):
            continue
        ctx = _unwrap(item.get("context", ""))
        ctx_words = set(str(ctx).lower().replace('"', "").split())
        felt = _unwrap(item.get("felt"))
        shown = _unwrap(item.get("shown"))
        if context_words & ctx_words and felt and shown:
            divergences.append(
                "in this context the subject characteristically feels %s "
                "but shows %s (%s)" % (felt, shown, ctx))

    return AffectState(
        valence=coarse.valence,
        arousal=coarse.arousal,
        categories=list(coarse.categories),
        naming_preference=naming,
        expression_bias=expression,
        divergences=divergences,
    )


def _unwrap(v):
    """Leaf values from the block parser arrive as {'value': x, ...}."""
    if isinstance(v, dict) and "value" in v:
        return v["value"]
    return v


def _get(d, *path):
    cur = d
    for p in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(p)
    if isinstance(cur, dict) and "value" in cur:
        cur = cur["value"]
    return cur
