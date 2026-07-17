# SOMA Design Document v0.1

Companion to the VHOS Unified Specification v3.0. This document gives
SOMA what the spec declared but did not define: a state schema, a
dynamics law, an appraisal path, and — most importantly — an
enforcement mechanism for "conditioned to treat soma as feeling rather
than data." Reference implementation: `vhos/soma/` and `vhos/affect/`.

## 1. The gap this document closes

Spec v3.0 makes SOMA foundational ("the feeling subsystem is
foundational, not decorative") and then specifies it in one paragraph.
Three things were missing.

First, no schema: what IS a soma state? Second, no dynamics: how does
it move through time? Third, no coupling mechanism: the phrase "the
cognitive core is conditioned to read these signals as its own bodily
feedback and to treat as feeling rather than data" names an outcome,
not a method. For a language-model substrate, any signal placed in
context arrives as tokens, and tokens are data. Something must make
the signal non-ignorable. This document specifies that something.

## 2. Where SOMA lives — and where it deliberately does not

SOMA is implemented OUTSIDE the substrate, as pure standard-library
mathematics in the AFFECT layer. This is an architectural decision
with a one-sentence justification: the affect subsystem must survive
substrate swaps, so it cannot live behind the substrate contract.
Contract 3's `read_soma`/`apply_tuning` remain as OPTIONAL acceleration
points a future engine may implement natively; the reference
implementations never require them. Nothing about a subject's body
simulation dies when the engine is replaced — which is the whole
CONTINUITY argument applied one layer down.

## 3. State schema (v0.1)

Four channels, each a scalar in [0,1], chosen directly from the spec's
own wording ("analogues of arousal, tension, fatigue, the autonomic
weather"):

| channel | is the analog of | observable calibration signal |
|---|---|---|
| arousal | sympathetic activation | heart rate; speech rate |
| tension | muscular / postural bracing | jaw, shoulders, EMG, micro-expression |
| fatigue | depleted capacity | actigraphy, HRV drift, blink rate |
| warmth  | parasympathetic / social-safety ease | vocal warmth, facial openness |

The visceral end of the build-order gradient — `gut`, `breath`, `pain`
— is RESERVED by name and not implemented, exactly as the spec's
gradient instructs: defer the visceral end until SOMA and multimodal
capture are mature. Reserving names keeps future additions minor-version.

Each channel carries four parameters, and these four parameters are
the missing link between HDL's `soma_calibration` block and running
code — this is what calibration MEANS now:

    baseline   homeostatic set point         (e.g. arousal_baseline_hr)
    tau        return time-constant, seconds (how fast the body recovers)
    gain       appraisal sensitivity         (how hard events land)
    noise      autonomic weather amplitude   (how restless the quiet body is)

A note on valence: there is deliberately no "valence" channel. Valence
is a READOUT (the General Affect Model's interpretation), not a body
signal. Bodies have activation and depletion; pleasantness is
constructed. This follows Barrett and keeps the layers honest.

## 4. Dynamics

Each channel is a leaky integrator with homeostatic return, stepped by
forward Euler and clamped to [0,1]:

    dx/dt = -(x - baseline)/tau + gain * impulse(t) + weather

`weather` is small Gaussian noise scaled by sqrt(dt): the body is
never perfectly still, and downstream layers must tolerate that.

Exactly two cross-couplings exist in v0.1 (each new coupling is a new
way to be wrong, so the set is minimal and must be argued into):

    arousal above baseline slowly accrues fatigue    (activation costs)
    warmth above baseline slowly releases tension    (safety un-braces)

Provable properties, enforced by unit test (tests/test_dynamics.py):
bounded under any impulse sequence; decays to baseline with no input;
impulse response proportional to gain; deterministic under a fixed seed.
A soma you cannot write property tests for is a soma you cannot debug.

## 5. Appraisal: how the world reaches the body

Events carry coarse tags (threat, loss, blocked_goal, novelty,
achievement, social_warmth, social_exposure, absurdity, rest,
exertion). A general table maps tags to channel impulses — this is the
input half of the General Human Affect Model: how situations land in a
human body generally. The personal layer enters as per-channel GAIN
multipliers from the subject's calibration: reactive bodies amplify,
phlegmatic bodies damp.

v0 appraisal is a rule table on purpose: transparent, testable,
substrate-free, and it serves as the test oracle for any future
LLM-as-appraiser (which would run through Contract 3 `reason()` with
the table as fallback).

## 6. The coupling problem — Tier 1 and Tier 2 (ADR-002)

This is the heart of the document. Two mechanisms, layered:

**Tier 1 — interoceptive rendering (portable).** The soma state is
rendered into the context window as SENSATION, second person, with a
hard rule: no emotion labels. "Jaw set, shoulders braced, breath a
little short" — never "you are anxious." Labeling is the General
Affect Model's job; a body does not announce categories, it tightens.
Keeping labels out of Tier 1 forces the engine to perform the
construction step itself — which is Barrett's theory, operationalized
as a prompt-engineering rule. Tier 1 works on any engine, including
cloud APIs, and is therefore the portability floor.

**Tier 2 — parameter modulation (non-ignorable).** Tier 1 can be
ignored the way any paragraph can. Tier 2 cannot: soma mechanically
changes how the engine samples.

| soma deviation | parameter effect | rationale |
|---|---|---|
| arousal ↑ | temperature ↑ (+0.30/unit) | energized speech, faster/looser selection |
| tension ↑ | top_p ↓ (−0.25/unit) | Easterbrook cue-utilization: stress narrows the set of considered continuations |
| fatigue ↑ | temperature ↑ (+0.20/unit), max_tokens ↓ (−45%) | tired speech is sloppier and shorter |
| activation ↑ | retrieval mood-congruence weight ↑ | agitated states preferentially recall charged material |

The retrieval row is the proposed v3.1 contract extension: `recall()`
accepts an optional AffectState. Affect that biases generation but not
memory is half a loop — mood-congruent recall is among the most
person-shaping affective biases in the literature, and v3.0's contract
had no way to express it.

All coefficients are v0 defaults and are explicitly CALIBRATION
TARGETS, not claims. The evaluation harness (§9) exists to tune them.

**Tier 3 — training-time integration (future).** Fine-tuning an engine
to respond to soma tokens natively is the strongest coupling — closest
to real interoception, where the signal is constitutive rather than
contextual. Deferred: it requires training infrastructure and paired
data that Stage 0–2 subjects do not yet have. The tier structure means
nothing breaks when Tier 3 arrives; it slots beneath Tiers 1–2.

## 7. The loop, end to end

    events --appraise--> impulses --SomaEngine--> SomaState
      --read_soma--> CoarseAffect (general: valence, arousal, categories)
      --apply_tuning--> AffectState (personal: subject's words, X′ tells,
                                     divergence warnings)
      --render--> Tier 1 interoception + Tier 2 GenParams
      --assemble--> system context --Contract 3--> engine output
      --> new events (what happened) --> appraise ...

Run `python3 scripts/demo_loop.py` to watch every stage of this loop
print itself on the Alan Turing subject. Scene 2 demonstrates the
signature move: the general model reads the body as distress; the
personal layer answers "in this subject that surfaces as dry wit, a
logical joke, continued work" and attaches the divergence warning
(felt: distressed, shown: amused). That is the Routledge letter,
operationalized.

## 8. Calibration

**Living subject** (the platform's real target): baseline from resting
heart rate; tau from post-stressor recovery curves in synchronized
sessions; gain from response amplitude to tagged events; noise from
resting variance. Every parameter is estimable from the spec's
existing capture channels — camera, smartwatch, journal — which is the
point: SOMA v0.1 requires no new capture hardware.

**Deceased subject** (the Turing case): no autonomic stream exists or
ever will. Calibration entries are PRIORS derived from mannerism
evidence (bitten nails and fidgeting → tension baseline prior 0.45;
hesitation-sharpening under pressure → arousal tell), confidence
capped at 0.35, and the block carries
`channel_status: "uncalibrated-priors-only"`. The honesty principle is
enforced in the data, not in a disclaimer.

## 9. Evaluation — the ablation test

Part VII's claim ("functional similarity is the entire claim") becomes
falsifiable as follows: run the same subject with AFFECT enabled and
with AFFECT ablated (no interoception, base parameters, no tuning),
against held-out affect-laden material — journal entries, decisions
under stress, humor moments the model never saw. If the affect-enabled
run does not predict the held-out behavior better than the ablation,
the subsystem is decoration and must be fixed. Fidelity asserted
without this test is marketing (spec Part V).

Secondary metrics: divergence reproduction (does the model show-one-
thing-feel-another in the contexts the divergence map says it should),
and soma plausibility (does the trace look like an autonomic record,
not a random walk — bounded, decaying, event-locked).

## 10. Open questions for v0.2

Circadian structure on fatigue. Whether warmth needs splitting
(safety vs. affection). Sleep/consolidation coupling to Appendix C's
save rule. Whether Tier 2 should also modulate refusal/hedging
thresholds (risk appetite), which is psychologically real but needs
careful safety analysis. LLM-as-appraiser behind the rule-table
oracle. And the visceral channels, which wait for capture maturity,
per the gradient.
