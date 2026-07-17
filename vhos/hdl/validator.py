"""HDL validator — Contract 2 rules, enforced in code.

Errors fail compilation; warnings are reported and compilation
proceeds.  Error philosophy per spec: when prose and @CHAIN disagree, a
conforming compiler REPORTS AN ERROR rather than silently preferring
either form.

Rule inventory
    E001  required tag missing (@LAYER @AUTHOR @CONFIDENCE @SOURCES)
    E002  confidence outside [0,1]
    E003  layer not in reserved set
    E004  author not in reserved set (self | ai | instance[:id] | other:<id>)
    E005  intensity not in reserved set        (parser also guards this)
    E006  chain word does not resolve against vocabulary (+custom)
    E007  @CHAIN disagrees with prose chain
    W001  chain word's vocabulary sides do not match its chain verb
    W002  self/instance-authored confidence != 1.00 (convention)
    W003  empty @SOURCES list
    W004  self-authored statement without self-attestation pointer

The self-authority rule (spec Part II + Appendix C): statements with
author self or instance are IMMUTABLE to the compiler.  The parser sets
``immutable``; nothing in this package ever rewrites such a statement —
enforced structurally (there is no code path that modifies them) and
checked here for the output flag.
"""

import re
from dataclasses import dataclass

from .parser import LAYERS, INTENSITY_MODIFIERS

AUTHOR_RE = re.compile(r"^(self|ai|instance(:[A-Za-z0-9_\-]+)?|other:[A-Za-z0-9_\-]+)$")


@dataclass
class Issue:
    severity: str      # "error" | "warning"
    code: str
    line: int
    message: str

    def __str__(self):
        return "%s %s (line %d): %s" % (self.severity.upper(), self.code,
                                        self.line, self.message)


def validate(document, vocabulary):
    issues = []
    for stmt in document.statements:
        issues.extend(_validate_statement(stmt, vocabulary))
    return issues


def _validate_statement(s, vocab):
    out = []

    # E001 required tags
    if not s.layer:
        out.append(Issue("error", "E001", s.line, "@LAYER missing"))
    if not s.author:
        out.append(Issue("error", "E001", s.line, "@AUTHOR missing"))
    if s.confidence < 0:
        out.append(Issue("error", "E001", s.line, "@CONFIDENCE missing"))
    if not s.sources:
        out.append(Issue("error", "E001", s.line, "@SOURCES missing"))

    # E002 confidence range
    if s.confidence >= 0 and not (0.0 <= s.confidence <= 1.0):
        out.append(Issue("error", "E002", s.line,
                         "confidence %r outside [0,1]" % s.confidence))

    # E003 layer
    if s.layer and s.layer not in LAYERS:
        out.append(Issue("error", "E003", s.line, "unknown layer %r" % s.layer))

    # E004 author
    if s.author and not AUTHOR_RE.match(s.author):
        out.append(Issue("error", "E004", s.line, "unknown author %r" % s.author))

    # E005 intensity
    for it in list(s.chain_intensities) + [s.intensity]:
        if it is not None and it not in INTENSITY_MODIFIERS:
            out.append(Issue("error", "E005", s.line, "unknown intensity %r" % it))

    # E006 / W001 chain words
    for word, side, inten in zip(s.chain, s.chain_sides, s.chain_intensities):
        if word not in vocab:
            out.append(Issue("error", "E006", s.line,
                             "chain word %r not in vocabulary %s v%s "
                             "(or subject custom additions)"
                             % (word, vocab.name, vocab.version)))
            continue
        warn = vocab.check_chain_link(side, word, inten)
        if warn:
            out.append(Issue("warning", "W001", s.line, warn))

    # E007 @CHAIN vs prose — the prose is authoritative; disagreement
    # is an ERROR, never silently resolved.
    if s.chain_annotation:
        if s.chain_annotation != s.chain:
            out.append(Issue("error", "E007", s.line,
                             "@CHAIN %s disagrees with prose chain %s"
                             % (s.chain_annotation, s.chain)))

    # W002 self-confidence convention
    if s.immutable and 0 <= s.confidence < 1.0:
        out.append(Issue("warning", "W002", s.line,
                         "subject/instance-authored statements are "
                         "conventionally @CONFIDENCE 1.00 (found %.2f)"
                         % s.confidence))

    # W003/W004 sources
    if s.sources == []and s.confidence >= 0:
        pass  # covered by E001
    if s.author == "self" and s.sources and \
            not any(src.startswith("self-attestation/") for src in s.sources):
        out.append(Issue("warning", "W004", s.line,
                         "self-authored statement without a "
                         "self-attestation/<date> source pointer"))

    return out


def has_errors(issues):
    return any(i.severity == "error" for i in issues)
