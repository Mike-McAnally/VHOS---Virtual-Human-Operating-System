"""Runtime loading helpers shared by scripts.

Loads a compiled subject (statements + fingerprint) and builds soma
parameters from the fingerprint's calibration block — including the
priors-only path used for historical subjects.
"""

import json
import os

from .. import COMPILER_VERSION
from ..soma.state import default_params


def load_compiled(subject_dir):
    """Return (statements, fingerprint) from the newest compile,
    compiling first if derived/ is missing."""
    derived = os.path.join(subject_dir, "derived", COMPILER_VERSION)
    if not os.path.exists(os.path.join(derived, "statements.json")):
        from ..hdl.compiler import compile_subject
        report, _ = compile_subject(subject_dir)
        if report["status"] != "ok":
            raise RuntimeError("compile failed: %s" % report["issues"])
    with open(os.path.join(derived, "statements.json"), encoding="utf-8") as f:
        statements = json.load(f)["statements"]
    with open(os.path.join(derived, "affect.json"), encoding="utf-8") as f:
        fingerprint = json.load(f)["fingerprint"]
    return statements, fingerprint


def soma_params_from_fingerprint(fingerprint):
    """Population prior overridden by the subject's soma_calibration.
    For subjects with channel_status uncalibrated-priors-only this
    applies exactly the recorded priors, nothing more."""
    params = default_params()
    cal = (fingerprint or {}).get("soma_calibration", {})
    tb = cal.get("tension_baseline_prior")
    if isinstance(tb, dict) and isinstance(tb.get("value"), (int, float)):
        params["tension"].baseline = float(tb["value"])
    ab = cal.get("arousal_baseline_prior")
    if isinstance(ab, dict) and isinstance(ab.get("value"), (int, float)):
        params["arousal"].baseline = float(ab["value"])
    return params
