//go:build !unix

package execres

import (
	"fmt"
	"os"
	"os/exec"
)

// Exec runs argv as a child process and returns its exit code (non-unix
// platforms have no execve; Windows support is roadmap).
func Exec(path string, argv []string) int {
	cmd := exec.Command(path, argv[1:]...)
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		if ee, ok := err.(*exec.ExitError); ok {
			return ee.ExitCode()
		}
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	}
	return 0
}
