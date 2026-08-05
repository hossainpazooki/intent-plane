# Split patches are proven equivalent by reverse-checking the full patch

ts: 2026-08-05T03:50:00Z (approximate to a few minutes; captured immediately
after unzipping the patch archive, before the gates ran)
commit: bec7589 (clean tree at capture; the patches under test became the
uncommitted worktree)
session: intent-plane-implementation (controller, landing the web-session
patch zip)
status: verified

fact: When a change arrives as one full patch PLUS per-concern splits, the
splits' fidelity is provable, not assumable: apply the splits in sequence,
then run `git apply --check --reverse` with the FULL patch. It succeeds iff
the applied tree is byte-identical to what the full patch would have
produced — any divergence (dropped hunk, reordered context, hand-edited
split) fails the reverse-check. This turns "the five commits equal the one
diff" from a claim into a two-second proof, before any commit exists.

basis: Applied 01..05 splits from patch_files.zip (9+8+2+13+5 files,
1199+449+241+167+420 insertions per split stat), then:
`git apply --check --reverse .../2026-08-04-plane-roles-amendment.patch` ->
exit 0, echoed "YES - applied splits reproduce the full patch exactly". The
full patch had independently passed `git apply --check` on the clean tree first
(37 files, +2476/-245, matching the sender's claim exactly).

re-verify: with the zip still at C:/Users/hossa/Downloads/patch_files.zip and a scratch clone at bec7589: apply 01..05 in order, then `git apply --check --reverse 2026-08-04-plane-roles-amendment.patch` — expect exit 0
