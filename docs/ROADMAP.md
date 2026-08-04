# Roadmap — recorded intent, NOT built

Entries here are design intent with named blockers. Nothing in this file is
implemented; presenting any row as built is a status-honesty violation. Source:
the intent-plane gate spec §3 (R1–R4, adopted in intent only) plus session
findings. Fork F4's routing decision is recorded in `CONTRACT.md`
§3.3 (doctrine ahead of demonstration — G5).

## Roadmap entries (spec §3)

| # | Entry | Blocker |
|---|---|---|
| R1 | **Standard signing envelopes** (DSSE/in-toto bridge) for attestations | ADR-0009 production key authority (RRE ADR-0025, PR #19 — verified still OPEN 2026-08-02). Test keys stay and provenance keeps saying so until it lands. |
| R2 | **Workload identity** for role separation (SPIFFE-style) — makes P3 "cannot sign" a deployment-graph fact | Deployment-infrastructure decisions outside this repo. Until R2, key-possession separation is documented, never claimed "enforced". |
| R3 | **Shadow mode as a signed authority state** — enforcement posture inside the spec payload | Canon-bump territory; needs its own ADR (ADR-0021 precedent). **Config-toggled shadow mode is explicitly forbidden — it is a bypass.** |
| R4 | **OTel trace emission as index** ("logs index, gates decide") | Permitted only if trivially additive; the durable record remains sole authority. Not exercised this session. |

## Findings (recorded production-posture gaps)

| Finding | Status | Consequence until closed |
|---|---|---|
| `force_scores` is a wire-reachable, unguarded total scoring bypass (`core/cmd/server/main.go` handleIntents; sanctioned by CONTRACT.md §2.2/§2.5, pinned by `TestForceScoresStillWins`) | documented test affordance; **no env/build/auth guard** | Qualifies "unevaluable never passes", "fail-closed twice", and "artifacts are the only crossings" in any production claim. Guarding it is a contract change — needs its own amendment. |
| Feed read surface (`GET /v2/events`, `GET /v2/intents/{id}/events`) is unauthenticated | by design (emit-and-observe) | Any network peer can read all ACHIEVED trace fields. A deployment posture decision, not a code defect — record it in any deployment doc. |
| Thinned-set blindness: the gate cannot see that a spec carries fewer criteria than its source document requires | structural (P1 not yet enforced) | Belongs to the ATLAS-side minimum-criteria/coverage invariant + the resolver-extraction slice. `CONTRACT.md` §4.2 step 1b closed the *vacuous* case only. |
| Criteria are declarant-supplied (P1 asserted, not enforced) | recorded parity debt (`GOLDEN_PAYMENT_CONFIG`, COMPASS side) | Closed by the **resolver-extraction slice**: criteria/thresholds read from the verified IntentSpec payload via `intent_spec()` / `iter_criteria()` — also retires the ADR-0003 float-threshold wire debt. |
| Empty-string and duplicate criterion NAMES pass the thin-spec defense and can ACHIEVE (2026-08-02 skeptic finding) | recorded, not built | These criteria ARE consulted against the scorer (a live scorer fails closed on unknown names), so they are not vacuous grants — but they are "thin" in a sense step 1b does not cover. Name-shape validation belongs with the resolver-extraction slice, where names come from the verified payload instead of the declarant. |
| Wire fixtures carry treasury names | open | `core/contract/scorer/*.json` pin `"criterion":"balance"`; exempt from `TestCoreNeutrality`. Follow-up: regenerate with neutral exemplar names in one change that re-greens BOTH byte-compare lanes. |
| Citation and comment polish backlog (2026-08-04 whole-branch review) | open | Small non-behavioral items bundled so they don't scatter: neutrality-test header note for the regex-invisible `intentspec_payment` carve-out; `key-pay-1` test-literal rename (bundle with fixture neutralization); `regexp.Find` -> `FindAll` in the neutrality gate (report all violations, not the first); stale comment cites (`main_test.go` `TestForceScoresStillWins` says §2.4, is §2.2/§2.5; `acceptance_test.go:3` external `§12` anchor; three chain-era phrasings in CONTRACT.md); README invariant list numbering is a restatement, not §5.1's order — add a one-line note; design doc §9 acceptance counts are capture-time (41/5, 46/46) — pointer to the 2026-08-04 handoff for measured values (42/5, 47/0). |

## Next slices (carried from the 2026-07-13 handoff, still current)

1. Durable KV/Postgres settlement-ledger adapter (COMPASS side).
2. Resolver-extraction slice (closes P1 gate-side; kills two recorded debts).
3. CI wheel-lane job (Linux, pinned `SCORER_ATLAS_DIR`; make `_wheel_lane()`
   skip-with-reason on absent fixture).
