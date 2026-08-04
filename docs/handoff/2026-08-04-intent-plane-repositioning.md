# Handoff -- intent-plane repositioning: core/treasury split, one CONTRACT.md, neutral core

2026-08-04. Baseline: main `a290d17`. ALL work is UNCOMMITTED on branch
`restructure/intent-plane` (zero agent commits by design; the diff is the
deliverable). Governing document:
`docs/2026-08-03-core-treasury-repositioning-design.md` (status: Implemented).
Run ledger with all review outcomes and the 21 parked minors:
`.git/sdd/progress.md`. Acceptance evidence transcripts:
`.git/sdd/task-10-gates-report.md`. Operator commit blocks:
`docs/superpowers/plans/2026-08-03-commit-ledger.md` (local-only, untracked).
Program memory: `treasury-intent-loop`.

**While the tree is uncommitted, `git stash` / `checkout` / `reset` / `clean`
destroys the entire run.** Pick up with `/rigor:pickup`; re-verify, don't trust.

## What changed, by task (T1-T10, all review-approved)

- **T1** -- Go tree moved under `core/` (`git mv` of `cmd/`, `internal/`,
  `contract/`); module renamed `github.com/pazooki/intent-plane`; one-time
  `gofmt -w` (retires drift that pre-existed on main, folded deliberately).
- **T2** -- gate env `TIC_` -> `INTENT_` (total); neutral boot log; binary
  `intent-gate`.
- **T3** -- scorer moved to `core/scorer/`; package `tis` -> `scorer`;
  `TIS_` -> `SCORER_`; distribution renamed `intent-scorer`; zero logic
  changes; fixtures untouched.
- **T4** -- `DEMO_FACTS` extracted to `treasury/facts.json`; the scorer's
  default facts are now EMPTY (every criterion Unevaluable = fail-closed
  boot posture), built red-first.
- **T5** -- third contractcheck gate `TestCoreNeutrality`: denylist
  (`payment`, `treasury`, `payer`, `balance`, `fx_rate`, `sanctions`,
  `invoice`) over `core/` `.go`/`.md`/`.py`, word-boundary, case-insensitive;
  went RED on the real tree first, then the tree was neutralized.
- **T6** -- the four-file contract amendment chain consolidated into ONE
  current-state `CONTRACT.md` (sections 1-10); the three chain files deleted
  (`git rm`, already staged) only AFTER the consolidation skeptic pass; vocab
  gate retargeted to `CONTRACT.md`; the retired pre-repositioning proper noun
  pinned at zero in the normative docs (`TestRetiredProperNouns`).
- **T7** -- `treasury/quickstart.ps1` + `.sh` twins: one command, 6-step
  self-asserting probe ladder (5 probe payloads + a cursor read). Five
  Important defects found in review, ALL inherited from the plan's own script
  sources, all fixed: probe-03 reject-guard, ps1 try/finally teardown, port
  fail-fast in both twins, `.gitattributes` `*.sh text eol=lf`, go-build
  `$LASTEXITCODE` guard.
- **T8** -- root `README.md` rewritten plane-first (honest tenses preserved:
  P1/P3 stay "asserted, not enforced"); `treasury/README.md` narrative
  (75 lines, verbatim from the design with one authorized delta).
- **T9** -- `docs/ROADMAP.md` paths/env/labels + a Findings row (columns
  corrected to Finding/Status/Consequence -- the inversion was the plan's bug);
  repo `CLAUDE.md` rewritten to the intent-plane identity (local-only file);
  design-doc status line -> Implemented; scorer README stale line fixed.
- **T10** -- acceptance (below) plus two post-gates fixes:
  `core/scorer/tests/test_resolver.py:179` sibling auto-detect
  `parents[2]` -> `parents[3]` (finding F1, controller-fixed, re-verified);
  cross-platform venv guard in `treasury/quickstart.sh` (finding F2,
  closer-fixed); root `.gitignore` `scorer/.venv/` -> `core/scorer/.venv/`
  (restructure fallout, skeptic hygiene advisory).

## Acceptance gates -- re-run command and observed result (all fresh 2026-08-04)

All seven lanes GREEN. Transcripts: `.git/sdd/task-10-gates-report.md`.

1. **Native Go** -- `go build ./... && go vet ./... && go test ./... -count=1`
   (repo root). Observed: BUILD OK, VET OK, all 9 test packages ok
   (`core/internal/intent` has no test files, expected).
2. **Windows pytest** -- `cd core/scorer && .venv/Scripts/python -m pytest`.
   Observed: **42 passed, 5 skipped** (47 collected; skip reason visible:
   ke-artifact-py wheel absent, Linux/CI-only by design). Re-run three times
   in-session (incl. after the F2 venv repair and after the F1 fix) --
   identical each time.
3. **WSL Go -race** -- `wsl -e bash -lc 'cd /mnt/c/Users/hossa/dev/treasury-intent-controller && /usr/local/go/bin/go test ./... -count=1 -race'`.
   Observed: all packages ok, no races.
4. **WSL wheel lane** -- two invocations, both recorded:
   - Auto-detect (works post-F1-fix, no `SCORER_ATLAS_DIR`):
     `wsl -e bash -lc 'cd /mnt/c/Users/hossa/dev/treasury-intent-controller/core/scorer && PYTHONPATH=/mnt/c/Users/hossa/dev/treasury-intent-controller/core/scorer/src python3 -m pytest -q'`
     Observed: **47 passed, ZERO skips**.
   - Explicit dir: same command with
     `SCORER_ATLAS_DIR=/mnt/c/Users/hossa/dev/regulatory-rule-engine` added.
     Observed: **47 passed, ZERO skips**.
   - The `PYTHONPATH` prefix is REQUIRED in both until the operator performs
     the F3 editable reinstall (below) -- the WSL user-site still carries an
     editable install pointing at the dead pre-move `scorer/src` path.
   - Count note: the 2026-07-14 learnings figure (46) is stale by exactly one
     test added since; reconciled by that entry's own method (Windows collects
     47 = 42 passed + 5 wheel skips). Superseding entry:
     `docs/learnings/2026-08-04-wheel-lane-count-47.md`.
