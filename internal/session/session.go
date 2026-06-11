// Package session defines the provider-agnostic session schema shared by
// providers, renderers, the TUI, and the exec dispatcher.
package session

// TokenUsage aggregates assistant-turn usage across a session.
type TokenUsage struct {
	Input       int64 `json:"input"`
	Output      int64 `json:"output"`
	CacheRead   int64 `json:"cache_read"`
	CacheCreate int64 `json:"cache_create"`
	Turns       int64 `json:"turns"`
}

// Prompt is one user prompt with its timestamp (empty string when unknown).
type Prompt struct {
	TS   string
	Text string
}

// Session is the common schema. String fields use "" for "absent" (the
// Python implementation used None); render/json restores explicit nulls.
type Session struct {
	Source       string
	SessionID    string
	Path         string
	ProjectLabel string
	Cwd          string
	FirstTS      string
	LastTS       string
	Title        string
	Subtitle     string
	FirstPrompt  string
	LastPrompt   string
	Prompts      []Prompt
	AsstCount    int
	Tokens       *TokenUsage // nil when no assistant turns carried usage
	ResumeArgv   []string
}

// Filters mirrors the CLI surface. Days < 0 means "unset" (provider default).
type Filters struct {
	Days    int
	Date    string
	AllTime bool
	Project string
	Limit   int
	Source  string
}
