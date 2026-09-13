package sensor

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func config(t *testing.T) Config {
	t.Helper()
	dir := t.TempDir()
	return Config{DataDir: dir, AllowedRoots: []string{dir}, SpoolCount: 10, SpoolBytes: 65536, SpoolHours: 1}
}
func TestSpoolRestartCapacityExpiryAndAck(t *testing.T) {
	c := config(t)
	s, e := OpenSpool(c)
	if e != nil {
		t.Fatal(e)
	}
	i := Identity{EndpointID: ID(), InstanceID: ID(), Policy: Policy{Version: "endpoint-policy-1"}}
	for n := 0; n < 12; n++ {
		if e = s.Add(i.Event("endpoint_heartbeat", "runtime", map[string]any{})); e != nil {
			t.Fatal(e)
		}
	}
	depth, stats := s.Health()
	if depth != 10 || stats.Dropped != 2 || stats.Expired != 0 {
		t.Fatal(depth, stats)
	}
	s, e = OpenSpool(c)
	if e != nil {
		t.Fatal(e)
	}
	events, names, e := s.Batch()
	if e != nil || len(events) != 10 {
		t.Fatal(e, len(events))
	}
	old := events[0].EventID
	expired := time.Now().Add(-2 * time.Hour)
	if e = os.Chtimes(filepath.Join(s.dir, names[0]), expired, expired); e != nil {
		t.Fatal(e)
	}
	events, names, e = s.Batch()
	if e != nil || len(events) != 9 || events[0].EventID == old || s.Stats.Dropped != 3 {
		t.Fatal("expiry/restart")
	}
	if e = s.Ack(names); e != nil {
		t.Fatal(e)
	}
	s, e = OpenSpool(c)
	if e != nil {
		t.Fatal(e)
	}
	depth, stats = s.Health()
	if depth != 0 || stats.Sent != 9 || stats.Dropped != 3 || stats.Expired != 1 {
		t.Fatal(depth, stats)
	}
}

func TestOpenSpoolConservativelyAccountsInterruptedWrites(t *testing.T) {
	c := config(t)
	s, err := OpenSpool(c)
	if err != nil {
		t.Fatal(err)
	}
	i := Identity{EndpointID: ID(), InstanceID: ID()}
	committed := i.Event("endpoint_heartbeat", "runtime", map[string]any{})
	if err = s.Add(committed); err != nil {
		t.Fatal(err)
	}
	fixtures := map[string][]byte{
		".pending-empty-event":   nil,
		".pending-partial-event": []byte(`{"event_id":"partial"`),
	}
	for name, body := range fixtures {
		if err = os.WriteFile(filepath.Join(s.dir, name), body, 0600); err != nil {
			t.Fatal(err)
		}
	}
	s, err = OpenSpool(c)
	if err != nil {
		t.Fatal(err)
	}
	events, _, err := s.Batch()
	if err != nil || len(events) != 1 || events[0].EventID != committed.EventID || s.Stats.Dropped != 2 || s.Stats.Expired != 0 {
		t.Fatal("pending recovery must retain committed event and conservatively count every artifact", err, s.Stats)
	}

	// Model a crash after Dropped was saved but before this pending artifact was removed.
	pending := filepath.Join(s.dir, ".pending-after-counter-save")
	if err = os.WriteFile(pending, []byte("not-an-event"), 0600); err != nil {
		t.Fatal(err)
	}
	s.Stats.Dropped++
	if err = s.save(); err != nil {
		t.Fatal(err)
	}
	// Deliberately do not remove pending: the next OpenSpool must count it again.
	s, err = OpenSpool(c)
	if err != nil || s.Stats.Dropped != 4 || s.Stats.Expired != 0 {
		t.Fatal("counter-save interruption recovery", err, s.Stats)
	}
	events, _, err = s.Batch()
	if err != nil || len(events) != 1 || events[0].EventID != committed.EventID {
		t.Fatal("previously committed event identity was not retained", err)
	}
	// OpenSpool removed the pending artifact, so a further restart cannot recount it.
	s, err = OpenSpool(c)
	if err != nil || s.Stats.Dropped != 4 || s.Stats.Expired != 0 {
		t.Fatal("cleared pending file was double-counted", err, s.Stats)
	}
}

