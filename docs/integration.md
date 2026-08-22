# Integration — what a platform team embeds

For the team that owns how agents call tools. You embed the gate once at the
framework layer and every agent inherits it: declare the intent, await the
terminal, proceed on `ACHIEVED` or surface the refusal.

**The disciplines below ship as code**: the `declarant/` package (Go,
`CONTRACT.md` §2.7) — exact wire marshal, `DeriveKey`, a total terminal
classification with fail-closed `Unknown`, the 500-edge feed consult, and the
cursor poll — plus the `intent-declare` CLI. `force_scores` exists in no
declarant type. This page remains the normative walkthrough; the package is
its executable form, proven live against the reference plane by the testing
monorepo's quickstart probes — one each for the Go SDK, the Python twin, the
LangChain adapter, the MCP middleware, and the gated MCP proxy.

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

## The clients never follow a redirect (2026-08-20)

Both SDK clients decline HTTP redirects. If you front the gate with a proxy
that answers a declaration with a 301/302/303, the SDK will not comply: an
ordinary HTTP client downgrades that POST to a GET and DROPS the declaration
body, so the redirect target receives no declaration at all — and an
`ACHIEVED`-shaped 200 from that target would then read as authorization for
an action nobody declared. A 3xx is therefore treated like any other
non-200 status: the per-intent feed is consulted before anything is decided,
and an unreachable feed decides nothing (`Indeterminate`). The gate's own
outbound call to the scorer seam follows the same rule — a 3xx answer to
`/ml/evaluate` is `Unevaluable`, never a criterion pass (`CONTRACT.md` §2.4;
the declarant-side rule is §2.7).

What this means operationally: an https-upgrade redirect, a moved path, or a
path-rewriting proxy in front of the gate surfaces as refusals rather than
as silent compliance. Point the SDK at the gate's final URL. **The rule
dates from 2026-08-20** — it was added after a mutation pass found the hole
in both shipped clients, so an SDK build older than that date does follow
redirects.

## LangChain: gate a tool in one call

For LangChain runtimes the embedding discipline ships pre-wired
(`declarant/pydeclarant/langchain_adapter.py`, optional — it imports
`langchain_core`, one of the two sanctioned exceptions to pydeclarant's
stdlib-only rule; the other is the MCP gate below, and `declare.py`,
`client.py`, and `gating.py` are stdlib-only):

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
  FRESH intent (episode seed = the idempotency key plus a per-invocation
  nonce — same-key retries never reuse an intent id), so the 500-edge
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

## MCP: gate a server you own — or one you don't

For MCP runtimes the same discipline ships as middleware
(`declarant/pydeclarant/mcp_adapter.py`, optional — it imports `fastmcp`,
the second sanctioned exception to the stdlib-only rule). Two entry points,
ONE gate implementation:

```python
from client import Client
from mcp_adapter import IntentGateMiddleware, gated_proxy

client = Client("http://127.0.0.1:8080")   # bounded by default (30s per call)

# (a) a server you OWN — attach the middleware
server.add_middleware(
    IntentGateMiddleware(
        client,
        intent_spec_hash=SPEC_HASH,    # content address of the attested spec
        scope="per-actor",
        run_id=agent_run_id,
        tools={"wire_transfer"},       # optional; omit to gate every tool
    )
)

# (b) a server you do NOT own — front it, unchanged
gated = gated_proxy(
    backend,                           # whatever fastmcp's create_proxy accepts
    client,
    intent_spec_hash=SPEC_HASH,
    scope="per-actor",
    run_id=agent_run_id,
)
```

`gated_proxy` attaches that same middleware to a proxy front end, which is
what makes it usable against a backend you cannot modify: the fronted server
never learns the gate exists, and **a refused call never reaches it at all**
— the gate declares and refuses before the pass-through fires. That is the
capability the framework adapter does not have, and it is the reason to
front a third-party MCP server rather than ask its owner to integrate.

- **Refusals arrive as `ToolError`.** The tool body runs ONLY on a fresh
  synchronous `Proceed`; every other outcome — `ShadowRecorded`,
  `Indeterminate`, the fail-closed `Unknown`, and the adapter-level
  `ALREADY_ACHIEVED` — raises `ToolError` with the body never called. MCP
  gives you no structured error channel, so the classification rides the
  message as literal substrings: `class=<CLASS>`, `terminal=`, `reason=`,
  and `retry_safe=<true|false>` (the §2.7 same-key retry position). Match on
  those, not on prose.
