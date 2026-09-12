//go:build windows

package sensor

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"
)

func Enroll(c Config, bootstrap string) error {
	if len(bootstrap) < 32 {
		return fmt.Errorf("bootstrap required in private environment")
	}
	checkEmpty := func() error {
		entries, err := os.ReadDir(c.DataDir)
		if os.IsNotExist(err) {
			return nil
		}
		if err != nil {
			return err
		}
		for _, entry := range entries {
			if entry.Name() != "sensor.lock" {
				return fmt.Errorf("enrollment requires an empty dedicated data directory")
			}
		}
		return nil
	}
	if err := checkEmpty(); err != nil {
		return err
	}
	if e := os.MkdirAll(c.DataDir, 0700); e != nil {
		return e
	}
	unlock, lockError := LockInstance(c.DataDir)
	if lockError != nil {
		return lockError
	}
	defer unlock()
	if err := checkEmpty(); err != nil {
		return err
	}
	if e := RestrictDirectory(c.DataDir); e != nil {
		return e
	}
	path := filepath.Join(c.DataDir, "identity.dpapi")
	if _, e := os.Stat(path); e == nil {
		return fmt.Errorf("identity already exists; revoke/reconcile before reenrollment")
	}
	t, e := NewTransport(c)
	if e != nil {
		return e
	}
	i := Identity{EndpointID: c.EndpointID, InstanceID: ID()}
	var out struct {
		Credential string `json:"credential"`
		Policy     Policy `json:"policy"`
	}
	if e = t.Call("POST", "/api/v1/endpoints/enroll", "", map[string]any{"endpoint_id": i.EndpointID, "sensor_instance_id": i.InstanceID, "bootstrap_secret": bootstrap}, &out); e != nil {
		return e
	}
	if out.Credential == "" || out.Policy.Version != "endpoint-policy-1" {
		return fmt.Errorf("invalid enrollment response")
	}
	i.Credential = out.Credential
	i.Policy = out.Policy
	b, _ := json.Marshal(i)
	encrypted, e := Protect(b)
	if e != nil {
		return e
	}
	return atomicWrite(path, encrypted)
}
func LoadIdentity(c Config) (Identity, error) {
	var i Identity
	b, e := os.ReadFile(filepath.Join(c.DataDir, "identity.dpapi"))
	if e != nil {
		return i, fmt.Errorf("enrollment required")
	}
	b, e = Unprotect(b)
	if e != nil {
		return i, e
	}
	if json.Unmarshal(b, &i) != nil || i.EndpointID != c.EndpointID || i.Policy.Version != "endpoint-policy-1" {
		return i, fmt.Errorf("identity mismatch")
	}
	return i, nil
}

type Manager struct {
	Config       Config
	Identity     Identity
	Spool        *Spool
	Transport    *Transport
	states       map[string]string
	processes    map[uint32]ProcessInfo
	connections  map[string]bool
	repositories map[string]Snapshot
	seen         map[string]string
	tools        []Tool
	online       bool
	ticks        int
}