func TestOpenSpoolConservativelyAccountsPendingCounterWrites(t *testing.T) {
	c := config(t)
	s, err := OpenSpool(c)
	if err != nil {
		t.Fatal(err)
	}
	i := Identity{EndpointID: ID(), InstanceID: ID()}
	committed := i.Event("endpoint_heartbeat", "runtime", map[string]any{})
	if err = s.Add(committed); err != nil {
		t.Fatal(err)
	}
	persisted := Counters{Sent: 7, Dropped: 3, Expired: 1, LastUpload: "2026-01-01T00:00:00Z"}
	counterBody, err := json.Marshal(persisted)
	if err != nil {
		t.Fatal(err)
	}
	eventBody, err := json.Marshal(i.Event("endpoint_heartbeat", "runtime", map[string]any{}))
	if err != nil {
		t.Fatal(err)
	}
	if err = os.WriteFile(filepath.Join(s.dir, "counters.json"), counterBody, 0600); err != nil {
		t.Fatal(err)
	}
	fixtures := []struct {
		name string
		body []byte
	}{
		{".pending-counter-complete", counterBody},
		{".pending-counter-empty", nil},
		{".pending-counter-partial", []byte(`{"dropped":`)},
		{".pending-event-complete", eventBody},
	}
	for _, fixture := range fixtures {
		if err = os.WriteFile(filepath.Join(s.dir, fixture.name), fixture.body, 0600); err != nil {
			t.Fatal(err)
		}
	}
	s, err = OpenSpool(c)
	if err != nil {
		t.Fatal(err)
	}
	events, _, err := s.Batch()
	if err != nil || len(events) != 1 || events[0].EventID != committed.EventID {
		t.Fatal("pending recovery must preserve committed event identity", err)
	}
	if s.Stats.Sent != persisted.Sent || s.Stats.Dropped != persisted.Dropped+uint64(len(fixtures)) || s.Stats.Expired != persisted.Expired || s.Stats.LastUpload != persisted.LastUpload {
		t.Fatal("pending counter recovery must conservatively preserve persisted fields", s.Stats)
	}
	for _, fixture := range fixtures {
		if _, err = os.Stat(filepath.Join(s.dir, fixture.name)); !os.IsNotExist(err) {
			t.Fatal("pending artifact not removed", fixture.name, err)
		}
	}
	s, err = OpenSpool(c)
	if err != nil || s.Stats.Dropped != persisted.Dropped+uint64(len(fixtures)) || s.Stats.Sent != persisted.Sent || s.Stats.Expired != persisted.Expired {
		t.Fatal("cleared pending counter writes were recounted or persisted fields changed", err, s.Stats)
	}
}

