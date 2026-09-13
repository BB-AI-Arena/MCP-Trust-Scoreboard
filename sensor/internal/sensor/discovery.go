package sensor

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"net/url"
	"os"
	"path/filepath"
	"strings"
)

// No discovered executable is run and no arguments/environment values are retained.
var Catalog = map[string][]string{
	"cursor":      {`AppData/Local/Programs/cursor/Cursor.exe`},
	"ollama":      {`AppData/Local/Programs/Ollama/ollama.exe`},
	"lm-studio":   {`AppData/Local/Programs/LM Studio/LM Studio.exe`},
	"claude-code": {`.local/bin/claude.exe`},
	"codex":       {`AppData/Roaming/npm/node_modules/@openai/codex/package.json`},
	"gemini-cli":  {`AppData/Roaming/npm/node_modules/@google/gemini-cli/package.json`},
}

type Discovery struct {
	Tools   []Tool
	Configs []string
}

func Discover(c Config, p Policy) (Discovery, error) {
	d := Discovery{}
	var visibilityError error
	for _, root := range c.ProfileRoots {
		if _, err := os.ReadDir(root); err != nil {
			visibilityError = fmt.Errorf("profile unavailable")
		}
	}
	for id, paths := range Catalog {
		for _, root := range c.ProfileRoots {
			for _, rel := range paths {
				path := filepath.Join(root, filepath.FromSlash(rel))
				if c.Allowed(path) {
					d.Tools = append(d.Tools, Tool{id, path})
				}
			}
		}
	}
	for _, t := range p.CustomTools {
		if c.Allowed(t.Path) {
			d.Tools = append(d.Tools, t)
		}
	}
	for _, root := range c.ProfileRoots {
		for _, dir := range []string{`.vscode/extensions`, `.cursor/extensions`} {
			base := filepath.Join(root, filepath.FromSlash(dir))
			if !c.Allowed(base) {
				continue
			}
			entries, e := os.ReadDir(base)
			if e != nil {
				continue
			}
			if len(entries) > 500 {
				return d, fmt.Errorf("extension limit")
			}
			for _, entry := range entries {
				if strings.HasPrefix(strings.ToLower(entry.Name()), "github.copilot-") || strings.HasPrefix(strings.ToLower(entry.Name()), "github.copilot-chat-") {
					path := filepath.Join(base, entry.Name(), "package.json")
					if c.Allowed(path) {
						d.Tools = append(d.Tools, Tool{"github-copilot", path})
					}
				}
			}
		}
		for _, rel := range []string{`.cursor/mcp.json`, `AppData/Roaming/Code/User/mcp.json`} {
			path := filepath.Join(root, filepath.FromSlash(rel))
			if c.Allowed(path) {
				d.Configs = append(d.Configs, path)
			}
		}
	}
	for _, path := range p.MCPPaths {
		if c.Allowed(path) {
			d.Configs = append(d.Configs, path)
		}
	}
	return d, visibilityError
}
func ReadMetadata(path string) (map[string]any, error) {
	st, e := os.Stat(path)
	if e != nil || st.Size() > 1<<20 || !st.Mode().IsRegular() {
		return nil, fmt.Errorf("metadata unavailable or oversized")
	}
	b, e := os.ReadFile(path)
	if e != nil {
		return nil, e
	}
	var out map[string]any
	if json.Unmarshal(b, &out) != nil {
		return nil, fmt.Errorf("malformed metadata JSON")
	}
	return out, nil
}
func ToolVersion(t Tool) string {
	if filepath.Base(t.Path) != "package.json" {
		return ""
	}
	m, e := ReadMetadata(t.Path)
	if e != nil {
		return ""
	}
	v, _ := m["version"].(string)
	if len(v) > 128 {
		return ""
	}
	return v
}
func MCPMetadata(path string) ([]map[string]any, error) {
	m, e := ReadMetadata(path)
	if e != nil {
		return nil, e
	}
	servers, ok := m["mcpServers"].(map[string]any)
	if !ok {
		servers, ok = m["servers"].(map[string]any)
	}
	if !ok || len(servers) > 100 {
		return nil, fmt.Errorf("unsupported MCP schema or limit")
	}
	out := []map[string]any{}
	for name, value := range servers {
		raw, ok := value.(map[string]any)
		if !ok || len(name) > 128 {
			return nil, fmt.Errorf("malformed MCP registration")
		}
		command, _ := raw["command"].(string)
		remote, _ := raw["url"].(string)
		transport := "unknown"
		domain := ""
		executable := ""
		if command != "" {
			transport = "stdio"
			executable = filepath.Base(command)
			if strings.ContainsAny(executable, " \t\r\n=\"'") || len(executable) > 128 {
				executable = "redacted"
			}
		}
		if remote != "" {
			u, e := url.Parse(remote)
			if e == nil && u.Hostname() != "" {
				transport = "http"
				domain = u.Hostname()
			}
		}
		args, _ := raw["args"].([]any)
		if len(args) > 1000 {
			return nil, fmt.Errorf("MCP argument limit")
		}
		data := map[string]any{"server_name": name, "transport": transport, "executable_name": executable, "argument_count": len(args), "remote_domain": domain, "configuration_source": path}
		// Digest only the selected non-secret metadata. Secret changes are deliberately
		// not a telemetry signal; no full-config digest or low-entropy secret oracle.
		b, _ := json.Marshal(data)
		h := sha256.Sum256(b)
		data["configuration_digest"] = hex.EncodeToString(h[:])
		out = append(out, data)
	}
	return out, nil
}
