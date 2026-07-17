# HDL Compiler Design v0.1 (vhosc-0.1.0)

The compiler turns `hdl/subject.hdl` (prose, the authored truth) into
the Contract 2 derived projections. Everything it writes can be
deleted and regenerated; nothing it writes is ever authoritative over
the prose. Implementation: `vhos/hdl/`.

## Pipeline

    subject.hdl
      -> parser.py     line-oriented, reports line numbers, never repairs
      -> validator.py  Contract 2 rules; errors fail, warnings report
      -> compiler.py   emits derived/<version>/:
           statements.json       compiled statements (Contract 2)
           heuristics.json       merged projection + sync report
           affect.json           the AFFECT_FINGERPRINT block
           compile_report.json   issues, counts, timestamps

## Grammar accepted (v0.1)

Headers: `HDL_VERSION SUBJECT_ID PRIMARY_AUTHOR_MODE LAST_COMPILED
VOCABULARY_NAME VOCABULARY_VERSION LAST_UPDATED`. Comments: `#`.

Assertion: `THIS SUBJECT <VERB> <object>[ <intensity>].` — the 16
reserved verbs; intensity is the final word when it is one of the six
modifiers, otherwise part of the object ("understanding nature deeply"
keeps "deeply").

Conditional/chain: `WHEN THIS SUBJECT <stimulus>, they FEEL <word>[
<int>][, THEN BECOME|ACT|FEEL <word>[ <int>]]*.` One link =
conditional; more = chain.

Annotations: one or more tags per line; `@SOURCES [` lists may wrap
lines until the bracket closes; an indented non-@ line inside the
annotation block continues the previous tag (multi-line `@NOTE`).

Blocks: `HEURISTICS_PROJECTION` and `AFFECT_FINGERPRINT`, indented,
in exactly the shapes the spec uses (keyed values with optional
`@CONFIDENCE`/`@SOURCES`/`@NOTE` tails; `- felt: x shown: y` list
items). Every leaf serializes as `{"value": v, "confidence": c,
"sources": [...]}`.

## Rules enforced

| code | severity | rule |
|---|---|---|
| E001 | error | required tag missing (@LAYER @AUTHOR @CONFIDENCE @SOURCES) |
| E002 | error | confidence outside [0,1] |
| E003 | error | layer not in reserved set |
| E004 | error | author not self / ai / instance[:id] / other:<id> |
| E005 | error | intensity not in reserved set |
| E006 | error | chain word not in vocabulary (+ subject custom) |
| E007 | error | @CHAIN disagrees with prose (prose is authoritative; disagreement is REPORTED, never silently resolved — spec Part II) |
| W001 | warn | chain word's vocabulary sides don't fit its verb (e.g. ACT amused — amused has no external side) |
| W002 | warn | self/instance-authored confidence != 1.00 |
| W004 | warn | self-authored statement lacking self-attestation pointer |

The intensity-split entries (ashamed, unhappy) resolve at vocabulary
lookup per Contract 2: low-intensity mapping only under a weakening
modifier (weakly, rarely).

## Self-authority, enforced structurally

Statements with `@AUTHOR self` or `instance` are marked immutable in
the output. The compiler contains NO code path that rewrites, lowers,
or drops a parsed statement — enforcement by absence, which is
stronger than enforcement by check. When evidence contradicts a
subject-authored statement, the correct move is a NEW ai-authored
statement beside it (spec: both voices remain visible).

## The heuristics projection: authored ⟂ derived, sync-checked

`projection.py` is the published mapping table the spec requires:
content-aware rules from (verb, object-keywords) to slot deltas, base
0.5, scaled by intensity factor and statement confidence, clamped to
[0,1]. Every derived slot records its contributing statement lines —
full retrace from number to prose to source.

When the author also writes a `HEURISTICS_PROJECTION` block, the
authored value WINS (self-authority extended to the block), the
derived value is recorded beside it, and gaps above 0.20 go to the
sync report. The Turing compile currently reports four such gaps —
that is the system working: the mapping table only sees what the prose
says, the author knows more, and a reviewer decides which needs
editing. Report, never silently prefer.

## Authoring guidelines learned from the Turing build

Write objects person-neutral ("truthfulness in oneself", not "in
himself") — assembly renders statements in second person and neutral
phrasing survives the transform. Keep stimuli simple verb phrases
("is threatened by institutional authority") — the runtime converts
the leading verb to second person heuristically. One idea per
statement; put connective tissue in `@NOTE`.

## Deviations from spec, declared

Subject-specific vocabulary additions are accepted as
`hdl/vocabulary-custom.json` (same shape as vocabulary.json) rather
than a `.hdl` file — revisit when custom-vocabulary authoring gets
real use. Multi-line @NOTE support is an extension (the spec never
shows one). Both are additive.
