"""Contract 1 — manifest builder and verifier.

manifest.json records the spec version, a SHA-256 for every file under
raw/, sessions/, and hdl/, and the compiler version of each derived
tree.  raw/ is append-only: a checksum that CHANGES is corruption or
tampering, never a legitimate edit.

CLI:
    python3 -m vhos.archive.manifest <subject_dir>            # (re)build
    python3 -m vhos.archive.manifest <subject_dir> --verify   # check
"""

import hashlib
import json
import os
import sys
from datetime import datetime, timezone

from .. import SPEC_VERSION

PROTECTED_TREES = ("raw", "sessions", "hdl")


def _sha256(path, bufsize=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(bufsize)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _walk_protected(subject_dir):
    for tree in PROTECTED_TREES:
        base = os.path.join(subject_dir, tree)
        if not os.path.isdir(base):
            continue
        for root, _dirs, files in os.walk(base):
            for name in sorted(files):
                full = os.path.join(root, name)
                rel = os.path.relpath(full, subject_dir).replace(os.sep, "/")
                yield rel, full


def build_manifest(subject_dir):
    files = {}
    for rel, full in _walk_protected(subject_dir):
        files[rel] = {"sha256": _sha256(full), "bytes": os.path.getsize(full)}
    derived = {}
    dbase = os.path.join(subject_dir, "derived")
    if os.path.isdir(dbase):
        for compiler_version in sorted(os.listdir(dbase)):
            tree = os.path.join(dbase, compiler_version)
            if os.path.isdir(tree):
                derived[compiler_version] = sorted(os.listdir(tree))
    manifest = {
        "$schema": "vhos/3.0/manifest",
        "spec_version": SPEC_VERSION,
        "subject_id": os.path.basename(os.path.abspath(subject_dir)),
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "file_count": len(files),
        "files": files,
        "derived_trees": derived,
        "preservation_note": (
            "Preservation priority: (1) raw capture, (2) hdl/, (3) derived "
            "projections, (4) everything else. Keep three copies of raw/, "
            "sessions/, and hdl/ on independent media (spec Part IV)."),
    }
    out = os.path.join(subject_dir, "manifest.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    return manifest


def verify_manifest(subject_dir):
    """Returns a list of problem strings; empty list means intact."""
    path = os.path.join(subject_dir, "manifest.json")
    if not os.path.exists(path):
        return ["manifest.json missing"]
    with open(path, encoding="utf-8") as f:
        manifest = json.load(f)
    problems = []
    seen = set()
    for rel, full in _walk_protected(subject_dir):
        seen.add(rel)
        rec = manifest["files"].get(rel)
        if rec is None:
            problems.append("NEW (not in manifest): %s" % rel)
        elif _sha256(full) != rec["sha256"]:
            problems.append("CHANGED (raw is append-only!): %s" % rel)
    for rel in manifest["files"]:
        if rel not in seen:
            problems.append("MISSING (never delete raw!): %s" % rel)
    return problems


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    subject_dir = argv[0]
    if "--verify" in argv:
        problems = verify_manifest(subject_dir)
        if problems:
            print("MANIFEST VERIFICATION FAILED:")
            for p in problems:
                print("  ", p)
            return 1
        print("manifest OK — protected trees intact")
        return 0
    m = build_manifest(subject_dir)
    print("manifest.json written: %d files under %s"
          % (m["file_count"], "/".join(PROTECTED_TREES)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
