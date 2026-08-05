# An import-boundary gate pins the seam, not the capability

ts: 2026-08-05T03:57:02Z (delivery stamp of the skeptic report whose probe is
the basis)
commit: bec7589 (+ the uncommitted plane-roles amendment worktree)
session: intent-plane-implementation (fable `rigor:skeptic-verifier` teammate
probe, adopted by controller)
status: refuted-assumption

fact: README's P3 row claimed "authoring and the gate structurally cannot
sign — an import-graph fact." Refuted as written: `TestKeyPossessionBoundary`
pins access to `plane/authority`'s key operations only; stdlib
`crypto/ed25519` + `os.ReadFile` compile in `authoring/` with the entire
contractcheck package green — stdlib is invisible to an intra-module import
walk by design. What the graph proves is "cannot reach the plane's signing
SEAM"; "cannot sign at all" is a deployment-graph claim (workload identity,
R2). Boundary tests pin architecture, not capability — word the claim at the
seam.

basis: Skeptic F4: "I added a function to the copy's authoring using stdlib
crypto/ed25519 + os.ReadFile on a key file: it builds and the entire
contractcheck package stays GREEN". README P3 row reworded same day to
"structurally cannot reach the plane's signing seam"; the test's own doc
comment already said "in-repo approximation".

re-verify: grep -n "signing seam" README.md   # the reworded row; to re-probe the refutation, add an ed25519 import to a COPY's authoring/main.go and run go test ./core/internal/contractcheck — expect green
