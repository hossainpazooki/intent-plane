// Package lifecycle defines the intent authorization state machine: the set of
// states and the legal transitions between them.
package lifecycle

// State is a single node in the intent lifecycle graph.
type State string

const (
	Declared         State = "DECLARED"
	Resolving        State = "RESOLVING"
	Active           State = "ACTIVE"
	Verifying        State = "VERIFYING"
	Achieved         State = "ACHIEVED"
	Failed           State = "FAILED"
	FailedAtDispatch State = "FAILED_AT_DISPATCH"
	// ShadowRecorded is the terminal of a shadow-posture intent: fully scored,
	// durably recorded, and NOT authorized (ADR-0006, Proposed).
	ShadowRecorded State = "SHADOW_RECORDED"
)

// IsTerminal reports whether s is one of ACHIEVED, FAILED, FAILED_AT_DISPATCH,
// SHADOW_RECORDED.
// Terminal states have no outgoing edges.
func (s State) IsTerminal() bool {
	switch s {
	case Achieved, Failed, FailedAtDispatch, ShadowRecorded:
		return true
	default:
		return false
	}
}
