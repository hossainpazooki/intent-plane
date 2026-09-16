# One repository: the kernel, the plane table, and the showcase

- **Status: Accepted** (2026-09-15, operator rulings in session). The fold this
  record describes is **assembled in the working tree and gated, not yet
  committed**: every claim below about what "ships here" is true of the tree a
  reviewer can run today, and becomes true of the published repository when the
  commit lands.
- Deciders: the operator.
- Amends: the 2026-08-05 layout directive ("the published repository is the
  minimal core only") and the 2026-08-12 per-tree ownership rule (consumer
  packages born here, plane internals ported in from a private testing
  monorepo). Leaves the 2026-08-05 layering decision — minimal core, roles in
  the application — **unchanged and load-bearing**.
- Relates: CONTRACT.md §7 (package boundary), §7.1 (consumer trees), §1.1
  (roles), the migration section (internal-reference pin).

## Context

Since 2026-08-05 the plane lived in two repositories carrying the same core:
this public one (the polished minimal SDK) and a private testing monorepo
(where plane internals were experimented with, and where the application
seats and the live probe ladder lived). Core was ported between them by hand.

The split had one stated reason: keep the public artifact minimal while
experimentation happened elsewhere. Its recorded cost is the drift the manual
port was meant to prevent — claim tables numbered differently on the two
sides, the private copy's scorer still carrying names this repo scrubbed, and,
found at the 2026-09-15 pick-up, the private copy's own gate red for three
weeks at a commit whose hand-off brief reported the pins green, because the
pins had been run on the other copy.

The operator has now ruled that the **plane table** — the surface where specs
are drafted, attested and inspected — belongs in the same repository as the
kernel. With that, this repository is no longer "minimal core only", and the
one reason for the second copy is gone.

## Decisions

1. **One repository holds the kernel, the plane table and the showcase.**
   - Kernel: `core/` and `plane/` — untouched, still pinned by table.
   - Plane table: `planetable/{authoring,control,authority}` — **one
     application tree, not three top-level directories** (see decision 2).
   - Showcase: `treasury/` — the reference application (facts, signed spec
     drafts, probes, the quickstart ladder).
   - Consumer trees `verifier/` and `declarant/`: unchanged.
   - Also folded in: a durability test that existed only in the private copy
     and would otherwise have been deleted, and a local chat tool used to
     interrogate these contracts.
2. **The seats are nested under one tree, and this is a correction.** An
   earlier draft of this record placed `authoring/`, `control/` and
   `authority/` at the repository root and asserted that the existing
   name-free pins would hold "with no table change". That was **mechanically
   false**, and the experiment that proves it was run in a scratch copy:
   - at the root, `TestImportBoundary` goes **red** on the legitimate
     `control -> authority` edge, because a slash-less directory is its own
     application tree;
   - worse, `TestKeyPossessionBoundary` **passes with a planted key-seat
     theft**, because its `/authority` suffix match never fires for a
     root-level package. The pin that makes "cannot sign" a code-graph fact
     silently stops protecting.
   Under one tree both pins behave: the legitimate edge passes and the planted
   theft goes red. The pins are therefore **unchanged**, and they are unchanged
   because the layout was chosen to fit them.
3. **The rule-engine project is a declarant of this plane**, not a publisher
   into it. Its own authority transitions are declared through the gate like
   any other action, via the declarant SDK. No spec flows from it into the
   plane; the 2026-08-05 decision that the plane's own signed payload is the
   single spec representation stands. That work is unbuilt.
4. **The fold lands as a single squashed commit, not as imported history.**
   The internal-reference pin walks the filesystem, not the object store, so a
   history-preserving import would publish every pre-scrub blob of the
   showcase — internal codenames included — permanently, by the one route the
   pin structurally cannot see. The full history survives in the private
   archive. The commit message carries the source revision.
5. **The private monorepo is to be archived**: flagged archived on the host,
   and its checkout moved aside, so that it holds no code of record. This step
   has **not been executed** at the time of writing — like the fold itself, it
   is decided and pending. Two things the operator must know when they run it:
   the move needs the editing sessions closed and an atomic rename, and the
   run records kept inside its `.git` directory survive a move but no clone.
6. **What deliberately does NOT cross**: the hand-off, learnings and research
   ledgers (hundreds of internal-name references, and the leak guard is exempt
   nowhere); the private roadmap; the earlier decision records; the showcase's
   own design notes; an unreferenced 660-line script in the showcase tree; and
   the chat tool's plan records. The consequence is stated plainly in
   "Consequences" below rather than left to be discovered.

## Consequences

- **The public surface grows, so core neutrality matters more.** Application
  vocabulary now sits one directory from `core/`. The neutrality pin is the
  line, and it scans only `core/` — which is exactly why nothing from the fold
  may land under `core/` except the durability test, which carries none.
- **Exactly one pin gains an exemption, and it is not the leak guard.**
  `TestForbiddenActorNouns` stops scanning `docs/handoff/` and
  `docs/learnings/`: dated records quote regulatory and historical terms, and
  a gate stricter than the vocabulary it protects only produces false alarms.
  The record that first held the gate red named a reporting obligation — the
  party on whose account a report is filed — which the pin reads as an actor
  role. Note what this paragraph cannot do: spell the banned word. Every other
  directory, `docs/adr/` included, stays scanned, and this file was itself
  caught by the pin for spelling it in an earlier draft.
  `TestInternalReferencesAbsent` gains **no** exemption anywhere: it is what
  keeps a public repository from publishing internal codenames, and a dated
  record is exactly where one would slip in. It earned that standing during
  this fold: it caught nine internal references in the incoming showcase.
- **The pins have two blind spots, and a scrub driven by their output alone is
  not enough.** The leak guard's extension list excludes `.ps1`, and its walk
  skips any directory named for plan records. One incoming reference sat in
  each. Both were scrubbed by hand.
- **Spec drafts are hashed as raw bytes**, so `.gitattributes` now pins
  `treasury/specs/*` against end-of-line conversion: without it the same draft
  has a different content address on different platforms.
- **The open production-posture findings and the earlier decision records stay
  in the archive** (decision 6). The live repository therefore has no roadmap
  file, and the standing residuals — identity-case folding, the ambiguous
  union on the proxy path, the unescaped separator in the key format — are
  carried in the session's loose-ends register, not here. Anyone who wants
  them visible in this repository must port them deliberately.
- **The by-hand copy discipline retires with the second copy.** There is no
  longer a byte-identical twin to diff, and the per-tree porting rule is moot.
- **The live ladder becomes this repository's own acceptance test.** It ran
  here on 2026-09-15 and printed `RESULT: 15/15 probes passed`, exactly 7
  ACHIEVED among 149 events, and a verifier recompute of 21 intents with the
  Go and Python reports identical.

## Not decided here

- The plane table's web and API surfaces (a separate design).
- Production key authority and workload identity: the key seat stays
  test-grade, and nothing here changes that stamp.
- Whether the rule-engine project ever becomes a second attesting authority of
  the plane. That would reopen the single-signed-object decision and needs its
  own record.
- Where the maker-checker flow test belongs. It exercises the plane table's
  seats but ships in the showcase tree, which is where it was written; moving
  it is a later, separate change.
