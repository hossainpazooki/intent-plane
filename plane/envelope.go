// Package plane defines the signed artifact that crosses every boundary of the
// intent plane: a DSSE-shaped envelope over an IntentSpec payload, the
// content-addressed spec store the control role publishes into, and the
// resolver the gate uses to turn a claimed intent_spec_hash into verified
// criteria bytes.
//
// This package holds VERIFICATION only (public keys). Signing, key generation,
// and every private-key operation live in plane/authority, and the
// contractcheck key-possession boundary pins which packages may import that
// side. "Holds no keys" is a code-graph fact in-repo; the deployment-graph
// half of that claim remains ROADMAP R2, asserted.
//
// Key authority is TEST-GRADE (production key authority is not landed):
// every envelope carries key_authority so provenance keeps saying so.
package plane

import (
	"crypto/ed25519"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
)

// PayloadType is the DSSE payloadType for an intent-plane spec payload.
const PayloadType = "application/vnd.intent-plane.spec+json"

// RevocationPayloadType is the DSSE payloadType for a signed revocation
// tombstone (the payload names the spec hash it revokes and a reason ref).
const RevocationPayloadType = "application/vnd.intent-plane.revocation+json"

// KeyAuthorityTest marks envelopes signed under the in-repo test key
// authority. It is stamped into every signature block and MUST NOT be dropped
// until production key authority lands (ROADMAP R1).
const KeyAuthorityTest = "test"

// Signature is one signature block of an envelope.
type Signature struct {
	KeyID        string `json:"keyid"`
	Sig          string `json:"sig"` // base64(ed25519 over PAE(payloadType, payload))
	KeyAuthority string `json:"key_authority"`
}

// Envelope is the DSSE-shaped signed artifact. Payload is base64 of the raw
// payload bytes; the spec hash is sha256 over those raw bytes, so "the artifact
// a human attested is the artifact the enforcement point executes, byte for
// byte" is a hash equality, not a metaphor.
type Envelope struct {
	PayloadType string      `json:"payloadType"`
	Payload     string      `json:"payload"`
	Signatures  []Signature `json:"signatures"`
}

// PAE is the DSSE v1 pre-authentication encoding: the byte string that is
// actually signed. Length prefixes are BYTE lengths.
func PAE(payloadType string, payload []byte) []byte {
	return fmt.Appendf(nil, "DSSEv1 %d %s %d %s", len(payloadType), payloadType, len(payload), payload)
}

// PayloadBytes decodes the envelope's payload. It does not verify anything.
func (e Envelope) PayloadBytes() ([]byte, error) {
	b, err := base64.StdEncoding.DecodeString(e.Payload)
	if err != nil {
		return nil, fmt.Errorf("plane: payload not base64: %w", err)
	}
	return b, nil
}

// SpecHash is the content address of a payload: lowercase-hex sha256 over the
// raw payload bytes.
func SpecHash(payload []byte) string {
	sum := sha256.Sum256(payload)
	return hex.EncodeToString(sum[:])
}

// KeyIDFor derives the key id of an ed25519 public key: first 16 hex of
// sha256(pubkey bytes).
func KeyIDFor(pub ed25519.PublicKey) string {
	sum := sha256.Sum256(pub)
	return hex.EncodeToString(sum[:])[:16]
}

// TrustRoot maps keyid -> ed25519 public key. The gate verifies against this
// and ONLY this; it holds no signing keys.
type TrustRoot struct {
	Keys map[string]ed25519.PublicKey
}

// trustRootFile is the on-disk shape: {"keys": {"<keyid>": "<b64 pub>"}}.
type trustRootFile struct {
	Keys map[string]string `json:"keys"`
}

// ParseTrustRoot parses the trust-root file bytes.
func ParseTrustRoot(b []byte) (TrustRoot, error) {
	var f trustRootFile
	if err := json.Unmarshal(b, &f); err != nil {
		return TrustRoot{}, fmt.Errorf("plane: trust root: %w", err)
	}
	tr := TrustRoot{Keys: map[string]ed25519.PublicKey{}}
	for id, b64 := range f.Keys {
		raw, err := base64.StdEncoding.DecodeString(b64)
		if err != nil {
			return TrustRoot{}, fmt.Errorf("plane: trust root key %s: %w", id, err)
		}
		if len(raw) != ed25519.PublicKeySize {
			return TrustRoot{}, fmt.Errorf("plane: trust root key %s: bad length %d", id, len(raw))
		}
		tr.Keys[id] = ed25519.PublicKey(raw)
	}
	return tr, nil
}

// ErrUnverified is returned when no signature on an envelope verifies against
// the trust root. Verification is fail-closed: an envelope with zero
// signatures, an unknown keyid, or a bad signature is unverified alike.
var ErrUnverified = errors.New("plane: no signature verifies against the trust root")

// Verify checks the envelope against the trust root and returns the raw
// payload bytes and the keyid that verified. Fail-closed: wrong payloadType,
// undecodable payload, and unverifiable signatures all refuse.
func (e Envelope) Verify(root TrustRoot, wantType string) (payload []byte, keyid string, err error) {
	if e.PayloadType != wantType {
		return nil, "", fmt.Errorf("plane: payloadType %q, want %q", e.PayloadType, wantType)
	}
	payload, err = e.PayloadBytes()
	if err != nil {
		return nil, "", err
	}
	pae := PAE(e.PayloadType, payload)
	for _, s := range e.Signatures {
		pub, ok := root.Keys[s.KeyID]
		if !ok {
			continue
		}
		sig, err := base64.StdEncoding.DecodeString(s.Sig)
		if err != nil {
			continue
		}
		if ed25519.Verify(pub, pae, sig) {
			return payload, s.KeyID, nil
		}
	}
	return nil, "", ErrUnverified
}
