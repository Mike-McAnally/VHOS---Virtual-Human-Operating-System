"""HDL parser — prose (the authored truth) -> AST.

Grammar per spec Part II.  Design rules honored:
  * the prose is authoritative; structured forms are derived,
  * a statement is assertion | conditional | chain,
  * every statement carries an annotation block (@LAYER @AUTHOR
    @CONFIDENCE @SOURCES required; @CHAIN @AS_OF @AFFECT @NOTE
    @REVIEWED optional),
  * multiple tags may share a line; @SOURCES lists may wrap lines,
  * lines beginning with # are comments,
  * HEURISTICS_PROJECTION and AFFECT_FINGERPRINT are indented blocks.

The parser is line-oriented, stdlib-only, and reports line numbers on
every error.  It never repairs input silently (spec: a conforming
compiler reports rather than silently prefers).
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional

ASSERTION_VERBS = (
    "VALUES", "BELIEVES", "FEARS", "TRUSTS", "PREFERS", "DECIDES",
    "WEIGHS", "DISCOUNTS", "ANCHORS_ON", "DEFAULTS_TO", "IS_SWAYED_BY",
    "RESISTS", "FRAMES", "HOPES", "IDENTIFIES_AS", "REJECTS",
)
CHAIN_VERBS = ("FEEL", "BECOME", "ACT")
INTENSITY_MODIFIERS = ("strongly", "moderately", "weakly",
                       "rarely", "occasionally", "always")
LAYERS = ("drives", "social", "heuristics", "narrative")
HEADER_KEYS = ("HDL_VERSION", "SUBJECT_ID", "PRIMARY_AUTHOR_MODE",
               "LAST_COMPILED", "VOCABULARY_NAME", "VOCABULARY_VERSION",
               "LAST_UPDATED")
REQUIRED_TAGS = ("LAYER", "AUTHOR", "CONFIDENCE", "SOURCES")
KNOWN_TAGS = REQUIRED_TAGS + ("CHAIN", "AS_OF", "AFFECT", "NOTE", "REVIEWED")


class ParseError(Exception):
    def __init__(self, line_no, message):
        super().__init__("line %d: %s" % (line_no, message))
        self.line_no = line_no


@dataclass
class Statement:
    form: str                         # assertion | conditional | chain
    verb: Optional[str]               # assertion verb, else None
    object: Optional[str]             # assertion object, else None
    stimulus: Optional[str]           # conditional/chain stimulus
    chain: List[str] = field(default_factory=list)
    chain_sides: List[str] = field(default_factory=list)   # feel|become|act
    chain_intensities: List[Optional[str]] = field(default_factory=list)
    intensity: Optional[str] = None
    layer: str = ""
    author: str = ""
    confidence: float = -1.0
    sources: List[str] = field(default_factory=list)
    as_of: Optional[str] = None
    affect_refs: List[str] = field(default_factory=list)
    note: Optional[str] = None
    reviewed: Optional[str] = None
    chain_annotation: List[str] = field(default_factory=list)  # from @CHAIN
    line: int = 0
    immutable: bool = False           # self / instance authored

    def to_contract2(self, subject_id):
        """Serialize per Contract 2 (vhos/3.0/statement)."""
        return {
            "$schema": "vhos/3.0/statement",
            "subject_id": subject_id,
            "form": self.form,
            "verb": self.verb,
            "object": self.object,
            "stimulus": self.stimulus,
            "chain": list(self.chain),
            "chain_sides": list(self.chain_sides),
            "intensity": self.intensity,
            "layer": self.layer,
            "author": self.author,
            "confidence": self.confidence,
            "sources": list(self.sources),
            "as_of": self.as_of,
            "affect_refs": list(self.affect_refs),
            "note": self.note,
            "reviewed": self.reviewed,
            "immutable": self.immutable,
            "source_line": self.line,
        }


@dataclass
class HdlDocument:
    header: dict
    statements: List[Statement]
    heuristics_projection: dict       # authored block (may be empty)
    affect_fingerprint: dict          # authored block (may be empty)


# ----------------------------------------------------------------------
# top-level parse
# ----------------------------------------------------------------------

def parse_hdl(text):
    lines = text.split("\n")
    header = {}
    statements = []
    heuristics = {}
    fingerprint = {}

    i = 0
    n = len(lines)
    while i < n:
        raw = lines[i]
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        first_word = stripped.split(None, 1)[0]

        if first_word in HEADER_KEYS:
            value = stripped[len(first_word):].strip().strip('"')
            header[first_word] = value
            i += 1
            continue

        if first_word == "HEURISTICS_PROJECTION":
            block, i = _consume_block(lines, i)
            heuristics = _parse_nested_block(block)
            continue

        if first_word == "AFFECT_FINGERPRINT":
            block, i = _consume_block(lines, i)
            fingerprint = _parse_nested_block(block)
            continue

        if stripped.startswith("THIS SUBJECT") or stripped.startswith("WHEN THIS SUBJECT"):
            stmt, i = _consume_statement(lines, i)
            statements.append(stmt)
            continue

        raise ParseError(i + 1, "unrecognized construct: %r" % stripped[:60])

    return HdlDocument(header=header, statements=statements,
                       heuristics_projection=heuristics,
                       affect_fingerprint=fingerprint)


# ----------------------------------------------------------------------
# statements
# ----------------------------------------------------------------------

def _consume_statement(lines, i):
    start = i
    body_parts = []
    n = len(lines)
    # accumulate statement prose until a line ends with '.'
    while i < n:
        s = lines[i].strip()
        if s.startswith("#"):
            i += 1
            continue
        body_parts.append(s)
        i += 1
        if s.endswith("."):
            break
    else:
        raise ParseError(start + 1, "statement never terminated with '.'")
    body = " ".join(body_parts)

    # accumulate annotation lines (indented or not, starting with @);
    # keep consuming while brackets are unbalanced (wrapped @SOURCES).
    # An indented non-@ line directly inside the annotation block is a
    # continuation of the previous tag's free text (multi-line @NOTE).
    ann_lines = []
    while i < n:
        raw = lines[i]
        s = raw.strip()
        if s.startswith("@"):
            buf = s
            while buf.count("[") > buf.count("]") and i + 1 < n:
                i += 1
                buf += " " + lines[i].strip()
            ann_lines.append(buf)
            i += 1
        elif s and ann_lines and raw[:1] in (" ", "\t") and not s.startswith("#"):
            ann_lines[-1] += " " + s
            i += 1
        elif not s and _next_nonblank_is_annotation(lines, i):
            i += 1
        else:
            break

    stmt = _parse_statement_body(body, start + 1)
    _apply_annotations(stmt, ann_lines, start + 1)
    return stmt, i


def _next_nonblank_is_annotation(lines, i):
    for j in range(i + 1, len(lines)):
        s = lines[j].strip()
        if s:
            return s.startswith("@")
    return False


def _parse_statement_body(body, line_no):
    body = re.sub(r"\s+", " ", body).strip()
    if not body.endswith("."):
        raise ParseError(line_no, "statement must end with '.'")
    body_noperiod = body[:-1].strip()

    if body.startswith("WHEN THIS SUBJECT"):
        return _parse_conditional_or_chain(body_noperiod, line_no)

    if body.startswith("THIS SUBJECT"):
        rest = body_noperiod[len("THIS SUBJECT"):].strip()
        m = re.match(r"([A-Z_]+)\s+(.+)$", rest)
        if not m:
            raise ParseError(line_no, "cannot parse assertion: %r" % body[:60])
        verb, obj = m.group(1), m.group(2).strip()
        if verb not in ASSERTION_VERBS:
            raise ParseError(line_no, "unknown assertion verb %r" % verb)
        obj, intensity = _strip_intensity(obj)
        return Statement(form="assertion", verb=verb, object=obj,
                         stimulus=None, intensity=intensity, line=line_no)

    raise ParseError(line_no, "statement must begin THIS SUBJECT or WHEN THIS SUBJECT")


def _parse_conditional_or_chain(body, line_no):
    rest = body[len("WHEN THIS SUBJECT"):].strip()
    m = re.search(r",\s*they\s+FEEL\s+", rest)
    if not m:
        raise ParseError(line_no, "conditional must contain ', they FEEL '")
    stimulus = rest[:m.start()].strip()
    tail = rest[m.end():]

    segments = re.split(r",\s*THEN\s+", tail)
    chain, sides, intensities = [], [], []

    word, inten = _strip_intensity(segments[0].strip().rstrip(","))
    chain.append(word.lower())
    sides.append("feel")
    intensities.append(inten)

    for seg in segments[1:]:
        seg = seg.strip().rstrip(",")
        m2 = re.match(r"(FEEL|BECOME|ACT)\s+(.+)$", seg)
        if not m2:
            raise ParseError(line_no, "chain link must start FEEL/BECOME/ACT: %r" % seg)
        w, it = _strip_intensity(m2.group(2).strip())
        chain.append(w.lower())
        sides.append(m2.group(1).lower())
        intensities.append(it)

    form = "conditional" if len(chain) == 1 else "chain"
    # overall intensity of a conditional = intensity of its single link
    overall = intensities[0] if form == "conditional" else None
    return Statement(form=form, verb=None, object=None, stimulus=stimulus,
                     chain=chain, chain_sides=sides,
                     chain_intensities=intensities,
                     intensity=overall, line=line_no)


def _strip_intensity(text):
    tokens = text.split()
    if tokens and tokens[-1].lower() in INTENSITY_MODIFIERS:
        return " ".join(tokens[:-1]).strip(), tokens[-1].lower()
    return text, None


# ----------------------------------------------------------------------
# annotations
# ----------------------------------------------------------------------

def _apply_annotations(stmt, ann_lines, line_no):
    for line in ann_lines:
        parts = re.split(r"(?=@[A-Z_]+)", line)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            m = re.match(r"@([A-Z_]+)\s*(.*)$", part, re.S)
            if not m:
                raise ParseError(line_no, "bad annotation fragment %r" % part[:40])
            tag, value = m.group(1), m.group(2).strip()
            if tag not in KNOWN_TAGS:
                raise ParseError(line_no, "unknown annotation tag @%s" % tag)
            _set_tag(stmt, tag, value, line_no)
    if stmt.author.startswith(("self", "instance")):
        stmt.immutable = True


def _set_tag(stmt, tag, value, line_no):
    if tag == "LAYER":
        stmt.layer = value.lower()
    elif tag == "AUTHOR":
        stmt.author = value.strip()
    elif tag == "CONFIDENCE":
        try:
            stmt.confidence = float(value)
        except ValueError:
            raise ParseError(line_no, "@CONFIDENCE not a number: %r" % value)
    elif tag == "SOURCES":
        stmt.sources = _parse_list(value)
    elif tag == "CHAIN":
        inner = value.strip()
        if inner.startswith("[") and inner.endswith("]"):
            inner = inner[1:-1]
        stmt.chain_annotation = [w.strip().lower()
                                 for w in inner.split("->") if w.strip()]
    elif tag == "AS_OF":
        stmt.as_of = value
    elif tag == "AFFECT":
        stmt.affect_refs = _parse_list(value)
    elif tag == "NOTE":
        stmt.note = value
    elif tag == "REVIEWED":
        stmt.reviewed = value


def _parse_list(value):
    v = value.strip()
    if v.startswith("[") and v.endswith("]"):
        v = v[1:-1]
    return [x.strip() for x in v.split(",") if x.strip()]


# ----------------------------------------------------------------------
# indented blocks (HEURISTICS_PROJECTION / AFFECT_FINGERPRINT)
# ----------------------------------------------------------------------

def _consume_block(lines, i):
    """Collect the block head line plus all following lines that are
    blank or indented.  Returns (list of (line_no, text), next_index)."""
    block = [(i + 1, lines[i])]
    i += 1
    n = len(lines)
    while i < n:
        raw = lines[i]
        if not raw.strip():
            i += 1
            continue
        if raw[0] in (" ", "\t"):
            block.append((i + 1, raw))
            i += 1
        else:
            break
    return block, i


_LEAF_META_RE = re.compile(r"@(CONFIDENCE|SOURCES|NOTE)\s*")


def _parse_nested_block(block):
    """Parse the spec's indented block shapes into nested dicts.

    Supported shapes (exactly those used in spec Parts II-III):
        key:                      -> sub-dict
        key: value [@CONFIDENCE x] [@SOURCES [...]]
        - felt: x  shown: y       -> list item dict
        follow-on lines of a list item (deeper indent) add keys
    Leaf values: number, "quoted string", [list, of, items], or token.
    Every leaf becomes {"value": v[, "confidence": c][, "sources": [...]]}.
    """
    head_no, head = block[0]
    m = re.match(r"\s*([A-Z_]+)(?:\s+subject_id\s*=\s*\"([^\"]*)\")?\s*$", head)
    if not m:
        raise ParseError(head_no, "bad block header: %r" % head.strip()[:60])
    result = {"_block": m.group(1)}
    if m.group(2):
        result["subject_id"] = m.group(2)

    # stack of (indent, container)
    stack = [(-1, result)]
    for line_no, raw in block[1:]:
        indent = len(raw) - len(raw.lstrip())
        text = raw.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        if not stack:
            raise ParseError(line_no, "indentation underflow")
        container = stack[-1][1]

        if text.startswith("- "):
            # list item: parent must accept appends (list or lazy node)
            if not hasattr(container, "append"):
                raise ParseError(line_no, "list item outside a list context")
            item = {}
            _parse_inline_pairs(text[2:], item, line_no)
            container.append(item)
            stack.append((indent, item))
            continue

        m2 = re.match(r"([A-Za-z_][A-Za-z0-9_ ]*?):\s*(.*)$", text)
        if not m2:
            raise ParseError(line_no, "expected 'key: value' in block: %r" % text[:60])
        key, rest = m2.group(1).strip(), m2.group(2).strip()
        if isinstance(container, list):
            raise ParseError(line_no, "keyed line inside a list; use '- '")

        if rest == "":
            # empty value: could be a dict (next lines deeper) or a list
            # of '- ' items; decide lazily with a placeholder dict that
            # converts to list on first '- ' child.
            child = _LazyNode()
            container[key] = child
            stack.append((indent, child))
        else:
            container[key] = _parse_leaf(rest, line_no)
    return _finalize(result)


class _LazyNode:
    """Placeholder that becomes a dict or list depending on children."""
    def __init__(self):
        self.dict = {}
        self.list = []

    def __setitem__(self, k, v):
        self.dict[k] = v

    def append(self, v):
        self.list.append(v)


def _finalize(node):
    if isinstance(node, _LazyNode):
        node = node.list if node.list else node.dict
    if isinstance(node, dict):
        return {k: _finalize(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_finalize(v) for v in node]
    return node


def _parse_inline_pairs(text, item, line_no):
    """Parse '- felt: x  shown: y' style inline pairs, plus trailing
    @CONFIDENCE/@SOURCES metadata."""
    meta = _extract_meta(text)
    text = meta.pop("_rest")
    pairs = re.findall(r"([a-z_]+):\s*(\"[^\"]*\"|\S+)", text)
    for k, v in pairs:
        item[k] = v.strip('"')
    item.update(meta)


def _extract_meta(text):
    """Pull @CONFIDENCE x and @SOURCES [...] off the end of a value."""
    out = {}
    m = re.search(r"@CONFIDENCE\s+([0-9.]+)", text)
    if m:
        out["confidence"] = float(m.group(1))
        text = text[:m.start()] + text[m.end():]
    m = re.search(r"@SOURCES\s+(\[[^\]]*\])", text)
    if m:
        out["sources"] = _parse_list(m.group(1))
        text = text[:m.start()] + text[m.end():]
    m = re.search(r"@NOTE\s+(.*)$", text)
    if m:
        out["note"] = m.group(1).strip()
        text = text[:m.start()] + text[m.end():]
    out["_rest"] = text.strip()
    return out


def _parse_leaf(rest, line_no):
    meta = _extract_meta(rest)
    v = meta.pop("_rest")
    value = None
    if v.startswith("[") and v.endswith("]"):
        value = _parse_list(v)
    elif v.startswith('"') and v.endswith('"') and len(v) >= 2:
        value = v[1:-1]
    else:
        try:
            value = float(v)
        except ValueError:
            value = v          # qualitative token (spec allows these)
    leaf = {"value": value}
    leaf.update(meta)
    return leaf
