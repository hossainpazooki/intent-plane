ts: 2026-08-04T20:56:47Z
commit: a290d17 (HEAD = baseline main; the entire restructure is UNCOMMITTED on branch `restructure/intent-plane` at capture -- the basis tree includes the uncommitted `core/scorer` move)
session: intent-plane repositioning, Task 10 acceptance (closer run + controller fix, same day)
status: verified
kills: 2026-07-14-wheel-lane-count-corrected.md (its count only -- its reconciliation method and its correction of the 07-13 number both stand)

fact: The WSL wheel-lane zero-skip total is **47 passed**, not the 46 that the
2026-07-14 entry records. Exactly one test was added to the suite since that
entry's capture; the count reconciles by that entry's OWN method: the Windows
lane collects 47 items = 42 passed + 5 wheel-lane skips, and WSL runs all 47.
The 46 was stale by one, not wrong in kind.

Second finding, same lane (the T10 closer's F1): the restructure moved the
tests from `scorer/tests/` to `core/scorer/tests/`, and the sibling
auto-detect in `test_resolver.py` computed the ATLAS checkout as
`Path(__file__).resolve().parents[2].parent / "regulatory-rule-engine"`.
Post-move, `parents[2]` is `core/`, one level too shallow -- the auto-detect
resolved to a path INSIDE the repo and the lane skipped with "ATLAS checkout
absent" on a host where the checkout was present and correct. A directory move
silently changes every `parents[N]` computation under it, and this one
converted "sibling present" into a by-design-looking skip. On Windows the
break was invisible because skip-reason attribution masked it: the
`importorskip("ke_artifact_py")` fires first, so all 5 skips read as the
wheel's by-design absence and the dead auto-detect path never surfaced. This
is the same failure SHAPE as 2026-07-13-wheel-lane-import-name-bug (a skip
that reads as by-design masking a lane that cannot run) -- that lesson
recurred, this time via path arithmetic instead of a module name. Fixed same
day (`parents[3]`, controller-applied) and re-verified both sides.

basis: T10 closer transcripts (`.git/sdd/task-10-gates-report.md`), all
2026-08-04 on this tree. Pre-fix: WSL with `PYTHONPATH` only ->
`42 passed, 5 skipped` with reason "ATLAS checkout absent"; direct probe
printed `parents2: .../treasury-intent-controller/core`, `is_dir: False`,
while the sibling checkout was proven present (`fixtures/artifacts/
intentspec_payment/` in HEAD; wheel import OK). With
`SCORER_ATLAS_DIR=/mnt/c/Users/hossa/dev/regulatory-rule-engine` ->
`47 passed, 1 warning`. Post-fix (controller re-run): WSL auto-detect WITHOUT
`SCORER_ATLAS_DIR` -> `47 passed, 0 skips`; Windows lane unchanged at
`42 passed, 5 skipped` (47 collected).

re-verify: `wsl -e bash -lc 'cd /mnt/c/Users/hossa/dev/treasury-intent-controller/core/scorer && PYTHONPATH=/mnt/c/Users/hossa/dev/treasury-intent-controller/core/scorer/src python3 -m pytest -q'`
-- expect **47 passed, zero skips** with NO `SCORER_ATLAS_DIR` (auto-detect),
provided the sibling RRE checkout carries the fixture
(2026-07-14-wheel-lane-depends-on-sibling-checkout-state.md). The `PYTHONPATH`
prefix is needed only until the operator's F3 editable reinstall (handoff
2026-08-04); after it, drop the prefix.

lesson: `Path(__file__).parents[N]` is a load-bearing count that no compiler
checks -- audit every occurrence when a directory moves, and never trust a
skip's printed reason on a platform where an earlier skip guard fires first:
prove the later guard reachable-as-false on a platform where it actually runs.
