"""The showcase's System One fact source (CONTRACT.md section 5.4 claim 21).
Stdlib-only; the live API is a local http.server double. Nothing here skips."""

from __future__ import annotations

import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

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


class _Static:
    def __init__(self, facts):
        self.facts = facts

    def get(self, criterion, intent_id):
        return self.facts.get(criterion)


def _recording(tmp_path, lines):
    p = tmp_path / "rec.jsonl"
    p.write_text("".join(json.dumps(line, sort_keys=True) + "\n" for line in lines), encoding="utf-8")
    return p


def _entry(book, name):
    return book[name]


# --- the book -----------------------------------------------------------------------


def test_book_loads_three_criteria_with_evidence_hashes():
    book = load_book(BOOK)
    assert set(book) == {"reserve-backed", "reserve-shortfall-absent", "reserve-audit-current"}
    for entry in book.values():
        assert isinstance(entry, CriterionEntry)
        assert entry.evidence.startswith("Reserve attestation, Example Issuer S.A.")
        assert len(entry.evidence_sha256) == 64
        assert set(entry.criteria) == {"true", "false"}


# --- replay -------------------------------------------------------------------------


def test_replay_answers_the_first_recorded_noul_for_the_evidence(tmp_path):
    book = load_book(BOOK)
    sha = book["reserve-backed"].evidence_sha256
    rec = _recording(tmp_path, [
        {"criterion": "reserve-backed", "evidence_sha256": sha, "noul": 0.91, "model": MODEL},
        {"criterion": "reserve-backed", "evidence_sha256": sha, "noul": 0.88, "model": MODEL},
    ])
    src = SystemOneFactSource(book, "replay", rec)
    assert src.get("reserve-backed", "i-1") == 0.91


def test_replay_miss_and_stale_evidence_answer_none(tmp_path):
    book = load_book(BOOK)
    rec = _recording(tmp_path, [{"criterion": "reserve-backed", "evidence_sha256": "0" * 64, "noul": 0.9, "model": MODEL}])
    src = SystemOneFactSource(book, "replay", rec)
    assert src.get("reserve-backed", "i-1") is None          # evidence changed since the recording
    assert src.get("reserve-shortfall-absent", "i-1") is None  # never recorded


@pytest.mark.parametrize("line", [
    {"model": "jev-1.13.0", "noul": 0.9},   # a model other than the pinned one
    {"noul": 0.9},                          # no model recorded at all
    {"model": MODEL, "noul": 5.0},          # outside [0, 1]
    {"model": MODEL, "noul": -1},
    {"model": MODEL, "noul": 1.0000001},
    {"model": MODEL, "noul": 10 ** 400},    # too big for a float: None, not OverflowError
    {"model": MODEL, "noul": True},
    {"model": MODEL, "noul": "0.9"},
    {"model": MODEL, "noul": None},
])
def test_replay_refuses_what_record_would_refuse(tmp_path, line):
    book = load_book(BOOK)
    sha = book["reserve-backed"].evidence_sha256
    rec = _recording(tmp_path, [dict(line, criterion="reserve-backed", evidence_sha256=sha)])
    assert SystemOneFactSource(book, "replay", rec).get("reserve-backed", "i-1") is None


@pytest.mark.parametrize("noul", [0.0, 1.0, 1])
def test_replay_accepts_the_closed_unit_interval(tmp_path, noul):
    book = load_book(BOOK)
    sha = book["reserve-backed"].evidence_sha256
    rec = _recording(tmp_path, [{"criterion": "reserve-backed", "evidence_sha256": sha, "noul": noul, "model": MODEL}])
    assert SystemOneFactSource(book, "replay", rec).get("reserve-backed", "i-1") == float(noul)


def test_replay_needs_an_existing_recording(tmp_path):
    with pytest.raises(ValueError):
        SystemOneFactSource(load_book(BOOK), "replay", tmp_path / "absent.jsonl")


