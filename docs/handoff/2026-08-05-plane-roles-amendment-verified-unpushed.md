# Handoff — plane-roles amendment: verified locally, deliberately unpushed

2026-08-05 (~04:10 UTC). Newest commit this brief describes: **`bec7589`**
(HEAD of `main`, local == origin). **Everything else — the entire 37-file
plane-roles amendment plus the verification-wave fixes — is UNCOMMITTED
worktree state on top of it** (32 changed paths at write time). The operator
chose not to push tonight; tomorrow starts with review + the commit sequence
at the bottom of this brief. Until those commits run, `git stash`,
`git checkout`, `git reset`, or `git clean` in this repo DESTROYS the work.

## Current state

- **built — the plane-roles amendment** (from the web-session patch zip
  `C:/Users/hossa/Downloads/patch_files.zip`; five split patches proven
  byte-equivalent to the full 37-file patch before application): `plane/`
  (DSSE envelopes, content-addressed spec store, hybrid resolver, signed
  revocation tombstones), `plane/authority` + `control/` + `authoring/` role
  trees, gate defenses 1a2–1a5 + dispatch-edge revocation re-check +
  `SHADOW_RECORDED`, criteria removed from the wire DTO, `force_scores`
  guard + `scorer_id` witness.
  re-verify: `go build ./... && go vet ./... && go test ./... -count=1`
- **built — both quickstart twins at 8 probes** incl. live keygen → attest →
  publish → revoke legs; ps1 was its FIRST-ever execution (8/8, exit 0), WSL
  twin 8/8.
  re-verify: `powershell -File treasury\quickstart.ps1` (ports 8000/8080 free)
- **built — skeptic findings F1–F4 closed mechanically** (2026-08-05 fable
  skeptic: 4 claims survive; findings were untested-guard/wording, no
  behavioral bug): wire-guard pins adopted as
  `core/cmd/server/wire_guard_test.go` (old-shape 400, top-level-criteria
  400, flag-off refusal incl. empty map); `scorer_id` positively asserted in
  `TestDeterminismConditionalOnScores` (plant-red proven: deleting the
  stamping in a temp copy fails the suite — before the pin it stayed green);
  README P3 row reworded ("cannot reach the plane's signing seam", not
  "cannot sign").
  re-verify: `go test ./core/cmd/server -run 'OldWireShape|TopLevelCriteria|ForceScoresRefused|DeterminismConditional' -count=1 -v`
- **built — whole-contract review outcomes** (against the pitch PDFs in
  `~/Downloads/intent-plane-pitch*.pdf`): ADR-0007 **Accepted**
  (`docs/adr/2026-08-05-ADR-0007-spec-payload-is-the-signed-object.md`);
  ADR-0006 gained the idempotency-fidelity ratification criterion; CONTRACT
  §1 role-seat mapping + §5.3 row (h); ROADMAP header/status rows + six new
  decision rows.
  re-verify: read those files; `go test ./core/internal/contractcheck -count=1 -v` (6 pins PASS)
- **built — WSL lanes** at this tree: `-race` green; scorer pytest 42/5
  native.
  re-verify: `wsl -e bash -lc 'cd /mnt/c/Users/hossa/dev/treasury-intent-controller && /usr/local/go/bin/go test ./... -count=1 -race'`
- **planned — the commit sequence** (bottom of this brief), NOT run tonight
  by operator choice.
- **planned — open decision rows** in `docs/ROADMAP.md` findings table
  (draft-crossing signing, terminal-record witness placement, refusal-record
  asymmetry, stuck-key runbook, human-judgment marker-vs-approval-channel)
  and ADR-0006 ratification.

## Locked decisions

- **ADR-0007 (Accepted, operator ruling 2026-08-05): `plane.SpecPayload` IS
  the signed object.** ATLAS `IntentSpec` retired as a criteria source;
  scorer-side resolver-extraction slice retired; `rule_artifact_hash` stays
  as rule provenance only. Reason: the pitch's "one signed object" is
  undermined by two spec systems with an unstated relationship.
- **Exact-decimal payload thresholds BEFORE R1** (binding trigger inside
  ADR-0007). Reason: float64 debt inside content-addressed signed bytes
  costs a re-attest-everything migration once real specs exist; today every
  spec is test-authority and disposable.
- **ADR-0006 stays Proposed** — SHADOW_RECORDED is implemented-and-pinned,
  not settled practice; ratification criteria now include the shadow
  idempotency-optimism fix. Reason: governance decision awaits its
  consumer-side exercise.
