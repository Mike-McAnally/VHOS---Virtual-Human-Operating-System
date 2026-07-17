# ADR-003: Turing corpus — verbatim excerpts + operator-run fetch

Date: 2026-07-14 · Status: accepted · Decided by: Michael McAnally

## Decision

The shipped archive contains verbatim EXCERPTS with full provenance
and a verification ladder (VERIFIED / APPROXIMATE / SECONDARY-NOTES,
each with a confidence cap). Complete texts are downloaded by the
operator via `scripts/fetch_sources.py`, checksummed into
raw/text/full/. The operator (Michael McAnally) explicitly accepted
responsibility for US-copyright-term full texts (Turing d. 1954: PD in
UK/EU since 2025; US terms on the 1936/1950 papers run to the 2030s–
2040s), judging impact negligible-to-harmless with no descendants.

## The fidelity constraint (why fetch, not transcribe)

Independent of copyright: the assistant does not reproduce long texts
from memory, because memory reproduction introduces errors and a
corrupted raw/ violates "raw material is sacred" at the root. Short
excerpts it is confident of, marked; everything long arrives by
download with a checksum. Raw means the actual bytes of the actual
words.

## Note

The Part VIII third-party-consent exemption applies to this subject
(deceased; sources public). This exemption does not extend to anyone
living, and this ADR sets no precedent for living subjects.
