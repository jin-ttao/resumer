// Package gemini parses Gemini CLI session JSONL files under
// ~/.gemini/tmp/<project-hash>/chats.
package gemini

import (
	"bufio"
	"encoding/json"
	"io/fs"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"time"

	"github.com/jin-ttao/resumer/internal/session"
	"github.com/jin-ttao/resumer/internal/textutil"
)

const envSessionRoot = "RESUMER_GEMINI_SESSION_ROOT"

const maxLineBytes = 10 << 20

var sessionFileRE = regexp.MustCompile(`^session-.*\.jsonl$`)

func sessionRoot() string {
	if v := os.Getenv(envSessionRoot); v != "" {
		return v
	}
	home, _ := os.UserHomeDir()
	return filepath.Join(home, ".gemini", "tmp")
}

// Provider implements provider.Provider for Gemini CLI.
type Provider struct{}

func New() *Provider {
	return &Provider{}
}

func (p *Provider) Name() string      { return "gemini" }
func (p *Provider) Badge() string     { return "gemini" }
func (p *Provider) BadgeANSI() string { return "\x1b[34m" } // blue

func (p *Provider) IsAvailable() bool {
	st, err := os.Stat(sessionRoot())
	return err == nil && st.IsDir()
}

// geminiContentPart is one part of a Gemini message content array.
type geminiContentPart struct {
	Text string `json:"text"`
}

// geminiRecord is one line of a Gemini JSONL session file.
type geminiRecord struct {
	Type       string          `json:"type"`
	SessionID  string          `json:"sessionId"`
	StartTime  string          `json:"startTime"`
	LastUpdated string         `json:"lastUpdated"`
	Content    json.RawMessage `json:"content"`
	Timestamp  string          `json:"timestamp"`
	Payload    json.RawMessage `json:"payload"`
}

// extractText pulls readable text out of a content field, which may be a
// plain string or an array of {text: "..."} parts (as the real Gemini CLI
// writes).
func extractText(content json.RawMessage) string {
	if len(content) == 0 {
		return ""
	}
	var parts []geminiContentPart
	if err := json.Unmarshal(content, &parts); err == nil {
		var texts []string
		for _, part := range parts {
			if t := strings.TrimSpace(part.Text); t != "" {
				texts = append(texts, t)
			}
		}
		if len(texts) > 0 {
			return strings.Join(texts, "\n")
		}
	}
	var s string
	if err := json.Unmarshal(content, &s); err == nil {
		return strings.TrimSpace(s)
	}
	return ""
}

// parseJSONL parses one Gemini JSONL session file. Returns nil if the file
// has no valid session metadata.
func (p *Provider) parseJSONL(path string) *session.Session {
	var sessionID, startTime, lastUpdated string
	var prompts []session.Prompt

	f, err := os.Open(path)
	if err != nil {
		return nil
	}
	defer f.Close()

	sc := bufio.NewScanner(f)
	sc.Buffer(make([]byte, 0, 64<<10), maxLineBytes)
	for sc.Scan() {
		var r geminiRecord
		if err := json.Unmarshal(sc.Bytes(), &r); err != nil {
			continue
		}
		if r.SessionID != "" && sessionID == "" {
			sessionID = r.SessionID
		}
		if r.StartTime != "" && startTime == "" {
			startTime = r.StartTime
		}
		if r.LastUpdated != "" {
			lastUpdated = r.LastUpdated
		}
		if r.Type == "user" {
			text := extractText(r.Content)
			if text != "" {
				prompts = append(prompts, session.Prompt{
					TS:   r.Timestamp,
					Text: text,
				})
			}
		}
	}

	if sessionID == "" {
		return nil
	}

	firstPrompt, lastPrompt := "", ""
	if len(prompts) > 0 {
		firstPrompt = prompts[0].Text
		lastPrompt = prompts[len(prompts)-1].Text
	}

	// Project label from the session file's parent directory name.
	projectLabel := filepath.Base(filepath.Dir(filepath.Dir(path)))
	if projectLabel == "" || projectLabel == "." {
		projectLabel = "(unknown)"
	}

	return &session.Session{
		Source:       "gemini",
		SessionID:    sessionID,
		Path:         path,
		ProjectLabel: projectLabel,
		FirstTS:      startTime,
		LastTS:       lastUpdated,
		Title:        "",
		FirstPrompt:  firstPrompt,
		LastPrompt:   lastPrompt,
		Prompts:      prompts,
		ResumeArgv:   []string{"gemini", "--resume", sessionID},
	}
}

func findSessionFiles(root string) []string {
	var out []string
	_ = filepath.WalkDir(root, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return nil
		}
		if !d.IsDir() && sessionFileRE.MatchString(d.Name()) {
			out = append(out, path)
		}
		return nil
	})
	return out
}

func touchesDate(s *session.Session, day time.Time) bool {
	start := time.Date(day.Year(), day.Month(), day.Day(), 0, 0, 0, 0, time.UTC)
	end := start.Add(23*time.Hour + 59*time.Minute + 59*time.Second)
	fs_, okF := textutil.ParseISO(s.FirstTS)
	ls, okL := textutil.ParseISO(s.LastTS)
	if !okF && !okL {
		return false
	}
	if !okF {
		fs_ = ls
	}
	if !okL {
		ls = fs_
	}
	return !(ls.Before(start) || fs_.After(end))
}

func cutoffForFilters(f session.Filters) *time.Time {
	if f.AllTime || f.Date != "" {
		return nil
	}
	days := f.Days
	if days < 0 {
		days = 3
	}
	now := time.Now()
	midnight := time.Date(now.Year(), now.Month(), now.Day(), 0, 0, 0, 0, now.Location())
	cutoff := midnight.AddDate(0, 0, -days)
	return &cutoff
}

func (p *Provider) ListSessions(f session.Filters) ([]session.Session, error) {
	root := sessionRoot()
	cutoff := cutoffForFilters(f)
	var day *time.Time
	if f.Date != "" {
		if d, err := time.ParseInLocation("2006-01-02", f.Date, time.UTC); err == nil {
			day = &d
		}
	}

	var out []session.Session
	// Walk every <root>/<hash>/chats/ directory for session-*.jsonl files.
	_ = filepath.WalkDir(root, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return nil
		}
		if d.IsDir() {
			return nil
		}
		if !sessionFileRE.MatchString(d.Name()) {
			return nil
		}
		s := p.parseJSONL(path)
		if s == nil {
			return nil
		}
		if f.Project != "" &&
			!strings.Contains(strings.ToLower(s.ProjectLabel), strings.ToLower(f.Project)) {
			return nil
		}
		if day != nil {
			if !touchesDate(s, *day) {
				return nil
			}
		} else if cutoff != nil {
			ls, ok := textutil.ParseISO(s.LastTS)
			if !ok || ls.Before(*cutoff) {
				return nil
			}
		}
		out = append(out, *s)
		return nil
	})
	return out, nil
}

func (p *Provider) LoadDetail(id string) (*session.Session, error) {
	var found *session.Session
	_ = filepath.WalkDir(sessionRoot(), func(path string, d fs.DirEntry, err error) error {
		if err != nil || found != nil {
			return nil
		}
		if d.IsDir() || !sessionFileRE.MatchString(d.Name()) {
			return nil
		}
		s := p.parseJSONL(path)
		if s != nil && s.SessionID == id {
			found = s
		}
		return nil
	})
	if found == nil {
		return nil, nil
	}
	return found, nil
}

// ensure Provider implements the interface at compile time.
