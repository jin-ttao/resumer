//go:build unix

// Package execres wraps the final process-replacement step behind a build
// tag so a future Windows port can swap in run-and-exit semantics without
// touching callers.
package execres

import (
	"fmt"
	"os"
	"syscall"
)

// Exec replaces the current process with argv. path must be the resolved
// absolute binary path (syscall.Exec does not search PATH). Returns an exit
// code only if exec itself failed.
func Exec(path string, argv []string) int {
	if err := syscall.Exec(path, argv, os.Environ()); err != nil {
		fmt.Fprintf(os.Stderr, "error: exec %s: %v\n", path, err)
		return 1
	}
	return 0 // unreachable
}
