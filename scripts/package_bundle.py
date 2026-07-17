"""Package the whole framework into a portable, integrity-checked zip.

    python3 scripts/package_bundle.py

Steps performed:
  1. verify the subject archive manifest (refuses to package a
     corrupted archive; --force overrides, loudly)
  2. zip EVERYTHING — spec PDF, code, docs, subject archive, derived
     projections, examples — excluding only caches and dist/
  3. write dist/vhos-framework-bundle-<date>.zip plus a .sha256 file

On the target machine:
    (compare sha256)              certutil -hashfile <zip> SHA256   (Windows)
                                  shasum -a 256 <zip>               (mac/Linux)
    (unzip anywhere)
    python3 -m vhos.archive.manifest subjects/alan_turing --verify
    python3 -m unittest discover -s tests

The bundle is self-contained: stdlib-only Python 3.10+, no install
step, no network needed except the engine itself (spec: local-first).
"""

import hashlib
import os
import sys
import zipfile
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from vhos.archive.manifest import verify_manifest                 # noqa: E402

EXCLUDE_DIRS = {"__pycache__", ".pytest_cache", "dist", ".git"}
EXCLUDE_SUFFIX = (".pyc",)


def should_skip(path):
    parts = set(os.path.normpath(path).split(os.sep))
    if parts & EXCLUDE_DIRS:
        return True
    return path.endswith(EXCLUDE_SUFFIX)


def main():
    force = "--force" in sys.argv

    problems = verify_manifest(os.path.join(ROOT, "subjects", "alan_turing"))
    if problems:
        print("MANIFEST PROBLEMS:")
        for p in problems:
            print("  ", p)
        if not force:
            print("refusing to package a possibly-corrupted archive "
                  "(--force to override). If you added files on purpose, "
                  "rebuild first:\n"
                  "  python3 -m vhos.archive.manifest subjects/alan_turing")
            return 1
        print("--force given; packaging anyway.")

    dist = os.path.join(ROOT, "dist")
    os.makedirs(dist, exist_ok=True)
    name = "vhos-framework-bundle-%s.zip" % date.today().strftime("%Y%m%d")
    zpath = os.path.join(dist, name)

    count = 0
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for dirpath, dirnames, filenames in os.walk(ROOT):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
            for fn in filenames:
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, ROOT)
                if should_skip(rel) or full == zpath:
                    continue
                z.write(full, os.path.join("VHOS Framework", rel))
                count += 1

    h = hashlib.sha256()
    with open(zpath, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    digest = h.hexdigest()
    with open(zpath + ".sha256", "w", encoding="utf-8") as f:
        f.write("%s  %s\n" % (digest, name))

    print("packaged %d files -> dist/%s" % (count, name))
    print("sha256: %s" % digest)
    print("\nTransfer BOTH files. On the target machine, compare the "
          "hash before unzipping (see LIVE-TEST-GUIDE.pdf, Part C).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
