// Package intent holds the pure-data description of an authorization intent.
// Intent carries no mutable lifecycle state; the gate's runtime owns the state
// machine.
package intent

import (
	"crypto/sha256"
	"encoding/hex"
)

// Volatility marks whether a criterion is scored once (stable) or re-verified at
// the dispatch edge (volatile).
type Volatility string

const (
	Stable   Volatility = "stable"
	Volatile Volatility = "volatile"
)

// Phase identifies which scoring pass a criterion is being scored in.
type Phase string

const (
	Declaration Phase = "declaration" // first scoring pass
	Dispatch    Phase = "dispatch"    // volatile re-verify at the dispatch edge
)

// Criterion is one named condition the intent must satisfy.
type Criterion struct {
	Name       string
	Threshold  float64
	Volatility Volatility
}

// IdempotencyKey is the required at-most-once key for an intent.
type IdempotencyKey string

// Posture is the enforcement posture carried inside the ATTESTED spec payload
// (never a config toggle). Zero value is invalid: an unknown posture refuses
// (unevaluable-shaped absence), so a caller that forgets to resolve posture
// authorizes nothing.
type Posture string

const (
	PostureEnforce Posture = "enforce"
	PostureShadow  Posture = "shadow"
)

// Resolution records how the spec content was obtained. Attested is set ONLY
// by the plane resolver after signature verification and content-address
// equality; the zero value refuses at the gate (P1: no verified spec, no
// scoring). RevokedRef carries the ref of a verified revocation tombstone
// found at declaration time.
type Resolution struct {
	Attested   bool
	Source     string // "store" | "wire" | "" when unattested
	KeyID      string // attester keyid (author of record)
	RevokedRef string
}

// IntentSpecParams carries the criteria/thresholds/idempotency the gate consumes
// directly (no artifact reads in this slice).
type IntentSpecParams struct {
	ActionClass      string // domain action class, from the ATTESTED payload
	Criteria         []Criterion
	IdempotencyScope string  // e.g. "per-actor"
	Posture          Posture // from the ATTESTED payload; unknown refuses
	// HumanJudgment names the payload's unresolved deliberately-unquantified
	// obligations. Non-empty NEVER authorizes: the gate refuses
	// `unevaluable:human-judgment:<first>` — abstention as a success state.
	HumanJudgment []string
}

// Intent is pure data. It carries NO mutable lifecycle state; the gate's runtime
// owns the state machine. The three audit hashes are opaque to this slice.
type Intent struct {
	EpisodeSeed      string // determinism source; the intent ID derives from this
	Spec             IntentSpecParams
	IdempotencyKey   IdempotencyKey // required; "" is invalid
	RuleArtifactHash string         // opaque
	IntentSpecHash   string         // content address of the attested spec payload
	Resolution       Resolution     // how Spec was obtained; zero value refuses
}

// ID is deterministically derived from EpisodeSeed (stable across runs). It is
// the hex prefix of sha256(EpisodeSeed).
func (i Intent) ID() string {
	sum := sha256.Sum256([]byte(i.EpisodeSeed))
	return hex.EncodeToString(sum[:])[:16]
}
