"""Fetch full canonical source texts into the Turing archive.

The archive ships with verbatim EXCERPTS (accurate, provenance-marked).
Full texts are fetched by the OPERATOR with this script, because
(a) bulk copyright responsibility is the operator's (ADR-003), and
(b) fetching beats an AI reproducing long texts from memory — memory
    introduces errors, and a corrupted raw/ violates "raw is sacred".

Usage:
    python3 scripts/fetch_sources.py --list
    python3 scripts/fetch_sources.py --fetch turing-1936-paper
    python3 scripts/fetch_sources.py --all
    python3 scripts/fetch_sources.py --all --insecure       # see below
    python3 scripts/fetch_sources.py --register <id> <file> # manual path

Failure handling, in order of preference:
  1. Each source lists MIRRORS; the script tries them in order, so one
     dead or misconfigured host does not fail the source.
  2. --insecure disables TLS certificate verification for this run
     (for mirrors with expired certificates). The download still gets
     checksummed, and the provenance record is marked
     "tls_verified": false — the archive never hides how bytes arrived.
     Use only when you've judged the mirror trustworthy anyway.
  3. Download manually in a browser, then:
         python3 scripts/fetch_sources.py --register turing-1936-paper ~/Downloads/Turing_Paper_1936.pdf
     which copies it into raw/text/full/, checksums it, and records
     "method": "manual-register".

Each acquisition is recorded in
subjects/alan_turing/raw/text/full/PROVENANCE.json.  Re-run
`python3 -m vhos.archive.manifest subjects/alan_turing` afterwards.

URLs curated 2026-07-14; all except `routledge-reproduction` are
UNVERIFIED mirrors — open them once yourself before trusting.
"""

import argparse
import hashlib
import json
import os
import shutil
import ssl
import sys
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST_BASE = os.path.join(ROOT, "subjects", "alan_turing", "raw", "text", "full")

SOURCES = [
    {
        "id": "turing-1936-paper",
        "title": "On Computable Numbers (1936) — institutional mirrors",
        "mirrors": [
            "https://www.cs.ox.ac.uk/activities/ieg/e-library/sources/tp2-ie.pdf",
            "https://people.math.ethz.ch/~halorenz/4students/Literatur/TuringFullText.pdf",
            "https://www.cs.virginia.edu/~robins/Turing_Paper_1936.pdf",
        ],
        "dest": "on-computable-numbers-1936.pdf",
        "status": "unverified mirrors (Oxford, ETH Zurich, UVA) — UVA cert expired as of 2026-07",
    },
    {
        "id": "turing-1950-paper",
        "title": "Computing Machinery and Intelligence (1950) — PDF mirrors",
        "mirrors": [
            "https://www.csee.umbc.edu/courses/471/papers/turing.pdf",
            "https://phil415.pbworks.com/f/TuringComputing.pdf",
        ],
        "dest": "computing-machinery-1950.pdf",
        "status": "unverified mirrors — US copyright to ~2046, operator accepts (ADR-003)",
    },
    {
        "id": "routledge-reproduction",
        "title": "Routledge letter reproduction (Letters of Note via WEIT)",
        "mirrors": [
            "https://whyevolutionistrue.com/2014/11/29/yours-in-distress-a-letter-from-alan-turing/",
        ],
        "dest": "routledge-letter-reproduction.html",
        "status": "VERIFIED 2026-07-14 — excerpt in raw/text/letters matches this page",
    },
    {
        "id": "turingarchive-index",
        "title": "Turing Digital Archive, King's College Cambridge (index)",
        "mirrors": ["https://turingarchive.kings.cam.ac.uk/"],
        "dest": "turingarchive-index.html",
        "status": "canonical holding — navigate to AMT/K/1 (Morcom), AMT/D/14a (Routledge)",
    },
    {
        "id": "turing-org-uk",
        "title": "The Alan Turing Home Page (Andrew Hodges)",
        "mirrors": ["https://www.turing.org.uk/"],
        "dest": "turing-org-uk.html",
        "status": "biographer's site — bibliography and source pointers",
    },
]