- **Guard + witness, both** for `force_scores` (boot flag → loud 400; feed
  witness on SCORED/RECHECK). Reason: a silently-dropped bypass is a bypass
  in waiting; an unwitnessed forced grant is indistinguishable evidence.
- **Revoked wins over unattested** in refusal causes. Reason: collapsing a
  verified tombstone into `unattested-spec` erases a fact the feed exists to
  witness (`TestRevokedResolutionWinsOverUnattested`).
- **Shadow does not reserve the key.** Reason: shadow must not consume
  real-world uniqueness (pinned by
  `TestShadowPostureRecordsWithoutAuthorizing`); its collision-optimism is
  an ADR-0006 ratification item, not a change to this rule.
- **Commit sequence stages CURRENT file state per pathspec** with messages
  scoped accordingly. Reason: the 2026-08-04 C1 review proved per-task
  blocks against an accumulated tree ship false history.

## Reuse map

- `core/cmd/server/wire_guard_test.go` — the pattern for pinning loud-400 /
  guard-off paths (boot a mux with the guard explicitly OFF).
- Plant-red recipe for witness/guard pins: copy `core plane go.mod` to a
  temp dir (variable NOT named `TMP` — Windows Go reads it), delete the
  mechanism there, run the focused test, expect FAIL.
- Split-patch equivalence check: after applying splits in order, a reverse
  `--check` of the FULL patch proves byte-equivalence (see learnings entry
  2026-08-05-split-patch-equivalence-check).
- `docs/handoff/2026-08-04-plane-roles-amendment-design.md` — the
  amendment's own design record (scope, role trees, verification record,
  consumer-research demand map appendix).
- `.git/sdd/task-10-skeptic-report.md` + this session's two skeptic reports
  (repositioning + plane) — prompt shapes for adversarial passes that
  produced real findings.

## Invariants

- **No `git stash` / `checkout` / `reset` / `clean` until the commit
  sequence runs** — the whole amendment is uncommitted worktree state.
- Agents never commit/push; the operator runs the sequence below.
- `core/contract/scorer/` fixtures are byte-frozen (checkout may show CRLF;
  index blobs are LF — content unchanged, verified by raw-blob cmp).
- `CLAUDE.md` and `docs/superpowers/` are local-only (`.git/info/exclude`)
  and must never be staged.
- The contractcheck six (import boundary, key-possession, neutrality, vocab
  presence, forbidden nouns, retired noun) must pass after ANY doc or
  package change: `go test ./core/internal/contractcheck -count=1`.
- SHADOW_RECORDED must not be quoted as settled practice while ADR-0006 is
  Proposed; `key_authority: "test"` stamps stay until ADR-0009.
- A new §2.3 wire field lands WITH its §5.3 acceptance row (§5.3(h)'s
  discipline note — `scorer_id` initially violated it and the witness was
  provably deletable).

## Open / next

**First thing tomorrow: review the tree, then run the commit sequence and
push.** Review aids: `git status --short` (32 paths), `git diff HEAD --stat`;
every gate is one command away per the re-verify lines above.

```bash
cd ~/dev/treasury-intent-controller
git add plane control authoring core/internal/contractcheck
git commit -m "feat: plane role trees - signed specs, store, resolver, key-possession boundary"
git add core/internal
git commit -m "feat: gate resolution defenses, revocation re-check, SHADOW_RECORDED, scorer-id witness"
git add core/cmd/server        # includes the wire-guard pins + positive witness assertion (2026-08-05 skeptic fixes)
git commit -m "feat: criteria leave the wire - spec resolution, guarded force_scores, wire-guard pins"
git add treasury
git commit -m "feat: treasury 8-probe plane ladder - attest, publish, revoke live"
git add CONTRACT.md README.md docs
git commit -m "docs: contract 2.6 amendment; ADR-0006 Proposed, ADR-0007 Accepted; whole-contract review outcomes"
git status --short             # only CLAUDE.md + docs/superpowers/ should remain (local-only)
git push
```

After the push, in order of leverage: (1) rule on the human-judgment
marker-vs-approval-channel row (it shapes the payload schema; decide before
R1's schema freeze); (2) ADR-0006 ratification criteria; (3) the remaining
ROADMAP decision rows; (4) out-of-repo follow-ups (COMPASS/ATLAS docs stale
per ADR-0007; WSL editable reinstall; TIC_*/TIS_* scripts). Blockers: none —
everything above is operator-choice sequencing, not a technical block.
