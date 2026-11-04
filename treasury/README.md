# treasury — a demonstration deployment of the intent plane

This directory shows the intent plane doing its job in a concrete domain:
**payment controls**. The control role's key attests a spec — a balance
floor, an fx-rate floor — and publishes it into the spec store; an agent (the
declarant) then declares a payment intent citing that spec's content address
plus a declared idempotency key (the wire carries no criteria at all). The
plane's gate resolves the signed spec, scores its criteria against facts
served by the scorer, refuses anything unevaluable or unattested, reserves
the key at the dispatch edge, and emits exactly one durable `ACHIEVED` record
that a settlement consumer can observe. Value moves only after that record
exists.

Nothing in `core/` knows any of these words: *payment*, *balance*, *fx rate*
live only here (mechanically enforced by `TestCoreNeutrality`). The one
deliberate exception: the frozen wire fixtures in `core/contract/scorer/`
carry the criterion name `"balance"` from their capture date — regenerating
them with neutral names is a recorded follow-up, carried in the maintainers'
working notes rather than in this repository.

## Quickstart

Run from the repo root:

    # Windows
    powershell -File treasury\quickstart.ps1
    # Linux / macOS / WSL
    ./treasury/quickstart.sh

Requirements: Go and Python 3.11+. The script creates the scorer venv on
first run, boots the scorer with `facts.json` (`balance: 250.0`,
`fx_rate: 1.30`) injected via `SCORER_FACTS_JSON`, then runs the plane leg —
keygen (test key authority), trust root, attest + publish the eight spec drafts in `specs/` — builds and boots the gate with `INTENT_SCORER_URL` and
`INTENT_TRUST_ROOT`, runs the probe ladder (including a live signed
revocation, the declarant-SDK consumption probe, the LangChain and MCP
live legs, the reporting-gate probe, and the verifier-twin recompute), and
tears everything down.
Expected final line: `RESULT: 17/17 probes passed` on a host where
`ke-artifact-py` imports (Linux / WSL), `RESULT: 16/16 probes passed (1
skipped: provenance root needs ke-artifact-py)` elsewhere — every probe
asserts its terminal, a skip is printed and never counted, so the demo
doubles as a smoke gate.

## The probe ladder

