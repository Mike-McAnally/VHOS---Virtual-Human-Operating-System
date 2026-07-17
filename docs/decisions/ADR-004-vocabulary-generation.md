# ADR-004: vocabulary.json is generated from Appendix A, never edited

Date: 2026-07-14 · Status: accepted

## Decision

`vhos/vocabulary.json` (220 words, 286 side-rows) was machine-extracted
from Appendix A of VHOS_v3_unified.pdf on 2026-07-14 and validated:
count matches the spec's 220; every side/category pair belongs to the
published category sets; the two intensity-split entries (ASHAMED,
UNHAPPY) carry machine-readable conditions; multi-word and multi-row
entries (AT EASE, PATIENT with three rows) verified by spot check.

Per the spec's own rule, the appendix is canonical and any machine file
is generated FROM it — so this file is never hand-edited. Vocabulary
changes happen in the spec document first; regeneration follows.
Subject-specific additions live in per-subject custom files and never
touch this one.
