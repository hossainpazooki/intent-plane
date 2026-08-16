# scorer — the intent layer's Python service

The Python side of the intent layer's scoring seam: one service = **resolver**
(artifact verify, injected) + **scorer** (fact vs threshold), answering
`POST /ml/evaluate` for the Go authorization gate in `core/`.

**The contract is the source of truth, not this README**: `../../CONTRACT.md`
(the wire seam in §2.4, this service in §8, the fixtures in §9). The golden wire
fixtures in `../contract/scorer/` are the ONLY surface shared with the Go side —
neither side imports the other.

## Behavior (spec invariant 2, fail-closed, across the network)

Tri-state closed set `PASS | FAIL | UNEVALUABLE`. For a well-formed request the
service ALWAYS answers `200` — unknown criterion, missing fact, resolver
failure, internal exception are all evaluations that answer `UNEVALUABLE`.
Non-2xx is reserved for malformed requests (`422`) and infrastructure; the Go
client maps those to `Unevaluable` anyway. An outage can only ever make the
gate refuse.

`basis` is observability only: free text, never allowed into the gate's audit
log, durable feed, or any hash.

## Run / test

```bash
cd core/scorer
python -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m pytest          # unit + service matrix + wire fixtures
.venv/Scripts/python -m scorer          # serve on 127.0.0.1:8000 (SCORER_HOST/SCORER_PORT)
```

Fixture tests find `../contract/scorer` by default (`SCORER_CONTRACT_DIR`
overrides). Absent fixtures SKIP visibly — a skip is NOT a pass.

## Implemented vs planned

- **[built]** `EvalRequest`/`EvalResponse` models, evaluator, `StaticFactSource`,
  `NullResolver`, FastAPI app + service fail-closed matrix, wire-fixture
  byte-agreement tests.
- **[built — 2026-07-12]** the wheel-backed `KeArtifactResolver`
  (`ke-artifact-py`, Linux/CI only; verify runs in an executor for the GIL
  caveat). Verifies the governing artifacts by content address against a
  `.kew` store + the four rule-engine verify inputs; fail-closed on absent hash,
  rejected verdict, or re-address mismatch. Configure via
  `SCORER_ARTIFACT_DIR` + `SCORER_VERIFY_INPUTS_DIR` + `SCORER_EXPORTED_AT_UNIX`
  (all-or-nothing; a partially-configured server refuses to boot). Its pytest
  lane runs against the real rule-engine goldens on Linux and skips visibly
  elsewhere. NOTE: green requires the rule-engine's kind-aware verification
  fix — before it, no IntentSpec could verify at all.
- **[recorded debt]** one resolver = ONE verification environment (one
  policy/context set). Mixed-kind requests (a rule hash + a spec hash from
  different corpora) fail closed rather than verify both; the fix is a
  binding-side kind-aware environment, an rule-engine follow-up.
- **[planned — later slice]** a live fact source. `StaticFactSource` is the
  demo configuration and is labeled as such; do not fake a live one.