func TestRevocationRetainsStableSpoolAndReportsAuthentication(t *testing.T) {
	c := config(t)
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { w.WriteHeader(401) }))
	defer server.Close()
	c.Server = server.URL
	c.AllowLoopbackHTTP = true
	c.AllowedCIDRs = []string{"127.0.0.1/32"}
	s, _ := OpenSpool(c)
	i := Identity{EndpointID: ID(), InstanceID: ID(), Credential: "fixture"}
	event := i.Event("endpoint_heartbeat", "runtime", map[string]any{})
	s.Add(event)
	transport, _ := NewTransport(c)
	if transport.Upload(i, s) == nil || !transport.AuthRejected {
		t.Fatal("revocation not reported")
	}
	if transport.Upload(i, s) == nil || !transport.AuthRejected {
		t.Fatal("retry hid revocation")
	}
	s, _ = OpenSpool(c)
	events, _, err := s.Batch()
	if err != nil || len(events) != 1 || events[0].EventID != event.EventID {
		t.Fatal("rejected evidence lost")
	}
}
func TestMCPRedactsNeverExecutesAndTracksOnlyMetadata(t *testing.T) {
	c := config(t)
	p := filepath.Join(c.DataDir, "mcp.json")
	body := `{"mcpServers":{"fixture":{"command":"DO_NOT_EXECUTE.exe","args":["--secret","credential-fixture"],"env":{"TOKEN":"credential-fixture"},"url":"https://user:password@example.invalid/path?token=credential-fixture"}}}`
	if e := os.WriteFile(p, []byte(body), 0600); e != nil {
		t.Fatal(e)
	}
	m, e := MCPMetadata(p)
	if e != nil {
		t.Fatal(e)
	}
	b, _ := json.Marshal(m)
	if strings.Contains(string(b), "credential-fixture") || strings.Contains(string(b), "password") || strings.Contains(string(b), "TOKEN") || m[0]["remote_domain"] != "example.invalid" {
		t.Fatal(string(b))
	}
	os.WriteFile(p, []byte(strings.ReplaceAll(body, "credential-fixture", "another-secret")), 0600)
	next, _ := MCPMetadata(p)
	if m[0]["configuration_digest"] != next[0]["configuration_digest"] {
		t.Fatal("secret change must not produce hash oracle")
	}
}
func TestTransportOutageAckIdempotencyAndRedirect(t *testing.T) {
	c := config(t)
	s, _ := OpenSpool(c)
	i := Identity{EndpointID: ID(), InstanceID: ID(), Credential: "fixture-only", Policy: Policy{Version: "endpoint-policy-1"}}
	event := i.Event("endpoint_heartbeat", "runtime", map[string]any{})
	s.Add(event)
	calls := 0
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		calls++
		if calls == 1 {
			w.WriteHeader(503)
			return
		}
		if calls == 2 {
			http.Redirect(w, r, "http://127.0.0.1:1", 302)
			return
		}
		json.NewEncoder(w).Encode(map[string]any{"accepted": []map[string]string{{"event_id": event.EventID, "job_id": "durable-fixture-job"}}})
	}))
	defer server.Close()
	c.Server = server.URL
	c.AllowLoopbackHTTP = true
	c.AllowedCIDRs = []string{"127.0.0.1/32"}
	transport, e := NewTransport(c)
	if e != nil {
		t.Fatal(e)
	}
	if transport.Upload(i, s) == nil {
		t.Fatal("outage must retain")
	}
	transport.notBefore = time.Time{}
	if transport.Upload(i, s) == nil {
		t.Fatal("redirect must fail")
	}
	transport.notBefore = time.Time{}
	events, _, _ := s.Batch()
	if len(events) != 1 || events[0].EventID != event.EventID {
		t.Fatal("stable event lost")
	}
	if e = transport.Upload(i, s); e != nil {
		t.Fatal(e)
	}
	n, _ := s.Health()
	if n != 0 || calls != 3 {
		t.Fatal(n, calls)
	}
}
func TestPathsAndMetadataBounds(t *testing.T) {
	c := config(t)
	outside := t.TempDir()
	p := filepath.Join(outside, "private.txt")
	os.WriteFile(p, []byte("private"), 0600)
	if c.Allowed(p) {
		t.Fatal("outside scope")
	}
	oversized := filepath.Join(c.DataDir, "mcp.json")
	os.WriteFile(oversized, make([]byte, (1<<20)+1), 0600)
	if _, e := MCPMetadata(oversized); e == nil {
		t.Fatal("limit")
	}
	for _, server := range []string{"http://example.com", "https://user:password@example.com", "http://169.254.169.254"} {
		c.Server = server
		if _, e := NewTransport(c); e == nil {
			t.Fatal(server)
		}
	}
}

func TestTransportRequiresTrustedTLSAndExplicitPrivateScope(t *testing.T) {
	calls := 0
	server := httptest.NewTLSServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { calls++; w.Write([]byte(`{}`)) }))
	defer server.Close()
	c := config(t)
	c.Server = server.URL
	transport, e := NewTransport(c)
	if e != nil {
		t.Fatal(e)
	}
	var out map[string]any
	if transport.Call("GET", "/health", "fixture-private-token", nil, &out) == nil {
		t.Fatal("unscoped private destination accepted")
	}
	c.AllowedCIDRs = []string{"127.0.0.1/32"}
	transport, e = NewTransport(c)
	if e != nil {
		t.Fatal(e)
	}
	if transport.Call("GET", "/health", "fixture-private-token", nil, &out) == nil {
		t.Fatal("untrusted TLS accepted")
	}
	if calls != 0 {
		t.Fatal("credentials reached untrusted endpoint")
	}
}
