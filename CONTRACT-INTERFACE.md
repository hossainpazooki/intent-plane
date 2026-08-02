# CONTRACT-INTERFACE — the intent interface (amendment, 2026-08-02)

Amends `CONTRACT.md` (slice 1) and `CONTRACT-DURABILITY.md` in the repo's
amendment-file convention: **where this file and an earlier contract name the
same thing, this file wins.** Everything not named here is unchanged. Source:
the "Intent Plane — gate implementation spec" session (premise clauses P1–P7;
build items B1–B4; forks F2/F4/F5 ruled by the operator, recorded here).

## §I.0 Role vocabulary (W1)

Four roles, and only these, for actors in normative text:

| Role | Meaning |
|---|---|
| **declarant** | the caller that declares an intent (`POST /v2/intents`) and consumes verdicts / the completion feed |
| **author** | the drafting function (authoring plane); proposes IntentSpecs, holds no keys, cannot sign/publish/activate |
| **attester** | the human author of record; what they sign is what the gate is meant to execute |
| **gate** | this repo's deterministic core; sole ACHIEVED authority |

Pre-existing non-actor senses (HTTP "client", Go-doc "caller", build-meta
"agent"/"owner") stay as they are. Mechanically enforced by
`internal/contractcheck/vocab_test.go` (required presence + forbidden list).

## §I.1 The intent interface (public surface)

The gate's ONLY public surface, in full:

1. `POST /v2/intents` — declaration in; verdict record out (`terminal`,
   `reason`, `trajectory_hash`, `achieved_seq`).
2. `GET /v2/events?since=&type=` — the completion feed, cursor read. A
   **by-design gate-free read** (emit-and-observe); note it is unauthenticated
   (deployment posture, see ROADMAP findings).
3. `GET /v2/intents/{id}/events` — per-intent records.
4. `GET /healthz`.

Plus two non-HTTP wire surfaces: the durable feed's JSONL record format
(`durable.Record` JSON tags, §V2.1) and the `/ml/evaluate` scorer seam
(CONTRACT-SCORER). No Go symbol is public API: every package except
`cmd/server` lives under `internal/`.

**`force_scores`** (CONTRACT-SCORER §S.0/§S.3) remains the documented test
affordance, preserved verbatim — and remains a wire-reachable total scoring
bypass with no env/build/auth guard. That is a recorded **production-posture
gap** (see ROADMAP): it qualifies "unevaluable never passes", "fail-closed
twice", and "artifacts are the only crossings" until guarded. Removing or
guarding it is a contract change; this amendment records, it does not build.

## §I.2 Boundary (B1)

The intra-repo import adjacency and the package set are **pinned** by
`internal/contractcheck/boundary_test.go` (stdlib `go/parser`; runs inside the
named gate). Production edges: leaves {intent, lifecycle, audit, durable};
adapter/idempotency/scoring → intent; gate → {audit, durable, idempotency,
intent, lifecycle, scoring}; cmd/server → {durable, gate, idempotency, intent,
scoring}. Sanctioned test-only extras: gate_test → adapter (+lifecycle),
server_test → lifecycle. **Adding a package or an edge means amending this
contract first**, then the pinned tables — never the reverse.

## §I.3 Thin-spec defense (B2/B2b) — gate algorithm step 1b

Inserted after the absent-key refusal, before any lifecycle transition or
scoring. Spec resolution today happens at declaration decode; these checks
belong to **resolution** and move with it if resolution ever moves (the pinned
property, not the seat: *a resolved spec with zero criteria never reaches
ACHIEVED, regardless of where resolution happens*).

- **Empty criteria** (`len(Spec.Criteria) == 0`, nil and empty alike):
  append `UNEVALUABLE` with detail `empty-criteria:<intent_spec_hash>` (the
  refusal record witnesses WHICH claimed spec was thin; blank hash ⇒ bare
  `empty-criteria:`), terminal `FAILED`, reason `unevaluable:empty-criteria`.
  The scorer is never consulted.