| # | Probe | Expected | What it demonstrates |
|---|---|---|---|
| 1 | Declare a payment within limits (signed spec) | `ACHIEVED` | the full lifecycle against an attested spec and real scored facts; one durable record |
| 2 | Near-duplicate: same key, different spec | `FAILED_AT_DISPATCH` `idempotency-collision` | at-most-once by construction, not by adapter dedup |
| 3 | Declare over-threshold | `FAILED`, reason names `balance` (and NOT `unevaluable`) | criteria actually bind |
| 4 | Declare citing a hash nobody attested | `FAILED` `unevaluable:unattested-spec` | no signature, no scoring — P1's fail-closed floor |
| 5 | Revoke the within-limits spec (signed tombstone), declare against it | `FAILED` `revoked:quickstart-pull` | authority is revocable; the tombstone's ref is witnessed |
| 6 | Declare through the published declarant SDK (`bin/intent-declare`, derived deterministic key), then repeat with the SAME derived key | first: `class=PROCEED terminal=ACHIEVED`, exit 0; second: `class=ALREADY_RESERVED`, `same_key_retry_safe=false`, exit 1 | the embedding half of the two-sided sale runs live: derived keys make dedup real, and a collision is classified, not mysterious (§2.7) |
| 7 | Declare through the Python declarant twin (`declarant/pydeclarant`'s `Client`, its own derived key), then repeat with the SAME key | first: `class=PROCEED terminal=ACHIEVED`; second: `class=ALREADY_RESERVED`, `same_key_retry_safe=false` | the twin's first LIVE leg (2026-08-18): the shared golden bytes speak the same wire against the real gate, not only in a lab byte-compare (§2.7) |
| 8 | Invoke a LangChain tool wrapped by `gate_tool` (the adapter), then repeat with the SAME args | first: tool body executes exactly once, result returned; second: `IntentRefused` `class=ALREADY_RESERVED`, body NOT re-fired | the adapter's LIVE leg (2026-08-18): a wrapped agent tool fires its consequence exactly once, and a refusal is a classified outcome, not an exception to debug. Its first live run failed the ladder at the verifier-recompute probe — the verifier refuted a reused episode seed the lab double could not see, and the per-invocation nonce is the fix that records it |
| 9 | Call a gated `fastmcp` tool through `IntentGateMiddleware`, repeat with the SAME args, then retry those args against a SECOND, independent middleware instance (same scope/run, its own server and counter) | first: tool body executes exactly once, result returned; second: `ToolError` carrying `class=ALREADY_RESERVED`, body NOT re-fired; third: `ALREADY_RESERVED` again with the second instance's counter still 0 | the MCP gate's LIVE leg (2026-08-20), and the stateless/multi-replica claim proven live: the idempotency key is DERIVED, not remembered, so a retry landing on a replica that shares no state is refused just the same (§2.7) |
| 10 | Front an UNGATED backend with `gated_proxy` under its own `run_id` and call it twice with the SAME args (plus a call omitting a property whose schema declares no default) | first: passes through, INNER counter 1; second: `ToolError` `class=ALREADY_RESERVED`, INNER counter still 1; the omitted-property call is refused BEFORE anything is declared (`strict_args`) | a server you do not own is gated without changing it — the INNER counter is what proves the refused call never reached the backend at all, and an unkeyable call earns no `ACHIEVED` (§2.7) |
| 11 | Submit a valuation (VALU) through the stdlib reporting adapter (`gate_submission`), repeat with the SAME identity but DIFFERENT report bytes, declare an erasure (EROR) under a spec carrying an unresolved human-judgment entry, then declare an unkeyable NEWT (an `as_of` on a type that does not key on it) — runs while the scorer is still live, since its `balance` criterion is scored at declaration | first: submits once, repository counter 1; second: refused `ALREADY_RESERVED`, counter still 1; third: refused by the GATE `class=HUMAN_JUDGMENT`, counter unchanged; fourth: `ReportUnkeyable` BEFORE any declaration | content-blind keying proven live — the second valuation is the duplicate a trade repository will NOT reject, refused by identity, not content; the erasure is refused by the plane's own abstention, not by adapter code (§2.7) |
| 16 | Gate a CDM `WorkflowStep` through `gate_cdm_event` on a criterion the showcase's System One (TypeSafe AI, Jev) fact source scores — replayed from `recordings/` — four times: a grant, a low score, an unreachable judge (fault-injected), and an erasure under the human-judgment spec | `ACHIEVED` with `calls=+1 scored_records=1`; `POLICY_DENIED`; `UNEVALUABLE`; `HUMAN_JUDGMENT` with `calls=+0 scored_records=0` | the judge's probability is a fact behind the unchanged `/ml/evaluate` wire and never a record; the human-judgment refusal happens with the judge never asked — two independent witnesses per leg (claim 21) |
| 17 | Declare the same spec twice citing a rule artifact from `provenance/` by content hash: one the verifier accepts, one it rejects (Linux/WSL only; skipped visibly elsewhere) | `ACHIEVED calls=+1`; `UNEVALUABLE calls=+0` | the authoring plane is the provenance root: an unverifiable citation is refused before the judge is consulted (§2.4 `rule` mode) |
| 12 | Kill the scorer, declare again | `FAILED` `unevaluable:` | fail-closed on outage, demonstrated live |
| 13 | Declare an attested-but-thin spec (zero criteria) | `FAILED` `unevaluable:empty-criteria` | attestation does not launder vacuity |
| 14 | Read `GET /v2/events?since=0` | exactly nine `ACHIEVED` (eight when probe 17 is skipped) — one per authorized key | emit-and-observe: consumers settle only from the feed, and no key ever settles twice |
| 15 | Run BOTH verifier twins (`bin/intent-verify` + `verifier/pyverifier/verify.py`) over the live `events.jsonl` | `RESULT: VERIFIED`, exit 0, reports byte-identical | an independent examiner re-derives every commitment — trajectory hashes on grants AND refusals, sequence contiguity, exactly-one-ACHIEVED — from the record bytes alone, with no trust in the gate |

`force_scores` (the guarded test affordance) is deliberately absent from this
showcase — the gate here boots WITHOUT `INTENT_UNSAFE_FORCE_SCORES`, so the
wire would refuse it anyway. The plane's spec attestation runs live above at
test key authority (`key_authority: "test"` until production key authority
lands, R1). Scorer-side verification of a signed artifact from the authoring
plane runs on the Linux/WSL lane only (probe 17, `provenance/`,
`SCORER_VERIFY_HASHES=rule`); on Windows the scorer runs with the null
resolver and says so on the wire (`resolver=null: verification skipped`),
which is the honest boundary of that lane.

## The chassis flow test

The quickstart proves the *gate* half live. The seats themselves — authoring,
authority, control, which live in the plane table at `planetable/` — are
covered by `go test ./treasury` (`flow_test.go`),
which takes the **maker-checker chain as the unit**: one linear test builds
the real seat binaries and execs them exactly as an operator would (no
production code was refactored for testability), running
author → keygen → root → attest → publish → promote → revoke and asserting
each refusal edge where it naturally occurs (a second keygen over the same
file, a publish under a foreign trust root, a second promotion of an
already-enforcing payload).

What it pins is `CONTRACT.md` §5.4 claim 19: passage-exact source pins and
shadow-by-default out of authoring; attested bytes identical to executed
bytes through the store; promotion as a NEW artifact rather than an edit in
place; revocation scoped to exactly one content address. The pins are over
behavior that already existed, so green-on-first-run proves nothing about
them — non-vacuity comes from three plant-red runs recorded in the claim row.

## The extended demonstration (separate environments required)

Everything below is **built and was live-verified on 2026-07-12**, but needs
more than Go+Python on one machine — it is documented, not scripted here:

- **Signed-artifact verification**: the scorer's artifact resolver binds the
  upstream verification wheel (Linux/WSL only) and verifies a spec artifact
  published by the artifact plane, by content hash, before scoring. Env:
  `SCORER_ARTIFACT_DIR`, `SCORER_VERIFY_INPUTS_DIR`, `SCORER_EXPORTED_AT_UNIX`
  (all-or-nothing; partial config refuses to boot). The wheel pytest lane is
  wired by `SCORER_GOLDENS_DIR` alone — unset, it skips visibly; there is no
  sibling-checkout fallback.
- **Settlement consumption**: a settlement consumer, living in its own
  repository, polls `GET /v2/events?since=<cursor>` by cron, recomputes
  settlement from the `ACHIEVED` trace fields `{intent_id, idempotency_key,
  rule_artifact_hash, intent_spec_hash, trajectory_hash, seq}`, and writes a
  keyed at-most-once ledger. The full loop — declare through settle, with a
  restatement replay and a real scorer-kill negative — ran green end-to-end
  on 2026-07-12. That consumer is not part of this repository and its run is
  not reproducible from this clone, which is why it sits below the line.

## Facts

The quickstart's scorer answers a criterion from exactly two places, both in
this directory:

- `facts.json` — the static map (`balance`, `fx_rate`) injected via
  `SCORER_FACTS_JSON`, which the payment and reporting specs 01-08 score
  (05, the thin spec, deliberately cites no criterion).
- the System One (TypeSafe AI, Jev) adapter in `scorer_ext/`, loaded through
  `SCORER_FACTS_MODULE`. It answers only the criteria its book
  `scorer_ext/criteria.json` names — `reserve-backed`,
  `reserve-shortfall-absent`, `reserve-audit-current`, scored by specs 09-11
  — each judged over its evidence file in `evidence/`; every other criterion
  falls through to `facts.json`. The quickstart runs it in `replay` mode over
  the committed recording `recordings/systemone-jev-1.14.0.jsonl`, so it
  never touches the network: the judge's recorded probability is the fact,
  and the signed spec's `0.7` threshold decides. The quickstart also faults
  `reserve-audit-current` on purpose (`SCORER_FACTS_FAULT`) — that is probe
  16's unreachable-judge leg. `record` mode, the only one that calls the live
  API, is an operator step with a key held outside every repository, never
  part of the quickstart.

The scorer's built-in default is an **empty** fact map — a scorer that knows
nothing scores everything UNEVALUABLE and the gate refuses everything. The
adapter keeps that posture: no recorded answer for a criterion's exact
evidence bytes, an answer that is not a probability in [0, 1], or one from a
model other than the pinned `jev-1.14.0` answers nothing, so the gate
refuses; a missing recording refuses the scorer's boot. Fail-closed is the
default posture; the demonstration opts *into* facts.
