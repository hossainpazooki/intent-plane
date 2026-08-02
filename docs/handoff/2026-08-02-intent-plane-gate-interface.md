# Handoff — intent-plane gate session: thin-spec defense + interface contract

2026-08-02. Base commit this session built on — measure drift from it:
**tic `93d2a6d`** (main, in sync with origin at session start; tree was clean).
All work is UNCOMMITTED at handoff (zero commits, per spec §6/§7); the diff is
the deliverable, commit commands emitted to the operator. Governing document:
the "Intent Plane — gate implementation spec" (PROPOSED, supplied in-session).
Program memory: `treasury-intent-loop`.

**Input gap, recorded:** the spec's companion migration seed
(`2026-07-22-seed-intent-plane-migration.md`) was not on disk and was never
provided; the pitch WAS provided inline mid-session. Forks F1–F3 and W1 were
taken from the spec's own summaries (the spec declares itself winner on
conflict). If the seed surfaces, diff its W1 tables against
CONTRACT-INTERFACE §I.0 before trusting the vocabulary gate's forbidden list.

## Current state

- **[built] B2 thin-spec defense** — gate step 1b (`internal/gate/gate.go`,
  after the absent-key refusal): zero criteria (nil ≡ empty) ⇒ FAILED
  `unevaluable:empty-criteria`, UNEVALUABLE detail `empty-criteria:<spec-hash>`
  (binds WHICH claimed spec was thin; blank hash ⇒ bare `empty-criteria:`);
  scorer never consulted. **Red-first demonstrated**: all probes FAILED against
  unmodified `93d2a6d` (recorded 2026-08-02T16:58:38Z — the wire probe's red
  output shows the durable feed holding two full-trace ACHIEVED records for
  zero-criteria bodies on a ZERO-CONFIG server), then green after the fix.
  re-verify: `go test ./internal/gate -run 'TestFailClosedEmptyCriteria' -count=1 -v`
  and `go test ./cmd/server -run 'TestEmptyCriteriaRefusedOverWire' -count=1 -v`
- **[built] B2b unknown-volatility refusal** — same seat: volatility ∉
  {stable, volatile} (incl. blank/omitted) ⇒ FAILED
  `unevaluable:invalid-volatility:<name>`, detail
  `invalid-volatility:<name>:<raw>`. Red-first: pre-fix, a typo'd "volatil" +
  passing scorer reached ACHIEVED with ZERO RECHECK events (the stale-pass
  hole). **Wire-behavior change**: omitted/blank volatility previously scored
  silently as stable; now refuses. Honesty bound: typo case only — semantic
  mislabeling is authoring/attestation territory.
  re-verify: `go test ./internal/gate -run 'TestFailClosedInvalidVolatility' -count=1 -v`
- **[built] B1 boundary check** — `internal/contractcheck/boundary_test.go`
  (test-only package, stdlib go/parser): pins the package SET and the
  production import adjacency; sanctioned test-only edges pinned separately;
  any new package outside internal/ (except cmd/server) fails. Passed against
  reality on first run (adjacency was already clean).
  re-verify: `go test ./internal/contractcheck -run TestImportBoundary -count=1 -v`