- **The `tools=` filter is opt-in narrowing, and an unlisted tool passes
  UNGATED.** The default (`tools=None`) gates every tool; naming a subset is
  the operator's explicit choice to leave the rest ungoverned. Pass a
  collection of names — a bare string is refused at construction, because
  `tools="wire_transfer"` is a collection of CHARACTERS that no tool name
  matches, which would silently leave everything ungated.
- **`strict_args`: a refusal you will meet in practice.** On the proxy path
  the gate sees a JSON Schema and no callable, so a call that OMITS a
  non-required property whose schema declares no default is REFUSED before
  anything is declared — the effective value is unknowable from a schema
  alone (a remote `default_factory` is invisible in JSON Schema), and
  guessing it would fork the idempotency key. The remedy is to pass the
  property explicitly. `strict_args=False` is the explicit opt-out, and it
  is a written acceptance that such a call is keyed AS SPELLED. A `required`
  property that is absent is refused in both paths regardless of this flag.
  Recorded residual, on the proxy path only: a genuine union
  (`anyOf`/`oneOf` with more than one non-null branch) is left as spelled,
  so two equivalent spellings of one value would fork the key — `CONTRACT.md`
  §2.7 records this as a standing fail-open.
- **Stateless deployment — replicas need no shared state.** The gate holds
  nothing between calls. The idempotency key is DERIVED from the action's
  identity, so a retry that lands on a different replica derives the same
  key and is refused just as correctly as on the original; each call still
  mints its OWN fresh episode seed (key + per-invocation nonce), so no
  intent id is ever redeclared. Run identity — `scope`, `run_id`,
  `intent_spec_hash` — is middleware CONFIGURATION, not session state:
  configure every replica identically and scale horizontally.

Like the LangChain adapter, the MCP gate is optional: on a host without
`fastmcp` its tests skip visibly and nothing else in the tree changes.

## Regulatory reporting (stdlib-only)

`reporting_adapter.py` gates report SUBMISSIONS. The plane never sees the
report; it keys the report's regulatory identity and refuses the second
submission of the same logical report however its bytes differ.

```python
from client import Client
from reporting_adapter import ReportIdentity, gate_submission, gate_batch, reconcile

client = Client("http://127.0.0.1:8080")
SPECS = {"VALU": VALU_SPEC_HASH, "EROR": EROR_SPEC_HASH}   # an erasure declares under a human-judgment spec

ident = ReportIdentity(reporting_entity=MY_LEI, uti=uti, action_type="VALU",
                       rule_set="ESMA-EMIR-REFIT-VR-1.4.0", as_of="2026-08-21")
done = gate_submission(ident, lambda: tr.submit(report_xml), client,
                       intent_spec_hash=SPECS, scope="per-actor", run_id=run_id)
# done.key is recomputable from `ident` alone; done.result is the TR's ack.

# Later, the auditor:
achieved, _ = client.poll_achieved(since=0)
print(reconcile(achieved, submission_log_identities, scope="per-actor", run_id=run_id).ok)
```

What it refuses before declaring anything: an unknown action type, an empty
base field, a discriminator the action type does not key on, a non-ISO
`as_of`, an action type with no mapped spec. What the gate refuses after
declaring: everything in the section 2.7 class table, including the
human-judgment abstention for erasures. `gate_batch` is one outcome per
record and promises no batch atomicity. The action-type table is
EMIR-Refit-shaped and must be verified against the current validation
rules before any production claim.

Normalize identity fields before you build a `ReportIdentity`. Leading or
trailing whitespace and non-NFC Unicode are refused before anything is
declared, but letter case is keyed as given: `529900T8BM49AURSDO55` and its
lowercase spelling derive two different keys, and a retry spelled the other
way is NOT refused as a duplicate. Case-folding is deliberately left to the
caller (`CONTRACT.md` §2.7, recorded residual) because the module cannot know
whether case is significant for your identifier scheme.

A CDM desk: `gate_cdm_event(step, ...)` reads the UTI and refs from the
`WorkflowStep` and returns the outcome as a `WorkflowStep` keyed by the
plane's idempotency key; pass your `Qualify_*` dispatch as `qualifier=` to
refuse a step whose declared intent is not what its instruction qualifies as.

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
