"""Probe 17's wiring (provenance_root_live.py): two legs under spec 09, the
outcome each must reach, and the rule artifact hash each one cites. The live
legs run in the quickstart ladder on the resolver lane; this pins the wiring
in the gate, with the two calls that touch the network replaced."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import provenance_root_live as probe  # noqa: E402

GATE, HASH09, CALLS = "http://127.0.0.1:9", "09" * 32, "calls.jsonl"
VERIFIED, REJECTED = "aa" * 32, "bb" * 32


def _uti(step):
    return step["businessEvent"]["after"][0]["trade"]["tradeIdentifier"][0]["assignedIdentifier"][0]["identifier"]


def test_main_runs_two_legs_each_citing_its_own_rule_hash(monkeypatch):
    legs, gated = [], []

    def fake_gate_cdm_event(step, submit, client, **kw):
        gated.append((_uti(step), step["eventIdentifier"][0]["assignedIdentifier"][0]["identifier"], kw))
        return {"businessEvent": {}}

    def fake_run_leg(name, feed, call_log, repo, declare, want):
        declare()
        legs.append((name, call_log, want))
        return True, None

    monkeypatch.setattr(probe, "gate_cdm_event", fake_gate_cdm_event)
    monkeypatch.setattr(probe, "run_leg", fake_run_leg)
    assert probe.main(GATE, HASH09, CALLS, VERIFIED, REJECTED) == 0
    assert legs == [("provenance verified", CALLS, ("ACHIEVED", 1, 1, 1)),
                    ("provenance rejected", CALLS, ("UNEVALUABLE", 0, 0, 1))]
    assert [(uti, ref, kw["rule_artifact_hash"], kw["intent_spec_hash"]) for uti, ref, kw in gated] == [
        (probe.UTI_VERIFIED, "evt-verified", VERIFIED, HASH09),
        (probe.UTI_REJECTED, "evt-rejected", REJECTED, HASH09),
    ]
    assert {kw["run_id"] for _, _, kw in gated} == {"quickstart-provenance"}


def test_main_exits_nonzero_when_either_leg_fails(monkeypatch):
    for failing in ("provenance verified", "provenance rejected"):
        monkeypatch.setattr(probe, "run_leg", lambda name, *a, failing=failing: (name != failing, None))
        assert probe.main(GATE, HASH09, CALLS, VERIFIED, REJECTED) == 1
