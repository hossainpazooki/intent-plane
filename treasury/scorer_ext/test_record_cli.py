"""record.py: the one-time live capture. Tested against a local double so the
suite never touches the network and never needs the key."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scorer_ext import record  # noqa: E402
from scorer_ext.test_systemone_facts import BOOK, MODEL, _Double, _ok  # noqa: E402


def test_record_refuses_without_a_key(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    rc = record.main(["--book", str(BOOK), "--out", str(tmp_path / "r.jsonl"), "--runs", "1"])
    assert rc == 2
    assert "TYPESAFE_API_KEY" in capsys.readouterr().out


def test_record_writes_runs_times_criteria_lines_and_prints_the_spread(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-not-a-secret")
    script = []
    for _ in range(2):
        for name in ("reserve-backed", "reserve-shortfall-absent", "reserve-audit-current"):
            body = _ok(0.5)
            body["answers"] = {name: {"type": "noul", "noul": 0.5}}
            script.append((200, body, 0))
    double = _Double(script)
    server, url = double.serve()
    try:
        rc = record.main(["--book", str(BOOK), "--out", str(tmp_path / "r.jsonl"), "--runs", "2", "--endpoint", url])
    finally:
        server.shutdown()
    assert rc == 0
    lines = [json.loads(l) for l in (tmp_path / "r.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 6 and all(l["model"] == MODEL for l in lines)
    out = capsys.readouterr().out
    assert "criterion=reserve-backed runs=2 noul_min=0.5000 noul_max=0.5000 model=jev-1.14.0" in out
    assert "test-key-not-a-secret" not in out


# --- review fixes (wave 2, Task 7): the failure shapes Step 5 plans for ---------------------

NAMES = ("reserve-backed", "reserve-shortfall-absent", "reserve-audit-current")


def _all_ok(runs, noul=0.5):
    script = []
    for _ in range(runs):
        for name in NAMES:
            body = _ok(noul)
            body["answers"] = {name: {"type": "noul", "noul": noul}}
            script.append((200, body, 0))
    return script


def test_record_prints_zero_runs_instead_of_raising_when_every_call_fails(tmp_path, monkeypatch, capsys):
    """A bad key or a wrong request shape writes no line at all; the operator gets
    runs=0 lines and rc 1, never a traceback."""
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-not-a-secret")
    double = _Double([(401, {"error": {"message": "bad key"}}, 0)] * 3)
    server, url = double.serve()
    try:
        rc = record.main(["--book", str(BOOK), "--out", str(tmp_path / "r.jsonl"), "--runs", "1", "--endpoint", url])
    finally:
        server.shutdown()
    assert rc == 1
    assert len(double.requests) == 3
    out = capsys.readouterr().out
    for name in NAMES:
        assert "criterion=%s runs=0 noul_min=none noul_max=none" % name in out
    assert "3 of 3 calls wrote no line" in out
    assert "test-key-not-a-secret" not in out


def test_record_refuses_to_append_to_an_existing_capture(tmp_path, monkeypatch, capsys):
    """Replay serves the FIRST line per (criterion, evidence sha256), and the hash covers the
    evidence text only: a retry appended after an instructions- or criteria-only rewrite would
    keep serving the old capture. Refuse before any paid call."""
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-not-a-secret")
    prior = tmp_path / "r.jsonl"
    prior.write_text('{"criterion": "reserve-backed"}\n', encoding="utf-8")
    double = _Double([])
    server, url = double.serve()
    try:
        rc = record.main(["--book", str(BOOK), "--out", str(prior), "--runs", "1", "--endpoint", url])
    finally:
        server.shutdown()
    assert rc == 3
    assert double.requests == []
    assert prior.read_text(encoding="utf-8") == '{"criterion": "reserve-backed"}\n'
    assert "nothing recorded" in capsys.readouterr().out


def test_record_strips_a_trailing_crlf_from_the_key(tmp_path, monkeypatch, capsys):
    """A CRLF key file read through tr -d with LF only leaves a trailing CR; http.client
    rejects that header and every call would write nothing."""
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-not-a-secret\r\n")
    double = _Double(_all_ok(1))
    server, url = double.serve()
    try:
        rc = record.main(["--book", str(BOOK), "--out", str(tmp_path / "r.jsonl"), "--runs", "1", "--endpoint", url])
    finally:
        server.shutdown()
    assert rc == 0
    assert [headers["Authorization"] for _, headers, _ in double.requests] == ["Bearer test-key-not-a-secret"] * 3
    assert "test-key-not-a-secret" not in capsys.readouterr().out


def test_record_treats_a_blank_key_as_absent(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TYPESAFE_API_KEY", " \r\n")
    double = _Double([])
    server, url = double.serve()
    try:
        rc = record.main(["--book", str(BOOK), "--out", str(tmp_path / "r.jsonl"), "--runs", "1", "--endpoint", url])
    finally:
        server.shutdown()
    assert rc == 2
    assert double.requests == []
    assert not (tmp_path / "r.jsonl").exists()
    assert "TYPESAFE_API_KEY" in capsys.readouterr().out