def _record(entry, data, method, url=None, tls_verified=True):
    os.makedirs(DEST_BASE, exist_ok=True)
    dest = os.path.join(DEST_BASE, entry["dest"])
    with open(dest, "wb") as f:
        f.write(data)
    sha = hashlib.sha256(data).hexdigest()
    record = {
        "id": entry["id"],
        "url": url,
        "method": method,
        "tls_verified": tls_verified,
        "fetched": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sha256": sha,
        "bytes": len(data),
        "status": entry["status"],
    }
    prov_path = os.path.join(DEST_BASE, "PROVENANCE.json")
    prov = []
    if os.path.exists(prov_path):
        with open(prov_path, encoding="utf-8") as f:
            prov = json.load(f)
    prov = [p for p in prov if p["id"] != entry["id"]] + [record]
    with open(prov_path, "w", encoding="utf-8") as f:
        json.dump(prov, f, indent=1)
    print("  saved %s (%d bytes, sha256 %s...)%s"
          % (entry["dest"], len(data), sha[:16],
             "" if tls_verified else "  [TLS UNVERIFIED — recorded]"))


def fetch(entry, insecure=False):
    ctx = None
    if insecure:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    last_err = None
    for url in entry["mirrors"]:
        req = urllib.request.Request(
            url, headers={"User-Agent": "VHOS-archive-fetch/0.2"})
        print("fetching %s ..." % url)
        try:
            with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
                data = resp.read()
            _record(entry, data, method="fetch", url=url,
                    tls_verified=not insecure)
            return True
        except ssl.SSLError as e:
            print("  TLS failure: %s" % e)
            print("  -> this mirror's certificate is bad; trying next mirror.")
            last_err = e
        except Exception as e:                     # noqa: BLE001
            print("  failed: %s" % e)
            last_err = e
    print("  ALL MIRRORS FAILED for %s (last: %s)" % (entry["id"], last_err))
    if not insecure and isinstance(last_err, ssl.SSLError):
        print("  If you judge a mirror trustworthy despite its expired "
              "certificate, re-run with --insecure (recorded in provenance),")
    print("  or download in a browser and run:\n"
          "    python3 scripts/fetch_sources.py --register %s <downloaded-file>"
          % entry["id"])
    return False


def register(entry_id, filepath):
    matches = [e for e in SOURCES if e["id"] == entry_id]
    if not matches:
        print("unknown id; use --list")
        return 1
    if not os.path.exists(filepath):
        print("no such file:", filepath)
        return 1
    with open(filepath, "rb") as f:
        data = f.read()
    _record(matches[0], data, method="manual-register", url=None,
            tls_verified=False)
    print("registered manual download for %s" % entry_id)
    print("Now re-run: python3 -m vhos.archive.manifest subjects/alan_turing")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--fetch", metavar="ID")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--insecure", action="store_true",
                    help="disable TLS verification for this run; "
                         "recorded per-file in PROVENANCE.json")
    ap.add_argument("--register", nargs=2, metavar=("ID", "FILE"),
                    help="record a manually downloaded file")
    args = ap.parse_args()

    if args.register:
        return register(args.register[0], args.register[1])
    if args.fetch:
        matches = [e for e in SOURCES if e["id"] == args.fetch]
        if not matches:
            print("unknown id; use --list")
            return 1
        return 0 if fetch(matches[0], insecure=args.insecure) else 1
    if args.all:
        failures = 0
        for e in SOURCES:
            if not fetch(e, insecure=args.insecure):
                failures += 1
        print("\n%d source(s) failed." % failures if failures
              else "\nAll sources fetched.")
        print("Now re-run: python3 -m vhos.archive.manifest subjects/alan_turing")
        return 1 if failures else 0
    for e in SOURCES:
        print("%-24s %s" % (e["id"], e["title"]))
        for u in e["mirrors"]:
            print("%-24s   %s" % ("", u))
        print("%-24s   -> %s" % ("", e["status"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