def test_record_needs_an_api_key(tmp_path):
    with pytest.raises(ValueError):
        SystemOneFactSource(load_book(BOOK), "record", tmp_path / "rec.jsonl")


def test_unknown_mode_refuses(tmp_path):
    with pytest.raises(ValueError):
        SystemOneFactSource(load_book(BOOK), "live", tmp_path / "rec.jsonl")


# --- fault, call log, fallback --------------------------------------------------------


def test_fault_criterion_answers_none_even_when_recorded(tmp_path):
    book = load_book(BOOK)
    sha = book["reserve-audit-current"].evidence_sha256
    rec = _recording(tmp_path, [{"criterion": "reserve-audit-current", "evidence_sha256": sha, "noul": 0.95, "model": MODEL}])
    src = SystemOneFactSource(book, "replay", rec, fault="reserve-audit-current")
    assert src.get("reserve-audit-current", "i-1") is None


def test_every_get_logs_one_line_before_anything_else(tmp_path):
    book = load_book(BOOK)
    rec = _recording(tmp_path, [])
    log = tmp_path / "calls.jsonl"
    src = SystemOneFactSource(book, "replay", rec, call_log=log, fallback=_Static({"balance": 250.0}))
    src.get("reserve-backed", "i-1")
    src.get("balance", "i-2")
    src.get("nowhere", "i-3")
    lines = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines()]
    assert [(l["criterion"], l["intent_id"]) for l in lines] == [("reserve-backed", "i-1"), ("balance", "i-2"), ("nowhere", "i-3")]


def test_criteria_outside_the_book_fall_back_to_the_static_map(tmp_path):
    book = load_book(BOOK)
    src = SystemOneFactSource(book, "replay", _recording(tmp_path, []), fallback=_Static({"balance": 250.0}))
    assert src.get("balance", "i") == 250.0
    assert src.get("fx_rate", "i") is None
    assert SystemOneFactSource(book, "replay", _recording(tmp_path, [])).get("balance", "i") is None


# --- record mode against a local double --------------------------------------------------


class _Double:
    """Scripted System One: each entry is (status, body_dict_or_bytes, delay_s)."""

    def __init__(self, script):
        self.script = list(script)
        self.requests = []
        self.redirect_target_hits = 0

    def serve(self):
        double = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length)
                if self.path == "/elsewhere":
                    double.redirect_target_hits += 1
                    self.send_response(200)
                    self.end_headers()
                    return
                double.requests.append((self.path, dict(self.headers), json.loads(body)))
                status, payload, delay = double.script.pop(0)
                if delay:
                    time.sleep(delay)
                data = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
                self.send_response(status)
                if status in (301, 302, 307):
                    self.send_header("Location", "/elsewhere")
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):  # keep pytest output clean
                pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return server, "http://127.0.0.1:%d/v1/systemone" % server.server_address[1]


def _ok(noul, model=MODEL):
    return {"model": model, "answers": {"reserve-backed": {"type": "noul", "noul": noul}},
            "usage": {"input_tokens": 120, "output_tokens": 3}}


def _record_source(book, tmp_path, url, **over):
    kw = dict(api_key="test-key-not-a-secret", endpoint=url, timeout_s=0.5)
    kw.update(over)
    return SystemOneFactSource(book, "record", tmp_path / "rec.jsonl", **kw)


