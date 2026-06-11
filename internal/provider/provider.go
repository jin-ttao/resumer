// Package provider defines the Provider interface and the registry that
// merges sessions across providers. Adding a provider (e.g. Gemini) means
// one new package plus one entry in the registry slice.
package provider

import (
	"fmt"
	"sort"

	"github.com/jin-ttao/resumer/internal/session"
)

// Provider is the contract each AI-CLI session source implements.
// Implementations must read their env overrides at call time (not init)
// so test harnesses can inject fixture roots per invocation.
type Provider interface {
	Name() string
	Badge() string
	BadgeANSI() string
	IsAvailable() bool
	ListSessions(f session.Filters) ([]session.Session, error)
	LoadDetail(id string) (*session.Session, error)
}

var registry []Provider

// Register appends a provider. Called from cli wiring to avoid import cycles
// and keep this package dependency-free for tests.
func Register(p Provider) {
	registry = append(registry, p)
}

// All returns every registered provider.
func All() []Provider {
	out := make([]Provider, len(registry))
	copy(out, registry)
	return out
}

// Active returns providers whose data sources are present on this machine.
func Active() []Provider {
	var out []Provider
	for _, p := range registry {
		if p.IsAvailable() {
			out = append(out, p)
		}
	}
	return out
}

// Get returns the provider with the given name, or nil.
func Get(name string) Provider {
	for _, p := range registry {
		if p.Name() == name {
			return p
		}
	}
	return nil
}

// AvailableSourceNames lists names of active providers.
func AvailableSourceNames() []string {
	var out []string
	for _, p := range Active() {
		out = append(out, p.Name())
	}
	return out
}

// SortSessions orders by (LastTS, Source) descending — string comparison,
// matching the Python registry's sort for output parity — with Path as a
// final tiebreak for deterministic ordering on identical timestamps.
func SortSessions(out []session.Session, ascending bool) {
	sort.SliceStable(out, func(i, j int) bool {
		a, b := out[i], out[j]
		less := false
		switch {
		case a.LastTS != b.LastTS:
			less = a.LastTS > b.LastTS
		case a.Source != b.Source:
			less = a.Source > b.Source
		default:
			less = a.Path < b.Path
		}
		if ascending {
			return !less
		}
		return less
	})
}

// MergedList collects sessions from active providers (or the single provider
// named in filters), sorted last-activity-descending, limit applied.
func MergedList(f session.Filters) ([]session.Session, error) {
	var out []session.Session
	if f.Source != "" {
		p := Get(f.Source)
		if p == nil {
			return nil, fmt.Errorf("unknown provider: %s", f.Source)
		}
		if !p.IsAvailable() {
			return nil, fmt.Errorf(
				"%s provider not available (binary or session directory missing)", f.Source)
		}
		ss, err := p.ListSessions(f)
		if err != nil {
			return nil, err
		}
		out = append(out, ss...)
	} else {
		for _, p := range Active() {
			ss, err := p.ListSessions(f)
			if err != nil {
				return nil, err
			}
			out = append(out, ss...)
		}
	}
	SortSessions(out, false)
	if f.Limit > 0 && len(out) > f.Limit {
		out = out[:f.Limit]
	}
	return out, nil
}
