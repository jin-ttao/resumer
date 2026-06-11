package provider

import (
	"sort"
	"testing"

	"github.com/jin-ttao/resumer/internal/session"
)

func mk(last, source, path string) session.Session {
	return session.Session{LastTS: last, Source: source, Path: path}
}

func ids(ss []session.Session) []string {
	var out []string
	for _, s := range ss {
		out = append(out, s.Path)
	}
	return out
}

func TestSortSessionsDescending(t *testing.T) {
	ss := []session.Session{
		mk("2026-04-15T01:00:00Z", "claude-code", "a"),
		mk("2026-04-15T07:00:00Z", "codex", "b"),
		mk("2026-04-15T03:00:00Z", "claude-code", "c"),
	}
	SortSessions(ss, false)
	got := ids(ss)
	want := []string{"b", "c", "a"}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("descending order = %v, want %v", got, want)
		}
	}
}

func TestSortSessionsAscendingIsReverse(t *testing.T) {
	ss := []session.Session{
		mk("2026-04-15T01:00:00Z", "claude-code", "a"),
		mk("2026-04-15T07:00:00Z", "codex", "b"),
		mk("2026-04-15T03:00:00Z", "claude-code", "c"),
	}
	SortSessions(ss, true)
	got := ids(ss)
	want := []string{"a", "c", "b"}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("ascending order = %v, want %v", got, want)
		}
	}
}

func TestSortSessionsStrictWeakOrderingOnTies(t *testing.T) {
	// Fully equal elements must not panic and must keep a stable, valid
	// order in both directions (the comparator must return false for
	// equal pairs — regression guard for the ascending !less bug).
	var ss []session.Session
	for i := 0; i < 50; i++ {
		ss = append(ss, mk("2026-04-15T01:00:00Z", "claude-code", "same"))
	}
	SortSessions(ss, true)
	SortSessions(ss, false)
	if len(ss) != 50 {
		t.Fatal("sort lost elements")
	}
	// Distinct paths on equal (ts, source): deterministic tiebreak.
	tie := []session.Session{
		mk("2026-04-15T01:00:00Z", "claude-code", "z"),
		mk("2026-04-15T01:00:00Z", "claude-code", "a"),
	}
	SortSessions(tie, false)
	if !sort.SliceIsSorted(tie, func(i, j int) bool { return tie[i].Path < tie[j].Path }) {
		t.Errorf("descending tiebreak should order by path asc, got %v", ids(tie))
	}
}
