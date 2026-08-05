package plane

import (
	"os"
	"testing"
)

// RemoveEnvFileForTest deletes the stored envelope body for hash, leaving the
// pin — a test hook for exercising the hybrid wire path.
func RemoveEnvFileForTest(t *testing.T, s *Store, hash string) {
	t.Helper()
	if err := os.Remove(s.path(hash, ".env.json")); err != nil {
		t.Fatal(err)
	}
}
