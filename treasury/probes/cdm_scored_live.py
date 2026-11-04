"""Probe 16: a CDM WorkflowStep gated on a criterion scored by the showcase's
System One fact source, through the unchanged /ml/evaluate wire (CONTRACT.md
section 5.4 claim 21). Four legs, each printing TWO independent witnesses of
whether the scorer was consulted: the adapter call-log delta (scorer side) and
the feed's SCORED-record count for the leg (gate side).

  1. grant: a New step under spec 09 (reserve-backed); the recorded noul is at
     or above 0.7 -> PASS -> ACHIEVED step, submit() ran once;
  2. refuse on score: a New step under spec 10 (reserve-shortfall-absent); the
     recorded noul is below 0.7 -> FAIL -> rejected step POLICY_DENIED, nothing
     submitted;
  3. upstream outage: a New step under spec 11 (reserve-audit-current), which
     the adapter is booted to fail on purpose -> None -> UNEVALUABLE -> rejected
     step, nothing submitted (the dead-scorer case is probe 12; this is the
     judge being unreachable while the scorer is up);
  4. human judgment before any score: a Cancel of leg 1's event under spec 08
     (erasure-approval) -> HUMAN_JUDGMENT, call log unchanged, zero SCORED
     records: the scorer was never asked, not overruled.

Usage: cdm_scored_live.py <gate_url> <hash09> <hash10> <hash11> <hash08> <call_log>
Exit 0 iff all four legs match. ASCII output only. Stdlib only.
"""

import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "declarant" / "pydeclarant"))

from client import Client  # noqa: E402
from cdm_adapter import gate_cdm_event  # noqa: E402

SCOPE = "per-actor"
RUN_ID = "quickstart-cdm-scored"
LEI = "5493001KJTIIGC8Y1R12"
RULES = "EMT-RESERVE-ASSETS-2023"
TS = "2026-11-03T12:00:00Z"
UTI_GRANT = "2E1A4C6B8D0F1E3A5C7B9D1F2A4C6E8B"
UTI_REFUSE = "3F2B5D7C9E1A2F4B6D8C0E2A3B5D7F9C"
UTI_OUTAGE = "4A3C6E8D0F2B3A5C7E9D1F3B4C6E8A0D"


def cdm_step(action, uti, event_ref, prior_ref=""):
    trade_state = {"trade": {"tradeIdentifier": [
        {"identifierType": "UniqueTransactionIdentifier", "assignedIdentifier": [{"identifier": uti}]}]}}
    step = {
        "action": action,
        "timestamp": [{"dateTime": TS, "qualification": "eventCreationDateTime"}],
        "eventIdentifier": [{"assignedIdentifier": [{"identifier": event_ref}]}],
        "businessEvent": {"eventDate": TS[:10], "after": [trade_state]},
    }
    if prior_ref:
        step["previousWorkflowStep"] = {"eventIdentifier": [{"assignedIdentifier": [{"identifier": prior_ref}]}]}
    return step


def outcome_of(step):
    if step.get("rejected"):
        return str(step["messageInformation"]["messageId"]).split(":", 1)[0]
    return "ACHIEVED" if "businessEvent" in step else "UNKNOWN"


def count_lines(path):
    p = Path(path)
    if not p.exists():
        return 0
    return sum(1 for line in p.read_text(encoding="utf-8").splitlines() if line.strip())


class Feed:
    def __init__(self, gate_url):
        self.url = gate_url

    def _get(self, since, typ=""):
        q = "/v2/events?since=%d" % since + ("&type=%s" % typ if typ else "")
        with urllib.request.urlopen(self.url + q, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def cursor(self):
        return int(self._get(0)["next_since"])

    def scored_since(self, since):
        return len(self._get(since, "SCORED")["events"])


class Repository:
    def __init__(self):
        self.n = 0

    def submit(self):
        self.n += 1
        return "ack-%d" % self.n


def run_leg(name, feed, call_log, repo, declare, want):
    """declare() -> step. want = (class, submitted, calls, scored_records)."""
    calls0, seq0, n0 = count_lines(call_log), feed.cursor(), repo.n
    step = declare()
    got = (outcome_of(step), repo.n - n0, count_lines(call_log) - calls0, feed.scored_since(seq0))
    print("%s: class=%s submitted=%d calls=+%d scored_records=%d" % ((name,) + got))
    return got == want, step


def main(gate_url, hash09, hash10, hash11, hash08, call_log):
    client = Client(gate_url)
    feed = Feed(gate_url)
    repo = Repository()

    def gate(step, spec_hash):
        return lambda: gate_cdm_event(step, repo.submit, client, reporting_entity=LEI, rule_set=RULES,
                                      intent_spec_hash=spec_hash, scope=SCOPE, run_id=RUN_ID, timestamp_utc=TS)

    ok1, grant = run_leg("scored grant", feed, call_log, repo,
                         gate(cdm_step("New", UTI_GRANT, "evt-grant"), hash09), ("ACHIEVED", 1, 1, 1))
    ok2, _ = run_leg("scored refuse", feed, call_log, repo,
                     gate(cdm_step("New", UTI_REFUSE, "evt-refuse"), hash10), ("POLICY_DENIED", 0, 1, 1))
    ok3, _ = run_leg("scored outage", feed, call_log, repo,
                     gate(cdm_step("New", UTI_OUTAGE, "evt-outage"), hash11), ("UNEVALUABLE", 0, 1, 1))
    grant_key = grant["eventIdentifier"][0]["assignedIdentifier"][0]["identifier"]
    ok4, _ = run_leg("human judgment", feed, call_log, repo,
                     gate(cdm_step("Cancel", UTI_GRANT, "evt-erase", prior_ref=grant_key), hash08),
                     ("HUMAN_JUDGMENT", 0, 0, 0))
    return 0 if (ok1 and ok2 and ok3 and ok4) else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:7]))
