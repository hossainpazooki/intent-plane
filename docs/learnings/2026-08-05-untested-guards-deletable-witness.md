# Untested guards are deletable with every gate green

ts: 2026-08-05T04:04:30Z (approximate to the minute; the plant-red basis below
was captured in this session between the skeptic report at 03:57:02Z and the
04:10 handoff close)
commit: bec7589 (+ the uncommitted plane-roles amendment worktree this entry
describes; the amendment was not yet committed anywhere)
session: intent-plane-implementation (Claude Code, 2026-08-04/05; skeptic =
fable `rigor:skeptic-verifier` teammate, plant-red re-proof by controller)
status: verified

fact: The plane-roles amendment red-first-tested every new REFUSAL path but
shipped its GUARDS untested — the loud-400 unknown-field contract, the
`force_scores` flag-off refusal, and the `scorer_id` feed witness were claimed
in three docs and exercised by zero tests. Consequence proven, not argued: the
witness stamping could be deleted entirely with the FULL Go suite and both
quickstarts staying green (the determinism test zeroed the field before
comparing; empty==empty passed). Refusals get tested because they are the
feature; guards get assumed because they are the frame — the twin-red
discipline has to be pointed at both.

basis: Skeptic F3: "I removed the stamping lines entirely in the copy and the
FULL Go suite stayed green". Controller re-proof after adding the positive
assertion — sed-deleted `rec.ScorerID = g.scorerID` in a temp COPY, ran
`go test ./core/cmd/server -run TestDeterminismConditionalOnScores`:
"FAIL github.com/pazooki/intent-plane/core/cmd/server 1.513s" (real tree
untouched). Pins now: `wire_guard_test.go` (3 tests) + the positive witness
assertion, CONTRACT.md §5.3 row (h).

re-verify: D=$(mktemp -d) && cp -r core plane go.mod "$D"/ && cd "$D" && sed -i 's/rec.ScorerID = g.scorerID/_ = g.scorerID/' core/internal/gate/gate.go && go test ./core/cmd/server -run TestDeterminismConditionalOnScores -count=1; cd - && rm -rf "$D"   # expect FAIL
