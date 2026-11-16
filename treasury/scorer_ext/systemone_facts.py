"""System One (TypeSafe AI, Jev) fact source for the showcase scorer
(CONTRACT.md section 8 hook; section 5.4 claim 21).

Loaded by the scorer through SCORER_FACTS_MODULE. The judge's noul
probability IS the fact; the signed spec's threshold decides PASS/FAIL in
the scorer's evaluator; the probability leaves this process only inside
`basis`, which the contract keeps off every record and hash.

Modes (SCORER_FACTS_MODE): `replay` (default) answers from the recording
file and never touches the network; `record` calls the live API with
TYPESAFE_API_KEY and appends what it saw. Every failure -- timeout, non-200,
redirect, unparseable body, an answer that is not a probability in [0, 1],
a model other than the pinned one -- answers None, which the evaluator maps
to UNEVALUABLE and the gate refuses. Replay applies the same acceptance rule
to the recorded line, so a run that record refused never answers on replay.

Env: SCORER_FACTS_BOOK (criteria.json), SCORER_FACTS_RECORDING (jsonl),
SCORER_FACTS_MODE, SCORER_FACTS_FAULT (a criterion that fails on purpose),
SCORER_FACTS_CALL_LOG (one line per get(), the scorer-consulted witness),
TYPESAFE_API_KEY (record mode only; never logged or recorded).
Stdlib only. ASCII only.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # annotations only; the module stays stdlib-only at runtime
    from scorer.facts import FactSource

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-1.14.0"
MODES = ("replay", "record")


@dataclass(frozen=True)
class CriterionEntry:
    instructions: str
    criteria: dict          # {"true": ..., "false": ...}
    evidence: str           # the evidence text the judge sees as `state`
    evidence_sha256: str    # binds a recording to the exact evidence bytes


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # a redirect is a failure, never followed


def load_book(path: Path) -> dict[str, CriterionEntry]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    book = {}
    for name, entry in raw.items():
        text = (Path(path).parent / entry["evidence"]).resolve().read_text(encoding="utf-8")
        book[name] = CriterionEntry(
            instructions=entry["instructions"],
            criteria=dict(entry["criteria"]),
            evidence=text,
            evidence_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        )
    return book


def _probability(value):
    """A noul answer is a real number in [0, 1]; anything else is no answer."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    # Compare before float(): NaN fails every comparison, and an int too big
    # for a float is out of range here instead of raising OverflowError.
    if not 0 <= value <= 1:
        return None
    return float(value)


class SystemOneFactSource:
    def __init__(self, book: dict[str, CriterionEntry], mode: str, recording_path: Path, fault: str | None = None,
                 call_log: Path | None = None, fallback=None, api_key: str | None = None,
                 model: str = MODEL, endpoint: str = ENDPOINT, timeout_s: float = 3.0, opener=None) -> None:
        if mode not in MODES:
            raise ValueError("mode must be one of %s, got %r" % (MODES, mode))
        if mode == "record" and not api_key:
            raise ValueError("record mode needs an API key (TYPESAFE_API_KEY)")
        recording_path = Path(recording_path)
        if mode == "replay" and not recording_path.exists():
            raise ValueError("replay mode needs an existing recording: %s" % recording_path)
        self._book = dict(book)
        self._mode = mode
        self._recording = recording_path
        self._fault = fault
        self._call_log = Path(call_log) if call_log else None
        self._fallback = fallback
        self._api_key = api_key
        self._model = model
        self._endpoint = endpoint
        self._timeout = timeout_s
        self._opener = opener or urllib.request.build_opener(_NoRedirect)
        self._replay = self._index(recording_path) if mode == "replay" else {}

    @staticmethod
    def _index(path: Path) -> dict:
        index = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            # The FIRST recorded run answers; later runs are the spread. A first
            # run that record refused answers None on replay, as it did live.
            index.setdefault((rec["criterion"], rec["evidence_sha256"]), rec)
        return index

    def get(self, criterion: str, intent_id: str):
        self._log(criterion, intent_id)
        entry = self._book.get(criterion)
        if entry is None:
            return self._fallback.get(criterion, intent_id) if self._fallback is not None else None
        if criterion == self._fault:
            return None
        if self._mode == "replay":
            rec = self._replay.get((criterion, entry.evidence_sha256))
            return self._accept(rec.get("model"), rec.get("noul")) if rec else None
        return self._record(criterion, entry)

    def _accept(self, model, noul):
        """The one acceptance rule, shared by record and replay."""
        return _probability(noul) if model == self._model else None

    def _log(self, criterion: str, intent_id: str) -> None:
        if self._call_log is None:
            return
        with self._call_log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"criterion": criterion, "intent_id": intent_id, "ts": time.time()}, sort_keys=True) + "\n")

    def _record(self, criterion: str, entry: CriterionEntry):
        body = json.dumps({
            "model": self._model,
            "state": entry.evidence,
            "questions": {criterion: {"type": "noul", "instructions": entry.instructions, "criteria": entry.criteria}},
        }).encode("utf-8")
        req = urllib.request.Request(
            self._endpoint, data=body, method="POST",
            headers={"Authorization": "Bearer " + self._api_key, "Content-Type": "application/json",
                     "Accept": "application/json"},
        )
        started = time.monotonic()
        try:
            with self._opener.open(req, timeout=self._timeout) as resp:
                if resp.status != 200:
                    return None
                payload = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            return None
        if not isinstance(payload, dict):
            return None
        latency_ms = int((time.monotonic() - started) * 1000)
        answered_model = payload.get("model")
        answers = payload.get("answers") or {}
        answer = answers.get(criterion) if isinstance(answers, dict) else None
        noul = _probability(answer.get("noul")) if isinstance(answer, dict) else None
        rec = {
            "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "criterion": criterion,
            "evidence_sha256": entry.evidence_sha256,
            "model_requested": self._model,
            "model": answered_model,
            "noul": noul,
            "usage": payload.get("usage"),
            "latency_ms": latency_ms,
        }
        with self._recording.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
        return self._accept(answered_model, noul)


def fact_source_from_env(fallback: FactSource | None) -> FactSource:
    """The SCORER_FACTS_MODULE factory (CONTRACT.md section 8)."""
    try:
        call_log = os.environ.get("SCORER_FACTS_CALL_LOG")
        return SystemOneFactSource(
            book=load_book(Path(os.environ["SCORER_FACTS_BOOK"])),
            mode=os.environ.get("SCORER_FACTS_MODE", "replay"),
            recording_path=Path(os.environ["SCORER_FACTS_RECORDING"]),
            fault=os.environ.get("SCORER_FACTS_FAULT") or None,
            call_log=Path(call_log) if call_log else None,
            fallback=fallback,
            api_key=os.environ.get("TYPESAFE_API_KEY"),
        )
    except (KeyError, ValueError, OSError) as exc:
        raise SystemExit("systemone fact source: %s" % exc)
