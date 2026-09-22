package plane

import (
	"encoding/json"
	"fmt"
	"strings"
)

// Posture is the enforcement posture carried INSIDE the signed payload.
// Promotion from shadow to enforce is a NEW attestation with a NEW hash — an
// authority act, never a config toggle (governance decision Proposed, not
// ratified; ROADMAP R3's only permitted shadow shape).
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
// Name rules (§2.6, 2026-09-22) are enforced here so that no seal point —
// attest, publish, resolve — can carry a payload whose names would defeat
// the refusal classifier (§2.7) or hide a duplicate under the thin-spec
// defense. Zero criteria still parse: thinness is the gate's refusal.
func ParseSpecPayload(b []byte) (SpecPayload, error) {
	var p SpecPayload
	dec := jsonDecoderStrict(b)
	if err := dec.Decode(&p); err != nil {
		return SpecPayload{}, fmt.Errorf("plane: spec payload: %w", err)
	}
	if err := validateNames(p); err != nil {
		return SpecPayload{}, err
	}
	return p, nil
}

// validateNames: every criterion and human-judgment name is non-empty,
// contains no ':' (the refusal-classification separator), and is unique
// within its list.
func validateNames(p SpecPayload) error {
	check := func(kind string, names []string) error {
		seen := make(map[string]bool, len(names))
		for _, n := range names {
			switch {
			case n == "":
				return fmt.Errorf("plane: spec payload: empty %s name", kind)
			case strings.Contains(n, ":"):
				return fmt.Errorf("plane: spec payload: %s name %q contains ':'", kind, n)
			case seen[n]:
				return fmt.Errorf("plane: spec payload: duplicate %s name %q", kind, n)
			}
			seen[n] = true
		}
		return nil
	}
	crit := make([]string, len(p.Criteria))
	for i, c := range p.Criteria {
		crit[i] = c.Name
	}
	if err := check("criterion", crit); err != nil {
		return err
	}
	hj := make([]string, len(p.HumanJudgment))
	for i, h := range p.HumanJudgment {
		hj[i] = h.Name
	}
	return check("human_judgment", hj)
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
