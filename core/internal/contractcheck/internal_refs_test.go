package contractcheck

// Internal-reference gate (CONTRACT.md migration section, amendments
// 2026-08-16 and 2026-08-18). This repository is public; names and document
// numbers that resolve only inside the maintainers' private estate are pinned
// at zero across tracked source, docs, scripts, and data. A hit is a
// regression, not a style issue: it either leaks an internal codename or
// hands a public reader a reference they cannot follow. That is the whole
// rationale as of the 2026-09-15 fold: the pin was first written to stop a
// mechanical port from a second, private copy of these trees from reverting
// the scrub, and there is no longer a second copy — but incoming work still
// arrives carrying private names, and this gate is what catches it. It is
// exempt nowhere, in any directory.

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// TestInternalReferencesAbsent: every banned internal reference is pinned at
// zero. Matching is case-sensitive on purpose — each entry is an exact
// internal spelling, and a case-folded match would invite false positives.
func TestInternalReferencesAbsent(t *testing.T) {
	root := repoRoot(t)

	banned := []string{
		"ATLAS",        // retired codename (scrubbed 2026-08-16)
		"COMPASS",      // retired codename (scrubbed 2026-08-16)
		"SCORER_ATLAS", // retired env-var prefix (renamed 2026-08-16, shim-free)
		"treasury-intent-controller", // a cross-project identifier this tree must not reference, by design
		"regulatory-rule-engine",     // a cross-project identifier this tree must not reference, by design
		"ke-cli",                     // that project's CLI ("ke_artifact_py", the wheel, is a real dependency and stays)
		"ADR-00",                     // private decision-record numbers (de-numbered 2026-08-18)
	}

	exts := map[string]bool{
		".go": true, ".md": true, ".py": true, ".sh": true, ".ps1": true,
		".json": true, ".jsonl": true, ".toml": true, ".yml": true, ".yaml": true,
	}

	err := filepath.WalkDir(root, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			name := d.Name()
			// Skip untracked/local trees: dot-dirs, build output, venvs, the
			// release staging dir, and the local-only planning dir — the pin
			// governs what the repo SHIPS, and those never ship.
			if path != root && (strings.HasPrefix(name, ".") || name == "bin" ||
				name == "data" || name == "dist" || name == "superpowers" ||
				name == "node_modules" || strings.HasSuffix(name, ".egg-info") ||
				name == "__pycache__") {
				return filepath.SkipDir
			}
			return nil
		}
		if !exts[filepath.Ext(d.Name())] {
			return nil
		}
		// CLAUDE.md is local-only (untracked by design); this file's own
		// banned-string literals are not occurrences.
		if d.Name() == "CLAUDE.md" || d.Name() == "internal_refs_test.go" {
			return nil
		}
		b, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		s := string(b)
		for _, ref := range banned {
			if idx := strings.Index(s, ref); idx >= 0 {
				rel, _ := filepath.Rel(root, path)
				line := 1 + strings.Count(s[:idx], "\n")
				t.Errorf("%s:%d: banned internal reference %q — this repo is public; describe the thing by role, never by internal name or number (CONTRACT.md migration section)", rel, line, ref)
			}
		}
		return nil
	})
	if err != nil {
		t.Fatalf("walk: %v", err)
	}
}
