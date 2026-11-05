"""One-time live capture for the replay ladder: ask System One each criterion
in the book N times and write every answer to a fresh recording. The FIRST
answer per criterion is what replay serves; the rest are the spread the spec
appendix reports. Never prints the key. ASCII only. Stdlib only.

Refuses (exit 3) a --out that already holds a line: replay keys on
(criterion, evidence sha256) and the hash covers the evidence text only, so a
retry appended after an instructions- or criteria-only rewrite would keep
serving the old capture. Move the old capture aside before a retry.
The key is stripped of surrounding whitespace (a CRLF key file leaves a CR
that http.client refuses); a blank key counts as absent (exit 2). A call that
writes no line (non-200, timeout, network or request error) is counted, never
raised.

Usage: python -m scorer_ext.record --book treasury/scorer_ext/criteria.json \
           --out treasury/recordings/systemone-jev-1.14.0.jsonl --runs 5
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .systemone_facts import ENDPOINT, MODEL, SystemOneFactSource, load_book


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--endpoint", default=ENDPOINT)
    args = ap.parse_args(argv)
    key = os.environ.get("TYPESAFE_API_KEY", "").strip()
    if not key:
        print("record: TYPESAFE_API_KEY is not set (or blank); nothing recorded")
        return 2
    out = Path(args.out)
    if out.exists() and out.read_text(encoding="utf-8").strip():
        print("record: --out already holds a capture; replay serves its first line per criterion,"
              " so move it aside before a retry; nothing recorded")
        return 3
    book = load_book(Path(args.book))
    out.parent.mkdir(parents=True, exist_ok=True)
    src = SystemOneFactSource(book, "record", out, api_key=key, endpoint=args.endpoint)
    for run in range(args.runs):
        for name in book:
            src.get(name, "record-run-%d" % (run + 1))
    lines = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines() if l.strip()] if out.exists() else []
    for name in book:
        mine = [l for l in lines if l["criterion"] == name]
        nouls = [l["noul"] for l in mine if l["noul"] is not None]
        models = sorted({str(l["model"]) for l in mine})
        print("criterion=%s runs=%d noul_min=%s noul_max=%s model=%s latency_ms_max=%s" % (
            name, len(mine),
            "%.4f" % min(nouls) if nouls else "none", "%.4f" % max(nouls) if nouls else "none",
            ",".join(models), max((l["latency_ms"] for l in mine), default=0)))
    calls = args.runs * len(book)
    if len(lines) < calls:
        print("record: %d of %d calls wrote no line (non-200, timeout, network or request error)" % (calls - len(lines), calls))
    return 0 if len(lines) == calls and all(l["noul"] is not None and l["model"] == MODEL for l in lines) else 1


if __name__ == "__main__":
    sys.exit(main())
