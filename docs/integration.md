# Integration — what a platform team embeds

For the team that owns how agents call tools. You embed the gate once at the
framework layer and every agent inherits it: declare the intent, await the
terminal, proceed on `ACHIEVED` or surface the refusal.

**The disciplines below ship as code**: the `declarant/` package (Go,
`CONTRACT.md` §2.7) — exact wire marshal, `DeriveKey`, a total terminal
classification with fail-closed `Unknown`, the 500-edge feed consult, and the
cursor poll — plus the `intent-declare` CLI. `force_scores` exists in no
declarant type. This page remains the normative walkthrough; the package is
its executable form, proven live against the reference plane (the monorepo's
quickstart probes 6 and 7 — the Go SDK and the Python twin respectively).

## The shape of the integration

Declaration is **one synchronous request** (`POST /v2/intents`) that returns
the terminal — no asynchronous state machine to build. Refusal reasons form a
**contractually closed set** (`CONTRACT.md` §3.3 — adding a cause amends the
table first), so the framework switches on stable strings and version skew
fails loudly (`DisallowUnknownFields`: any speculative extra field is a 400).

The declarant supplies: `episode_seed` (determinism source — derive it, never
random it), the idempotency key and scope, the spec's content address
(`intent_spec_hash`), and optionally a `spec_envelope` (the hybrid wire path
for attested specs). Criteria never ride the wire — the field does not exist.

## The two disciplines the framework owns

1. **Derive the idempotency key deterministically from the action's
   identity.** Never a fresh UUID per attempt — that deletes the
   at-most-once (dedup) property. Never too coarse — reservations are permanent, so
   a key that collides across genuinely distinct calls bricks the second
   call forever. A workable shape:
   `<scope>:<agent-run-id>:<tool-name>:<sha256(canonical-args)>`.
2. **Settle side effects only from observed `ACHIEVED` records in the
   durable feed** (`GET /v2/events?since=<cursor>`), treating the
   synchronous response as UX. Persist `next_since` durably; the feed is
   poll-only — the gate never calls out.

A collision (`FAILED_AT_DISPATCH` / `idempotency-collision`) means the
action already happened or was reserved: reconcile from the record, never
mint a new key to get past it. On an HTTP 500 the terminal is indeterminate
(a key may be reserved with no `ACHIEVED` record): consult
`GET /v2/intents/{id}/events` before deciding anything.

## Retry semantics follow reservation position

The key is reserved at the dispatch edge, after the volatile re-check and
before `ACHIEVED`. So: a `FAILED` at declaration or a `volatile-recheck`
stop never reserved the key — same-key retry is safe once facts change.
`ACHIEVED` reserved it — a same-key retry correctly collides.
`unevaluable:*` refusals are "cannot evaluate", never "denied on the
merits": retry with backoff on outages; route thin-spec shapes
(`empty-criteria`, `invalid-volatility`) to the spec owner, not the agent.

## Posture caveats to state, not hide

The feed read surface is unauthenticated by design — network isolation is a
deployment decision your platform owns. `force_scores` exists for test
posture only and is refused unless the server booted with
`INTENT_UNSAFE_FORCE_SCORES=1`; never expose it in any SDK type, sample, or
doc. Zero-config is fail-closed: a gate booted with no trust root and no
scorer URL authorizes nothing.

## LangChain: gate a tool in one call

For LangChain runtimes the embedding discipline ships pre-wired
(`declarant/pydeclarant/langchain_adapter.py`, optional — it is the one
pydeclarant module that imports `langchain_core`; everything else in the
tree is stdlib-only):

```python
from client import Client
from langchain_adapter import gate_tool, IntentRefused

gated = gate_tool(
    my_tool,                       # any LangChain tool
    Client("http://127.0.0.1:8080"),   # bounded by default (30s per call)
    intent_spec_hash=SPEC_HASH,    # content address of the attested spec
    scope="per-actor",
    run_id=agent_run_id,
)
```

The gated tool executes ONLY on `Proceed`. Every other outcome raises
`IntentRefused`, which carries the §2.7 classification (`class_`,
`terminal`, `reason`), the machine-readable `same_key_retry_safe`
position, and prose `retry_guidance` — the wrapped tool function is never
called, so the worst case is an action that wrongly waits. What the
adapter takes off your hands:

- **Canonicalization** (§2.7's caller duty): schema-validated keyword args
  are canonicalized by a fixed recipe (pydantic models via
  `model_dump(mode="json")`, then sorted-key compact JSON), so
  omit-vs-explicit defaults and dict-vs-model inputs derive the SAME
  idempotency key. String/positional input is refused before any
  declaration — it would fork the key.
- **Per-call intent scoping**: each invocation declares under its own
  intent (episode seed derived from the idempotency key), so the 500-edge
  feed consult reads the calling intent's records, never another call's.
  And a `Proceed` read back from that consult is HISTORICAL — the
  consequence already fired once — so the adapter refuses
  (`ALREADY_ACHIEVED`) instead of re-firing it; execution requires a fresh
  synchronous `Proceed`.
- **Async**: `ainvoke` delegates to the gated sync path — the async route
  is gated by construction, not separately wired.

Both SDK clients are bounded by default (30s per call); an unbounded
client is an explicit opt-in (Go: supply your own `http.Client`; Python:
`timeout=None`), never something you inherit by forgetting a parameter.

## Forwarding the record to observability — logs index, gates decide

The durable feed is a line-delimited JSON file
(`$INTENT_DATA_DIR/events.jsonl`, one event per line, fsynced per append).
Any log shipper can tail it into your observability stack — a Datadog agent
logs entry, a fluent-bit tail, a vector source — with **zero SDK change**:
the file is already the export surface, and each line parses as structured
JSON without a grok pattern.

Two rules keep the forwarded copy honest:

1. **The copy is an index, never an authority.** Dashboards, monitors, and
   alerts on the forwarded stream are how operators watch the gate; the
   feed on disk remains the sole authority, and anything that matters is
   re-derived from it (`GET /v2/events?since=cursor`, or the verifier).
   Nothing downstream of the shipper may feed back into a decision.
2. **Emission can never touch decisions — structurally.** The gate does not
   know the shipper exists; a dropped, lagging, or misconfigured forwarder
   cannot block or fail an authorization. Push-based trace export (OTel) is
   staged (R4 in the project roadmap) and deliberately absent today.

Useful monitors fall out of the event vocabulary: rate of `FAILED`
refusals by cause prefix (`unevaluable:*` spikes mean the scorer or a fact
source is down — remember refusal is the system working, so alert on the
*rate change*, not the refusal), any `FAILED_AT_DISPATCH`
(`idempotency-collision` or volatile drift — both worth eyes), and
`SHADOW_RECORDED` volume during a staged rollout (the governance record for
that terminal is still Proposed, not settled — `docs/assurance.md`).
