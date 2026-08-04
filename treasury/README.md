# treasury — a demonstration deployment of the intent plane

This directory shows the intent plane doing its job in a concrete domain:
**payment controls**. An agent (the declarant) declares a payment intent with
criteria — a balance floor, an fx-rate floor, a declared idempotency key. The
plane's gate scores those criteria against facts served by the scorer, refuses
anything unevaluable, reserves the key at the dispatch edge, and emits exactly
one durable `ACHIEVED` record that a settlement consumer can observe. Value
moves only after that record exists.

Nothing in `core/` knows any of these words: *payment*, *balance*, *fx rate*
live only here (mechanically enforced by `TestCoreNeutrality`). The one
deliberate exception: the frozen wire fixtures in `core/contract/scorer/`
carry the criterion name `"balance"` from their capture date — regenerating
them with neutral names is a recorded roadmap follow-up.

## Quickstart

Run from the repo root:

    # Windows
    powershell -File treasury\quickstart.ps1
    # Linux / macOS / WSL
    ./treasury/quickstart.sh

Requirements: Go and Python 3.11+. The script creates the scorer venv on
first run, boots the scorer with `facts.json` (`balance: 250.0`,
`fx_rate: 1.30`) injected via `SCORER_FACTS_JSON`, builds and boots the gate
with `INTENT_SCORER_URL`, runs the probe ladder, and tears everything down.
Expected final line: `RESULT: 6/6 probes passed` — every probe asserts its
terminal, so the demo doubles as a smoke gate.

## The probe ladder

| # | Probe | Expected | What it demonstrates |
|---|---|---|---|
| 1 | Declare a payment within limits | `ACHIEVED` | the full lifecycle against real scored facts; one durable record |
| 2 | Near-duplicate: same key, one changed field | `FAILED_AT_DISPATCH` `idempotency-collision` | at-most-once by construction, not by adapter dedup |
| 3 | Declare over-threshold | `FAILED`, reason names `balance` | criteria actually bind |
| 4 | Kill the scorer, declare again | `FAILED` `unevaluable:` | fail-closed on outage, demonstrated live |
| 5 | Declare with empty criteria | `FAILED` `unevaluable:empty-criteria` | thin-spec defense: no criteria is never a pass |
| 6 | Read `GET /v2/events?since=0` | exactly one `ACHIEVED` | emit-and-observe: consumers settle only from the feed |

`force_scores` (the documented test affordance on the wire) is deliberately
absent from this showcase. Artifact verification is also absent here — the
scorer runs with the null resolver and says so on the wire
(`resolver=null: verification skipped`), which is the honest boundary between
this quickstart and the extended demonstration below.

## The extended demonstration (separate environments required)

Everything below is **built and was live-verified on 2026-07-12**, but needs
more than Go+Python on one machine — it is documented, not scripted here:

- **Signed-artifact verification**: the scorer's `KeArtifactResolver` binds
  the `ke-artifact-py` wheel (Linux/WSL only) and verifies the ATLAS-published
  `IntentSpec` artifact by content hash before scoring. Env:
  `SCORER_ARTIFACT_DIR`, `SCORER_ATLAS_INPUTS_DIR`, `SCORER_EXPORTED_AT_UNIX`
  (all-or-nothing; partial config refuses to boot). The wheel pytest lane
  requires a sibling `regulatory-rule-engine` checkout containing
  `fixtures/artifacts/intentspec_payment/`.
- **Settlement consumption**: the COMPASS settlement consumer (separate repo)
  polls `GET /v2/events?since=<cursor>` by cron, recomputes settlement from
  the `ACHIEVED` trace fields `{intent_id, idempotency_key,
  rule_artifact_hash, intent_spec_hash, trajectory_hash, seq}`, and writes a
  keyed at-most-once ledger. The full loop — declare through settle, with a
  restatement replay and a real scorer-kill negative — ran green end-to-end
  on 2026-07-12 (see `docs/handoff/2026-07-13-atlas-treasury-payment-loop.md`).

## Facts

`facts.json` is the only place treasury facts exist. The scorer's built-in
default is an **empty** fact map — a scorer that knows nothing scores
everything UNEVALUABLE and the gate refuses everything. Fail-closed is the
default posture; the demonstration opts *into* facts.
