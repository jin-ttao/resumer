package gemini

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/jin-ttao/resumer/internal/session"
)

func absFixture(t *testing.T) string {
	t.Helper()
	abs, err := filepath.Abs(filepath.Join("..", "..", "..", "tests", "fixtures", "gemini", "sessions"))
	if err != nil {
		t.Fatalf("abs fixture root: %v", err)
	}
	return abs
}

func TestGeminiNameBadge(t *testing.T) {
	p := New()
	if got := p.Name(); got != "gemini" {
		t.Errorf("Name() = %q, want %q", got, "gemini")
	}
	if got := p.Badge(); got != "gemini" {
		t.Errorf("Badge() = %q, want %q", got, "gemini")
	}
	if got := p.BadgeANSI(); got != "\x1b[34m" {
		t.Errorf("BadgeANSI() = %q, want %q", got, "\x1b[34m")
	}
}

func TestGeminiListSessions(t *testing.T) {
	root := absFixture(t)
	os.Setenv("RESUMER_GEMINI_SESSION_ROOT", root)
	t.Cleanup(func() { os.Unsetenv("RESUMER_GEMINI_SESSION_ROOT") })

	p := New()
	ss, err := p.ListSessions(session.Filters{AllTime: true})
	if err != nil {
		t.Fatalf("ListSessions: %v", err)
	}
	if len(ss) != 2 {
		t.Fatalf("ListSessions returned %d sessions, want 2 (%+v)", len(ss), ss)
	}
	ids := map[string]bool{}
	for _, s := range ss {
		ids[s.SessionID] = true
		if s.ResumeArgv[0] != "gemini" || s.ResumeArgv[1] != "--resume" || len(s.ResumeArgv) != 3 {
			t.Errorf("session %q ResumeArgv = %v, want [gemini --resume <id>]", s.SessionID, s.ResumeArgv)
		}
	}
	if !ids["gemini-session-001"] {
		t.Error("missing gemini-session-001")
	}
	if !ids["gemini-session-002"] {
		t.Error("missing gemini-session-002")
	}
}

func TestGeminiLoadDetail(t *testing.T) {
	root := absFixture(t)
	os.Setenv("RESUMER_GEMINI_SESSION_ROOT", root)
	t.Cleanup(func() { os.Unsetenv("RESUMER_GEMINI_SESSION_ROOT") })

	p := New()
	s, err := p.LoadDetail("gemini-session-001")
	if err != nil {
		t.Fatalf("LoadDetail: %v", err)
	}
	if s == nil {
		t.Fatal("LoadDetail returned nil for existing session")
	}
	if s.SessionID != "gemini-session-001" {
		t.Errorf("LoadDetail SessionID = %q, want %q", s.SessionID, "gemini-session-001")
	}
	if len(s.Prompts) != 3 {
		t.Errorf("LoadDetail Prompts = %d, want 3", len(s.Prompts))
	}
	if s.FirstPrompt != "Hello Gemini" {
		t.Errorf("FirstPrompt = %q, want %q", s.FirstPrompt, "Hello Gemini")
	}
	if s.LastPrompt != "Thank you" {
		t.Errorf("LastPrompt = %q, want %q", s.LastPrompt, "Thank you")
	}
	if s.LastTS != "2026-10-01T12:30:00Z" {
		t.Errorf("LastTS = %q, want %q", s.LastTS, "2026-10-01T12:30:00Z")
	}
}

func TestGeminiLoadDetailMissing(t *testing.T) {
	root := absFixture(t)
	os.Setenv("RESUMER_GEMINI_SESSION_ROOT", root)
	t.Cleanup(func() { os.Unsetenv("RESUMER_GEMINI_SESSION_ROOT") })

	p := New()
	s, err := p.LoadDetail("nonexistent-session")
	if err != nil {
		t.Fatalf("LoadDetail missing: %v", err)
	}
	if s != nil {
		t.Errorf("LoadDetail for missing session = %v, want nil", s)
	}
}

func TestGeminiIsAvailableMissingRoot(t *testing.T) {
	os.Setenv("RESUMER_GEMINI_SESSION_ROOT", filepath.Join(t.TempDir(), "nonexistent"))
	t.Cleanup(func() { os.Unsetenv("RESUMER_GEMINI_SESSION_ROOT") })

	p := New()
	if p.IsAvailable() {
		t.Error("IsAvailable() = true, want false when root missing")
	}
}

func TestGeminiParseJSONLMetadata(t *testing.T) {
	root := absFixture(t)
	os.Setenv("RESUMER_GEMINI_SESSION_ROOT", root)
	t.Cleanup(func() { os.Unsetenv("RESUMER_GEMINI_SESSION_ROOT") })

	p := New()
	path := filepath.Join(root, "abc123", "chats", "session-2026-10-01T10-00-gemini-session-001.jsonl")
	s := p.parseJSONL(path)
	if s == nil {
		t.Fatal("parseJSONL returned nil")
	}
	if s.SessionID != "gemini-session-001" {
		t.Errorf("SessionID = %q, want %q", s.SessionID, "gemini-session-001")
	}
	if s.FirstTS != "2026-10-01T10:00:00Z" {
		t.Errorf("FirstTS = %q, want %q", s.FirstTS, "2026-10-01T10:00:00Z")
	}
	if s.LastTS != "2026-10-01T12:30:00Z" {
		t.Errorf("LastTS = %q, want %q", s.LastTS, "2026-10-01T12:30:00Z")
	}
}