- **Unknown volatility** (neither `stable` nor `volatile`, including blank /
  field omitted): append `UNEVALUABLE` with detail
  `invalid-volatility:<name>:<raw>`, terminal `FAILED`, reason
  `unevaluable:invalid-volatility:<name>`. Closes the P4-adjacent stale-pass
  hole where a typo'd `volatile` silently became stable and skipped the
  dispatch-edge re-verify. **Behavior change on the wire**: a criterion with
  omitted/blank volatility previously scored as stable; it now refuses.

**Invariant 2, restated non-vacuously** (supersedes the CONTRACT.md wording
"`allPassed` ⟺ every criterion `Pass`", which is satisfied by an empty set):

> Authorized ⟺ the criteria set is **non-empty**, every criterion is
> validly shaped, and every criterion scores `Pass` (volatile ones again at
> the dispatch edge). "No criterion failed" is never satisfied by "no
> criterion existed."

The scorer-side twin of this guard is `scorer/src/tis/resolver.py`'s
hashless-verify refusal (`all([]) is True` would be fail-open).

**Out-of-domain scores fail closed** (added after the 2026-08-02 skeptic pass
refuted the totality claim at the injectable-Scorer seam): `scoring.Score` is
an open int; the declaration switch treats anything that is not exactly `Pass`
or `Fail` as unevaluable — mirroring the dispatch edge's exact-Pass check.
Before this, a custom Scorer returning `Score(3)` fell through as an implicit
pass, yielding the self-contradictory log `SCORED <name>:UNEVALUABLE` →
`ACHIEVED`. Unreachable via any in-repo scorer; closed anyway (pinned by
`TestFailClosedOutOfDomainScore`, red-first).

**Honesty bounds.** B2 closes the *vacuous* case only: a **thinned** set
(three criteria where the source document requires five) is structurally
invisible gate-side and belongs to the ATLAS-side minimum-criteria/coverage
invariant. B2b closes the *typo* case only: a criterion semantically
mislabeled stable is authoring/attestation territory the string cannot
reveal. Every gate-side `unevaluable:empty-criteria` event is evidence a spec
escaped compile that shouldn't have — a measurable cross-repo signal.

Pinned by: `internal/gate/acceptance_test.go` (`TestFailClosedEmptyCriteria`,
`TestFailClosedInvalidVolatility`) and `cmd/server/main_test.go`
(`TestEmptyCriteriaRefusedOverWire`, `TestInvalidVolatilityRefusedOverWire`) —
all four demonstrated red against the pre-amendment gate (2026-08-02), then
green.

## §I.4 FAILED_AT_DISPATCH cause classes (F4)

`FAILED_AT_DISPATCH` names **where the error entered** — the dispatch edge —
via a closed set of reason cause classes:

| Cause class | Meaning | Status |
|---|---|---|
| `volatile-recheck:<name>` | volatile fact drifted between scoring and dispatch | built |
| `idempotency-collision` | key already reserved (near-duplicate) | built |
| `revoked:<ref>` | the pinned spec was revoked between verification and dispatch | **reserved — doctrine ahead of demonstration (G5): no revocation signal reaches the gate today; routing decision recorded so the terminal set stays closed when one does** |

A future revocation signal routes here, not to a new terminal: revocation
observed at the edge IS a volatile-fact drift. Adding any other cause class
means amending this table first.

## §I.5 Public terminology (F5)

**`ACHIEVED` is the public API term** for the gate's success terminal — wire
values (`terminal`, feed record `type`, accepted `?type=` query), field names
(`achieved_seq`), exported identifiers, and the cross-repo trace contract all
speak it. `COMPLETED` is not used anywhere in this repo and MUST NOT be
introduced; buyer-facing prose (the pitch) yields to the wire, not the
reverse.

## §I.6 What this amendment does NOT change

No new artifact kinds; no IntentSpec payload changes (canon-bump territory);
no route added, removed, or reshaped; the ACHIEVED record path (`gate.go`
step 5) untouched; `force_scores` untouched; the adapter, durable, scoring,
idempotency, audit, lifecycle packages untouched.
