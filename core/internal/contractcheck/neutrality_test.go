package contractcheck

// Core-neutrality gate (repositioning design 2026-08-03 §7): core/ is the
// domain-agnostic intent plane; treasury vocabulary lives only under
// treasury/. "settlement" is ruled CORE vocabulary (the generic
// consequence-commit named by invariants 4-5) and is deliberately not listed.
//
// Exemptions, each byte-pinned or fixture-coupled — NOT judgment calls:
//   - core/contract/scorer/       frozen wire fixtures (criterion "balance")
//   - core/internal/scoring/scorer_test.go   embeds those fixture bytes
//   - core/scorer/tests/test_fixtures.py     reproduces those fixture bytes
// Regenerating the fixtures with neutral names is a recorded ROADMAP
// follow-up; until then the exemption is explicit here.

import (
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"testing"
)

var treasuryNouns = regexp.MustCompile(`(?i)\b(payments?|treasury|payers?|balance|fx[_-]rate|sanctions?|invoices?)\b`)

var neutralityExemptFiles = map[string]bool{
	"core/internal/scoring/scorer_test.go": true,
	"core/scorer/tests/test_fixtures.py":   true,
}

func TestCoreNeutrality(t *testing.T) {
	root := repoRoot(t)
	coreRoot := filepath.Join(root, "core")
	err := filepath.WalkDir(coreRoot, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			name := d.Name()
			if strings.HasPrefix(name, ".") || name == "__pycache__" || name == "data" {
				return filepath.SkipDir
			}
			rel, _ := filepath.Rel(root, path)
			if filepath.ToSlash(rel) == "core/contract/scorer" {
				return filepath.SkipDir
			}
			return nil
		}
		if !strings.HasSuffix(d.Name(), ".go") && !strings.HasSuffix(d.Name(), ".md") && !strings.HasSuffix(d.Name(), ".py") {
			return nil
		}
		rel, _ := filepath.Rel(root, path)
		relSlash := filepath.ToSlash(rel)
		// A gate's own pattern literal is not an occurrence: this file carries
		// the treasury-noun regex, and internal_refs_test.go carries the
		// banned-internal-reference literals (one of which embeds "treasury").
		if neutralityExemptFiles[relSlash] || d.Name() == "neutrality_test.go" || d.Name() == "internal_refs_test.go" {
			return nil
		}
		b, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		if m := treasuryNouns.Find(b); m != nil {
			t.Errorf("%s: treasury noun %q in core/ — domain vocabulary belongs under treasury/ (design 2026-08-03 §7)", relSlash, string(m))
		}
		return nil
	})
	if err != nil {
		t.Fatalf("walk: %v", err)
	}
}
