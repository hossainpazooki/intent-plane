# Representation debt escalates when it enters signed, content-addressed bytes

ts: 2026-08-05T04:13:05Z (fresh basis capture at entry-writing time; the
finding itself surfaced during the whole-contract review ~04:00Z)
commit: bec7589 (+ the uncommitted plane-roles amendment worktree)
session: intent-plane-implementation (controller whole-contract review vs the
pitch PDFs; ruling recorded as ADR-0007)
status: verified

fact: The ADR-0003 float-threshold debt was replicated INTO the new signed
spec payload: `plane/spec.go:22` pins `Threshold float64 json:"threshold"`.
A representation flaw in a wire DTO is cheap to migrate; the same flaw inside
content-addressed, attested bytes costs a re-attest-everything migration the
moment real specs exist (every fix changes every hash, and each new hash is a
fresh authority act). The general rule: decide numeric (and any lossy)
representation BEFORE a format becomes signed and content-addressed —
"disposable test-authority specs" is the last cheap moment. Recorded as a
binding trigger, not a tonight-fix: ADR-0007 requires exact-decimal payload
thresholds before ADR-0009 production key authority lands.

basis: `grep -n "Threshold" plane/spec.go` -> `22:	Threshold  float64
`json:"threshold"`` (captured 2026-08-05T04:13:05Z against this worktree);
trigger recorded in docs/adr/2026-08-05-ADR-0007-spec-payload-is-the-signed-object.md
("before ADR-0009 production key authority lands ... exact decimal strings").

re-verify: grep -n "Threshold" plane/spec.go && grep -n "exact decimal" docs/adr/2026-08-05-ADR-0007-spec-payload-is-the-signed-object.md
