# intent-plane consumer research: the verifier and the platform team

2026-08-04. Research memo, PROPOSED thinking only -- nothing here is repo
doctrine, and nothing described as a package or SDK exists unless marked built.
Grounded against the `restructure/intent-plane` tree (baseline `a290d17`),
which has since merged to `main` and the repo renamed to
`github.com/hossainpazooki/intent-plane` (2026-08-04) -- file:line citations
resolve against that main.

Anchoring note (honest): the phrase "cross-language consumer" appears nowhere
in the repo's docs (grepped 2026-08-04); the question it names originates in
project discussion. The repo-side anchors it resolves against are CONTRACT.md Section 9
("cross-language golden fixtures", also `core/scorer/tests/test_fixtures.py:1`
and `core/internal/scoring/scorer_test.go:289`) and Section 6's byte-identity
clauses. This memo treats the verifier as the answer to that question and
argues it from the code.

---

## 1. Introduction: who intent-plane is for

*Two independent reads, kept distinguishable. This introduction is one
analyst's view, formed while executing the 2026-08 repositioning of the repo
end to end (with its full review and adversarial-verification record);
sections 2-5 below are a second analyst's independent research, untouched.
Where the two reads disagree, the disagreement is stated, not averaged.*

```
who intent-plane serves -- the two-sided sale

   demand side (the buyer)              supply side (the integrator)
  +----------------------+   requires   +------------------------+
  | accountability       |------------->| platform team wrapping |
  | function: audit,     |  examinable  | the agent runtime      |
  | compliance, model    |   records    | ("how our agents       |
  | risk, counterparty   |              |   call tools")         |
  +----------------------+              +------------------------+
         |                                        |
         | runs the verifier package              | embeds the declarant
         | against the records                    | SDK once, at the
         | (no trust in the gate)                 | framework layer
         v                                        v
  +--------------------------------------------------------------+
  |                       the intent plane                       |
  |  agents propose -> gate disposes (fail-closed, deterministic)|
  |      -> exactly one durable ACHIEVED record per action       |
  |      -> append-only feed, polled by cursor                   |
  +--------------------------------------------------------------+
```

**Independent finding 1 -- the target consumer is whoever answers for the
action afterward, and the architecture already knows it.** Read the cost
structure of this codebase as a revealed preference. The properties that were
expensive to build and are expensive to keep -- per-intent logical clocks and
no wallclock (CONTRACT.md Section 6), a length-prefixed JSON-free hash
encoding (`core/internal/audit/eventlog.go:69-83`), ten byte-frozen
cross-language fixtures with a one-commit re-green rule (Section 9), fsync
before every durable-append success, exactly-one ACHIEVED per key -- buy
nothing at decision time. A policy engine makes the same allow/deny without
any of them. They pay off only when someone who does NOT trust the gate
re-derives the record later. So the target consumer is not "teams running
agents"; it is the accountability function behind those teams -- model risk,
compliance, internal audit, the counterparty's diligence -- in deployments
where agent actions are irreversible and examined after the fact. The
verifier is not one consumer of this system; it is the consumer the system's
distinctive costs were already paying for. (This independently confirms the
second analyst's substrate assessment from the opposite direction: they argue the
encoding serves the verifier well; I argue nothing else explains the
encoding.)

**Independent finding 2 -- the two consumers are one two-sided sale, not two
markets.** The platform team has weak intrinsic demand: a framework owner who
merely wants tool-call gating will reach for a policy check in middleware and
be done by Friday. What they cannot build in middleware is an examinable
record -- and they only need one when the accountability function demands it.
The verifier side generates the demand; the declarant side removes the
friction of saying yes. Consequence for sequencing: the verifier package is
the pitch (build it first -- Section 4's sequencing opinion, which I
independently reach), and the declarant SDK is the concession that makes the
pitch land. Neither half sells alone, and pricing/positioning should treat
them as one product with two audiences.

