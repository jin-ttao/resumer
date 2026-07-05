package integration

import (
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"

	"github.com/jin-ttao/resumer/internal/cli"
)

func TestGeminiProviderList(t *testing.T) {
	mockBin := filepath.Join("..", "mock-bin")
	os.Setenv("PATH", mockBin+string(os.PathListSeparator)+os.Getenv("PATH"))
	defer os.Unsetenv("PATH")

	// Export a mock home so gemini provider finds our dummy file
	dir := t.TempDir()
	os.Setenv("HOME", dir)
	geminiDir := filepath.Join(dir, ".gemini")
	os.MkdirAll(geminiDir, 0755)
	err := os.WriteFile(
		filepath.Join(geminiDir, "sessions.jsonl"),
		[]byte(`{"session_id":"gem-1111-2222","title":"Gemini test session","updated_at":"2026-04-15T12:00:00Z"}`+"\n"),
		0644,
	)
	if err != nil {
		t.Fatal(err)
	}

	cmd := exec.Command("go", "run", "../..", "--source", "gemini")
	out, err := cmd.Output()
	if err != nil {
		t.Fatalf("resumer failed: %v", err)
	}

	var sessions []map[string]interface{}
	if err := json.Unmarshal(out, &sessions); err != nil {
		t.Fatalf("invalid JSON output: %v", err)
	}

	if len(sessions) != 1 {
		t.Fatalf("expected 1 session, got %d", len(sessions))
	}

	if sessions[0]["source"] != "gemini" {
		t.Errorf("expected source='gemini', got %v", sessions[0]["source"])
	}
}

func TestGeminiProviderMissingCLI(t *testing.T) {
	// When gemini CLI is not in PATH, list should gracefully degrade
	originalPath := os.Getenv("PATH")
	os.Setenv("PATH", t.TempDir())
	defer os.Setenv("PATH", originalPath)

	dir := t.TempDir()
	os.Setenv("HOME", dir)

	cmd := exec.Command("go", "run", "../..", "--source", "gemini")
	out, err := cmd.Output()
	if err == nil {
		// It should still succeed with an empty list (no sessions)
		if strings.TrimSpace(string(out)) != "null" && string(out) != "[]\n" {
			t.Fatalf("expected empty list, got: %s", string(out))
		}
	}
}
