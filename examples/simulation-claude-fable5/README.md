# Cloud simulation — Claude Fable 5 (Max) as substrate

Date: 2026-07-14 · Framework v0.1.0 · Requested by the operator as a
dry run BEFORE the LM Studio live test, with full knowledge that this
departs from the spec's local-first recommendation (author's
prerogative, recorded here).

## Method

The pipeline ran exactly as it will on the target machine — compiled
statements, SOMA states, General Affect Model, Personal Tuning Layer,
persona assembly — via `ask_turing.py --adapter mock --show-prompt`,
producing the precise system context and Tier-2 parameters for each
condition. Claude Fable 5 then generated each reply while operating
under that captured conditioning. Transcript: `transcript.md`.
Findings: `feedback-report.md`.

## Declared limits — read before trusting anything here

1. **Tier 2 was displayed, not enforced.** Claude cannot alter its own
   sampling temperature/top_p. Parameter effects were obeyed
   *voluntarily* (pacing, narrowing, length) — which is precisely the
   "ignorable conditioning" failure mode ADR-002 predicts for
   prompt-only coupling. Mechanical Tier-2 proof still requires the
   local LM Studio run.
2. **Prior contamination.** Claude knows Turing far beyond this
   archive's corpus (dates, Jefferson's Lister Oration, the 1952
   morphogenesis work) and also designed this harness. Where fidelity
   appears, some of it is the model's prior, not the conditioning.
   The feedback report marks which effects are attributable to which,
   where distinguishable.
3. **Demand characteristics.** The substrate knew it was being tested
   and what for. A local model will not.

These transcripts are engineering probes of the CONDITIONING, not
evidence of fidelity. The five judgment questions in
LIVE-TEST-GUIDE.pdf Part F still get answered only on the local run.