5. **Fixture byte-proof vs `a290d17`** -- Git Bash, repo root:
   ```
   for f in $(git show a290d17:contract/scorer --name-only 2>/dev/null | tail -n +2); do
     git show "a290d17:contract/scorer/$f" | cmp -s - "core/contract/scorer/$f" && echo "OK  $f" || echo "DIFF $f"
   done
   ```
   Observed: **10/10 OK, 0 DIFF**, and `ls core/contract/scorer/ | wc -l` = 10
   (no extra files at the destination). The move was a pure relocation.
6. **Quickstart, Windows** -- `powershell -File treasury\quickstart.ps1`.
   Observed: `RESULT: 6/6 probes passed`, exit 0 (twice, incl. post-repair).
7. **Quickstart, WSL** -- `wsl -e bash -lc 'cd /mnt/c/Users/hossa/dev/treasury-intent-controller && PATH=/usr/local/go/bin:$PATH ./treasury/quickstart.sh'`.
   Observed: `RESULT: 6/6 probes passed`, exit 0 -- the FIRST real end-to-end
   execution of the `.sh` twin ever, green after the F2 fix. Both twins print
   identical probe verdicts, terminals, and reasons.

## Red-first / non-vacuity evidence

- **Neutrality gate**: RED against the REAL tree at T5 (the gate enumerated
  actual treasury vocabulary in `core/` before neutralization; the gate, not
  the plan, was the completeness authority). At T10 the skeptic re-proved
  non-vacuity with a fresh planted violation in a temp copy -- red as required.
- **TestRetiredProperNouns**: plant-red proven on the README.md arm; the
  CONTRACT.md arm shares the same loop body (ledger minor 12 records the
  exact-case-only scope, plan-mandated).
- **Quickstart negative controls**: every T7 fix verified two-sided (red
  reproduced, then green). Notably the go-build stale-binary FALSE GREEN was
  reproduced live, then killed with the `$LASTEXITCODE` guard.
- **T4 fail-closed default**: real RED evidence recorded before the
  empty-default fix landed.

## Skeptic verdicts

- **T6 consolidation skeptic (fable)**: "no pinned contract statement lost or
  weakened" SURVIVES -- zero losses, two-pass method over every pinned symbol,
  invariant, and rule; all 5 implementation deviations ratified (incl. the
  owner-map drop, claim renumbering, and a `:9000` -> `:8000` example fix).
  Chain deletion was executed only after this pass.
- **T10 skeptic (fable), three claims, ALL SURVIVE**:
  - (A) Consolidation-lossless holds for the FINAL `CONTRACT.md` -- untouched
    since T6, proven three ways (file mtime precedes the T6 report; T7-T9
    task-report files-changed sections; content spot-checks). Fresh pin
    extraction: 19/19 JSON wire tags, 5/5 routes, 3/3 env renames mapped,
    6/6 ACHIEVED trace fields, cause classes intact.
  - (B) Core neutrality -- gate re-run PASS, fresh plant-red in a temp copy,
    plus an INDEPENDENT wider sweep including off-denylist terms (custody,
    iban, currency, ...): zero new violations. Residues adjudicated benign,
    see the exemption list below.
  - (C) Fixtures -- 10/10 `cmp`-identical against the raw `a290d17` blobs, no
    extra files, EOL drift explicitly ruled out.
- **Marginal notes a-d** (recorded, none blocking): (a) the claim-1 probe lost
  the word "corrupt" (the recovery rule survives verbatim in CONTRACT.md
  sec. 2.3); (b) claims 3/5 dropped literal probe commands (the assertions
  survive); (c) the old scorer chapter's specific happy-path-test requirement
  is no longer contract-letter (the test exists; the substance is pinned three
  other ways); (d) the slice-1 "gate reads NO artifacts" sentence is gone as
  prose (it survives structurally in the boundary pin).

## Neutrality exemption list (complete)

- `core/contract/scorer/` wire fixtures -- explicit, commented in the gate;
  byte-pinned from both languages; regenerating them with neutral exemplar
  names is an open `docs/ROADMAP.md` finding, NOT built.
