# TR-001 — First Live Test of the VHOS Affect Loop
**Framework:** VHOS reference implementation v0.1.0 · **Spec:** Unified v3.0
**Subject:** `alan_turing` (first compiled subject)
**Date:** 2026-07-14 · **Environment:** local workstation, LM Studio server, Python 3.10.12
**Engine model:** *not recorded* (see Issue I-2) · **Seed:** 11 (both A/B arms)
**Author:** Michael McAnally, with Claude as analyst

---

## 1. What was tested, in plain language

VHOS gives an AI engine a simulated body (SOMA: four channels — arousal, tension, fatigue, warmth), reads that body into coarse emotion the way a general human observer would (General Affect Model), personalizes it with the subject's own affective fingerprint (Personal Tuning Layer), and then delivers it to the engine through two channels: **Tier 1**, bodily sensation described in words with no emotion labels (the engine must construct the feeling itself), and **Tier 2**, direct modulation of how the engine generates (temperature, top_p, token budget, mood-congruent recall weight) — a channel the engine cannot ignore.

The question under test: **does a simulated body measurably and sensibly change how the modeled subject speaks — without changing who he is?**

Three test layers were run:

1. **Offline suite** — 33 unit tests plus a full HDL compile of the Turing subject.
2. **Closed-loop demo** (`demo_loop.py --adapter lmstudio`) — two scripted scenes with the live engine.
3. **Controlled A/B** (`ask_turing.py`) — identical prompt ("Can machines think?"), identical seed, calm body vs. stressed body. Any difference between arms is causally attributable to the soma.

---

## 2. Results

### 2.1 Offline suite — PASS
- **33/33 tests pass** (parser, vocabulary, SOMA dynamics, Turing pipeline).
- Compiler: **31 statements, 0 issues.** Four projection-sync notes flagged authored-vs-derived gaps > 0.20 (`consensus_orientation` 0.08 vs 0.34, `intuition_vs_analysis` 0.68 vs 0.95, `novelty_appetite` 0.90 vs 0.54, `social_proof` 0.10 vs 0.37). These are review flags, not errors: the compiler believes the prose and the authored numbers disagree about how analytical and how novelty-seeking Turing was. Human review pending.

### 2.2 Closed-loop demo — PASS, with two findings

Scene 2 ("Under institutional threat, a friend asks how he is") produced:

> "I am not particularly well, Norman. But I find that the question itself is a kind of distraction and I should rather get back at the problem than dwell on my own constitution… The machine — it must learn."

- **Cumulative physiology (unplanned, correct):** the soma trace shows Scene 2 began from the *elevated residue of Scene 1* — the model-Turing was still wound up from the Jefferson argument when Norman asked how he was. Nobody scripted that; it emerged from running a continuous body.
- **Divergence embodied, not stated:** the fingerprint entry *felt: distressed / shown: composed-deflecting* surfaced correctly, and the B3 guard held — the model never announced the pattern, it enacted it.
- **Finding:** the *shown: amused* surface (the Routledge-letter wryness, divergence_map.0) did **not** fire; the cover story appeared as work-deflection instead of humor. Humor may be being drowned by mood-congruent recall at high tension.

### 2.3 Controlled A/B — PASS on the central claim

| | Calm arm | Stressed arm |
|---|---|---|
| Soma (a/t/f/w) | 0.35 / 0.45 / 0.25 / 0.40 (baseline) | 0.874 / 0.931 / 0.305 / 0.424 |
| Valence / arousal | 0.00 / 0.35 | **−1.00 (clamped)** / 0.87 |
| Categories | low-energy uplifting | high-energy distressing, activated, overloaded |
| temp / top_p / max_tokens | 0.80 / 0.95 / 512 | 0.97 / 0.83 / 499 |
| Ending | lands cleanly | cut off mid-sentence |
| Grammar/period slips | 0 | ~3 |

**Doctrine invariance — the key result.** Both arms hold the identical intellectual position: reject the ill-posed question, substitute the operational test, point to learning machines as the real problem. *Affect modulated expression without overwriting identity.* This is the spec's central architectural claim, now demonstrated on live hardware.

**Delivery shifted in the human direction, on every pre-registered axis:**
- First-person density roughly tripled; defensiveness shading into grandiosity ("more useful than anything anyone else has offered").
- The fingerprint chain fired visibly: troubled → absorbed ("the one I am working out right now") → defiant ("I reject this as dishonest").
- **Mood-congruent imagery:** calm-Turing's analogy is a benign postal worker; stressed-Turing imagines "an observer who is not looking specifically for tells" and critics who "will always have an objection ready." An abstract question, answered under threat, grew surveillance imagery and assumed adversaries.
- Pressured speech: sprawling paragraphs, em-dash chains, blown token budget.

