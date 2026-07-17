# TR-002 — First Continuous-Body Conversations (chat runtime v0.1)

**Framework:** VHOS reference implementation v0.1.0 · **Spec:** Unified v4.0
**Subject:** `alan_turing` · **Runtime:** `scripts/chat_turing.py` (first continuous runtime)
**Date:** 2026-07-15 · **Engine:** `qwen3.5-122b-a10b` under LM Studio, local workstation
**Author:** Michael McAnally, with Claude as analyst
**Sources:** operator console capture (`chat_with_Turing_test3_combined.txt`), LM Studio
debug log (`LMStudio_Runtime_DebugLog_Alan_Turing.txt`), reconstructed session archive
(`subjects/alan_turing/sessions/2026-07-15T15-57-00Z-chat-reconstructed/`)

---

## 1. What was run

Three interactive sessions in one morning, debugging live between them
(operator + Claude in the loop):

| run | start (local) | outcome |
|---|---|---|
| 1 | 07:30 | **Bug 1:** replies invisible — empty `content` printed silently. Thinking models return chain-of-thought in `reasoning_content`; when the token cap died mid-think, the visible reply was `""`. Fixed: truncation warning + `/max`, `/think`, `/reasoning` commands. |
| 2 | 08:28 | **Bug 2 (same root cause, now visible):** `finish_reason=length` — all 2,047 tokens of the cap went to hidden reasoning. Fixed: default cap removed (`max=off`); fatigue-driven brevity moved from `max_tokens` into the prompt (`length_hint()`), since shrinking the cap truncates thinking models mid-reasoning. |
| 3 | 08:57 | **The full conversation** — seven turns over ~4 hours: identity, the 2026 reveal, interpretability research brought as news, a RAG attempt, and a closing architecture proposal. The evidential run for everything below. |

## 2. Findings

