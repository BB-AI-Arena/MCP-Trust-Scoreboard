package sensor

import (
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"
)

const Version = "0.1.0"

var Commit = "development"
var ApplicationVersion = "2.0.0-alpha.1"

type Repository struct {
	ID             string `json:"id"`
	Path           string `json:"path"`
	Classification string `json:"classification"`
}
type Tool struct {
	ID   string `json:"id"`
	Path string `json:"path"`
}
type Policy struct {
	Version           string       `json:"version"`
	Repositories      []Repository `json:"repositories"`
	ApprovedTools     []string     `json:"approved_tools"`
	CustomTools       []Tool       `json:"custom_tools"`
	MCPPaths          []string     `json:"mcp_paths"`
	IndicatorSHA256   []string     `json:"indicator_sha256"`
	KnownDestinations []string     `json:"known_destinations"`
}
type Config struct {
	Server            string   `json:"server"`
	EndpointID        string   `json:"endpoint_id"`
	DataDir           string   `json:"data_dir"`
	AllowedRoots      []string `json:"allowed_roots"`
	ProfileRoots      []string `json:"profile_roots"`
	AllowedCIDRs      []string `json:"allowed_cidrs"`
	AllowLoopbackHTTP bool     `json:"allow_loopback_http"`
	IntervalSeconds   int      `json:"interval_seconds"`
	SpoolCount        int      `json:"spool_count"`
	SpoolBytes        int64    `json:"spool_bytes"`
	SpoolHours        int      `json:"spool_hours"`
}
type Identity struct {
	EndpointID string `json:"endpoint_id"`
	InstanceID string `json:"instance_id"`
	Credential string `json:"credential"`
	Policy     Policy `json:"policy"`
}
type Event struct {
	SchemaVersion string         `json:"schema_version"`
	EventID       string         `json:"event_id"`
	EndpointID    string         `json:"endpoint_id"`
	InstanceID    string         `json:"sensor_instance_id"`
	ObservedAt    string         `json:"observed_at"`
	Collector     string         `json:"collector"`
	SensorVersion string         `json:"sensor_version"`
	PolicyVersion string         `json:"policy_version"`
	EventType     string         `json:"event_type"`
	Data          map[string]any `json:"data"`
}

func ID() string {
	b := make([]byte, 16)
	if _, err := rand.Read(b); err != nil {
		panic("random source unavailable")
	}
	b[6] = (b[6] & 15) | 64
	b[8] = (b[8] & 63) | 128
	s := hex.EncodeToString(b)
	return fmt.Sprintf("%s-%s-%s-%s-%s", s[:8], s[8:12], s[12:16], s[16:20], s[20:])
}
func timestamp() string { return time.Now().UTC().Format(time.RFC3339Nano) }
func (i Identity) Event(kind, collector string, data map[string]any) Event {
	return Event{"endpoint-1", ID(), i.EndpointID, i.InstanceID, timestamp(), collector, Version, i.Policy.Version, kind, data}
}
func LoadConfig(path string) (Config, error) {
	var c Config
	b, err := os.ReadFile(path)
	if err != nil || len(b) > 65536 {
		return c, fmt.Errorf("configuration unreadable or oversized")
	}
	d := json.NewDecoder(strings.NewReader(string(b)))
	d.DisallowUnknownFields()
	if err = d.Decode(&c); err != nil {
		return c, fmt.Errorf("invalid configuration")
	}
	if c.IntervalSeconds == 0 {
		c.IntervalSeconds = 2
	}
	if c.SpoolCount == 0 {
		c.SpoolCount = 10000
	}
	if c.SpoolBytes == 0 {
		c.SpoolBytes = 32 << 20
	}
	if c.SpoolHours == 0 {
		c.SpoolHours = 168
	}
	if !filepath.IsAbs(c.DataDir) || len(c.AllowedRoots) > 20 || len(c.ProfileRoots) > 20 || c.IntervalSeconds < 1 || c.IntervalSeconds > 60 || c.SpoolCount < 10 || c.SpoolCount > 100000 || c.SpoolBytes < 65536 || c.SpoolBytes > 256<<20 || c.SpoolHours < 1 || c.SpoolHours > 168 {
		return c, fmt.Errorf("invalid configuration limits")
	}
	for _, root := range append(append([]string{c.DataDir}, c.AllowedRoots...), c.ProfileRoots...) {
		if !filepath.IsAbs(root) || strings.HasPrefix(root, `\\`) || filepath.Dir(filepath.Clean(root)) == filepath.Clean(root) {
			return c, fmt.Errorf("explicit non-root local paths required")
		}
	}
	return c, nil
}

// Reject reparse/symlink traversal: compare resolved target to an explicitly
// approved local root. Collectors also skip symlinks/reparse points when walking.
func (c Config) Allowed(path string) bool {
	resolved, err := filepath.EvalSymlinks(path)
	if err != nil || strings.HasPrefix(resolved, `\\`) {
		return false
	}
	for _, root := range c.AllowedRoots {
		base, err := filepath.EvalSymlinks(root)
		if err != nil {
			continue
		}
		rel, err := filepath.Rel(base, resolved)
		if err == nil && rel != ".." && !strings.HasPrefix(rel, ".."+string(filepath.Separator)) && !filepath.IsAbs(rel) {
			return true
		}
	}
	return false
}