func NewManager(c Config) (*Manager, error) {
	i, e := LoadIdentity(c)
	if e != nil {
		return nil, e
	}
	s, e := OpenSpool(c)
	if e != nil {
		return nil, e
	}
	t, e := NewTransport(c)
	if e != nil {
		return nil, e
	}
	return &Manager{Config: c, Identity: i, Spool: s, Transport: t, states: map[string]string{"runtime": "active", "software": "supported", "ai": "supported", "mcp": "supported", "process": "supported", "network": "supported", "filesystem": "supported", "dns": "unsupported", "udp": "unsupported", "file_writer": "unsupported"}, processes: map[uint32]ProcessInfo{}, connections: map[string]bool{}, repositories: map[string]Snapshot{}, seen: map[string]string{}}, nil
}
func (m *Manager) emit(kind, collector string, data map[string]any) error {
	return m.Spool.Add(m.Identity.Event(kind, collector, data))
}
func (m *Manager) discovery() error {
	inventory, e := Inventory()
	m.states["software"] = "active"
	if e != nil {
		m.states["software"] = "degraded"
	}
	for _, data := range inventory {
		key := fmt.Sprint(data)
		if m.seen[key] == "" {
			if e = m.emit("software_inventory", "software", data); e != nil {
				return e
			}
			m.seen[key] = "seen"
		}
	}
	d, e := Discover(m.Config, m.Identity.Policy)
	m.states["ai"] = "active"
	if len(m.Config.ProfileRoots) == 0 && len(m.Identity.Policy.CustomTools) == 0 {
		m.states["ai"] = "supported"
	}
	if e != nil {
		m.states["ai"] = "degraded"
	}
	m.tools = d.Tools
	for _, t := range d.Tools {
		key := t.ID + ":" + t.Path
		v := ToolVersion(t)
		if m.seen[key] != v+"seen" {
			data := map[string]any{"tool_id": t.ID, "path": t.Path, "version": v, "source": "configured_path"}
			if e = m.emit("ai_tool_discovered", "ai", data); e != nil {
				return e
			}
			if e = m.emit("software_inventory", "software", map[string]any{"product": t.ID, "path": t.Path, "version": v, "source": "configured_path"}); e != nil {
				return e
			}
			m.seen[key] = v + "seen"
		}
	}
	m.states["mcp"] = "active"
	if len(m.Config.ProfileRoots) == 0 && len(m.Identity.Policy.MCPPaths) == 0 {
		m.states["mcp"] = "supported"
	}
	for _, path := range d.Configs {
		metadata, e := MCPMetadata(path)
		if e != nil {
			m.states["mcp"] = "degraded"
			continue
		}
		for _, data := range metadata {
			key := path + ":" + data["server_name"].(string)
			digest := data["configuration_digest"].(string)
			if m.seen[key] != digest {
				kind := "mcp_configuration_discovered"
				if m.seen[key] != "" {
					kind = "mcp_configuration_changed"
				}
				if e = m.emit(kind, "mcp", data); e != nil {
					return e
				}
				m.seen[key] = digest
			}
		}
	}
	return nil
}
func (m *Manager) Tick() error {
	if m.ticks%30 == 0 {
		if e := m.discovery(); e != nil {
			return e
		}
	}
	next, denied, e := Processes()
	m.states["process"] = "active"
	if denied > 0 {
		m.states["process"] = "permission_missing"
	}
	if e != nil {
		m.states["process"] = "degraded"
	} else {
		hashes := 0
		for pid, p := range next {
			old, ok := m.processes[pid]
			if !ok || old.Key != p.Key {
				if hashes < 8 {
					p.Hash = BoundedHash(p.Executable)
					hashes++
				}
				next[pid] = p
				if e = m.emit("process_started", "process", p.Data()); e != nil {
					return e
				}
			}
			for _, t := range m.tools {
				if strings.EqualFold(filepath.Clean(t.Path), filepath.Clean(p.Executable)) {
					if e = m.emit("ai_tool_running", "ai", map[string]any{"tool_id": t.ID, "path": p.Executable, "process_key": p.Key, "source": "process_snapshot"}); e != nil {
						return e
					}
				}
			}
		}
		for pid, p := range m.processes {
			if current, ok := next[pid]; !ok || current.Key != p.Key {
				if e = m.emit("process_stopped", "process", p.Data()); e != nil {
					return e
				}
			}
		}
		m.processes = next
	}
	connections, e := Connections()
	m.states["network"] = "active"
	if e != nil {
		m.states["network"] = "degraded"
	} else {
		current := map[string]bool{}
		for _, connection := range connections {
			p, ok := m.processes[connection.PID]
			if !ok {
				continue
			}
			key := p.Key + ":" + connection.Key
			current[key] = true
			if !m.connections[key] {
				if e = m.emit("process_network_connection", "network", map[string]any{"process_key": p.Key, "pid": p.PID, "destination_ip": connection.IP, "destination_port": connection.Port, "transport": "tcp", "direction": connection.Direction}); e != nil {
					return e
				}
			}
		}
		m.connections = current
	}
	m.states["filesystem"] = "active"
	if len(m.Identity.Policy.Repositories) == 0 {
		m.states["filesystem"] = "supported"
	}
	for _, repo := range m.Identity.Policy.Repositories {
		snapshot, e := RepositorySnapshot(m.Config, repo)
		if e != nil {
			m.states["filesystem"] = "degraded"
			continue
		}
		old, ok := m.repositories[repo.ID]
		if ok {
			for _, change := range Changes(old, snapshot) {
				data := map[string]any{"repository_id": repo.ID, "relative_path": change.Path, "previous_relative_path": change.Previous, "size": change.Size, "relationship": "repository_metadata_observation"}
				if e = m.emit(change.Kind, "filesystem", data); e != nil {
					return e
				}
				if e = m.emit("repository_interaction", "filesystem", data); e != nil {
					return e
				}
			}
		}
		m.repositories[repo.ID] = snapshot
	}
	if m.ticks%10 == 0 {
		depth, stats := m.Spool.Health()
		connectivity := "offline"
		if m.online {
			connectivity = "online"
		}
		health := map[string]any{"service_status": "running", "collectors": m.states, "spool_depth": depth, "events_sent": stats.Sent, "events_dropped": stats.Dropped, "last_upload": stats.LastUpload, "connectivity": connectivity, "reason": "polling_gap"}
		for _, kind := range []string{"endpoint_heartbeat", "endpoint_capabilities", "collector_health", "visibility_gap"} {
			if e = m.emit(kind, "runtime", health); e != nil {
				return e
			}
		}
	}
	m.ticks++
	m.online = m.Transport.Upload(m.Identity, m.Spool) == nil
	return nil
}
func Run(ctx context.Context, c Config) error {
	unlock, e := LockInstance(c.DataDir)
	if e != nil {
		return e
	}
	defer unlock()
	m, e := NewManager(c)
	if e != nil {
		return e
	}
	ticker := time.NewTicker(time.Duration(c.IntervalSeconds) * time.Second)
	defer ticker.Stop()
	for {
		if e = m.Tick(); e != nil {
			return fmt.Errorf("collector/spool failure; telemetry unavailable")
		}
		select {
		case <-ctx.Done():
			return nil
		case <-ticker.C:
		}
	}
}
