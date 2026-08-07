# Integration — what a platform team embeds

For the team that owns how agents call tools. You embed the gate once at the
framework layer and every agent inherits it: declare the intent, await the
terminal, proceed on `ACHIEVED` or surface the refusal.

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
   exactly-once property. Never too coarse — reservations are permanent, so
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
