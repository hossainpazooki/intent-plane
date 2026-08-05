# ADR-0008 — the core is a minimal SDK; roles live in the application

- **Status: Accepted** (2026-08-05, operator ruling, mid-restructure — this
  ADR lands in the same change that implements it).
- Deciders: Hossain (operator).
- Relates: CONTRACT.md §1.1 (role seats), §7 (package boundary), ADR-0007
  (signed payloads), ADR-0009/R1 (key authority, pending), the 2026-08-03
  core/treasury repositioning design.

## Context

The 2026-08-04 plane-roles amendment landed the role system — signing
authority, key-ops CLI, drafting chassis — as top-level trees of this repo
(`plane/authority`, `control/`, `authoring/`), seated beside the core. The
operator's ruling: that is the wrong layer. **intent-plane is a minimal
library/wrapper/SDK for agentic deployments** — the authorization primitive
(declaration wire, deterministic tri-state fail-closed gate, idempotency,
durable observable feed, replay, scorer seam) plus the verification side of
trust. Applications built ON the plane — treasury is the first — add the
human-authority machinery: authors, attesters, per-action approvers, key
custody, promotion, approval workflow. Baking one application's role topology
into the core couples every future deployment to it and bloats the SDK's
surface with seats most deployments will fill differently.

## Decision

1. **The CORE is `core/` plus `plane/`.** `plane/` is the boundary artifact —
   envelope, payload, content-addressed store, hybrid resolver — and is
   verification-only: **the SDK verifies what applications sign, never the
   reverse.** The SDK holds no signing seat anywhere.
2. **The seats move under the application:** `treasury/authority` (every
   private-key operation), `treasury/control` (attest / publish / revoke /
   promote — the attester's seat, sole production importer of the signing
   package), `treasury/authoring` (drafting chassis). `treasury/` is a
   demonstration application, and its seat layout is one instantiation, not
   the pattern's definition.
3. **Core checks are name-free.** The contractcheck pins split: core packages
   are pinned exactly by table; application trees are pinned BY RULE — an
   application package may import only `plane` and its own tree; the core
   imports no application package in production or test code; within any
   tree, only `<tree>/control` may import `<tree>/authority`. Core
   neutrality (no application vocabulary under `core/`) is what keeps the
   rules name-free, and it mechanically caught the first draft of this very
   restructure hard-coding the application's name into core tables.
4. **Core tests sign locally.** Fixture signing in `core/cmd/server` and
   `plane` tests uses test-local helpers (`testKeyFile`), not the
   application's authority package — the previous test-only edges
   `core/cmd/server → authority` and `plane → authority` are deleted, not
   sanctioned.

## Consequences

- CONTRACT.md §1.1 role seats and §7 boundary text are rewritten to this
  layering; the pinned tables shrink to core-only and gain the generic
  application rules (both proven non-vacuous by plant-red: a core→application
  import and an authoring→authority import each fail the suite).
- The quickstart builds the control CLI from `treasury/control`.
- The four-role vocabulary (§1.1 declarant / author / attester / gate) is
  unchanged: the CONTRACT still defines what the roles MEAN — the ruling is
  about where their code seats live. The gate and declarant are the SDK's two
  parties; author and attester are application seats.
- A second application tree beside `treasury/` is governed by the same rules
  the day it appears, with no core amendment.
- The deployment half of key possession (workload identity, R2) and
  production key authority (ADR-0009) are untouched and stay future tense.