- **[built] B3 vocabulary gate** — `vocab_test.go`: declarant/attester/gate
  required in README + CONTRACT-INTERFACE.md; the two forbidden actor nouns
  (named only in the gate's own pattern, deliberately not here — quoting them
  in any .md is itself a hit, which is how the gate proved its non-vacuity by
  catching this brief's first draft) pinned at zero repo-wide. Sweep basis:
  declarant/attester/author-as-noun had ZERO
  occurrences (migration = introduction, not rename); existing
  client/caller/agent/owner/user hits are non-actor senses, audited and
  deliberately NOT gated (a gate stricter than reality only false-positives).
  re-verify: `go test ./internal/contractcheck -run 'TestRoleVocabulary|TestForbiddenActorNouns' -count=1 -v`
- **[built] B4 docs** — `CONTRACT-INTERFACE.md` (new amendment file: §I.0
  roles, §I.1 public surface, §I.2 boundary, §I.3 step 1b + invariant-2
  restated non-vacuously, §I.4 FAILED_AT_DISPATCH cause classes incl. reserved
  `revoked:` [F4, G5-labeled], §I.5 ACHIEVED is the public term [F5]);
  README premise-mapping table (P1–P7, clause → file:line, honest
  "asserted, not enforced" for P1/P3) + refusal edge in the mermaid;
  `docs/ROADMAP.md` (R1–R4 with blockers + findings); CLAUDE.md invariants
  7–8; learnings entry `2026-08-02-vacuity-asymmetry-gate-vs-resolver.md`.
- **[verified] Full acceptance (spec §6), all fresh-run this session:**
  - Native: `go build ./... && go vet ./... && go test ./... -count=1` — all ok
    (incl. contractcheck).
  - WSL: `go test ./... -count=1 -race` — all ok.
  - Scorer: Windows `.venv/Scripts/python -m pytest -q` → 41 passed/5 visible
    skips; WSL `python3 -m pytest -q` → 46 passed, zero skips (wheel lane
    executed; sibling RRE checkout on `docs/adr-0024-acceptance-stamp` carries
    the fixture).
  - Byte-determinism: `TestDeterminismReplay` green; `git diff --stat
    contract/ scorer/` empty (fixtures + Python side byte-untouched).
- **[built] Out-of-domain-score fail-closed** (post-skeptic fix): the
  declaration scoring switch now refuses anything that is not exactly
  Pass/Fail (default arm = unevaluable), mirroring the dispatch edge's
  exact-Pass semantics. Found by the skeptic pass refuting the totality claim
  at the injectable-Scorer seam: a custom Scorer returning `Score(3)`
  previously fell through as an implicit pass — log read
  `SCORED c1:UNEVALUABLE` then `ACHIEVED`. Unreachable via any in-repo scorer
  or the wire; closed anyway, red-first.
  re-verify: `go test ./internal/gate -run TestFailClosedOutOfDomainScore -count=1 -v`
- **[skeptic pass, 4 claims]** totality PARTIALLY (refuted at the
  injectable-Scorer seam → fixed above; empty-name/duplicate-name criteria
  recorded as ROADMAP finding, not fixed — they ARE scorer-consulted, so not
  vacuous); no-weakening SURVIVES (diff pure-additive, 0 deletions); byte-
  determinism SURVIVES (old-vs-new harness: identical Events+TrajectoryHash on
  valid, decl-fail, decl-unevaluable, dispatch-fail paths); fixtures-untouched
  SURVIVES (`git status --porcelain -- contract/ scorer/` empty).
- **[not done / not in scope]** force_scores guarding (recorded finding),
  resolver-extraction slice, KV ledger, CI wheel lane, anything R1–R4.

## Locked decisions (this session, operator-ruled)

- **F2**: empty-criteria refusal lives at *resolution* (today = declaration
  decode) and moves with resolution; the probe pins the property, not the
  seat. Reason tag `unevaluable:empty-criteria` reconciled and hardcoded.
- **F4**: mid-flight revocation → FAILED_AT_DISPATCH, reserved cause class
  `revoked:<ref>` (CONTRACT-INTERFACE §I.4). Record-only; no revocation signal
  reaches the gate today (doctrine ahead of demonstration).
- **F5**: ACHIEVED stays the public API term; the pitch yields (edit list
  below). COMPLETED must never be introduced.
- Spec §3 R1–R4 adopted in intent only; R3's config-toggled shadow mode is
  explicitly forbidden as a bypass.

## §4 pitch-viability register, re-audited

| Pitch claim | Was | Now | Pitch edit required |
|---|---|---|---|
| Unevaluable never passes | built (vacuous-set exception live) | **strengthened** — empty-criteria + typo'd-volatility cases closed; thinned-set + semantic drift remain ATLAS-/authoring-side | annotate "strengthened", NOT "closed"; add force_scores qualifier |
| Fail-closed twice / stale PASS cannot authorize | built | built (B2b also closed the volatility-typo recheck skip) | add force_scores qualifier |
| One byte-exact event | built | built — record path untouched, determinism re-verified | none |
| Spokes never touch / artifacts-only crossings | partially true | mechanically pinned gate-side (B1), *modulo force_scores* | add force_scores qualifier |
| **Gate executes attester-signed spec (P1) — NEW ROW** | (claimed built in pitch prose) | **not yet true**: declarant supplies criteria (`main.go:173`); hashes opaque; closer = resolver-extraction slice | **tense-downgrade the two central sentences** (below) |
| Key possession separation | asserted (deployment) | asserted; documented in README P3 row | keep future tense until R2 |
| Standard signing envelopes | design intent | roadmap R1 (ADR-0025 PR #19 verified OPEN 2026-08-02) | none (tense already future) |
| Signed shadow-mode rollout | design intent | roadmap R3; config-toggle forbidden | none |
| Abstention is the system working | built (gate substrate) | built | none |
| Officer is author of record | built (attestation path, ATLAS-side) | built | none |

**Enumerated pitch edits** (pitch not in repo; apply to the HTML source):
1. Tense-downgrade: "the same artifact a human attested **is** the artifact
   the enforcement point executes" → future/roadmap phrasing until the
   resolver-extraction slice lands. Same for "evaluates each declared intent
   **against the pinned, signed specification**".
2. fig-2 terminal `COMPLETED` → `ACHIEVED` (F5); glossary map DENIED→FAILED,
   STOPPED AT EDGE→FAILED_AT_DISPATCH.
3. "unevaluable, which never passes": add the strengthened-not-closed footnote
   + force_scores production-posture qualifier (3 rows above).
4. "the only component holding keys": keep, but label as deployment design
   (R2), not current enforcement.

## Reuse map

- `internal/gate/gate.go` step 1b — the resolution-seat validation block; the
  resolver-extraction slice RELOCATES these checks with resolution (the
  acceptance tests pin the property and survive the move).
- `internal/contractcheck/` — extend `allowedProd`/`allowedTestExtra` ONLY
  after amending CONTRACT-INTERFACE §I.2; the package-set pin will catch any
  new package automatically.
- Red-run evidence: scratchpad `b2-red-run.txt` (session-local); the learnings
  entry carries the durable record.
- Premise mapping: README "The premise, mapped to code" — update the P1 row
  when the extraction slice lands (that's the moment P1 flips to enforced).

## Invariants (unchanged + new)

All prior invariants hold (CLAUDE.md 1–6). New: CLAUDE.md 7–8 / CONTRACT-
INTERFACE §I.3–§I.5 — thin-spec refusal before scoring; pinned boundary and
vocabulary; closed FAILED_AT_DISPATCH cause-class set; ACHIEVED is the public
term. Never weaken the new tests; the empty-criteria detail format
(`empty-criteria:<hash>`) is durable-record content — renaming it later is a
record-format change, not cosmetics.

## Open / next

1. **Operator: review diff + commit** (commands in the session's final
   message; one commit per concern: gate defense, contractcheck, docs).
2. **Evaluator session** reviews the diff against spec §6 (actor/evaluator
   separation, spec §7) — this brief is the actor's claim set, not the verdict.
3. Then the standing next slices, unchanged: KV/Postgres ledger adapter →
   resolver-extraction slice (flips P1) → CI wheel-lane job.
4. Apply the enumerated pitch edits wherever the pitch HTML lives.
