// Package contractcheck mechanically enforces CONTRACT.md: the production
// import adjacency (§7), the role vocabulary (§1), and core neutrality
// (§9). It is
// test-only — it ships no production code, and no package imports it.
//
// P2 ("artifacts are the only crossings") is a deployment claim; what this
// package makes mechanical is its gate-side precondition: the intent interface
// (the four HTTP routes plus the durable feed) is the ONLY surface, because
// every Go package stays under core/internal/ and the intra-repo import graph
// matches the pinned adjacency exactly. Any new edge, any new package outside
// core/internal/ (other than core/cmd/server), or any dropped edge fails here.
package contractcheck

import (
	"go/parser"
	"go/token"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"testing"
)

const modulePrefix = "github.com/pazooki/intent-plane/"

// allowedProd pins the production (non-_test.go) import adjacency, intra-module
// edges only. Keys are the complete set of Go package directories: a package
// missing here — or present here but missing on disk — is a boundary change
// and must be made deliberately, in CONTRACT.md first.
var allowedProd = map[string][]string{
	"core/cmd/server":             {"core/internal/durable", "core/internal/gate", "core/internal/idempotency", "core/internal/intent", "core/internal/scoring"},
	"core/internal/adapter":       {"core/internal/intent"},
	"core/internal/audit":         {},
	"core/internal/contractcheck": {},
	"core/internal/durable":       {},
	"core/internal/gate":          {"core/internal/audit", "core/internal/durable", "core/internal/idempotency", "core/internal/intent", "core/internal/lifecycle", "core/internal/scoring"},
	"core/internal/idempotency":   {"core/internal/intent"},
	"core/internal/intent":        {},
	"core/internal/lifecycle":     {},
	"core/internal/scoring":       {"core/internal/intent"},
}

// allowedTestExtra pins edges that exist ONLY in _test.go files, beyond the
// production adjacency. gate -> adapter is the sanctioned one: the acceptance
// suite drives the TEST-ONLY reference adapter (CONTRACT.md §7.2).
var allowedTestExtra = map[string][]string{
	"core/cmd/server":             {"core/internal/lifecycle"},
	"core/internal/adapter":       {},
	"core/internal/audit":         {},
	"core/internal/durable":       {},
	"core/internal/gate":          {"core/internal/adapter", "core/internal/lifecycle"},
	"core/internal/idempotency":   {},
	"core/internal/intent":        {},
	"core/internal/lifecycle":     {},
	"core/internal/scoring":       {},
	"core/internal/contractcheck": {},
}

// repoRoot walks up from the test's CWD to the directory holding go.mod.
func repoRoot(t *testing.T) string {
	t.Helper()
	dir, err := os.Getwd()
	if err != nil {
		t.Fatalf("Getwd: %v", err)
	}
	for {
		if _, err := os.Stat(filepath.Join(dir, "go.mod")); err == nil {
			return dir
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			t.Fatal("go.mod not found above the test directory")
		}
		dir = parent
	}
}

// skipDir reports directories the walk never descends into: VCS, build output,
// the Python service, and anything hidden.
func skipDir(name string) bool {
	return strings.HasPrefix(name, ".") || name == "bin" || name == "scorer" || name == "data" || name == "docs" || name == "contract"
}

// goPackageDirs returns every directory (repo-relative, slash-separated) that
// contains at least one .go file.
func goPackageDirs(t *testing.T, root string) []string {
	t.Helper()
	seen := map[string]bool{}
	err := filepath.WalkDir(root, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			if path != root && skipDir(d.Name()) {
				return filepath.SkipDir
			}
			return nil
		}
		if strings.HasSuffix(d.Name(), ".go") {
			rel, err := filepath.Rel(root, filepath.Dir(path))
			if err != nil {
				return err
			}
			seen[filepath.ToSlash(rel)] = true
		}
		return nil
	})
	if err != nil {
		t.Fatalf("walk: %v", err)
	}
	dirs := make([]string, 0, len(seen))
	for d := range seen {
		dirs = append(dirs, d)
	}
	sort.Strings(dirs)
	return dirs
}

// intraModuleImports parses every .go file in dir and returns the intra-module
// import sets, split into production and test-only.
func intraModuleImports(t *testing.T, root, dir string) (prod, testOnly map[string]bool) {
	t.Helper()
	prod, testOnly = map[string]bool{}, map[string]bool{}
	entries, err := os.ReadDir(filepath.Join(root, dir))
	if err != nil {
		t.Fatalf("ReadDir(%s): %v", dir, err)
	}
	fset := token.NewFileSet()
	for _, e := range entries {
		if e.IsDir() || !strings.HasSuffix(e.Name(), ".go") {
			continue
		}
		f, err := parser.ParseFile(fset, filepath.Join(root, dir, e.Name()), nil, parser.ImportsOnly)
		if err != nil {
			t.Fatalf("parse %s/%s: %v", dir, e.Name(), err)
		}
		into := prod
		if strings.HasSuffix(e.Name(), "_test.go") {
			into = testOnly
		}
		for _, imp := range f.Imports {
			p := strings.Trim(imp.Path.Value, `"`)
			if strings.HasPrefix(p, modulePrefix) {
				into[strings.TrimPrefix(p, modulePrefix)] = true
			}
		}
	}
	return prod, testOnly
}

func sorted(set map[string]bool) []string {
	out := make([]string, 0, len(set))
	for k := range set {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}

// TestImportBoundary pins the intent interface boundary: the package set and
// its import adjacency match CONTRACT.md §7 exactly.
func TestImportBoundary(t *testing.T) {
	root := repoRoot(t)
	dirs := goPackageDirs(t, root)

	// The package SET is pinned: nothing appears or disappears silently, and
	// nothing lives outside core/internal/ except core/cmd/server.
	want := sorted(func() map[string]bool {
		m := map[string]bool{}
		for k := range allowedProd {
			m[k] = true
		}
		return m
	}())
	if got := strings.Join(dirs, ","); got != strings.Join(want, ",") {
		t.Fatalf("Go package set changed.\n got: %v\nwant: %v\nA new or removed package is a boundary change: amend CONTRACT.md first.", dirs, want)
	}
	for _, d := range dirs {
		if d != "core/cmd/server" && !strings.HasPrefix(d, "core/internal/") {
			t.Errorf("package %q lives outside core/internal/ — only core/cmd/server may be non-internal", d)
		}
	}

	for _, d := range dirs {
		prod, testOnly := intraModuleImports(t, root, d)

		wantProd := map[string]bool{}
		for _, p := range allowedProd[d] {
			wantProd[p] = true
		}
		if got, want := strings.Join(sorted(prod), ","), strings.Join(sorted(wantProd), ","); got != want {
			t.Errorf("%s: production import edges changed.\n got: [%s]\nwant: [%s]", d, got, want)
		}

		wantTest := map[string]bool{}
		for _, p := range allowedTestExtra[d] {
			wantTest[p] = true
		}
		for p := range testOnly {
			if !wantProd[p] && !wantTest[p] {
				t.Errorf("%s: unsanctioned TEST-ONLY import edge -> %s", d, p)
			}
		}
	}
}
