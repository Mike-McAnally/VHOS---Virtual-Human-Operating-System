# MATERIAL Capture Guide

How data enters the archive (Contract 1), for both subject types this
repo now demonstrates: the living subject the platform is FOR, and the
deceased/historical subject used to exercise the machinery.

## The layout (Contract 1)

    subjects/<subject_id>/
      manifest.json          spec version + SHA-256 of everything protected
      raw/                   APPEND-ONLY, the irreplaceable record
        text/  audio/  video/  biometrics/  interviews/
      sessions/<ISO-ts>/     synchronized capture units (shared clock!)
      hdl/subject.hdl        the authored truth
      derived/<compiler>/    regenerable; delete freely

Tools: `python3 -m vhos.archive.scaffold subjects <id>` creates the
tree; `python3 -m vhos.archive.manifest subjects/<id>` checksums it;
`--verify` detects any change to protected trees. A changed checksum
under raw/ is never a legitimate edit — it is corruption or tampering.
Three copies of raw/, sessions/, hdl/ on independent media, minimum.

## Living subject — the priority order (spec Part V, Stage 0)

1. The two-hour life-story interview, recorded and transcribed — the
   single highest-leverage artifact known.
2. Journals that name feelings USING THE VOCABULARY (Appendix A words)
   — these become the labels for everything else.
3. Synchronized sessions: camera + smartwatch + shared clock recorded
   in `sessions/<ts>/clock.json`, journal entry afterwards. Even a
   handful begins the triangulation record.
4. Corpus export (email, posts, chat) into raw/text/, open formats.
5. Self-authored HDL: open subject.hdl and write `@AUTHOR self`
   statements with `@SOURCES [self-attestation/<date>]`. These are the
   statements no compiler may ever override.

## Deceased subject — the adaptations (learned building alan_turing)

**Verification ladder.** Every raw text file carries a header with
`verification:` one of VERIFIED (checked verbatim against a
reproduction, dated), APPROXIMATE (quoted from secondary memory;
compiler must cap dependent confidence — we used 0.70), or
SECONDARY-SOURCE NOTES (biography-derived observations, cap 0.75).
The cap travels in the file header so the compiler and the reviewer
see the same rule.

**Secondary sources are material.** Contemporary accounts (Hodges,
colleagues' recollections) live under `raw/text/secondary/` — the
spec's own Einstein example cites Isaacson the same way. They are the
deceased subject's substitute for the video channel: the externalized
soma as witnesses recorded it.

**Absence is provenance.** Channels that cannot exist get a README
saying so and what that caps: no interviews (BBC audio wiped) means
fidelity claims cap at written-material evaluation; no biometrics
means soma_calibration is priors-only at confidence ≤ 0.35 with
`channel_status: "uncalibrated-priors-only"`. List what does NOT
survive as explicitly as what does.

**Excerpts + operator fetch.** The archive ships accurate verbatim
excerpts with full citations; complete texts are fetched by the
operator via `python3 scripts/fetch_sources.py --all` (checksummed
into raw/text/full/PROVENANCE.json). Reason: an AI reproducing long
texts from memory introduces errors, and a corrupted raw/ poisons
everything downstream — "raw is sacred" is first a FIDELITY rule.
Bulk copyright responsibility for full texts rests with the operator
(ADR-003).

## The triangulation rule, restated for practice

Journal says what was felt; video says what was shown; biometrics say
what the body did. Agreement ≈ a true label. Divergence is not noise —
it is the most identifying data you will capture (the felt-one-thing-
showed-another signatures). For historical subjects the same structure
survives in weakened form: self-report letters vs. witnessed manner —
the Routledge letter (self-labeled distress) against colleagues'
memory of the wit is exactly a divergence pair, and it is in the
Turing fingerprint as one.
