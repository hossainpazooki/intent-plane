# intent-verify — the examiner's kit

You have been handed an `events.jsonl` feed by a team running the
intent-plane gate, and this kit. You do not need to trust their gate, their
platform, or this project: the binary here re-derives every commitment from
the record bytes alone (CONTRACT.md §9.1), and a byte-frozen fixture pair
lets you watch it refuse a tampered record before you point it at theirs.

## Three commands

```sh
# 1. A known-good feed verifies (exit 0, canonical report to stdout):
./intent-verify fixtures/events-good.jsonl

# 2. The same feed with ONE byte flipped (PASS -> PAST) refutes (exit 1):
./intent-verify fixtures/events-tampered.jsonl

# 3. The feed you were actually handed:
./intent-verify path/to/their/events.jsonl
```

The expected outputs of commands 1 and 2 ship in this kit
(`fixtures/report-good.txt`, `fixtures/report-tampered.txt`) — diff against
them. Exit codes: `0` VERIFIED, `1` anything else (refuted or unverifiable —
unverifiable never passes), `2` usage/IO error.

## What a VERIFIED report proves — and what it does not, yet

Proves today: the record is **self-consistent** — every per-intent
trajectory hash recomputes from the record bytes, terminal commitments are
present where required, and the verdict is tri-state fail-closed (an empty
or unreadable feed is UNVERIFIABLE, never verified).

Not yet provable, stated rather than hidden (`docs/assurance.md`, stage
table): that the log was **never rewritten** (record signing is staged, R1)
— a consistently rewritten log would verify today; and that the gate was the
**sole writer** (workload identity, R2). Signatures in the wider system are
test-grade and say so on every envelope (`key_authority: "test"`).

A second, independent implementation of this verifier ships in the same
repository (`verifier/pyverifier/`): pure-stdlib Python (its only imports
are `hashlib`, `json`, `sys`), held byte-identical to the Go lane on the
same frozen fixture pair. The Go verifier tree is mechanically import-pinned
to run none of the gate's code; the Python twin is held to the same reading
by the fixtures. Recompute with both if you want to distrust the examiner
too.

## Integrity of this kit

`SHA256SUMS` in the kit root covers every kit file except itself; verify
with `sha256sum -c SHA256SUMS`. That check proves the kit you hold is the
kit that was assembled — it is not, by itself, a claim about who assembled
it.

To rebuild a binary from source and compare hashes, check out the commit in
`VERSION`, use the exact toolchain version recorded there, and use **this
exact flag set**:

```sh
CGO_ENABLED=0 GOOS=<os> GOARCH=<arch> go build \
    -trimpath -buildvcs=false -ldflags=-buildid= \
    ./verifier/cmd/intent-verify
```

All three flags are load-bearing, and each was measured on the same commit
and toolchain:

- **`-trimpath`** — a plain build embeds the builder's absolute checkout
  path in the binary.
- **`-buildvcs=false`** — building inside a git checkout stamps
  `vcs.revision`/`vcs.time`/`vcs.modified` and resolves the module to a VCS
  pseudo-version, while building from an extracted source archive stamps
  none of it and resolves to `(devel)`. Left on, the same source produces
  different bytes depending on whether *you* have a `.git` directory.
- **`-ldflags=-buildid=`** — Go stamps a build ID whose action-ID component
  varies with the build directory even under `-trimpath`. This is why two
  builds of identical source can differ in exactly 59 bytes while agreeing
  on every other byte and on the build ID's own content component.

A different Go toolchain patch release will also change the bytes; that is
why `VERSION` records `go env GOVERSION` alongside the commit.

If your rebuild does not match, the fixture checks above are the stronger
evidence and stand on their own: they are recomputed from the record bytes
by the binary in your hand, and do not depend on reproducing anyone else's
build environment.