- `intentspec_payment` fragments in `core/scorer/tests/test_resolver.py` --
  external ATLAS artifact name (regex-invisible carve-out; adding it to the
  gate header comment is parked minor 1).
- The gate's self-exemption by basename (brief-mandated; parked minor 5).
- Adjudicated regex-invisible residues (T10 skeptic; benign, kept):
  `"key-pay-1"` in `acceptance_test.go` (cosmetic flavor, parked minor 2);
  "sanctioned/unsanctioned" in `boundary_test.go` (English homonym describing
  approved test-only import edges, not the treasury denylist term).

## Controller rulings worth carrying forward

- `docs/2026-07-05-tic-concept-chat-design.md` and
  `docs/2026-07-06-*-plan.md` still cite the deleted chain files and now
  dangle. EXCLUDED from the citation retarget as capture-time historical
  documents (same immutability class as `docs/handoff/`). Deliberate, not an
  oversight.
- `skipDir("treasury")` reversal (T5): `boundary_test.go` no longer skips
  `treasury/` -- any future `.go` file under `treasury/` fails
  `TestImportBoundary` LOUDLY, by design (treasury is payloads and scripts,
  not Go; a Go file appearing there should be a decision, not a drift).
- T5 deviations ratified in review: `types.go` comment reword (the brief's own
  text was self-contradictory), "sanctions" criterion -> "gamma" (extends the
  alpha/beta mapping pattern).
- T9 review caught ONE fabricated-strength claim in the rewritten CLAUDE.md
  ("never called 'the demo' in prose" overstated the naming ruling); fixed to
  naming-only before approval. The operator's ruling bans the name, not the
  word in prose.

## Deliberately NOT done (do not mistake for drift)

- **Fixture neutralization** -- neutral exemplar names in
  `core/contract/scorer/`: open ROADMAP Findings row, queued, not built.
- **GitHub repo rename** `treasury-intent-controller` -> `intent-plane` and
  the local folder rename -- operator's steps, pending.
- **Out-of-repo scripts** still using `TIC_*` / `TIS_*` env names --
  operator's to update; not enumerable from inside this repo.
- **F3 -- stale WSL editable install** (environmental, deliberately left):
  `~/.local/lib/python3.12/site-packages/_editable_impl_treasury_intent_scorer.pth`
  points at the dead pre-move path and `pip list` still advertises
  `treasury-intent-scorer 0.1.0`. Operator command (from the gates report;
  stated, not executed):
  ```
  wsl -e bash -lc 'python3 -m pip uninstall -y treasury-intent-scorer && python3 -m pip install --user -e /mnt/c/Users/hossa/dev/treasury-intent-controller/core/scorer'
  ```
  Until then every WSL pytest invocation needs
  `PYTHONPATH=<repo>/core/scorer/src`. The uninstall is explicit because the
  distribution name also changed (`treasury-intent-scorer` -> `intent-scorer`)
  -- shadowing the stale one would leave a lie in `pip list`.
- **21 parked review minors** -- enumerated in `.git/sdd/progress.md`, fed to
  the final whole-branch review; none blocked any gate.

## Operator actions

1. Run the commit blocks in
   `docs/superpowers/plans/2026-08-03-commit-ledger.md` IN ORDER (Git Bash),
   then push. Caveat recorded there: run against the accumulated tree, later
   fixes to files named in earlier blocks fold forward; the ledger's comments
   state where.
2. GitHub repo rename to `intent-plane` (redirects preserve old clones/links);
   local folder rename.
3. F3 WSL editable reinstall (command above).
4. Update out-of-repo `TIC_*` / `TIS_*` scripts.
5. Session close: update the `treasury-intent-loop` memory and `briefs/`
   pointers (design sec. 12).

## Verified vs assumed

- **Verified this session**: all seven acceptance lanes (closer transcripts in
  `.git/sdd/task-10-gates-report.md`); the F1 fix's effect (Windows lane
  unchanged at 42 passed / 5 skipped; WSL auto-detect WITHOUT
  `SCORER_ATLAS_DIR` now 47 passed / 0 skips); fixture bytes recomputed
  independently by the T10 skeptic from raw `a290d17` blobs (not restated from
  the closer); consolidation-lossless and neutrality by the skeptic methods
  above; the sibling RRE checkout's fixture presence at run time.
- **Assumed / not re-checked**: the remote's state (no fetch -- the rigor
  git-guard blocks it; use `gh` for remote truth); GitHub rename redirect
  behavior; "ATLAS/COMPASS consume the wire contracts only" is the design
  sec. 11 argument, not probed against those repos; the F3 reinstall command
  is transcribed from the gates report, never executed.

## Open / next

1. Final whole-branch review on fable, fed the 21 parked minors plus skeptic
   marginal notes a-d -- its verdict is not part of this brief's claims.
2. Operator: diff review + the commit blocks + push, then the rename steps.
3. Standing queue unchanged: resolver-extraction slice (flips P1), KV ledger,
   CI wheel-lane job, fixture neutralization follow-up.