def test_record_posts_the_noul_question_and_records_the_answer(tmp_path):
    book = load_book(BOOK)
    double = _Double([(200, _ok(0.93), 0)])
    server, url = double.serve()
    try:
        src = _record_source(book, tmp_path, url)
        assert src.get("reserve-backed", "i-1") == 0.93
    finally:
        server.shutdown()
    path, headers, body = double.requests[0]
    assert path == "/v1/systemone"
    assert headers["Authorization"] == "Bearer test-key-not-a-secret"
    assert body["model"] == MODEL
    assert body["state"] == book["reserve-backed"].evidence
    assert body["questions"] == {"reserve-backed": {"type": "noul",
                                                    "instructions": book["reserve-backed"].instructions,
                                                    "criteria": book["reserve-backed"].criteria}}
    rec = json.loads((tmp_path / "rec.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert rec["criterion"] == "reserve-backed" and rec["noul"] == 0.93 and rec["model"] == MODEL
    assert rec["evidence_sha256"] == book["reserve-backed"].evidence_sha256
    assert rec["usage"] == {"input_tokens": 120, "output_tokens": 3}
    assert isinstance(rec["latency_ms"], int)
    assert "test-key-not-a-secret" not in (tmp_path / "rec.jsonl").read_text(encoding="utf-8")


@pytest.mark.parametrize("script", [
    [(500, {"error": "boom"}, 0)],
    [(429, {"error": "slow down"}, 0)],
    [(200, b"not json", 0)],
    [(200, {"model": MODEL, "answers": {}, "usage": {}}, 0)],
    [(200, _ok("0.9"), 0)],
    [(200, _ok(float("nan")), 0)],
    [(200, _ok(7), 0)],
    [(200, _ok(-0.1), 0)],
    [(200, _ok(1.0000001), 0)],
    [(200, _ok(True), 0)],
    [(200, _ok(0.9, model="jev-1.13.0"), 0)],
    [(200, _ok(0.9), 1.5)],
])
def test_record_failures_answer_none(tmp_path, script):
    book = load_book(BOOK)
    double = _Double(script)
    server, url = double.serve()
    try:
        assert _record_source(book, tmp_path, url).get("reserve-backed", "i-1") is None
    finally:
        server.shutdown()


def test_record_never_follows_a_redirect(tmp_path):
    book = load_book(BOOK)
    double = _Double([(302, {}, 0)])
    server, url = double.serve()
    try:
        assert _record_source(book, tmp_path, url).get("reserve-backed", "i-1") is None
    finally:
        server.shutdown()
    assert double.redirect_target_hits == 0


def test_a_wrong_model_recording_replays_as_none(tmp_path):
    """Record refuses a non-pinned model but still appends what it saw; replay must not answer it."""
    book = load_book(BOOK)
    double = _Double([(200, _ok(0.9, model="jev-1.13.0"), 0)])
    server, url = double.serve()
    try:
        assert _record_source(book, tmp_path, url).get("reserve-backed", "i-1") is None
    finally:
        server.shutdown()
    seen = json.loads((tmp_path / "rec.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert seen["model"] == "jev-1.13.0" and seen["noul"] == 0.9  # the line carries a passing-looking noul
    assert SystemOneFactSource(book, "replay", tmp_path / "rec.jsonl").get("reserve-backed", "i-1") is None


# --- the hook -------------------------------------------------------------------------


def test_fact_source_from_env_builds_replay_with_fallback(tmp_path, monkeypatch):
    book = load_book(BOOK)
    sha = book["reserve-backed"].evidence_sha256
    rec = _recording(tmp_path, [{"criterion": "reserve-backed", "evidence_sha256": sha, "noul": 0.8, "model": MODEL}])
    for var in ("SCORER_FACTS_MODE", "SCORER_FACTS_FAULT", "SCORER_FACTS_CALL_LOG", "TYPESAFE_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("SCORER_FACTS_BOOK", str(BOOK))
    monkeypatch.setenv("SCORER_FACTS_RECORDING", str(rec))
    src = fact_source_from_env(_Static({"balance": 250.0}))
    assert src.get("reserve-backed", "i") == 0.8
    assert src.get("balance", "i") == 250.0


def test_fact_source_from_env_refuses_without_a_book(monkeypatch):
    monkeypatch.delenv("SCORER_FACTS_BOOK", raising=False)
    with pytest.raises(SystemExit):
        fact_source_from_env(None)
