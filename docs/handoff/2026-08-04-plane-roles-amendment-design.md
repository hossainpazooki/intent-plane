# Design — plane roles amendment: signed specs, role trees, shadow posture

- Date: 2026-08-04. **Status: Implemented** (this doc entered the tree as part
  of the diff it describes; it was the in-chat contract for the build, not a
  pre-approval gate).
- Base: `bec7589` (main). All work uncommitted at handoff — zero agent
  commits; the operator commits.
- Companion: `docs/handoff/2026-08-04-intent-plane-repositioning.md` (framing),
  `docs/research/2026-08-04-intent-plane-consumer-research.md` (demand map —
  see Appendix A), `docs/adr/2026-08-04-ADR-0006-shadow-recorded-terminal.md`
  (Proposed).

## Contents

1. [Scope decision](#1-scope-decision)
2. [The three role trees](#2-the-three-role-trees)
3. [The signed artifact](#3-the-signed-artifact)
4. [Spec store and the hybrid resolution rule](#4-spec-store-and-the-hybrid-resolution-rule)
5. [Gate amendments](#5-gate-amendments)
6. [Wire amendments](#6-wire-amendments)
7. [Guards and witnesses](#7-guards-and-witnesses)
8. [What this did NOT make true](#8-what-this-did-not-make-true)
9. [Verification record](#9-verification-record)
- [Appendix A — consumer-research demand map](#appendix-a--consumer-research-demand-map)

## 1. Scope decision

Everything claimable in-repo is built and pinned; everything that is a
deployment-graph or external-authority fact is tense-fixed, not claimed:
production key authority (ADR-0009/R1), workload identity (R2), and the
drafting AI that fills the authoring seat all stay future tense. Spec
distribution is **hybrid**: the store is authoritative; a wire envelope is
accepted iff verified AND pinned.

## 2. The three role trees

Top-level packages, adjacency pinned in `boundary_test.go`:

- `plane` — envelope, payload types, store, resolver. **Verification only**
  (public keys). `core/cmd/server → plane` is the gate's only new edge.
- `plane/authority` — every private-key operation (keygen, sign, attest,
  tombstone). Production-importable ONLY from `control/`; the key-possession
  boundary (`TestKeyPossessionBoundary`) walks the whole tree and makes
  "authoring and the gate cannot sign" an import-graph fact. Honest scope:
  the IN-REPO half of P3; the deployment half is R2, asserted.
- `control` — CLI: keygen, root, attest, publish, revoke, promote. Promote
  refuses non-shadow drafts and re-attests with posture flipped: a NEW hash,
  because promotion is an authority act.
- `authoring` — CLI: deterministic drafting chassis. Quantified+mapped
  provisions → criteria with `source_pins` (sha256 of the exact passage);
  unmapped → `named_unknowns` (surfaced, never silently omitted);
  deliberately-unquantified → `human_judgment` (the gate refuses these:
  abstention as a success state). Drafts default to shadow posture. The
  drafting INTELLIGENCE is not in this repo; the chassis around the seat is.

## 3. The signed artifact

DSSE-shaped envelope (PAE v1, ed25519, stdlib only): payloadType
`application/vnd.intent-plane.spec+json`, payload = base64 of the raw spec
bytes, signatures carry `keyid` (16-hex sha256 prefix of the pubkey) and
`key_authority: "test"` — the stamp stays until ADR-0009 lands, and the
provenance keeps saying so. `intent_spec_hash` = sha256 over the raw payload
bytes: "what the officer attested is what the gate executes, byte for byte"
is a hash equality (`TestTamperedPayloadRefuses` flips one byte and watches
verification refuse). Revocation tombstones are envelopes too
(`.../revocation+json`): revocation is an authority act; a stranger-signed
tombstone does not revoke (`TestForgedTombstoneDoesNotRevoke`).

## 4. Spec store and the hybrid resolution rule

`INTENT_SPEC_DIR` (default `<data>/specs`): `<hash>.env.json`, `<hash>.pin`,
`<hash>.revoked.json`. No wallclock anywhere. Publish is verify-then-write.
Resolution: tombstone → `RevokedError`; store envelope (verify + hash
equality) → source `store`; wire envelope → source `wire` iff verified
against the SAME root AND pinned; else `ErrUnattested`. The zero-config
server (no `INTENT_TRUST_ROOT`) has an empty root: every spec is unattested
and the gate refuses everything — the same fail-closed boot posture as the
scorer.

## 5. Gate amendments

New declaration defenses, in order (each red-first): 1a2 revocation-at-
resolution (`revoked:<ref>` WINS over unattested — ordering bug found by the
end-to-end smoke, not by unit tests; pinned by
`TestRevokedResolutionWinsOverUnattested`), 1a3 attestation
(`unevaluable:unattested-spec`, scorer never consulted), 1a3b live-checker
revocation, 1a4 posture (`unevaluable:invalid-posture`; the zero value never
defaults to enforce), 1a5 human judgment
(`unevaluable:human-judgment:<name>`). Dispatch edge: 4a2 revocation
re-check (activates the reserved §3.3 cause class; key NOT reserved), 4a3
shadow terminal (`SHADOW_RECORDED`: fully scored, durable record with trace
fields, no ACHIEVED, no reservation — ADR-0006, Proposed). `Gate` gained a
variadic `Option` (`WithRevocations`, `WithScorerID`); existing call sites
unchanged.

## 6. Wire amendments

`specDTO` is `{idempotency_scope}` only — criteria, action class, and posture
have NO wire fields, so `DisallowUnknownFields` turns the old client shape
into a loud 400: P1 closed at the type level. New optional `spec_envelope`
(raw JSON) is the hybrid wire path. All twelve wire tests rewritten around an
attest-then-declare flow; the thin-spec and invalid-volatility probes became
attested-but-defective specs, proving attestation does not launder vacuity.

## 7. Guards and witnesses

`force_scores` is honored only when the server booted with
`INTENT_UNSAFE_FORCE_SCORES=1`; otherwise carrying it is a 400 — never a
silent ignore. Every SCORED/RECHECK feed record carries `scorer_id`
("forced" | "live"): a forced grant is never byte-indistinguishable from a
live-scored one. The witness is feed-level and hash-exempt like `GlobalSeq`;
determinism-conditional-on-scores holds over every other field byte-for-byte
(the carve-out is explicit in `TestDeterminismConditionalOnScores`).

## 8. What this did NOT make true

- **Production key authority.** Keys are files on disk; `key_authority` says
  "test" everywhere. ADR-0009 / R1 remains the blocker.
- **The deployment half of P3.** Workload identity (R2) is untouched; the
  import graph proves what the CODE cannot do, not what a deployment cannot.
- **The drafting AI.** `authoring` is the chassis; nothing in this repo reads
  free-text policy prose.
- **The verifier package.** The independent Go+Python feed verifier, the
  refusal-hash commitment, the declarant SDK, and the golden feed fixture
  remain the daily-driver seed (S1–S5), untouched.
- **Thinned-set coverage.** The gate now proves criteria came from a signed
  payload; it still cannot see that the payload covers fewer obligations than
  its source document requires (ATLAS-side invariant).
- **The scorer-side twin.** Python `intent_spec()` / `iter_criteria()` and
  the ADR-0003 float-threshold debt remain the resolver-extraction slice.
- **ADR-0006 ratification.** SHADOW_RECORDED is implemented and pinned;
  the ADR is Proposed. It is not settled practice until ratified.
- **quickstart.ps1 execution.** Amended in parallel with the sh twin but NOT
  executed this session (no PowerShell on the build host).

## 9. Verification record

Capture-time measurements (re-measure, don't trust): `go test ./...` fully
green including `contractcheck` (import boundary re-pinned for the four role
trees + `TestKeyPossessionBoundary`); scorer pytest 42 passed / 5 skipped
(untouched); end-to-end smoke 8/8 paths (human-judgment refusal, shadow,
promoted-enforce ACHIEVED, unattested, legacy-wire 400, revoked with correct
cause, scorer_id witness, force_scores guard); treasury quickstart.sh 8/8
against the LIVE Python scorer. One bug was found by the smoke and not by
unit tests (the revoked/unattested cause ordering) — the unit suite's
mkIntent default (`Attested: true`) hid the server-path shape; recorded here
because that gap pattern (test defaults masking integration shapes) recurs.

## Appendix A — consumer-research demand map

Keyed to `docs/research/2026-08-04-intent-plane-consumer-research.md`
(GitHub: `docs/research/2026-08-04-intent-plane-consumer-research.md` on
`hossainpazooki/intent-plane`), §4 demand rows and §5 open questions.

**Closed by this amendment:**

| Memo demand | Disposition |
|---|---|
| P1 — "what the pitch trips over in the first diligence meeting" | Closed gate-side at test key authority: no criteria field on the wire; resolution = signature + content address; unattested refuses before scoring. |
| Cheapest-server-wins: scorer-identity witness | Built as `scorer_id` on SCORED/RECHECK feed records (hash-exempt, feed-level). |
| `force_scores` guard | Built: boot-env guard + loud 400 + witness. The memo's guard+witness pairing (Q1) is exactly what landed. |
| R3 shadow rollout | Built behind ADR-0006 (Proposed): posture in the signed payload, promotion = new attestation. |

**Deferred to the daily-driver seed (S1–S5), deliberately untouched:**

| Memo demand | Where it lives |
|---|---|
| Verifier package (Go+Python twins, tri-state VERIFIED/REFUTED/UNVERIFIABLE, zero server changes) | Seed S1 — the memo's "verifier package first" sequencing is preserved; this amendment is the SERVER half and does not preempt it. |
| Refusal-hash commitment | Seed S2 (the witness half of S2 landed here; the commitment half did not). |
| Declarant SDK | Seed S4. |
| Golden feed fixture under `core/contract/feed/` | Seed S1/Q4. |

**Open-question annotations (memo §5):**

- **Q1 (guard vs witness):** settled — BOTH, as staked in the seed; now
  built.
- **Q2 (refusal-hash commitment):** still open; nothing here forecloses it.
- **Q3 (scope folded into key):** untouched by this amendment.
- **Q4 (fixture location):** untouched; the smoke artifacts in `/tmp` were
  deliberately NOT committed as fixtures to avoid preempting the Q4 layout.
- **Q5 (in-repo verifier + import-boundary gate):** the boundary machinery
  this amendment extended (`allowedProd` role trees) is the natural home for
  the verifier's import gate when S1 lands; no decision taken.
