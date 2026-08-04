package contractcheck

// Vocabulary gate (CONTRACT.md §1). The plane's four roles — declarant
// (declares intents), author (drafts, holds no keys), attester (human author of
// record), gate (deterministic, sole ACHIEVED authority) — are the normative
// actor vocabulary.
//
// Deliberately NOT gated: the repo's existing non-actor senses — HTTP "client",
// Go-doc "caller", build-meta "agent"/"owner", WSL "user" — were audited
// (2026-08-02 sweep) and none denotes an actor role. A gate stricter than the
// vocabulary it protects only produces false positives, and always-false
// alarms get silenced.

import (
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"testing"
)

// TestRoleVocabularyPresent: the normative docs speak the role vocabulary.
func TestRoleVocabularyPresent(t *testing.T) {
	root := repoRoot(t)
	for _, doc := range []string{"README.md", "CONTRACT.md"} {
		b, err := os.ReadFile(filepath.Join(root, doc))
		if err != nil {
			t.Fatalf("read %s: %v (the normative docs are part of the interface)", doc, err)
		}
		low := strings.ToLower(string(b))
		for _, term := range []string{"declarant", "attester", "gate"} {
			if !strings.Contains(low, term) {
				t.Errorf("%s: required role term %q absent", doc, term)
			}
		}
	}
}

// TestForbiddenActorNouns: actor nouns outside the role vocabulary are pinned
// at zero across Go source and markdown.
func TestForbiddenActorNouns(t *testing.T) {
	root := repoRoot(t)
	forbidden := regexp.MustCompile(`(?i)\b(principals?|requesters?)\b`)

	err := filepath.WalkDir(root, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			name := d.Name()
			if path != root && (strings.HasPrefix(name, ".") || name == "bin" || name == "data" || name == ".venv") {
				return filepath.SkipDir
			}
			return nil
		}
		if !strings.HasSuffix(d.Name(), ".go") && !strings.HasSuffix(d.Name(), ".md") && !strings.HasSuffix(d.Name(), ".py") {
			return nil
		}
		if d.Name() == "vocab_test.go" {
			return nil // the gate's own pattern literal is not an occurrence
		}
		b, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		if m := forbidden.Find(b); m != nil {
			rel, _ := filepath.Rel(root, path)
			t.Errorf("%s: forbidden actor noun %q — the role vocabulary is declarant/author/attester/gate", rel, string(m))
		}
		return nil
	})
	if err != nil {
		t.Fatalf("walk: %v", err)
	}
}

// TestRetiredProperNouns: the pre-repositioning concept name must not creep
// back into the normative docs (design 2026-08-03 §2 — the noun "interface"
// is reserved, lowercase, for the contract surface).
func TestRetiredProperNouns(t *testing.T) {
	root := repoRoot(t)
	for _, doc := range []string{"README.md", "CONTRACT.md"} {
		b, err := os.ReadFile(filepath.Join(root, doc))
		if err != nil {
			t.Fatalf("read %s: %v", doc, err)
		}
		if strings.Contains(string(b), "Intent Interface") {
			t.Errorf("%s: retired proper noun \"Intent Interface\" — say \"the intent plane\" (position) or \"the interface\" (contract surface, lowercase)", doc)
		}
	}
}
