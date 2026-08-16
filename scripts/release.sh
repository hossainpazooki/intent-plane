#!/bin/sh
# Assemble the auditor kit for verifier/cmd/intent-verify.
# Cross-compiles (stdlib only, CGO off), packages the byte-frozen fixture
# pair, self-verifies with the host-native binary, writes SHA256SUMS.
# Exit 0 ONLY if the good fixture verifies byte-exactly and the tampered
# fixture refutes.
#
# Build flags are load-bearing for reproducibility and are documented in
# verifier/KIT.md. All three are required for an auditor rebuilding from a
# source archive to land on the same bytes:
#   -trimpath          drops the builder's absolute checkout path
#   -buildvcs=false    drops git stamping, which is present in a checkout
#                      and absent from an extracted archive
#   -ldflags=-buildid= drops the build ID, whose action-ID component varies
#                      with the build directory even under -trimpath
# Measured 2026-08-16: without the last two, a checkout build and an archive
# build of identical source differ while agreeing on every content byte.
set -eu

cd "$(dirname "$0")/.."
SHA=$(git rev-parse --short HEAD)
KIT="dist/intent-verify-kit-$SHA"
BUILDFLAGS="-trimpath -buildvcs=false -ldflags=-buildid="
rm -rf "$KIT"
mkdir -p "$KIT/fixtures"

for target in linux/amd64 linux/arm64 darwin/arm64 windows/amd64; do
    GOOS=${target%/*}
    GOARCH=${target#*/}
    ext=""
    if [ "$GOOS" = "windows" ]; then
        ext=".exe"
    fi
    echo "build $GOOS/$GOARCH"
    # shellcheck disable=SC2086
    CGO_ENABLED=0 GOOS="$GOOS" GOARCH="$GOARCH" \
        go build $BUILDFLAGS -o "$KIT/intent-verify-$GOOS-$GOARCH$ext" \
        ./verifier/cmd/intent-verify
done

# byte-frozen fixtures: plain cp, never rewrite
cp core/contract/feed/events-good.jsonl \
   core/contract/feed/events-tampered.jsonl \
   core/contract/feed/report-good.txt \
   core/contract/feed/report-tampered.txt \
   "$KIT/fixtures/"
cp verifier/KIT.md "$KIT/README.md"
# VERSION records commit, toolchain AND flags: rebuild-to-same-hash requires
# all three (see the flag notes above).
printf 'commit %s\ntoolchain %s\nbuildflags %s\n' \
    "$SHA" "$(go env GOVERSION)" "$BUILDFLAGS" > "$KIT/VERSION"

# self-verify with the host-native binary
HOST_GOOS=$(go env GOOS)
HOST_GOARCH=$(go env GOARCH)
hostext=""
if [ "$HOST_GOOS" = "windows" ]; then
    hostext=".exe"
fi
BIN="$KIT/intent-verify-$HOST_GOOS-$HOST_GOARCH$hostext"

"$BIN" "$KIT/fixtures/events-good.jsonl" > "$KIT/.report-good.out"
diff "$KIT/.report-good.out" "$KIT/fixtures/report-good.txt"
if "$BIN" "$KIT/fixtures/events-tampered.jsonl" > "$KIT/.report-tampered.out"; then
    echo "FATAL: tampered fixture did NOT refute" >&2
    exit 1
fi
diff "$KIT/.report-tampered.out" "$KIT/fixtures/report-tampered.txt"
rm -f "$KIT/.report-good.out" "$KIT/.report-tampered.out"

# list files explicitly: a bare ./* glob would include the fixtures/ DIR
# and sha256sum errors on directories, killing the script under set -e
( cd "$KIT" && sha256sum intent-verify-* README.md VERSION fixtures/* > SHA256SUMS )
echo "kit OK: $KIT (good=VERIFIED byte-exact, tampered=refuted)"
