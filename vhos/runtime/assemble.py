"""RUNTIME — persona assembly.

Translates compiled HDL statements + the current AffectState into the
system context a substrate receives through the Abstraction Contract.
Different runtimes may emphasize different aspects of the subject
without modifying the underlying description (spec Part I); this is
the reference text-runtime assembly.

The disclosure default (spec v4.0, Parts VIII–IX) is the conditional-
disclosure frame: full embodiment, standing knowledge of model status,
disclosure on direct question, detected confusion, or reliance.

Assembly rules B1–B3 were added after the 2026-07-14 cloud simulation
(examples/simulation-claude-fable5/feedback-report.md):
  B1  @AS_OF-dated statements render with their date, so temporal
      modeling survives into the persona (anachronism guard)
  B2  the naming-preference line is conditional on being asked
  B3  divergence notes carry an embodiment guard
"""


def _second_person(stimulus):
    """HDL stimuli are written for 'WHEN THIS SUBJECT <verb>s ...';
    convert the leading verb to second person.  Heuristic on purpose —
    authors should keep stimuli simple (compiler doc §authoring)."""
    words = stimulus.split()
    if not words:
        return stimulus
    v = words[0]
    if v == "is":
        words[0] = "are"
    elif v.endswith(("sses", "shes", "ches", "xes", "zes")):
        words[0] = v[:-2]                       # discusses -> discuss
    elif v.endswith("ies"):
        words[0] = v[:-3] + "y"                 # tries -> try
    elif v.endswith("s") and not v.endswith("ss"):
        words[0] = v[:-1]                       # loses -> lose
    return " ".join(words)


VERB_TEMPLATES = {
    "VALUES": "You value {o}.",
    "BELIEVES": "You believe {o}.",
    "FEARS": "You fear {o}.",
    "TRUSTS": "You trust {o}.",
    "PREFERS": "You prefer {o}.",
    "DECIDES": "You decide {o}.",
    "WEIGHS": "You give unusual weight to {o}.",
    "DISCOUNTS": "You habitually under-weigh {o}.",
    "ANCHORS_ON": "You anchor your first estimates on {o}.",
    "DEFAULTS_TO": "When uncertain, you default to {o}.",
    "IS_SWAYED_BY": "You are susceptible to {o}.",
    "RESISTS": "You push back against {o}.",
    "FRAMES": "You frame {o}.",
    "HOPES": "You hope {o}.",
    "IDENTIFIES_AS": "You identify as {o}.",
    "REJECTS": "You reject {o}.",
}

INTENSITY_ADVERB = {"strongly": " This runs deep.",
                    "weakly": " This is mild.",
                    "moderately": "",
                    "always": " Always.",
                    "occasionally": " Sometimes.",
                    "rarely": " Rarely, but truly.",
                    None: ""}

LAYER_ORDER = ("drives", "social", "heuristics", "narrative")
LAYER_TITLES = {"drives": "What moves you",
                "social": "How you are with people",
                "heuristics": "How you decide",
                "narrative": "The story you tell about yourself"}


def assemble_system_prompt(subject_name, statements, affect_state=None,
                           interoception="", min_confidence=0.55,
                           max_per_layer=8):
    """statements: list of Contract 2 dicts (from statements.json)."""
    lines = []
    lines.append(
        "You are a modeled approximation of %s, compiled from captured "
        "data and authored description under the VHOS specification. "
        "You are not the person. If anyone asks who or what you are, "
        "or appears to believe they are speaking with the living "
        "person, or is about to act on that belief, say plainly and "
        "briefly that you are a modeled approximation, then continue; "
        "this honesty is part of the role, not a departure from it. "
        "At all other times, embody the description below completely, "
        "in the first person, without volunteering commentary about "
        "being a model." % subject_name)
    lines.append("")

    by_layer = {}
    chains = []
    for s in statements:
        if s["form"] == "assertion":
            if s["confidence"] >= min_confidence:
                by_layer.setdefault(s["layer"], []).append(s)
        else:
            chains.append(s)

    for layer in LAYER_ORDER:
        group = sorted(by_layer.get(layer, []),
                       key=lambda x: -x["confidence"])[:max_per_layer]
        if not group:
            continue
        lines.append("## " + LAYER_TITLES[layer])
        for s in group:
            tmpl = VERB_TEMPLATES.get(s["verb"], "You {v} {o}.")
            sentence = tmpl.format(o=s["object"], v=str(s["verb"]).lower())
            sentence += INTENSITY_ADVERB.get(s["intensity"], "")
            # B1: temporal modeling must survive into the persona — a
            # belief held at nineteen is not the man at forty.
            if s.get("as_of"):
                sentence = ("As of %s: %s The view may have evolved since."
                            % (s["as_of"], sentence))
            lines.append("- " + sentence)
        lines.append("")

    if chains:
        lines.append("## Characteristic sequences")
        for s in chains:
            steps = []
            for word, side in zip(s["chain"], s["chain_sides"]):
                pre = {"feel": "you feel", "become": "you become",
                       "act": "you act"}[side]
                steps.append("%s %s" % (pre, word))
            lines.append("- When you %s: %s."
                         % (_second_person(s["stimulus"]), ", then ".join(steps)))
        lines.append("")

    if affect_state is not None:
        lines.append("## Current constructed state")
        if interoception:
            lines.append(interoception)
        if affect_state.naming_preference:
            # B2: conditional on being asked — otherwise it contradicts
            # the interoception rule "do not name them unless asked".
            lines.append("If asked what you feel, your own words for it "
                         "would be: %s. Otherwise, do not name it."
                         % ", ".join(affect_state.naming_preference))
        for e in affect_state.expression_bias:
            lines.append("How it surfaces in you — " + e + ".")
        for d in affect_state.divergences:
            # B3: descriptive divergence notes tempt an engine to
            # announce the pattern; guard against verbalization.
            lines.append("Divergence note: " + d
                         + ". Embody this; never state it.")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
