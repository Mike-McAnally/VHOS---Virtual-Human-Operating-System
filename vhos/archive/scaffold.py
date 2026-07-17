"""Contract 1 — archive scaffolder.

Creates the per-subject directory layout of spec Part IV: plain files,
open formats, no database required to read it.

CLI:
    python3 -m vhos.archive.scaffold <subjects_root> <subject_id>
"""

import os
import sys
from datetime import date

TREE = (
    "raw/text",
    "raw/audio",
    "raw/video",
    "raw/biometrics",
    "raw/interviews",
    "sessions",
    "hdl",
    "derived",
)

STARTER_HDL = '''HDL_VERSION 0.4
SUBJECT_ID "{subject_id}"
PRIMARY_AUTHOR_MODE self
LAST_COMPILED {today}
VOCABULARY_NAME vhos-core
VOCABULARY_VERSION 0.2

# === Drives ===
# Begin with self-authored assertions. These are the statements no
# compiler may ever override (the self-authority rule, spec Part II).
#
# THIS SUBJECT VALUES <something> strongly.
#   @LAYER drives  @AUTHOR self  @CONFIDENCE 1.00
#   @SOURCES [self-attestation/{today}]
'''


def create_subject(subjects_root, subject_id):
    subject_dir = os.path.join(subjects_root, subject_id)
    for t in TREE:
        os.makedirs(os.path.join(subject_dir, t), exist_ok=True)
    hdl_path = os.path.join(subject_dir, "hdl", "subject.hdl")
    if not os.path.exists(hdl_path):
        with open(hdl_path, "w", encoding="utf-8") as f:
            f.write(STARTER_HDL.format(subject_id=subject_id,
                                       today=date.today().isoformat()))
    from .manifest import build_manifest
    build_manifest(subject_dir)
    return subject_dir


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 1
    path = create_subject(argv[0], argv[1])
    print("subject archive created:", path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
