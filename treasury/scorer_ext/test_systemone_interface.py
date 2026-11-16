"""Pins the System One fact source's interface as the 2026-11-03 plan states
it (Tasks 1 and 4; CONTRACT.md section 8 hook): the annotations, the
constructor's names and defaults, the recording and call-log line shapes,
the env names the factory reads, and the scorer boot finding the factory by
its hook name. The live API is an in-process fake opener. Nothing here skips."""

from __future__ import annotations

import inspect
import json
import re
import sys
import typing
from pathlib import Path

import pytest
from scorer.facts import FactSource

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scorer_ext.systemone_facts import (  # noqa: E402
    MODEL,
    CriterionEntry,
    SystemOneFactSource,
    fact_source_from_env,
    load_book,
)

HERE = Path(__file__).resolve().parent
BOOK = HERE / "criteria.json"
ENV = ("SCORER_FACTS_BOOK", "SCORER_FACTS_RECORDING", "SCORER_FACTS_MODE", "SCORER_FACTS_FAULT",
       "SCORER_FACTS_CALL_LOG", "TYPESAFE_API_KEY", "SCORER_FACTS_MODULE", "SCORER_FACTS_JSON")
RECORDING_KEYS = ["captured_at", "criterion", "evidence_sha256", "latency_ms",
                  "model", "model_requested", "noul", "usage"]


def _hints(obj):
    # FactSource is imported only under TYPE_CHECKING in the module; supply it here.
    return typing.get_type_hints(obj, localns={"FactSource": FactSource})


def _replay_file(tmp_path, book, noul=0.8):
    p = tmp_path / "rec.jsonl"
    line = {"criterion": "reserve-backed", "evidence_sha256": book["reserve-backed"].evidence_sha256,
            "noul": noul, "model": MODEL}
    p.write_text(json.dumps(line, sort_keys=True) + "\n", encoding="utf-8")
    return p


class _Response:
    status = 200

    def __init__(self, payload):
        self._body = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _Opener:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def open(self, req, timeout=None):
        self.calls.append((req, timeout))
        return _Response(self.payload)


@pytest.fixture
def env(monkeypatch, tmp_path):
    for var in ENV:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("SCORER_FACTS_BOOK", str(BOOK))
    monkeypatch.setenv("SCORER_FACTS_RECORDING", str(_replay_file(tmp_path, load_book(BOOK))))
    return monkeypatch


# --- annotations and signature --------------------------------------------------------


def test_factory_is_annotated_as_the_hook_contract():
    assert _hints(fact_source_from_env) == {"fallback": FactSource | None, "return": FactSource}


def test_book_loader_and_source_are_annotated_with_criterion_maps():
    assert _hints(load_book) == {"path": Path, "return": dict[str, CriterionEntry]}
    assert _hints(SystemOneFactSource.__init__)["book"] == dict[str, CriterionEntry]


def test_source_signature_names_and_defaults_match_the_plan():
    params = inspect.signature(SystemOneFactSource.__init__).parameters
    assert list(params) == ["self", "book", "mode", "recording_path", "fault", "call_log", "fallback",
                            "api_key", "model", "endpoint", "timeout_s", "opener"]
    defaults = {k: p.default for k, p in params.items() if p.default is not inspect.Parameter.empty}
    assert defaults == {"fault": None, "call_log": None, "fallback": None, "api_key": None,
                        "model": "jev-1.14.0", "endpoint": "https://api.typesafe.ai/v1/systemone",
                        "timeout_s": 3.0, "opener": None}


# --- record mode: opener, model, endpoint, timeout, recording line ----------------------


def test_record_posts_through_the_given_opener_with_its_model_endpoint_and_timeout(tmp_path):
    opener = _Opener({"model": "jev-pin-test", "answers": {"reserve-backed": {"noul": 0.9}}, "usage": {"calls": 1}})
    src = SystemOneFactSource(load_book(BOOK), "record", tmp_path / "rec.jsonl", api_key="k",
                              model="jev-pin-test", endpoint="http://127.0.0.1:9/v1/systemone", opener=opener)
    assert src.get("reserve-backed", "i-1") == 0.9
    [(req, timeout)] = opener.calls
    assert req.full_url == "http://127.0.0.1:9/v1/systemone"
    assert timeout == 3.0
    assert json.loads(req.data.decode("utf-8"))["model"] == "jev-pin-test"


def test_recording_line_has_the_eight_keys_in_sorted_order(tmp_path):
    book = load_book(BOOK)
    opener = _Opener({"model": MODEL, "answers": {"reserve-backed": {"noul": 0.9}}, "usage": {"calls": 1}})
    SystemOneFactSource(book, "record", tmp_path / "rec.jsonl", api_key="k", opener=opener).get("reserve-backed", "i-1")
    [line] = (tmp_path / "rec.jsonl").read_text(encoding="utf-8").splitlines()
    rec = json.loads(line)
    assert list(rec) == RECORDING_KEYS
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", rec["captured_at"])
    assert rec["model_requested"] == MODEL
    assert rec["evidence_sha256"] == book["reserve-backed"].evidence_sha256


# --- the call log -----------------------------------------------------------------------


def test_call_log_line_has_criterion_intent_id_and_a_float_ts(tmp_path):
    book = load_book(BOOK)
    log = tmp_path / "calls.jsonl"
    SystemOneFactSource(book, "replay", _replay_file(tmp_path, book), call_log=log).get("reserve-backed", "i-7")
    [line] = log.read_text(encoding="utf-8").splitlines()
    entry = json.loads(line)
    assert list(entry) == ["criterion", "intent_id", "ts"]
    assert entry["criterion"] == "reserve-backed" and entry["intent_id"] == "i-7"
    assert isinstance(entry["ts"], float)


# --- the env names the factory reads ----------------------------------------------------


def test_factory_reads_SCORER_FACTS_FAULT(env):
    assert fact_source_from_env(None).get("reserve-backed", "i") == 0.8
    env.setenv("SCORER_FACTS_FAULT", "reserve-backed")
    assert fact_source_from_env(None).get("reserve-backed", "i") is None


def test_factory_reads_SCORER_FACTS_CALL_LOG(env, tmp_path):
    log = tmp_path / "calls.jsonl"
    env.setenv("SCORER_FACTS_CALL_LOG", str(log))
    fact_source_from_env(None).get("reserve-backed", "i")
    assert len(log.read_text(encoding="utf-8").splitlines()) == 1


def test_factory_reads_SCORER_FACTS_MODE_and_TYPESAFE_API_KEY(env):
    env.setenv("SCORER_FACTS_MODE", "record")
    with pytest.raises(SystemExit, match="API key"):
        fact_source_from_env(None)
    env.setenv("TYPESAFE_API_KEY", "k")
    assert isinstance(fact_source_from_env(None), SystemOneFactSource)


# --- the hook, through the scorer's own boot code ----------------------------------------


def test_scorer_boot_finds_the_factory_by_its_hook_name(env):
    from scorer.__main__ import facts_from_env

    env.setenv("SCORER_FACTS_MODULE", "scorer_ext.systemone_facts")
    env.setenv("SCORER_FACTS_JSON", json.dumps({"balance": 250}))
    facts = facts_from_env()
    assert isinstance(facts, SystemOneFactSource)
    assert facts.get("reserve-backed", "i") == 0.8
    assert facts.get("balance", "i") == 250.0
