package plane

import (
	"encoding/json"
	"fmt"
)

// Posture is the enforcement posture carried INSIDE the signed payload.
// Promotion from shadow to enforce is a NEW attestation with a NEW hash — an
// authority act, never a config toggle (ADR-0006, Proposed; ROADMAP R3's only
// permitted shadow shape).
type Posture string

const (
	PostureEnforce Posture = "enforce"
	PostureShadow  Posture = "shadow"
)

// CriterionSpec is one machine-checkable criterion of an attested spec.
type CriterionSpec struct {
	Name       string  `json:"name"`
	Threshold  float64 `json:"threshold"`
	Volatility string  `json:"volatility"` // "stable" | "volatile"
}

// SourcePin binds a drafted value to the policy passage it came from:
// passage_sha256 is sha256 over the exact passage bytes the author read.
type SourcePin struct {
	Name          string `json:"name"`
	PassageSHA256 string `json:"passage_sha256"`
}

// NamedUnknown is an unmapped provision surfaced by the authoring role rather
// than silently omitted.
type NamedUnknown struct {
	ProvisionID   string `json:"provision_id"`
	PassageSHA256 string `json:"passage_sha256"`
	Note          string `json:"note,omitempty"`
}

// HumanJudgment is a deliberately-unquantified obligation routed to a
// human-judgment check instead of an invented number. A spec carrying any
// unresolved human-judgment entry NEVER authorizes: the gate refuses it
// `unevaluable:human-judgment:<name>` — abstention as a success state (P6).
type HumanJudgment struct {
	Name          string `json:"name"`
	PassageSHA256 string `json:"passage_sha256"`
}

// SpecPayload is the payload of a spec envelope. Its raw bytes are the content
// address: intent_spec_hash = sha256(payload bytes). Drafts share this shape
// unsigned; attestation wraps the same bytes in an envelope.
type SpecPayload struct {
	SpecVersion   int             `json:"spec_version"`
	ActionClass   string          `json:"action_class"`
	Posture       Posture         `json:"enforcement_posture"`
	Criteria      []CriterionSpec `json:"criteria"`
	SourcePins    []SourcePin     `json:"source_pins,omitempty"`
	NamedUnknowns []NamedUnknown  `json:"named_unknowns,omitempty"`
	HumanJudgment []HumanJudgment `json:"human_judgment,omitempty"`
}

// ParseSpecPayload parses verified payload bytes. Unknown fields refuse (the
// payload is a contract surface like the wire: version skew fails loudly).
func ParseSpecPayload(b []byte) (SpecPayload, error) {
	var p SpecPayload
	dec := jsonDecoderStrict(b)
	if err := dec.Decode(&p); err != nil {
		return SpecPayload{}, fmt.Errorf("plane: spec payload: %w", err)
	}
	return p, nil
}

// RevocationPayload is the payload of a signed revocation tombstone.
type RevocationPayload struct {
	Revoke string `json:"revoke"` // the spec hash being revoked
	Ref    string `json:"ref"`    // reason reference carried into `revoked:<ref>`
}

// ParseRevocationPayload parses verified tombstone payload bytes.
func ParseRevocationPayload(b []byte) (RevocationPayload, error) {
	var p RevocationPayload
	dec := jsonDecoderStrict(b)
	if err := dec.Decode(&p); err != nil {
		return RevocationPayload{}, fmt.Errorf("plane: revocation payload: %w", err)
	}
	return p, nil
}

func jsonDecoderStrict(b []byte) *json.Decoder {
	dec := json.NewDecoder(bytesReader(b))
	dec.DisallowUnknownFields()
	return dec
}