**Independent finding 3 -- the demo demonstrates to the wrong consumer.** The
treasury quickstart's six probes are all declare-shaped: they exercise the
declarant wire (terminals, collision, outage, thin-spec) and stop at counting
ACHIEVED records. No probe recomputes anything. A seventh probe that pulls
`/v2/events`, re-derives the TrajectoryHash per the Section 6 encoding in the
probe harness's own language (PowerShell/Python -- NOT Go, which is exactly
the cross-language point), and matches it against the ACHIEVED record would
make the core pitch executable in the demo with zero server changes. Today
the sales artifact ("run this against our records") exists as prose in two
READMEs; one probe would make it a command.

**Independent finding 4 -- where I weight the gaps differently.** The
second analyst ranks the unguarded `force_scores` bypass as the verifier's biggest
gap (a forced grant is byte-indistinguishable in the feed from a scored one
-- `gate.go:183-184` never witnesses the scorer's identity; confirmed, and it
is real). I rank P1 above it for the *target-consumer pitch*: criteria are
declarant-supplied (`main.go:171-177`, README premise table "asserted, not
enforced"), so the headline sentence -- "the artifact a human attested is the
artifact the enforcement point executed" -- is not yet true even on the
honest path. `force_scores` is what an adversary exploits; P1 is what the
pitch trips over in the first diligence meeting with nobody attacking
anything. A sales story survives a known-and-guarded bypass; it does not
survive its central sentence being future tense. Practical order: resolver
extraction (closes P1, already the roadmap's next slice) before or alongside
the force_scores close -- and note both memos agree the two cheapest
verifier-grade server changes (refusal-hash commitment, scorer-identity
witness) are contract amendments blocked on nothing.

**What "embed once" actually rests on** (kept from both reads): the
synchronous terminal (`main.go:188-201`) and the contractually CLOSED refusal
vocabulary -- cause classes are a pinned table that must be amended before it
can grow (CONTRACT.md Section 3.3). The platform integration is a switch
statement over stable strings, not a state machine over guessed ones. That
string stability is a contract property most gateways do not pin, it is
test-enforced here, and it is the quiet reason the declarant SDK can be ~rules
plus 200 lines rather than a client library that chases the server.

---

## 2. The verifier

### 2a. What is independently re-checkable TODAY

All from a decision record plus the feed (`GET /v2/events?since=`, `GET
/v2/intents/{id}/events`), with no trust in the gate:

1. **Re-derive the TrajectoryHash.** Fetch the per-intent records (ascending
   `intent_seq`, `core/cmd/server/main.go:228-237`); take each record's
   `(intent_seq, type, detail)` triple; apply the Section 6 encoding --
   `<len(seqStr)>:<seqStr>\n<len(Type)>:<Type>\n<len(Detail)>:<Detail>\n`,
   SHA-256, lowercase hex (`core/internal/audit/eventlog.go:69-83`); compare
   to the `trajectory_hash` on the ACHIEVED record. This works because the
   gate mirrors every in-memory event to the feed with `IntentSeq` copied
   unchanged (`core/internal/gate/gate.go:97-106`) and computes the hash over
   the log *including* the ACHIEVED event before emitting the durable record
   that carries it (`gate.go:262-273`). `GlobalSeq` is contractually excluded
   from the hash (CONTRACT.md Section 2.3, Section 6), so the recomputation
   needs no global state.
2. **Confirm hash passthrough.** The ACHIEVED record carries
   `intent_spec_hash` / `rule_artifact_hash` verbatim from the declaration
   (`gate.go:270-271`; wire tags `core/internal/durable/store.go:33-43`). A
   verifier holding the ATLAS artifact can independently re-hash its bytes and
   compare. Note precisely what this proves: the record *claims* these hashes;
   the gate never checked them (P1, Section 2d below).
3. **Terminal / achieved_seq consistency.** `achieved_seq >= 1` iff terminal
   ACHIEVED (CONTRACT.md Section 2.2), and it equals the ACHIEVED record's
   `seq`; the ACHIEVED event orders after the volatile RECHECK by both clocks
   (Section 5.3 row f).
4. **At-most-once evidence.** Scan `GET /v2/events?type=ACHIEVED` from
   `since=0`; group by `idempotency_key`; exactly one record per key
   (invariant 4, Section 5.1; probe row e, Section 5.3). Also checkable:
   `seq` strictly monotonic gap-free across the whole feed (Section 5.4 probe
   2), and no ACHIEVED record exists for any intent whose synchronous terminal
   was FAILED/FAILED_AT_DISPATCH (Section 5.3 row f).
5. **Lifecycle-graph replay.** The per-intent event-type sequence must be a
   walk of the closed transition graph (CONTRACT.md Section 3.1), reasons must
   fall in the closed cause-class set (Section 3.3), and the thin-spec
   refusal shapes are pinned strings (`gate.go:151-168`). Binding to a known
   declaration: `intent_id` = first 16 hex of sha256(EpisodeSeed) (CONTRACT.md
   Section 7.2, `intent.ID()`), and the DECLARED record's `detail` is that id.

```
the verifier's recomputation, from the feed alone

  gate's copy                          verifier's copy (any language)
  -----------                          ------------------------------
  GET /v2/events?since=0
       |
       v
  +----------------+   per intent:     +------------------------------+
  | event records  |   (seq, type,     | re-encode: len:seq \n        |
  | seq, type,     |    detail)        |   len:type \n len:detail \n  |
  | detail, hashes |------------------>| SHA-256 over raw bytes       |
  +----------------+                   | -- no JSON anywhere in the   |
       |                               |    hash path                 |
       |                               +------------------------------+
       |    walk + count                     | compare
       v                                     v
  1. lifecycle is a walk of the        recomputed TrajectoryHash
     closed transition graph      ==   hash on the ACHIEVED record
  2. reasons in the closed
     cause-class set                   achieved_seq == ACHIEVED seq
  3. exactly one ACHIEVED per          claimed spec/rule hashes ==
     idempotency key                     re-hashed artifact bytes
  4. global seq gap-free                 (claimed -- see 2d)
```

### 2b. Where independent implementations WILL silently diverge

- **UTF-8 byte length vs code points.** The Section 6 length prefix is the
  field's *byte* length. A Python implementation using `len(detail)` on a
  `str` diverges the moment any detail carries non-ASCII. Today all details
  are ASCII; nothing pins that.
- **CRLF and torn tails.** The store trims `\r\n` per line and tolerates a
  torn trailing line (`store.go:82`, `store.go:59-104`). A verifier reading
  `events.jsonl` directly (rather than over HTTP) must reproduce exactly that
  tolerance or fail on files the gate itself accepts.
- **Float representation.** Go marshals a `float64` threshold of 100.0 as
  `100` (`core/contract/scorer/request-pass.json:1`); Python's `json.dumps`
  emits `100.0`. This is precisely why the request-fixture byte-identity test
  exists ONLY on the Go side (`scorer_test.go:300-326`) while Python only
  *parses* requests and byte-compares its *responses* (CONTRACT.md Section 9)
  -- each language is the designated serializer of what it emits. The ADR-0003
  float debt (CONTRACT.md Section 2.4, thresholds lossy vs ATLAS exact
  ScalarValue) is the recorded deeper version of this. Design rule for the
  verifier: **parse, compare values, recompute hashes from raw bytes -- never
  re-serialize JSON and compare bytes.** The TrajectoryHash path never touches
  JSON, which is what makes cross-language recomputation feasible at all.
- **Key ordering / whitespace.** `durable.Record`'s field order IS the wire
  order (CONTRACT.md Section 2.3), but only because one serializer (Go)
  produces it. Same rule as above: a verifier that never re-serializes never
  cares.
- **The 10 byte-frozen fixtures as conformance vectors.** The five
  request/response pairs at `core/contract/scorer/` (glob-confirmed, 10
  files) already function as executable cross-language conformance: Go
  asserts byte-identical marshal of each request and correct Score decode of
  each response (`scorer_test.go:300-354`); Python asserts parse + response
  byte-identity (`test_fixtures.py`); absence makes the tests skip *visibly*
  (Section 9). That is exactly the mechanism a verifier package needs -- but
  for a different surface: what is missing is a **golden feed fixture** (a
  frozen `events.jsonl` plus its expected TrajectoryHash and pass/fail
  verdicts), which does not exist today. Proposed, named in Section 4.

### 2c. What a ~200-line verifier package looks like (proposed)

Twin implementations, Go (stdlib) and Python (stdlib), plus a shared fixture
directory, mirroring the Section 9 discipline.

- **Inputs:** (i) an events source -- a `/v2/events` or `/v2/intents/{id}/events`
  response body, or a raw `events.jsonl`; (ii) optionally the original
  declaration (for ID binding) and expected `intent_spec_hash` /
  `rule_artifact_hash` (or the artifact bytes to re-hash); (iii) optionally
  the synchronous `intentResponse` to cross-check.
- **Checks (one function each):** trajectory-hash recompute; lifecycle-graph
  walk; closed-set terminal/reason/cause-class membership; exactly-one-ACHIEVED
  per key; global `seq` monotonicity; `achieved_seq` equality; hash-passthrough
  equality; declaration binding (`intent_id` from seed).
- **Verdict semantics: tri-state, like the gate it audits.** `VERIFIED` /
  `REFUTED` / `UNVERIFIABLE` -- an unparseable line, an unknown event type, a
  missing input is UNVERIFIABLE, never VERIFIED (the verifier-side twin of
  invariant 2's non-vacuity; `verify([]) == UNVERIFIABLE`, echoing the
  scorer's hashless-verify refusal, CONTRACT.md Section 8). Exit code nonzero
  for anything but VERIFIED.
- **Conformance:** both twins must produce identical verdicts and identical
  recomputed hashes over the golden feed fixture, byte-compared in CI, same
  one-commit re-green rule as Section 9.

The ~200-line figure is credible because the hash encoding is ~15 lines
(`eventlog.go:69-83`), the lifecycle graph is a static table, and every check
is a fold over parsed records.

### 2d. The honest trust boundary

What the verifier CANNOT establish today, and which roadmap item buys each:

- **That the record was scored at all.** `force_scores` is a wire-reachable
  total scoring bypass with no guard (CONTRACT.md Section 2.2
  production-posture note; `docs/ROADMAP.md:22`), and the gate emits identical
  `SCORED <name>:PASS` events whichever `scoring.Scorer` answered
  (`gate.go:183-184` -- the scorer's identity never enters the log). A forced
  grant and a live-scored grant are byte-identical in the feed. Closer:
  guarding `force_scores` is a recorded contract change (ROADMAP finding); a
  scorer-identity witness in the log would be a further, currently unrecorded
  step.
- **That the criteria were the attester's.** P1 is asserted, not enforced
  (`README.md:132`): criteria arrive declarant-supplied
  (`main.go:171-177`) and the spec hashes ride opaquely. The verifier can
  check the *claimed* hash against artifact bytes but cannot check that the
  criteria scored match the artifact's contents. Closer: the
  resolver-extraction slice (`docs/ROADMAP.md:25`, next-slices item 2) --
  criteria read from the verified IntentSpec payload, which also retires the
  ADR-0003 float debt.
- **That the log was not rewritten.** `events.jsonl` is unsigned; whoever
  holds the disk (or sits on the unauthenticated read path,
  `docs/ROADMAP.md:23`) could fabricate an internally consistent log --
  internal consistency is exactly what the verifier checks, so consistency
  alone is not provenance. Closer: R1 (DSSE/in-toto signing envelopes,
  blocked on ADR-0009 key authority / RRE ADR-0025) makes records
  tamper-evident; R2 (SPIFFE-style workload identity) makes "the gate is the
  sole writer / cannot sign" a deployment-graph fact instead of prose
  (`docs/ROADMAP.md:13-14`, `README.md:134`).
- **That the facts were true.** Out of scope by design: determinism is
  conditional on scores (CONTRACT.md Section 6); the fact plane is the
  scorer's, and R4's OTel emission is index-only, never authority.

The pitch stays honest in this order: today the package proves *this record is
self-consistent and its hashes recompute*; after resolver-extraction it proves
*the gate executed the signed spec*; after R1/R2 it proves *this gate, and only
this gate, produced it*.

```
what the verifier can prove, by stage

  TODAY                    "this record is self-consistent
    |                       and its hashes recompute"
    |
    + resolver extraction  "the gate executed the signed spec"
    |  (closes P1: criteria read from the verified
    |   IntentSpec payload, not the declarant)
    |
    + R1 record signing    "this record was not rewritten"
    |  (DSSE/in-toto envelopes; tamper-evident log)
    |
    + R2 workload identity "this gate, and only this gate,
       (sole-writer as a    produced it"
        deployment fact)
```

**Addendum (2026-08-04, same day, post-amendment).** The plane-roles
amendment landed after this memo was written and moves two rungs of this
ladder: P1 is now closed GATE-SIDE at test key authority (the wire DTO
carries no criteria field at all; criteria reach the gate only through
signature verification + content-address equality, `CONTRACT.md` Section
2.6), and `force_scores` is now guarded (`INTENT_UNSAFE_FORCE_SCORES=1` at
boot, else a loud 400) AND witnessed (`scorer_id` on every SCORED/RECHECK
feed record, hash-exempt) — the guard+witness pairing this memo's Q1 asked
about, answered "both". Still true as written: R1 production key authority
(envelopes stamp `key_authority: "test"`), R2, the refusal-hash commitment
(Q2), and everything in Section 4's deferred rows. Sections 2d/3f above are
kept as capture-time text; read them with this addendum.

### 2e. Why this consumer justifies byte-identity

Every other consumer needs field *values*: the COMPASS settlement consumer
reads five trace fields and recomputes its own ledger entry
(`treasury/README.md:62-68`); a dashboard reads terminals. Only the verifier
needs the *preimage bytes*: a hash check is exact or it is nothing, and the
comparison crosses a language boundary by definition -- the audit firm does
not run your Go. One byte of encoding wobble does not degrade the check, it
inverts it: a correct record gets REFUTED, and a verifier that cries wolf gets
switched off, which is worse than no verifier. That is why the repo's two
byte-identity investments are exactly the two things the verifier consumes:
the JSON seam frozen as fixture bytes (Section 9) and the hash encoding frozen
as a length-prefixed, injection-safe byte stream (Section 6,
`eventlog.go:53-68`). The verifier SDK is also the sales artifact made
executable: "here is a ~200-line package your audit firm runs against our
records, and here -- in the same README -- is the list of what it cannot yet
prove" is the built-to-be-examined posture (`README.md:130-143`'s
asserted-vs-enforced table) turned into something a counterparty can run.

---

## 3. Platform teams wrapping agent runtimes

### 3a. The pattern on the actual wire

Declare -> await terminal -> proceed-or-surface maps cleanly because
`POST /v2/intents` is synchronous: the gate drives the full lifecycle
in-request and the response carries the terminal (`main.go:188-201`). There is
no async state machine for the framework to build; "await terminal" is an HTTP
round trip.

```
declare -> await terminal -> proceed-or-surface

  agent           framework layer (SDK)              gate
    |                    |                             |
    |  propose action    |                             |
    |------------------->|  POST /v2/intents           |
    |                    |  (derived idempotency key)  |
    |                    |---------------------------->|
    |                    |                             | score fail-closed,
    |                    |   synchronous terminal      | reserve key, emit
    |                    |<----------------------------| one durable record
    |  ACHIEVED: proceed |                             |
    |  refusal: surface  |                             |
    |<-------------------|                             |
    |                    |                             |
    |                    |  GET /v2/events?since=cursor|
    |                    |---------------------------->|
    |                    |  settle / observe ONLY from |
    |                    |  observed ACHIEVED records  |
```

Field ownership in `intentRequest` (CONTRACT.md Section 2.2):

- **Framework-owned:** `episode_seed` (determinism source; derive it, don't
  random it), `idempotency_key` (Section 3b), `spec.idempotency_scope`.
- **Passed through from the artifact plane:** `rule_artifact_hash`,
  `intent_spec_hash` -- opaque, ride to the ACHIEVED record and the scorer's
  resolver.
- **Today declarant-supplied, tomorrow not:** `spec.criteria`. Until the
  resolver-extraction slice, the framework must inject criteria itself --
  the P1 gap lands on exactly this consumer. The SDK should treat criteria
  as config it transports, never as something agent code constructs.
- **Never sent:** `force_scores` (Section 3f).

The decoder rejects unknown fields (`main.go:155`, `dec.DisallowUnknownFields`),
so the SDK must marshal the DTO exactly; any speculative extra field is a 400.
That is a feature for the framework (version skew fails loudly) and a
constraint on SDK evolution (additive changes need a contract amendment first).

### 3b. Idempotency-key construction discipline

The load-bearing fact: **`Reserve` keys on the raw key string alone, across
all intents and scopes** -- "collision (key already reserved, by any intent)"
(CONTRACT.md Section 7.2). `idempotency_scope` is carried data, not a keyspace
partition. Reservations are durable and never expire (`OpenStore` recovers all
keys forever, Section 7.2). So the SDK must encode:

- **Fold scope into the key string.** A good key for tool-call dedup is
  deterministic from the action's identity:
  `<scope>:<agent-run-id>:<tool-name>:<sha256(canonical-args)>`. Proposed
  shape, not doctrine.
- **Never a fresh UUID per attempt** -- a random key makes every retry a new
  action and deletes the dedup property the gate exists to enforce.
- **Never too coarse** -- reservations are permanent, so a key that collides
  across genuinely distinct calls bricks the second call forever.
- **Retry semantics follow reservation position** (`gate.go:244-250`: reserve
  happens after the volatile recheck, before ACHIEVED): a `FAILED` at
  declaration or a `volatile-recheck` at dispatch never reserved the key --
  same-key retry is safe. `ACHIEVED` reserved it -- same-key retry correctly
  collides. `idempotency-collision` means the action already happened (or was
  reserved): reconcile from the feed, never mint a new key to "get past it."
- **The 500 edge.** If `feed.Append` of the ACHIEVED record fails after
  `Reserve` succeeded, the key is reserved but no ACHIEVED record exists; the
  declarant sees HTTP 500 (`main.go:189-192`; CONTRACT.md Section 4.1: "no
  terminal guarantee is implied"). The SDK's 500 handler must consult
  `GET /v2/intents/{id}/events` before deciding anything. This is a real
  stuck-key state with no recorded remediation -- named in Section 4.

### 3c. Terminal-state handling table

What the framework layer should do, per terminal and cause class (Section 3.2,
Section 3.3; reason strings from `gate.go`):

| Terminal / reason | Meaning | Framework action |
|---|---|---|
| `ACHIEVED` (+ `achieved_seq`) | authorized, one durable record exists | proceed with the tool call / hand to executor; optionally confirm via feed (3d) |
| `FAILED`, reason = joined criterion names | criteria bound and failed | surface to agent as policy denial; same-key retry permitted after facts change |
| `FAILED`, `unevaluable:<criterion>` | scorer outage / missing fact | surface as "cannot evaluate"; retry with backoff, same key; never treat as pass |
| `FAILED`, `unevaluable:absent-key` | SDK bug -- key construction failed | fix the SDK; never auto-retry |
| `FAILED`, `unevaluable:empty-criteria` / `unevaluable:invalid-volatility:<name>` | spec malformed (thin-spec defense, step 1b) | route to spec owner, not the agent; never retry unchanged (3e) |
| `FAILED_AT_DISPATCH`, `volatile-recheck:<name>` | fact drifted between scoring and dispatch | surface; same-key re-declare permitted (key was not reserved) |
| `FAILED_AT_DISPATCH`, `idempotency-collision` | this action already happened / was reserved | retry-NEVER with intent to execute; reconcile from feed by key |
| `FAILED_AT_DISPATCH`, `revoked:<ref>` | reserved cause class, not built (CONTRACT.md Section 3.3) | route to surface-and-stop now so the arrival is a no-op |
| HTTP 400 | SDK marshaling bug (unknown field / bad JSON) | fix the SDK |
| HTTP 500 | indeterminate -- possibly reserved key, no ACHIEVED | consult the feed before any retry (3b) |

Every reason above is a closed, prefix-parseable string -- the SDK can switch
on them without regex heroics, and CONTRACT.md Section 3.3 pins that new cause
classes amend the table first.

### 3d. Feed consumption for settlement and observability

- **Cursor discipline:** persist `next_since` durably; resume with
  `?since=<cursor>`; `since=0` replays everything; `type=ACHIEVED` filters
  (`main.go:205-226`; CONTRACT.md Section 2.1). `next_since` echoes the input
  cursor when nothing returned, so the poll loop is a one-liner.
- **Exactly-one-ACHIEVED per key** is the settlement contract; the reference
  consumer pattern (cursor + key-idempotent recompute, poll-safe across
  reopen) is specified at CONTRACT.md Section 5.3 (`feedConsumer`) and ran
  live in COMPASS (`treasury/README.md:62-68`).
- **Why emit-and-observe beats trusting the synchronous response:** the
  response can be lost (crash, timeout, the 500 edge) while the fsynced record
  cannot (`store.go:111-135`, fsync-per-append; restart recovery proven,
  CONTRACT.md Section 5.4 probes 1-3). The gate never calls out; a crash on
  either side loses nothing (`README.md:89-121`). Side effects should key off
  observed ACHIEVED records; the synchronous response is UX, not settlement.
- **Posture caveat the platform team must own:** the feed is unauthenticated
  by design (`docs/ROADMAP.md:23`) -- network isolation is a deployment
  decision that the SDK's docs must state, not hide.

### 3e. Thin-spec refusals as framework UX

The step-1b refusals are the framework's best developer-experience surface:
`unevaluable:empty-criteria` (with the claimed spec hash bound into the event
detail, `gate.go:151-156` -- the refusal record witnesses WHICH spec was thin)
and `unevaluable:invalid-volatility:<name>:<raw>` (`gate.go:162-168`) are
config errors, not runtime denials. The SDK should surface them as build-time
shaped errors to the spec owner -- distinct channel from fact-based denials --
and CONTRACT.md Section 5.1's honesty bounds tell the team what NOT to expect:
thinned sets and semantic mislabeling are upstream (ATLAS / attestation)
territory the gate cannot see.

### 3f. What must NOT be exposed

`force_scores`. It is a wire-reachable **total scoring bypass with no
env/build/auth guard** (CONTRACT.md Section 2.2 production-posture note;
`docs/ROADMAP.md:22`; selection logic `main.go:183-186`). The SDK must not
carry the field in any type, sample, or doc -- but note honestly that SDK
omission is cosmetic while the wire accepts it from anyone; the guard itself
is a recorded contract change that has to happen server-side. Combined with
Section 2d: until guarded, any platform team's compliance story inherits the
qualifier, because the feed cannot show their calls were scored.

---

## 4. What the two consumers demand of the roadmap

Honest verbs: R1-R4 and the findings are recorded intent, none built
(`docs/ROADMAP.md:1-3`). Everything in the "new" rows below is proposed by
this memo, nowhere recorded in the repo.

| Demand | Consumer | Roadmap home |
|---|---|---|
| Guard `force_scores` (contract amendment) | both -- verifier cannot distinguish forced grants; platform compliance inherits the qualifier | existing finding (`docs/ROADMAP.md:22`) |
| Scorer-identity witness in the audit log (so forced vs live scoring is distinguishable in the feed) | verifier | **new** -- strictly stronger than guarding; not recorded anywhere |
| Criteria from the verified spec, not the declarant (P1) | both -- verifier's "executed what was signed"; platform's "don't make me own criteria" | resolver-extraction slice (`docs/ROADMAP.md:25`, next-slices 2) |
| Signed records / tamper-evidence | verifier | R1 (`docs/ROADMAP.md:13`, blocked on ADR-0009/PR#19 key authority) |
| Sole-writer as deployment fact | verifier | R2 (`docs/ROADMAP.md:14`) |
| Durable trajectory-hash commitment for refusal terminals (today ACHIEVED-only, `store.go:39-42`) | verifier | **new** -- contract change to Section 2.3 |
| Golden feed fixture (frozen events.jsonl + expected hash + verdicts) as verifier conformance vector | verifier | **new** -- extends the Section 9 discipline to a second surface |
| The verifier package itself, Go+Python twins | verifier | **new** |
| Fixture neutralization (treasury names in shipped conformance files) | verifier -- these files go to third parties | existing finding (`docs/ROADMAP.md:27`) |
| Declarant SDK: key-derivation, terminal table, 500-edge feed consult, cursor consumer | platform | **new** |
| Stuck-key remediation for the reserve-then-append-fail edge | platform | **new** -- no recorded posture |
| Scope-partitioned keyspace (or a documented ruling that scope stays declarant-folded) | platform | **new** -- decision-shaped, see Q3 |
| Shadow mode for incremental adoption (platform teams will ask; config-toggle is forbidden) | platform | R3 (`docs/ROADMAP.md:15`) |
| Feed authn or a documented isolation posture | platform | existing finding (`docs/ROADMAP.md:23`) |
| OTel index emission | platform (observability) | R4 (`docs/ROADMAP.md:16`) |

Sequencing implication, stated as opinion: the verifier package needs *no*
server changes to be worth building (checks 1-5 of Section 2a work today), and
building it first would surface the encoding-divergence traps (2b) while the
surface is small. The two cheapest server-side wins for the verifier are the
refusal-hash commitment and the scorer-identity witness; both are contract
amendments, neither is blocked on R1/R2.

## 5. Open questions (decision-shaped, max 5)

1. **Guard vs witness for `force_scores`:** is the close an env/build guard
   (recorded finding), a scorer-identity field in the log (verifier-grade,
   new contract surface), or both? Determines whether the verifier can ever
   say "scored" about historical records.
2. **Should refusal terminals durably commit their trajectory hash?** Today
   only ACHIEVED carries it in the feed (`store.go:39-42`). Yes = contract
   amendment to Section 2.3; no = the verifier's refusal story is
   recompute-only, and the memo's Section 2a check 1 stays ACHIEVED-scoped.
3. **Idempotency scope: fold into the key by SDK convention, or partition the
   store keyspace by scope server-side?** The former is a doc rule; the
   latter is a semantic change to `Reserve` (CONTRACT.md Section 7.2) with
   migration weight.
4. **Verifier conformance home:** does the golden feed fixture live under
   `core/contract/` beside the scorer fixtures (same one-commit re-green
   rule), or ship inside the verifier package? Affects the neutrality gate
   and who re-greens on encoding change.
5. **Is the verifier package in-repo (`core/` neutrality applies, Go twin
   shares stdlib rule) or a sibling repo consuming only the wire?** In-repo
   maximizes the fixture discipline; sibling proves the "no trust in the
   gate" claim structurally -- the audit-firm pitch is stronger if the
   verifier cannot even import the gate's code.
