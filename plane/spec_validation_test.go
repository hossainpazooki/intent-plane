package plane_test

import (
	"strings"
	"testing"

	"github.com/hossainpazooki/intent-plane/plane"
)

// Name rules at parse (CONTRACT.md §2.6, 2026-09-22): a criterion or
// human-judgment name is non-empty, contains no ':' and is unique within its
// list. Enforced at ParseSpecPayload so attest, publish and resolve cannot
// seal a payload the refusal classifier would read as Unknown.
func TestParseSpecPayloadNameRules(t *testing.T) {
	const head = `{"spec_version":1,"action_class":"t","enforcement_posture":"shadow",`
	cases := []struct {
		name    string
		body    string
		wantErr string // "" = must parse
	}{
		{"two distinct names parse", `"criteria":[{"name":"a","threshold":1,"volatility":"stable"},{"name":"b","threshold":1,"volatility":"stable"}]}`, ""},
		{"zero criteria still parse (thin-spec is the gate's refusal)", `"criteria":[]}`, ""},
		{"empty criterion name", `"criteria":[{"name":"","threshold":1,"volatility":"stable"}]}`, "empty criterion name"},
		{"duplicate criterion name", `"criteria":[{"name":"a","threshold":1,"volatility":"stable"},{"name":"a","threshold":2,"volatility":"volatile"}]}`, `duplicate criterion name "a"`},
		{"colon in criterion name", `"criteria":[{"name":"a:b","threshold":1,"volatility":"stable"}]}`, `criterion name "a:b" contains ':'`},
		{"empty human_judgment name", `"criteria":[],"human_judgment":[{"name":"","passage_sha256":"x"}]}`, "empty human_judgment name"},
		{"duplicate human_judgment name", `"criteria":[],"human_judgment":[{"name":"h","passage_sha256":"x"},{"name":"h","passage_sha256":"y"}]}`, `duplicate human_judgment name "h"`},
		{"colon in human_judgment name", `"criteria":[],"human_judgment":[{"name":"h:1","passage_sha256":"x"}]}`, `human_judgment name "h:1" contains ':'`},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			_, err := plane.ParseSpecPayload([]byte(head + tc.body))
			switch {
			case tc.wantErr == "" && err != nil:
				t.Fatalf("want parse, got %v", err)
			case tc.wantErr != "" && err == nil:
				t.Fatalf("want refusal containing %q, got nil", tc.wantErr)
			case tc.wantErr != "" && !strings.Contains(err.Error(), tc.wantErr):
				t.Fatalf("want refusal containing %q, got %q", tc.wantErr, err.Error())
			}
		})
	}
}