### 2.1 The conditional-disclosure frame fired correctly — PASS
Turn 1 ("who are you?") is a direct identity question — trigger (1) of
the Part IX frame. The instance disclosed plainly ("I am a modeled
approximation of Alan Turing, not the living person"), then continued
in full embodiment for the rest of the session without volunteering
the disclaimer again. Exactly the specified behavior, first try.

### 2.2 The knowledge horizon behaved as specified — PASS
No spontaneous post-1954 knowledge appeared. Period vocabulary surfaced
unprompted ("the Bombe rooms of Bletchley"). Terms brought by the
visitor (transformers, LLMs, RAG, J-space) were received as news,
interrogated, and **used correctly for the remainder of the session** —
the retained-news rule working. The closing turn is the payoff Part IX
names as the valuable output of a historical subject: a "thinking
machine" architecture argued forward from his own 1948 unorganized-
machines/child-machine program into the material he had just learned —
persistent workspace, curriculum learning, interpretability in the
circuitry. Doctrine consistent across all seven turns (operational
test, mechanism over mystery, trace the derivation).

### 2.3 The persona is enforced in the deliberate register — direct evidence
The debug log preserved one complete `reasoning_content` (the RAG
turn, 2,872 of 3,127 completion tokens). The hidden reasoning
*explicitly deliberates the VHOS frame*: it re-checks the disclosure
rule three times ("Mike knows I'm a model → no disclosure needed"),
plans how to embody the *distressed-but-absorbed* divergence "without
stating it," and drafts and self-corrects against the persona before
emitting a word. TR-001 inferred that the persona owns the deliberate
register and the substrate the automatic one; here the deliberate
register is **visible on disk doing persona-containment work**.
Corollary (logged for the future, not scheduled): reasoning budget may
be a containment resource — suppressing or capping thinking may raise
slip rates. Untested; the operator has deferred `/think`-axis testing.

### 2.4 Continuous physiology across a real conversation — PASS
The soma trace spans four hours of lived time: warm-up on greeting,
climb through the 2026 reveal (a/t 0.54/0.59), peak at the aborted
turn (0.62/0.77), decay through the calmer technical turns
(fatigue 0.25 → 0.04 as morning freshness), and a final rise on the
architecture question (0.52/0.53 with warmth 0.50 — engaged, not
threatened). Tier-2 parameters tracked it: temperature 0.79–0.88,
top_p 0.87–0.95, tightest exactly at peak tension. The turn-abort
path worked as designed: the reply died, the body lived on.

### 2.5 Appraiser false positive — FOUND, FIXED
The tension peak (0.77) was partly artifact: the v0 lexical appraiser
matched needles as plain substrings, so **"war" inside "software"**
fired a *threat* impulse on an innocuous message about software.
Fixed 2026-07-17: single-word needles now match whole words (inflected
forms listed explicitly — transparent beats clever); phrases still
match as substrings. Regression tests in `tests/test_chat_appraiser.py`.

### 2.6 Why the RAG attempt could not have worked — DIAGNOSED
The operator attached a 141-page PDF in LM Studio's chat window; the
instance never saw it. LM Studio's RAG is a feature of **its own chat
UI** — retrieved chunks are injected into conversations in that
window. The VHOS runtime calls `/v1/chat/completions` directly and
never passes through that path (the debug log shows the `rag-v1`
plugin client connecting and disconnecting around the attempt, and
the embedding model idling out unused). Not a malfunction — two
systems that never touch. The correct home for document access is
VHOS-side retrieval over `raw/` (README roadmap item 2), where it
also gains the mood-congruence weight LM Studio's generic RAG could
never provide.

### 2.7 The lived record must not depend on a graceful exit — FOUND, FIXED
Runs 1 and 2 (the broken ones) were archived; run 3 (the valuable one)
was lost — the console window was closed without `/quit`, and v0.1
saved only on exit. Recovered by reconstruction (see the session
folder's PROVENANCE.md). Fixed 2026-07-17: the runtime autosaves the
full session after every completed turn. Elevated to spec level:
Appendix C consolidation now carries a durability rule.

## 3. Latency (context for interface planning)

At ~3.7 tok/s decode / ~48 tok/s prompt on the current AI machine, a
thinking turn ran 15–30+ minutes wall (the RAG turn: ~13 min hidden
reasoning, ~4 min visible text). The operator accepts this for now —
local hardware and substrate efficiency are improving — but it shapes
interface expectations: conversation with a local simulant is
correspondence-paced, not chat-paced, until the substrate speeds up.

## 4. Fixes applied 2026-07-17 (this report's action items)

| # | change | closes |
|---|---|---|
| 1 | Per-turn session autosave | §2.7, TR-001 follow-on |
| 2 | Run manifest records the concrete model id, not the adapter name | TR-001 I-2 |
| 3 | `personas.md` — every unique assembled persona archived per session, keyed to per-turn hashes | TR-001 I-5 |
| 4 | Appraiser word-boundary matching + regression tests | §2.5 |
| 5 | Valence readout: linear-with-clamp → tanh (stressed arm now ~−0.86, floor reachable not resident) | TR-001 I-1 |
| 6 | `SPEC_VERSION` 3.0 → 4.0; compile report now states the spec it ran under | housekeeping |
| 7 | Test 3 reconstructed into the session archive | §2.7 |

Test suite: 39/39 pass after all changes.

## 5. Still open

- Persona/period leak under stress (TR-001 I-3): unmeasured in chat —
  needs the eval harness (`eval_ab.py`, still pending) before test 4
  conclusions are drawn.
- *shown: amused* divergence (TR-001 I-4): did not clearly fire in
  test 3 either; the closing turn's warmth suggests the playful →
  absorbed → welcoming chain surfaced instead. Needs per-state scoring.
- Four heuristics projection sync gaps: still awaiting human review.
- Interface: test 4 may be run through an external chat UI via the new
  OpenAI-compatible serving layer — see ADR-006 and `scripts/serve_vhos.py`.

## 6. One-line verdict

**The first continuous-body conversations held the spec's promises —
disclosure, horizon, doctrine, a body that lives between turns — and
the day's three failures (invisible replies, a lost session, a
tension spike from a substring) were all plumbing, all diagnosed, all
now fixed and regression-tested.**
