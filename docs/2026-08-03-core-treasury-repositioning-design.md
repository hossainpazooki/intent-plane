# Core / Treasury repositioning — design

**Date:** 2026-08-03. **Status:** Implemented on branch `restructure/intent-plane`
(this session); commits + GitHub rename are the operator's. Baseline: main `a290d17`.

## 1. Purpose

The repo's design has been revamped repeatedly; the directory structure,
contract chain, and README still narrate that lineage. This restructure trades
lineage for clarity: the **intent plane** — a domain-agnostic authorization
layer for agentic deployments — becomes the repo's subject, and the **treasury
system** becomes its working demonstration. Git history remains the only
lineage record; current-state documents replace amendment chains.

The two units are named **core** and **treasury** (operator ruling — not
"demo"). Correctness and collaborator readability outrank preservation.

## 2. Locked decisions (operator-ratified 2026-08-02/03)

| Decision | Ruling |
|---|---|
| Split depth | Structural: `core/` + `treasury/` inside one repo |
| Repo + module name | `intent-plane`; module `github.com/pazooki/intent-plane` (GitHub rename is the operator's step; ratified 2026-08-03 after collision-checking `intent-interface` — a crowded GitHub topic — and finding `superplane`/`metaplane`/`intent-gate` occupied) |
| Env prefix (gate) | `TIC_` → `INTENT_` |
| Scorer identity | Full neutral rename: package `tis` → `scorer`, `TIS_` → `SCORER_`, distribution `treasury-intent-scorer` → `intent-scorer` |
| Contracts | Consolidate the four-file amendment chain into one current-state `CONTRACT.md`; delete the chain (history keeps it) |
| Treasury UX | One-command showcase with a narrated, self-asserting probe ladder |
| Ledgers | `docs/handoff/`, `docs/learnings/` immutable — old names in old entries are correct at capture time |
| Vocabulary | Three-way split ruled 2026-08-03: **plane** = position, **gate** = decider, **interface** = contract surface (see below) |

### Vocabulary ruling (2026-08-03)

Three words, each answering a different question; any sentence self-selects
its term:

- **plane** — *where does it sit?* The architectural position among peers:
  "the intent plane" (= gate + scorer + contracts, everything this repo
  ships), beside the authoring plane, the artifact plane (ATLAS), and the
  settlement plane (COMPASS). A "plane crossing" is a signed artifact moving
  between them. Never a code component — nothing inside the repo is "a plane."
- **gate** — *what decides?* The deterministic enforcement component within
  the plane, and the fourth role in declarant / author / attester / **gate**
  (role and component are deliberately the same word — the role IS the
  deciding component). Use wherever agency appears: the gate refuses, scores,
  emits, holds sole ACHIEVED authority. `internal/gate` and the `intent-gate`
  binary are correctly named under this rule. Corollary: the gate is *smaller
  than* the plane — the scorer is in the plane but not in the gate, so "the
  gate consults the scorer," never "the gate scores facts."
- **interface** — *what do you code against?* Reserved for the contract
  surface only: the 4 routes, wire DTOs, the JSONL feed shape, the
  `/ml/evaluate` seam, the pinned package adjacency, the role vocabulary
  itself. Always lowercase and descriptive ("the plane's interface"). The
  proper-noun "Intent Interface" is retired with the old repo-name candidate;
  `CONTRACT.md` is the document that *states* the interface.

Edge rulings: treasury is "a demonstration **deployment of** the intent
plane," never a plane or a gate of its own; the README thesis names position
and agency with the right words ("agents propose; the plane's gate
disposes"); the `INTENT_` env prefix is untouched (it names the plane's
artifact, not any of the three terms).

Mechanization: `vocab_test.go` adds the retired proper-noun **"Intent
Interface"** (case-sensitive) to the forbidden list — the same class as the
existing forbidden-actor-noun gate — so the old name cannot creep back into
README or CONTRACT.md.

## 3. Target layout

```
intent-plane/
├── README.md            # the intent plane first; "See it work" -> treasury/
├── CONTRACT.md          # single current-state contract (see §4)
├── go.mod               # module github.com/pazooki/intent-plane
├── core/
│   ├── cmd/server/      # the gate's HTTP shell
│   ├── internal/        # intent, lifecycle, audit, durable, adapter,
│   │                    # idempotency, scoring, gate, contractcheck
│   ├── contract/scorer/ # byte-pinned wire fixtures (see §7 exemption)
│   └── scorer/          # Python scorer service (src/scorer)
├── treasury/
│   ├── README.md        # the value narrative (see §5)
│   ├── facts.json       # balance / fx_rate — the ONLY treasury-fact location
│   ├── quickstart.sh + quickstart.ps1
│   └── probes/          # ladder payloads (see §6)
└── docs/                # ROADMAP + immutable ledgers, unchanged
```

Go tooling note: `cmd/` and `internal/` move under `core/` via `git mv`;
`internal/` visibility semantics are unchanged (the boundary relative to
package path still holds — `core/internal/...` is importable only within the
module, and contractcheck pins the adjacency regardless).

### Renames (inventory grep-verified 2026-08-03)

- Gate env: `TIC_DATA_DIR`→`INTENT_DATA_DIR`, `TIC_SCORER_URL`→`INTENT_SCORER_URL`,
  `TIC_ADDR`→`INTENT_ADDR`.
- Scorer service env: `TIS_{HOST,PORT,ARTIFACT_DIR,ATLAS_INPUTS_DIR,EXPORTED_AT_UNIX,FACTS_JSON}`
  → `SCORER_*`.
- Scorer test env: `TIC_CONTRACT_DIR`→`SCORER_CONTRACT_DIR`, `TIC_ATLAS_DIR`→`SCORER_ATLAS_DIR`.
- `DEMO_FACTS` (`facts.py:25`, `{"balance": 250.0, "fx_rate": 1.30}`) leaves core:
  extracted to `treasury/facts.json`, injected via the existing `SCORER_FACTS_JSON`
  seam. The scorer's neutral default is **zero facts** — every criterion scores
  Unevaluable, which is the fail-closed posture a neutral core should boot into.
- Server binary `bin/tic.exe` → `bin/intent-gate.exe`; boot log line renamed.
- FastAPI title → `intent-scorer`.

## 4. CONTRACT.md — the consolidated contract

One root document replaces `CONTRACT.md` + `CONTRACT-DURABILITY.md` +
`CONTRACT-SCORER.md` + `CONTRACT-INTERFACE.md`. Current-state only — where the
chain's later-wins rule resolved a conflict, only the winner appears. Sections:

1. **Roles & vocabulary** — declarant / author / attester / gate (from §I.0);
   ACHIEVED is the public term, COMPLETED banned; states the
   plane / gate / interface three-way usage ruling (§2).
2. **The interface** — the 4 routes, wire DTOs, durable `Record` JSONL shape
   (`GlobalSeq` never in `TrajectoryHash`), the `/ml/evaluate` seam with both
   fail-closed matrices, `force_scores` and its production-posture note.
3. **Lifecycle & cause classes** — states, transitions, terminals;
   FAILED_AT_DISPATCH closed cause-class set (`volatile-recheck:`,
   `idempotency-collision`, reserved `revoked:` with its G5 doctrine label).
4. **Gate algorithm** — steps 1, 1b (thin-spec defense), 2–5 as built,
   including the out-of-domain-score fail-closed rule.
5. **Invariants 1–8** — consolidated, with invariant 2 in its non-vacuous
   wording (an empty criteria set REFUSES; it does not vacuously grant).
6. **Determinism & replay** — logical clock, byte-identity, replay = RECOMPUTE.
7. **Package boundary** — the pinned set + adjacency (mirrors
   `contractcheck/boundary_test.go`; amend the doc first, then the table).
8. **Scorer service contract** — all-or-nothing boot config, resolver
   fail-closed rules, visible-skip basis.
9. **Fixture discipline** — `core/contract/scorer/` byte-compared from both
   languages.
10. **Provenance footer** — names the four replaced files and the consolidation
   date; git history holds the originals.

**Guard:** consolidation is a rewrite, so before the chain is deleted a
skeptic pass diffs every pinned symbol, invariant, and rule in the new document
against the four-file chain — "no pinned statement lost or weakened" must be a
verified claim. `contractcheck/vocab_test.go` retargets from
`CONTRACT-INTERFACE.md` to `CONTRACT.md`.

## 5. README architecture

**Root `README.md`** leads with the layer, not the demo:

- Thesis: agents propose; the plane's gate disposes; unevaluable never
  passes. The well-formed-but-wrong-action problem, in the pitch register's
  honest tenses.
- The P1–P7 guarantees table mapped to `core/` paths — P1 and P3 keep their
  "asserted, not enforced" labels; no tense inflation.
- The two existing mermaid diagrams (lifecycle incl. the thin-spec refusal
  edge; emit-and-observe), paths updated.
- **"See it work"** — the one command and a capture of what it prints, linking
  to `treasury/`.
- Layout table, gates/commands, links to `CONTRACT.md` and `docs/ROADMAP.md`.

**`treasury/README.md`** owns the narrative: the payment-controls scenario,
what each probe demonstrates and why it matters, and the **extended
demonstration** section (ATLAS wheel-verified artifacts, COMPASS settlement,
the 2026-07-12 live-loop evidence) explicitly marked with its environment
requirements (Linux/WSL, sibling checkouts) and status tags — the quickstart
never claims what only the extended lane shows.

## 6. The quickstart (treasury)

`treasury/quickstart.sh` + `.ps1` twin (both maintained; POSIX-portable per
the global working agreement). Requirements: Go + Python only — no WSL, no
sibling checkouts, no ATLAS/COMPASS.

Mechanics: create the scorer venv if missing → boot the scorer with
`SCORER_FACTS_JSON` pointing at `treasury/facts.json` → build and boot the
gate with `INTENT_SCORER_URL` → run the probe ladder → teardown. Each step
prints one line of *why this matters* and **asserts the expected terminal** —
the demo doubles as a smoke gate and is itself part of acceptance (§9).

Probe ladder:

| # | Probe | Expected | Demonstrates |
|---|---|---|---|
| 1 | Declare a payment within limits | ACHIEVED + durable trace shown | the full lifecycle, emit-and-observe |
| 2 | Re-declare the same idempotency key | FAILED_AT_DISPATCH `idempotency-collision` | at-most-once by construction |
| 3 | Declare over-threshold | FAILED naming the criterion | criteria actually bind |
| 4 | Kill the scorer, declare again | FAILED unevaluable | fail-closed on outage, live |
| 5 | Declare with empty criteria | FAILED `unevaluable:empty-criteria` | thin-spec defense |
| 6 | Cursor read of `/v2/events` | the JSONL trace | the observable feed |

`force_scores` never appears in the showcase. Artifact verification is
narrated as belonging to the extended demonstration — the resolver's
visible-skip basis makes that honest on the wire itself.

## 7. Core neutrality, mechanized

`contractcheck` gains a third gate: **`core/` carries no treasury
vocabulary.** Denylist (tuned against the 2026-08-03 sweep to avoid a gate
stricter than reality): `payment`, `treasury`, `payer`, `balance`, `fx_rate`,
`sanctions`, `invoice` — case-insensitive word-boundary match over `core/`
`.go`/`.md`/`.py`. "Settlement" is ruled **core vocabulary** (the generic
consequence-commit in invariants 4–5), not a treasury noun.

Known sites to neutralize: the `ActionClass` doc-comment example
(`types.go:41` `// "payment" for slice 1`), test fixture literals using
`payment`/`balance` where not byte-pinned, the boot log line.

**Exemption (explicit, commented in the gate):** `core/contract/scorer/`
fixtures — they carry `"criterion":"balance"` etc., are byte-compared from
both languages, and changing their bytes is out of scope. Recorded as an
optional follow-up (regenerate with neutral exemplar names, both lanes
re-green in the same change). If the Go determinism goldens also embed a
treasury literal, the same exemption+follow-up treatment applies — the plan
enumerates this before build.

## 8. Migration order (branch `restructure/intent-plane`)

1. **Move + rename Go**: `git mv` `cmd/`, `internal/`, `contract/` under
   `core/`; module path rewrite + import rewrite; `TIC_`→`INTENT_`; one-time
   `gofmt -w` across the tree (every file is touched anyway — retires the
   pre-existing drift on main).
2. **Scorer**: `git mv` `scorer/` → `core/scorer/`; package `tis`→`scorer`;
   `TIS_`→`SCORER_`; test env renames; facts extraction → `treasury/facts.json`.
3. **contractcheck**: path/module updates; vocab gate retargets `CONTRACT.md`
   and adds the retired proper-noun "Intent Interface" to the forbidden list;
   **new neutrality gate** (§7) — red-first against a planted violation.
4. **CONTRACT.md consolidation**: write the new document; skeptic diff-pass
   (§4 guard); delete the four chain files only after the pass.
5. **Docs**: root README rewrite, `treasury/README.md`, quickstart + probes,
   `docs/ROADMAP.md` touch-ups (roadmap items unchanged in substance),
   repo `CLAUDE.md` rewrite (local-only file).
6. **Ledger close-out**: handoff brief + learnings entries (new dated files;
   never edits to old ones).

Each step leaves the tree buildable; gates run at every step, full acceptance
at the end.

## 9. Acceptance gates

- Go named gate: `go build ./... && go vet ./... && go test ./... -count=1`
  native **and** WSL `-race` — green.
- Scorer pytest: Windows lane (41 pass / 5 visible skips) and WSL wheel lane
  (46/46) — green. (Wheel lane still requires the sibling RRE checkout; that
  dependency is documented, not removed.)
- `core/contract/scorer/` fixtures **byte-identical** to main `a290d17`.
- contractcheck: boundary + vocab + neutrality all green; neutrality proven
  non-vacuous (fails on a planted treasury noun in a temp copy).
- **The quickstart itself runs green end-to-end on Windows** (and the `.sh`
  twin under WSL) — its self-assertions are the probe.
- Contract-consolidation skeptic pass recorded: no pinned statement lost.
- Zero commits by the assistant; diff + commit commands output for the
  operator (git.md format).

## 10. Out of scope

No behavior changes to the gate algorithm, scoring, durability, or wire
schemas; no route changes; no `force_scores` removal; no fixture byte changes;
no roadmap item built (resolver-extraction, KV ledger, CI wheel-lane all
remain queued); no edits to ledger history; no changes in ATLAS/COMPASS repos
(their references to the old repo name ride on GitHub's rename redirect and
are cleaned up opportunistically there).

## 11. Risks

- **Consolidation loses a pinned rule** — mitigated by the §4 skeptic
  diff-pass gating chain deletion.
- **Rename breaks an external consumer** — ATLAS/COMPASS code against the
  wire contracts, not the module path or env names; wire shapes and fixture
  bytes are unchanged. `INTENT_SCORER_URL`/deploy scripts outside this repo
  are the operator's to update; the handoff brief lists them.
- **`gofmt -w` folds unrelated drift into the move commits** — accepted
  deliberately (stated in the commit message); the drift pre-exists on main.
- **Neutrality gate false positives** — denylist tuned to the sweep;
  exemptions explicit and commented.

## 12. Operator actions (not the assistant's)

- Run the emitted commits; GitHub repo rename to `intent-plane`
  (redirects preserve old clones/links); local folder rename.
- Update any out-of-repo scripts using `TIC_*`/`TIS_*` env names.
- The `treasury-intent-loop` memory and `briefs/` pointers get updated at
  session close.
