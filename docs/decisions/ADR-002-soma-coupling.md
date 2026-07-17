# ADR-002: SOMA coupling = prompt + parameters (Tier 1 + Tier 2)

Date: 2026-07-14 · Status: accepted · Decided by: Michael McAnally

## Decision

SOMA state influences cognition through two simultaneous mechanisms:
Tier 1, interoceptive rendering into context (sensation language, no
emotion labels); Tier 2, mechanical modulation of engine parameters
(temperature, top_p, max_tokens, retrieval mood-congruence weight).

## Rationale

Tier 1 alone is ignorable — a paragraph the engine may weight at zero;
that leaves soma as "data about a body," exactly the failure the spec
names. Tier 2 cannot be ignored: it changes the sampling distribution
itself. Together they give portability (Tier 1 runs on any engine)
plus enforcement (Tier 2 wherever we control the engine — which
local-first already guarantees). Full mechanism: soma-design §6.

## Rejected

Prompt-only (maximum portability, no enforcement). Training-time
integration now (strongest coupling, but requires fine-tuning
infrastructure and paired data that Stage 0–2 subjects don't have;
the tier structure lets it arrive later as Tier 3 without breakage).
