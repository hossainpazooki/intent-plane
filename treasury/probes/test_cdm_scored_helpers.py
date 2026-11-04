"""Pure helpers of the scored-CDM probe (probe 16) and the shape of the three
new specs. The probes' live legs are exercised by the quickstart ladder."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cdm_scored_live import cdm_step, count_lines, outcome_of  # noqa: E402

SPECS = Path(__file__).resolve().parents[1] / "specs"


def test_outcome_of_reads_achieved_and_refusal_classes():
    achieved = {"businessEvent": {"after": []}}
    refused = {"rejected": True, "messageInformation": {"messageId": "POLICY_DENIED:reserve-shortfall-absent"}}
    bare = {"rejected": True, "messageInformation": {"messageId": "UNEVALUABLE"}}
    assert outcome_of(achieved) == "ACHIEVED"
    assert outcome_of(refused) == "POLICY_DENIED"
    assert outcome_of(bare) == "UNEVALUABLE"


def test_cdm_step_carries_uti_event_and_optional_prior():
    step = cdm_step("Cancel", "ab" * 16, "evt-9", prior_ref="key-1")
    assert step["action"] == "Cancel"
    assert step["eventIdentifier"][0]["assignedIdentifier"][0]["identifier"] == "evt-9"
    assert step["previousWorkflowStep"]["eventIdentifier"][0]["assignedIdentifier"][0]["identifier"] == "key-1"
    ts = step["businessEvent"]["after"][0]["trade"]["tradeIdentifier"][0]
    assert ts["identifierType"] == "UniqueTransactionIdentifier"
    assert ts["assignedIdentifier"][0]["identifier"] == "ab" * 16
    assert "previousWorkflowStep" not in cdm_step("New", "cd" * 16, "evt-1")


def test_count_lines_counts_non_blank_lines_and_tolerates_absence(tmp_path):
    p = tmp_path / "calls.jsonl"
    assert count_lines(p) == 0
    p.write_text('{"a":1}\n\n{"b":2}\n', encoding="utf-8")
    assert count_lines(p) == 2


def test_new_specs_name_one_scored_criterion_at_the_pinned_threshold():
    for name, criterion in [("09-reserve-backed.spec.json", "reserve-backed"),
                            ("10-reserve-shortfall.spec.json", "reserve-shortfall-absent"),
                            ("11-reserve-audit-unbound.spec.json", "reserve-audit-current")]:
        spec = json.loads((SPECS / name).read_text(encoding="utf-8"))
        assert spec["spec_version"] == 1
        assert spec["action_class"] == "regulatory-report"
        assert spec["enforcement_posture"] == "enforce"
        assert spec["criteria"] == [{"name": criterion, "threshold": 0.7, "volatility": "stable"}]
        assert "human_judgment" not in spec
