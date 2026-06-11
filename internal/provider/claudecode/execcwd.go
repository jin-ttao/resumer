package claudecode

// Resume cwd resolution.
//
// claude --resume <uuid> derives the project dir from the CURRENT cwd by
// encoding it (/, space, ~ all become -) and looking under
// ~/.claude/projects/<encoded>/. The cwd stored in the JSONL can be stale or
// mismatched against the file's actual location (observed with iCloud and
// Obsidian vault paths), making the resume fail. Defense: derive cwd from the
// session file's encoded parent dir, which is always correct because it is
// where claude stored the file.

import (
	"os"
	"path/filepath"
	"strings"
)

// maxWalkDepth guards against symlink loops; typical iCloud paths are ~8 deep.
const maxWalkDepth = 15

var cwdReplacer = strings.NewReplacer("/", "-", " ", "-", "~", "-")

// encodeCwd mimics Claude Code's cwd → project-dir encoding.
func encodeCwd(path string) string {
	return "-" + cwdReplacer.Replace(strings.TrimLeft(path, "/"))
}

func isDir(path string) bool {
	st, err := os.Stat(path)
	return err == nil && st.IsDir()
}

// ResolveExecCwd finds a filesystem dir whose encoding matches the session's
// encoded parent dir. Returns "" if no match.
//
// Fast path: storedCwd already encodes to the target (99%+ of sessions).
// Slow path: walk from / matching segment encodings, permission errors
// swallowed, depth limited.
func ResolveExecCwd(sessionPath, storedCwd string) string {
	return resolveExecCwdFrom("/", sessionPath, storedCwd)
}

// resolveExecCwdFrom is the testable form: walks from root instead of /.
func resolveExecCwdFrom(root, sessionPath, storedCwd string) string {
	encoded := filepath.Base(filepath.Dir(sessionPath))
	if !strings.HasPrefix(encoded, "-") {
		return ""
	}
	if storedCwd != "" && isDir(storedCwd) && encodeCwd(storedCwd) == encoded {
		return storedCwd
	}
	target := strings.TrimLeft(encoded, "-")
	return walkEncoded(root, target, 0)
}

func walkEncoded(current, remaining string, depth int) string {
	if depth > maxWalkDepth {
		return ""
	}
	if remaining == "" {
		if isDir(current) {
			return current
		}
		return ""
	}
	entries, err := os.ReadDir(current)
	if err != nil {
		return ""
	}
	for _, e := range entries {
		enc := cwdReplacer.Replace(e.Name())
		if remaining == enc {
			full := filepath.Join(current, e.Name())
			if isDir(full) {
				return full
			}
			return "" // exact-name match that isn't a dir ends this level
		}
		if strings.HasPrefix(remaining, enc+"-") {
			full := filepath.Join(current, e.Name())
			if isDir(full) {
				if hit := walkEncoded(full, remaining[len(enc)+1:], depth+1); hit != "" {
					return hit
				}
			}
		}
	}
	return ""
}
