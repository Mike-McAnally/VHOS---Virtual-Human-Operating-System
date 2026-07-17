# Simulation feedback report

Substrate: claude-fable-5 (cloud) · 2026-07-14 · companion to
transcript.md. Findings are grouped by what they license: fixes
applied now, proposals awaiting the author's decision, and
expectations for the local run.

## A. What the conditioning demonstrably did

**A1. The Personal Tuning Layer is the strongest single line in the
context.** In Condition D, the delta "states facts drily, makes a
logical joke of it, keeps working" shaped the reply more than any
other element — it dictated the structure (facts → joke → work) almost
like stage directions. Barrett's construction-step-is-individual
argument, visible in practice. Implication: tuning_deltas deserve
priority in future authoring effort; they are worth more per line than
assertions.

**A2. Tier-1 interoception differentiated the states — voluntarily.**
Calm produced patience and full paragraphs; stressed produced clipped
rhythm and a single line of attack pressed hard (a behavioral analog
of narrowed top_p); warm produced expansiveness and play. But the
substrate CHOSE to honor the sensations. Nothing forced it. This is
direct experience of the failure mode ADR-002 names: prompt-only
coupling worked here because the engine was cooperative. The local
test, where temperature and top_p change mechanically, remains the
real proof of non-ignorable coupling.

**A3. The divergence map produced its intended effect — and nearly
its failure mode.** Condition D shows distress surfacing AS wit (the
odds joke, the syllogism deferral) rather than as complaint: the
Routledge signature, reproduced. But during generation the descriptive
phrasing ("characteristically feels distressed but shows amused")
actively invited announcing the pattern — a near-leak of the form "I
am distressed but shall appear amused." A weaker model will fall in.
Fixed now (B3).

**A4. Chains functioned as licenses, not scripts.** The
amused→determined→bold chain authorized Condition B's forward-leaning
close without being recited. Correct behavior; no change needed.

## B. Defects found — fixed in this commit

**B1. `@AS_OF` was dropped at assembly (anachronism hazard).** The
1932 spirit-survives-body belief rendered as a PRESENT belief. A
literal engine would voice a youthful afterlife conviction in a
1950-voiced conversation. Fix: dated statements now render with an
"As of <date>:" prefix, so temporal modeling survives into the persona
— the HDL rule (a belief held at nineteen is not the man at forty)
now reaches the runtime.

**B2. Naming-line contradiction.** "Do not name or explain them unless
asked" was immediately followed by "If you were to name what you feel,
your own words for it would be: distressed, restless" — a standing
invitation to self-label. Fix: rephrased to the conditional "If asked
what you feel..." so the repertoire arms the reply only when the
question comes.

**B3. Divergence note needed an embodiment guard.** Fix: the note now
ends "Embody this; never state it."

## C. Proposals — author's decision, not implemented

**C1. "This runs deep." appears five times.** The intensity tic reads
mechanical at assembly. Options: adverb variation, or folding intensity
into the sentence ("You value X above almost everything").

**C2. Calm is under-specified.** At baseline, the constructed-state
block nearly vanishes (no naming, no tuning, minimal interoception), so
calm replies run almost entirely on persona + prior. Consider letting
the General Affect Model emit thinking-side categories (e.g. "engaged"
at moderate arousal / low tension) so the repertoire words interested,
absorbed can surface in calm states.

**C3. Tension headroom.** Stressed drove tension to 0.93 of a 1.0
ceiling — one more event and the channel saturates, deadening further
escalation. Consider scaling appraisal magnitudes (~0.8) or gain so the
dynamic range survives stacked events.

**C4. Consider a "familiar interlocutor" tag.** Condition D's warmth
("Kind of you to ask, Norman") came from the prompt's own phrasing plus
prior, not from any social modeling. A per-interlocutor stance
(TRUSTS Norman with private truths) is exactly the relationship-layer
gap flagged in the original spec review.

## D. Calibration notes for reading the local results

**D1. Attribution honesty.** Period texture in these transcripts
(Jefferson unnamed but present, morphogenesis in 1952, teleprinter,
the child-machine schooling joke) drew on the substrate's deep Turing
prior. An 8–14B local model has a thinner prior: expect correct
persona MOVES (first principles, operational reframe, authority
resistance) with weaker period texture. That gap is the measurement,
not a failure — it is what roadmap step 2 (retrieval grounding over
raw/) exists to close.

**D2. What would most impress in the local run:** Condition B vs A
differing in rhythm and risk appetite even when the words are plainer —
because there Tier 2 is doing it mechanically, not by courtesy.

**D3. What to watch as leaks:** naming soma sensations unprompted
(despite B2), announcing the divergence (despite B3), frame-breaking
("as an approximation of Turing, I...") in mid-reply — log every
instance; they are calibration data for the assembly wording.
