// Seat-owned tests for the authoring chassis. Like treasury/flow_test.go they
// build the REAL binary and exec it: no production code is imported from
// this package main, and none was refactored for testability.
package main_test

import (
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

var authoringBin string

func TestMain(m *testing.M) {
	dir, err := os.MkdirTemp("", "authoring-bin")
	if err != nil {
		panic(err)
	}
	exe := ""
	if runtime.GOOS == "windows" {
		exe = ".exe"
	}
	authoringBin = filepath.Join(dir, "authoring"+exe)
	if out, err := exec.Command("go", "build", "-o", authoringBin, ".").CombinedOutput(); err != nil {
		panic("build authoring: " + err.Error() + "\n" + string(out))
	}
	code := m.Run()
	os.RemoveAll(dir)
	os.Exit(code)
}

func run(t *testing.T, args ...string) (out string, ok bool) {
	t.Helper()
	b, err := exec.Command(authoringBin, args...).CombinedOutput()
	return string(b), err == nil
}

func write(t *testing.T, path, body string) {
	t.Helper()
	if err := os.WriteFile(path, []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}
}

// A source whose provisions map to two criteria of the same name would draft
// a payload the parser refuses (§2.6 name rules). The chassis refuses at
// draft time, before any file is written, with the parser's own reason.
func TestDraftRefusesDuplicateCriterionName(t *testing.T) {
	dir := t.TempDir()
	src := filepath.Join(dir, "policy.json")
	out := filepath.Join(dir, "draft.json")
	write(t, src, `{"action_class":"t","provisions":[
	 {"id":"p1","passage":"one","criterion":{"name":"x","threshold":1,"volatility":"stable"}},
	 {"id":"p2","passage":"two","criterion":{"name":"x","threshold":2,"volatility":"stable"}}]}`)
	got, ok := run(t, "draft", "-source", src, "-out", out)
	if ok {
		t.Fatalf("draft with a duplicate criterion name succeeded:\n%s", got)
	}
	if !strings.Contains(got, `duplicate criterion name "x"`) {
		t.Fatalf("refusal does not carry the parser's reason:\n%s", got)
	}
	if _, err := os.Stat(out); err == nil {
		t.Fatal("a refused draft was still written")
	}
}

// The happy path still writes a payload the parser accepts.
func TestDraftWritesParseablePayload(t *testing.T) {
	dir := t.TempDir()
	src := filepath.Join(dir, "policy.json")
	out := filepath.Join(dir, "draft.json")
	write(t, src, `{"action_class":"t","provisions":[
	 {"id":"p1","passage":"one","criterion":{"name":"x","threshold":1,"volatility":"stable"}}]}`)
	if got, ok := run(t, "draft", "-source", src, "-out", out); !ok {
		t.Fatalf("draft failed:\n%s", got)
	}
	if _, err := os.Stat(out); err != nil {
		t.Fatalf("draft not written: %v", err)
	}
}
