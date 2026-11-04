"""Probe 17: the authoring plane as provenance root (CONTRACT.md section 2.4
`rule` mode; section 5.4 claim 21). Two legs under spec 09, each citing a
rule artifact by content hash on the declaration:

  1. verified: the vendored rule artifact that VERIFIES under the shipped
     inputs at the pinned export instant -> the scorer verifies, then scores
     -> ACHIEVED, submit() ran once, the judge was consulted (calls=+1);
  2. rejected: the vendored artifact whose attestations the verifier REJECTS
     -> UNEVALUABLE "artifact verification failed" BEFORE any fact lookup ->
     rejected step, nothing submitted, call log unchanged (calls=+0).

Runs only where the scorer booted with the resolver (Linux/WSL lane); the
quickstart skips it visibly elsewhere.
Usage: provenance_root_live.py <gate_url> <hash09> <call_log> <verified_hash> <rejected_hash>
Exit 0 iff both legs match. ASCII output only. Stdlib only.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "declarant" / "pydeclarant"))

from client import Client  # noqa: E402
from cdm_adapter import gate_cdm_event  # noqa: E402
from cdm_scored_live import LEI, RULES, SCOPE, TS, Feed, Repository, cdm_step, run_leg  # noqa: E402

RUN_ID = "quickstart-provenance"
UTI_VERIFIED = "5B4D7F9E1A3C4B6D8F0E2A4C5D7F9B1E"
UTI_REJECTED = "6C5E8A0F2B4D5C7E9A1F3B5D6E8A0C2F"


def main(gate_url, hash09, call_log, verified_hash, rejected_hash):
    client = Client(gate_url)
    feed = Feed(gate_url)
    repo = Repository()

    def gate(step, rule_hash):
        return lambda: gate_cdm_event(step, repo.submit, client, reporting_entity=LEI, rule_set=RULES,
                                      intent_spec_hash=hash09, scope=SCOPE, run_id=RUN_ID, timestamp_utc=TS,
                                      rule_artifact_hash=rule_hash)

    ok1, _ = run_leg("provenance verified", feed, call_log, repo,
                     gate(cdm_step("New", UTI_VERIFIED, "evt-verified"), verified_hash), ("ACHIEVED", 1, 1, 1))
    ok2, _ = run_leg("provenance rejected", feed, call_log, repo,
                     gate(cdm_step("New", UTI_REJECTED, "evt-rejected"), rejected_hash), ("UNEVALUABLE", 0, 0, 1))
    return 0 if (ok1 and ok2) else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:6]))
