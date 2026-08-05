package plane

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
)

func bytesReader(b []byte) io.Reader { return bytes.NewReader(b) }

// Store is the content-addressed spec store the control role publishes into
// and the gate resolves from. Layout under dir:
//
//	<hash>.env.json      published spec envelope (content-addressed)
//	<hash>.pin           pin marker: {"pin": "<hash>", "keyid": "<attester>"}
//	<hash>.revoked.json  SIGNED revocation tombstone envelope
//
// The store carries no wallclock anywhere, matching the plane's no-wallclock
// determinism rule. Publish is attest-then-write: only verified envelopes
// whose payload hashes to their own name enter the store.
type Store struct {
	dir  string
	root TrustRoot
}

var hashRe = regexp.MustCompile(`^[0-9a-f]{64}$`)

// OpenStore opens (creating if needed) a spec store rooted at dir, verified
// against root.
func OpenStore(dir string, root TrustRoot) (*Store, error) {
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return nil, fmt.Errorf("plane: open store: %w", err)
	}
	return &Store{dir: dir, root: root}, nil
}

func (s *Store) path(hash, suffix string) string { return filepath.Join(s.dir, hash+suffix) }

// Publish verifies env against the trust root, checks the payload's content
// address, and writes it as <hash>.env.json plus its pin marker. It returns
// the hash. Fail-closed: an unverifiable envelope never enters the store.
func (s *Store) Publish(env Envelope) (string, error) {
	payload, keyid, err := env.Verify(s.root, PayloadType)
	if err != nil {
		return "", err
	}
	if _, err := ParseSpecPayload(payload); err != nil {
		return "", err
	}
	hash := SpecHash(payload)
	raw, err := json.Marshal(env)
	if err != nil {
		return "", err
	}
	if err := os.WriteFile(s.path(hash, ".env.json"), raw, 0o644); err != nil {
		return "", err
	}
	pin, _ := json.Marshal(map[string]string{"pin": hash, "keyid": keyid})
	if err := os.WriteFile(s.path(hash, ".pin"), pin, 0o644); err != nil {
		return "", err
	}
	return hash, nil
}

// Pinned reports whether hash has a pin marker (the hybrid rule's store-side
// authority for wire-supplied envelopes).
func (s *Store) Pinned(hash string) bool {
	if !hashRe.MatchString(hash) {
		return false
	}
	_, err := os.Stat(s.path(hash, ".pin"))
	return err == nil
}

// Revoke verifies a revocation tombstone envelope and writes it beside the
// spec it revokes. The tombstone itself is a signed artifact of the plane.
func (s *Store) Revoke(tomb Envelope) (RevocationPayload, error) {
	payload, _, err := tomb.Verify(s.root, RevocationPayloadType)
	if err != nil {
		return RevocationPayload{}, err
	}
	rp, err := ParseRevocationPayload(payload)
	if err != nil {
		return RevocationPayload{}, err
	}
	if !hashRe.MatchString(rp.Revoke) {
		return RevocationPayload{}, fmt.Errorf("plane: revoke target %q is not a spec hash", rp.Revoke)
	}
	raw, err := json.Marshal(tomb)
	if err != nil {
		return RevocationPayload{}, err
	}
	if err := os.WriteFile(s.path(rp.Revoke, ".revoked.json"), raw, 0o644); err != nil {
		return RevocationPayload{}, err
	}
	return rp, nil
}

// RevokedRef returns (ref, true) iff a VERIFIED revocation tombstone exists
// for hash. An unverifiable tombstone is ignored (it is not a revocation; it
// is litter) — but the spec it fails to revoke still only authorizes if its
// own envelope verifies.
func (s *Store) RevokedRef(hash string) (string, bool) {
	if !hashRe.MatchString(hash) {
		return "", false
	}
	raw, err := os.ReadFile(s.path(hash, ".revoked.json"))
	if err != nil {
		return "", false
	}
	var tomb Envelope
	if err := json.Unmarshal(raw, &tomb); err != nil {
		return "", false
	}
	payload, _, err := tomb.Verify(s.root, RevocationPayloadType)
	if err != nil {
		return "", false
	}
	rp, err := ParseRevocationPayload(payload)
	if err != nil || rp.Revoke != hash {
		return "", false
	}
	return rp.Ref, true
}

// Resolution is what the gate receives for a declared intent: the verified
// payload, where it came from, and which key attested it.
type Resolution struct {
	Payload SpecPayload
	Source  string // "store" | "wire"
	KeyID   string
}

// ErrUnattested means no verified, pinned spec exists for the claimed hash:
// not in the store, and no wire envelope that verifies AND is pinned. The
// gate maps this to `unevaluable:unattested-spec` — unevaluable never passes.
var ErrUnattested = errors.New("plane: unattested spec")

// RevokedError carries the ref of a verified revocation tombstone.
type RevokedError struct{ Ref string }

func (e RevokedError) Error() string { return "plane: spec revoked: " + e.Ref }

// Resolve turns a claimed intent_spec_hash (plus an optional wire envelope)
// into verified criteria bytes, hybrid rule: the store is authoritative; a
// wire envelope is accepted ONLY if it verifies against the same trust root,
// its payload hashes to the claimed hash, AND that hash is pinned in the
// store. Bare criteria cannot arrive here at all — the wire DTO has no such
// field (P1 closed at the type level).
func (s *Store) Resolve(hash string, wireEnv []byte) (Resolution, error) {
	if !hashRe.MatchString(hash) {
		return Resolution{}, ErrUnattested
	}
	if ref, ok := s.RevokedRef(hash); ok {
		return Resolution{}, RevokedError{Ref: ref}
	}
	// Store path.
	if raw, err := os.ReadFile(s.path(hash, ".env.json")); err == nil {
		var env Envelope
		if err := json.Unmarshal(raw, &env); err != nil {
			return Resolution{}, ErrUnattested
		}
		payload, keyid, err := env.Verify(s.root, PayloadType)
		if err != nil || SpecHash(payload) != hash {
			return Resolution{}, ErrUnattested
		}
		p, err := ParseSpecPayload(payload)
		if err != nil {
			return Resolution{}, ErrUnattested
		}
		return Resolution{Payload: p, Source: "store", KeyID: keyid}, nil
	}
	// Wire path (hybrid): verified AND pinned, else unattested.
	if len(wireEnv) > 0 && s.Pinned(hash) {
		var env Envelope
		if err := json.Unmarshal(wireEnv, &env); err != nil {
			return Resolution{}, ErrUnattested
		}
		payload, keyid, err := env.Verify(s.root, PayloadType)
		if err != nil || SpecHash(payload) != hash {
			return Resolution{}, ErrUnattested
		}
		p, err := ParseSpecPayload(payload)
		if err != nil {
			return Resolution{}, ErrUnattested
		}
		return Resolution{Payload: p, Source: "wire", KeyID: keyid}, nil
	}
	return Resolution{}, ErrUnattested
}