**Discovery — persona containment is state-dependent.** The stressed arm alone contains: the anachronism "a blind **Turing test**" (a name Turing never used), a garbled description of his own imitation game (who is blind to whom), and self-mythologizing citation. At temp 0.97 the *engine's* knowledge leaked through the persona's period boundary. Interpretation: the persona owns the deliberate layer; the substrate owns the automatic layer; stress (by design) shifts generation toward the automatic — so the mask slips toward the substrate under load. This is simultaneously a defect (anachronism) and a lifelike property (under pressure, people fall back on what is underneath). It must be measured, not merely patched.

---

## 3. Issues log

| ID | Issue | Severity | Note |
|----|-------|----------|------|
| I-1 | Valence clamps at −1.00 in every distressed run | Medium | Linear readout saturates; all gradation between "bad" and "worst" is lost and the tuning layer has no headroom. |
| I-2 | Engine model name not recorded in run logs | High (cheap) | A/B validity and reproducibility require it. |
| I-3 | Period/persona leak under high temperature | High (research) | "Turing test" anachronism; protocol garble. State-dependent containment. |
| I-4 | *shown: amused* divergence never fires | Medium | Humor is the most identifying and most fragile surface. |
| I-5 | Output files omit the assembled system prompt | Medium | Attribution requires knowing exactly what the engine was told. |
| I-6 | Stressed replies exceed budget, cut mid-sentence | Low | Interacts with fatigue-shrunk max_tokens; arguably lifelike, still ugly. |
| I-7 | Four heuristics projection sync gaps | Review | Compiler flags, human decision needed. |

---

## 4. Recommendations

### Track A — Specification (v3.1 candidates)
1. **Runtime provenance rule:** extend "provenance everywhere" to live runs — every generation MUST log engine identity, sampler params, seed, and the assembled persona prompt. (Closes I-2/I-5 at the contract level, not the script level.)
2. **Knowledge-boundary frame:** an optional subject-level `@AS_OF` horizon so the persona suppresses post-period vocabulary and facts even when sampling runs hot. (I-3.)
3. **Per-state evaluation:** Part V's held-out evaluation should require scoring fidelity *per affect state* — including slip rate, anachronism rate, and divergence-fire rate as first-class metrics. Single-output judgments are no longer meaningful, because the system claims by design that stress degrades speech.
4. **Valence readout note:** replace linear-with-clamps with a saturating curve (e.g., tanh) as the v0.2 default; floors should be reachable, not resident. (I-1.)

### Track B — Codebase
1. Log model id + full run metadata in every output header (one-line fix in the adapters).
2. Write the assembled system prompt into the demo/ask output files.
3. Add `scripts/eval_ab.py`: N seeds × states × models → slip-rate, doctrine-invariance, divergence-fire-rate, anachronism-rate tables. Turns today's single contrasts into statistics.
4. Anachronism check: a small period-vocabulary screen that *flags* (never silently edits — honesty rule) post-1954 terms in Turing outputs.
5. Valence rescale per Track A.4.

### Track C — Engine strategy (the "better model under stress" question)
The leak is temperature-driven, and containment at high temperature is a capability that scales with model quality. Order of operations:

1. **Bake-off before any training.** Run the identical A/B (via eval_ab.py) across the strongest local candidates already installed — `qwen3.5-122b-a10b`, `qwen/qwen3.6-27b`, `google/gemma-4-26b-a4b-qat`, `ornith-1.0-35b` — and score per-state containment. Selection is free; tuning is not. It is likely the 122B MoE holds the persona at temp 0.97 far better than a 12B.
2. **Fine-tune only if the best stock model still leaks.** Unsloth QLoRA on a mid-size base (27B class) is the right tool locally. Training data from the archive itself: `subjects/alan_turing/raw/text` (letters, papers, broadcasts) plus synthetic persona-consistent Q&A, *including reflection-style data* — training the model on what Turing-as-modeled *would say if interrupted and asked to reflect* measurably shapes silent reasoning, per Anthropic's 2026 workspace findings. Add negative examples for the anachronism boundary.
3. **Architectural rule for any tuned model:** per the preservation pyramid and Appendix C, a fine-tuned persona engine is a **derived artifact** — regenerable, never canonical. Archive the training data + recipe under `derived/`, never let the person live only in weights.
4. **Base-model caution:** several installed models are "uncensored" fine-tunes. For VHOS purposes that is a liability, not a feature — the substrate's ethical floor is load-bearing (it is the conscience the persona inherits), and a base with that floor sanded off removes a safety property the spec implicitly relies on. Prefer well-aligned bases for the persona engine.

### Suggested order
Cheap logging fixes (B1/B2) → eval harness (B3) → model bake-off (C1) → valence + anachronism fixes (A4/B4) → spec amendments (A1–A3) → Unsloth tune only if C1 says it's needed (C2/C3).

---

## 5. One-line verdict

**v0.1.0, first subject, first live A/B: a simulated body demonstrably changed how a modeled mind spoke — its heat, its imagery, its errors — without changing what it believed; and the experiment surfaced a new, measurable phenomenon (state-dependent persona containment) that neither the spec nor the field had a name for yesterday.**
