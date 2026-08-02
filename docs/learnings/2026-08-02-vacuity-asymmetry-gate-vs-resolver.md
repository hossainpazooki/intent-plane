ts: 2026-08-02T16:58:38Z
commit: 93d2a6d
session: intent-plane gate implementation (spec-governed)

fact: The Go gate carried the exact `all([]) == true` fail-open vacuity that the
Python resolver had already recognized and closed. A declaration with ZERO
criteria (nil or empty, `"criteria": []` or the field omitted) reached ACHIEVED
with all four trace fields populated — the scoring loop is vacuous, the volatile
recheck loop is vacuous, the key reserves, ACHIEVED emits. Sharpest form: the
ZERO-CONFIG server ("TIC_SCORER_URL unset: gate refuses everything") ACHIEVEs
exactly this request, because refusal lives in the scorer and the scorer is
never consulted. Meanwhile `scorer/src/tis/resolver.py` verify() refuses a
hashless call for the stated reason that `all([])` is True and answering True
would be a fail-open edge. Same repo, same structural situation, opposite
treatment — the guard existed as an idiom in one language and was missing in
the other. A criterion with a typo'd volatility ("volatil", or the field
omitted → "") was silently treated as stable and skipped the dispatch-edge
re-verify: the adjacent unknown-kind hole.

basis: red-first probes against the unmodified gate at `93d2a6d` (recorded
2026-08-02T16:58:38Z): `TestFailClosedEmptyCriteria` 3/3 sub-tests FAILED with
"a spec with zero criteria must never reach ACHIEVED";
`TestEmptyCriteriaRefusedOverWire` showed the durable feed holding two ACHIEVED
records with full trace fields for zero-criteria bodies on a zero-config server;
`TestFailClosedInvalidVolatility` 2/2 FAILED with ACHIEVED and zero RECHECK
events. All probes green after gate step 1b (CONTRACT-INTERFACE §I.3).

re-verify: `go test ./internal/gate -run 'TestFailClosedEmptyCriteria|TestFailClosedInvalidVolatility' -count=1`
and `go test ./cmd/server -run 'RefusedOverWire' -count=1` — green on the fixed
tree; to reproduce the red, revert the step-1b block in internal/gate/gate.go
in a TEMP COPY and watch all five fail with ACHIEVED.

lesson: when a fail-closed guard exists in one language of a polyglot seam,
grep the other side for the same shape before trusting symmetry — aggregation
vacuity (`all([])`, `len(failed) > 0` falling through) is invisible to every
per-item fail-closed test, and only a zero-item probe exercises it.
