# ADR-0007 — plane.SpecPayload is THE signed object

- **Status: Accepted** (2026-08-05, operator ruling — option (a) of the
  whole-contract review's finding A).
- Deciders: Hossain (operator).
- Relates: CONTRACT.md §2.6, ROADMAP resolver-extraction rows, ADR-0003
  (float-threshold debt), ADR-0009/R1 (key authority, pending).

## Context

After the plane-roles amendment the repo carried two candidate "signed
objects": the plane's own `SpecPayload` (DSSE envelope, gate-side resolution,
test key authority) and the ATLAS-published `IntentSpec` artifact (wheel-
verified scorer-side, `rule_artifact_hash` provenance, the original
resolver-extraction target). The pitch's first commitment — "one signed
object, not three systems" — is undermined if the plane itself grows two
spec systems with an unstated relationship.

## Decision

1. **`plane.SpecPayload` is the single spec representation the intent plane
   executes.** The ATLAS `IntentSpec` integration path is RETIRED as a
   criteria source: the ROADMAP's resolver-extraction slice (scorer-side
   `intent_spec()` / `iter_criteria()` reading criteria from the ATLAS
   artifact) is superseded by §2.6 resolution and will not be built.
2. **`rule_artifact_hash` remains** as opaque provenance for the upstream
   RULE artifact (the regulatory source the spec was drafted FROM); it is a
   pointer into the artifact plane, not a second spec channel. The authoring
   chassis's `source_pins` are the in-payload half of that provenance.
3. **The scorer keeps its seam unchanged**: it receives criteria from the
   gate per `/ml/evaluate` request (§2.4) and never resolves specs itself.
   The scorer-side `KeArtifactResolver` / wheel lane remains what it is
   today — verification of the ATLAS artifact when configured — and is no
   longer on the critical path to P1.

## Consequences

- ROADMAP rows referencing resolver-extraction as P1's closer are reworded
  to cite §2.6; the residuals that slice carried move to their own homes:
  criterion NAME-shape validation now belongs to `plane.ParseSpecPayload`
  (open, recorded), and the ADR-0003 float debt moves INSIDE the signed
  payload (see below).
- **Numeric representation trigger (binding):** `CriterionSpec.Threshold` is
  `float64` today — the ADR-0003 exactness debt now lives in content-
  addressed signed bytes, where migration means re-attesting every spec
  under new hashes. Therefore: **before ADR-0009 production key authority
  lands (R1) — i.e. before any non-test attestation exists — the payload
  schema moves to exact decimal strings** (conversion to float64 happens at
  resolution, documented as the lossy step, until the internal path follows).
  Rationale for deferring the schema change today: every existing spec is
  test-authority and disposable; the trigger is pinned here so R1 cannot
  land without it.
- COMPASS/ATLAS cross-repo docs that describe IntentSpec as this plane's
  spec source are stale by this ruling; correcting them is an out-of-repo
  operator follow-up.
