"""HDL compiler front end.

Pipeline:  subject.hdl --parse--> AST --validate--> Contract 2 JSON
           + heuristics projection (authored ⟂ derived, sync-checked)
           + affect fingerprint (authored block, serialized)

Outputs land in  <subject_dir>/derived/<compiler_version>/ :
    statements.json      compiled HDL statements (Contract 2)
    heuristics.json      merged projection with per-slot provenance
    affect.json          the AFFECT_FINGERPRINT block
    compile_report.json  issues, counts, timestamps

Everything under derived/ can be deleted and regenerated; the prose
remains the authored truth (spec Part II / IV).

CLI:
    python3 -m vhos.hdl.compiler <subject_dir>
"""

import json
import os
import sys
from datetime import datetime, timezone

from .. import COMPILER_VERSION, SPEC_VERSION
from ..vocabulary import Vocabulary
from . import parser as hdl_parser
from . import validator
from . import projection


def compile_subject(subject_dir, vocabulary_path=None):
    hdl_path = os.path.join(subject_dir, "hdl", "subject.hdl")
    if not os.path.exists(hdl_path):
        raise FileNotFoundError("no hdl/subject.hdl under %s" % subject_dir)
    custom = os.path.join(subject_dir, "hdl", "vocabulary-custom.json")
    vocab = Vocabulary(path=vocabulary_path,
                       custom_path=custom if os.path.exists(custom) else None)

    with open(hdl_path, encoding="utf-8") as f:
        text = f.read()
    doc = hdl_parser.parse_hdl(text)
    issues = validator.validate(doc, vocab)

    subject_id = doc.header.get("SUBJECT_ID", os.path.basename(subject_dir))
    derived_dir = os.path.join(subject_dir, "derived", COMPILER_VERSION)
    os.makedirs(derived_dir, exist_ok=True)

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    ok = not validator.has_errors(issues)

    report = {
        "$schema": "vhos/3.0/compile-report",
        "subject_id": subject_id,
        "compiler": COMPILER_VERSION,
        "spec": SPEC_VERSION,
        "vocabulary": "%s v%s (%d words)" % (vocab.name, vocab.version, len(vocab)),
        "compiled_at": now,
        "status": "ok" if ok else "errors",
        "statement_count": len(doc.statements),
        "immutable_count": sum(1 for s in doc.statements if s.immutable),
        "issues": [str(i) for i in issues],
    }

    if ok:
        # statements.json — Contract 2
        statements = {
            "$schema": "vhos/3.0/statement-set",
            "subject_id": subject_id,
            "compiler": COMPILER_VERSION,
            "compiled_at": now,
            "header": doc.header,
            "statements": [s.to_contract2(subject_id) for s in doc.statements],
        }
        _write(derived_dir, "statements.json", statements)

        # heuristics.json — authored wins, derived fills, divergence reported
        derived = projection.derive(doc.statements)
        merged, sync = projection.merge(doc.heuristics_projection, derived)
        heuristics = {
            "$schema": "vhos/3.0/heuristics-projection",
            "subject_id": subject_id,
            "compiler": COMPILER_VERSION,
            "compiled_at": now,
            "projection": merged,
            "sync_report": sync,
            "mapping_table": "vhos.hdl.projection RULES (vhosc-0.1.0)",
        }
        _write(derived_dir, "heuristics.json", heuristics)
        report["sync_report"] = sync

        # affect.json — the fingerprint block
        affect = {
            "$schema": "vhos/3.0/affect-fingerprint",
            "subject_id": subject_id,
            "compiler": COMPILER_VERSION,
            "compiled_at": now,
            "fingerprint": doc.affect_fingerprint,
        }
        _write(derived_dir, "affect.json", affect)

    _write(derived_dir, "compile_report.json", report)
    return report, issues


def _write(dirpath, name, obj):
    with open(os.path.join(dirpath, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    subject_dir = argv[0]
    try:
        report, issues = compile_subject(subject_dir)
    except (hdl_parser.ParseError, FileNotFoundError) as e:
        print("COMPILE FAILED:", e)
        return 2
    for i in issues:
        print(" ", i)
    print("compile: %s — %d statements (%d immutable), %d issue(s)"
          % (report["status"], report["statement_count"],
             report["immutable_count"], len(issues)))
    if report.get("sync_report"):
        print("projection sync notes:")
        for s in report["sync_report"]:
            print("  ", s)
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
