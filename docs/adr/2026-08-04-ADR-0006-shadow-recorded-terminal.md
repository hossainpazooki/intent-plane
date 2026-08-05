# ADR-0006 — SHADOW_RECORDED: shadow mode as a signed authority state

- **Status: Proposed** (2026-08-04). Implemented and mechanically pinned, NOT
  ratified. Until ratification, SHADOW_RECORDED may not be quoted as settled
  practice in positioning or external docs; the implementation exists so the
  decision can be judged against running code rather than prose.
- Deciders: (unratified)
- Amends: CONTRACT.md §3.1/§3.2 (terminal set), §4.2 step 4a3.
- Implements: ROADMAP R3. Forbidden alternative: config-toggled shadow mode.

## Context

R3 requires a rollout posture where a new spec's decisions are observable
before they gate anything. Every config-toggle shape (`SHADOW=1`, a header, a
per-request flag) is a bypass: it lets the enforcement decision be changed by
whoever controls the config, outside the signing authority, invisibly to the
feed. The plane's whole premise is that authority travels only inside signed
artifacts.

## Decision

1. Enforcement posture is a field INSIDE the signed spec payload
   (`enforcement_posture: enforce | shadow`). It is part of the bytes the
   content address seals: changing posture changes the hash.
2. A shadow-posture intent runs the FULL gate algorithm — declaration scoring,
   dispatch-edge volatile recheck, dispatch-edge revocation recheck — and then
   terminates in a new terminal, `SHADOW_RECORDED`: one durable record with
   the four trace fields, no ACHIEVED event, no idempotency-key reservation,
   nothing settles. The record answers "what WOULD this spec have done" with
   feed-grade evidence.
3. Promotion shadow→enforce is `control promote`: a NEW attestation over NEW
   payload bytes yielding a NEW hash. The shadow artifact remains exactly what
   it was; enforcement is a fresh authority act by the signing key.
4. An unknown or absent posture refuses (`unevaluable:invalid-posture`): the
   zero value never silently becomes enforce.

## Consequences

- The terminal set grows to four; every consumer switch over terminals must
  handle SHADOW_RECORDED (it is `IsTerminal() == true`).
- Authoring defaults new drafts to shadow: enforcement is the attester's
  promotion decision, never the author's default.
- The key NOT being reserved under shadow means a shadow run and a later
  enforce run may share an idempotency key by design
  (`TestShadowPostureRecordsWithoutAuthorizing` pins this).

## Mechanical pins

`lifecycle/transitions_test.go` (edge canon), `TestShadowPostureRecordsWithoutAuthorizing`,
`TestInvalidPostureRefuses`, `control promote` (refuses non-shadow drafts),
end-to-end smoke + treasury quickstart shadow leg.

## Ratification criteria (open)

- The consumer-side story for SHADOW_RECORDED records (who reads them, what a
  promotion review looks like) is exercised at least once outside tests.
- No second posture value is needed within one review cycle (guards against
  the enum growing into a config surface by increments).
- **Idempotency fidelity (added 2026-08-05, whole-contract review):** shadow
  short-circuits BEFORE the reserve step, so a shadow intent whose key is
  already reserved records SHADOW_RECORDED as if it would have authorized —
  when enforce posture would have collided. "What would this spec have done"
  is currently true modulo the idempotency dimension. Before ratification,
  either add a read-only collision check that writes `would-have-collided`
  into the SHADOW_RECORDED detail, or state the optimism explicitly in §3.2.
