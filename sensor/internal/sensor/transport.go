package sensor

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/netip"
	"net/url"
	"strings"
	"time"
)

type Transport struct {
	client    *http.Client
	origin    string
	notBefore time.Time
}

func NewTransport(c Config) (*Transport, error) {
	u, err := url.Parse(c.Server)
	if err != nil || u.Hostname() == "" || u.User != nil || u.RawQuery != "" || u.Fragment != "" || u.Path != "" && u.Path != "/" {
		return nil, fmt.Errorf("invalid server origin")
	}
	if u.Scheme != "https" {
		ip, e := netip.ParseAddr(u.Hostname())
		if u.Scheme != "http" || !c.AllowLoopbackHTTP || e != nil || !ip.IsLoopback() {
			return nil, fmt.Errorf("TLS required")
		}
	}
	prefixes := []netip.Prefix{}
	for _, v := range c.AllowedCIDRs {
		p, e := netip.ParsePrefix(v)
		if e != nil {
			return nil, fmt.Errorf("invalid allowed CIDR")
		}
		prefixes = append(prefixes, p)
	}
	transport := &http.Transport{Proxy: nil, MaxIdleConns: 2, ResponseHeaderTimeout: 5 * time.Second}
	transport.DialContext = func(ctx context.Context, network, address string) (net.Conn, error) {
		host, port, e := net.SplitHostPort(address)
		if e != nil {
			return nil, e
		}
		ips, e := net.DefaultResolver.LookupNetIP(ctx, "ip", host)
		if e != nil || len(ips) == 0 {
			return nil, fmt.Errorf("DNS unavailable")
		}
		for _, ip := range ips {
			ip = ip.Unmap()
			if ip.IsLinkLocalUnicast() || ip.IsMulticast() || ip.IsUnspecified() {
				return nil, fmt.Errorf("unsafe destination")
			}
			if ip.IsPrivate() || ip.IsLoopback() {
				ok := false
				for _, p := range prefixes {
					if p.Contains(ip) {
						ok = true
					}
				}
				if !ok {
					return nil, fmt.Errorf("private destination not scoped")
				}
			}
		}
		return (&net.Dialer{Timeout: 5 * time.Second}).DialContext(ctx, network, net.JoinHostPort(ips[0].String(), port))
	}
	return &Transport{client: &http.Client{Transport: transport, Timeout: 10 * time.Second, CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }}, origin: strings.TrimRight(c.Server, "/")}, nil
}
func (t *Transport) Call(method, path, token string, body any, out any) error {
	if time.Now().Before(t.notBefore) {
		return fmt.Errorf("retry deferred")
	}
	b, err := json.Marshal(body)
	if err != nil {
		return err
	}
	r, err := http.NewRequest(method, t.origin+path, bytes.NewReader(b))
	if err != nil {
		return fmt.Errorf("invalid request")
	}
	r.Header.Set("Content-Type", "application/json")
	if token != "" {
		r.Header.Set("Authorization", "Bearer "+token)
	}
	response, err := t.client.Do(r)
	if err != nil {
		t.notBefore = time.Now().Add(5 * time.Second)
		return fmt.Errorf("server unavailable")
	}
	defer response.Body.Close()
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		delay := 5 * time.Second
		if v := response.Header.Get("Retry-After"); v != "" {
			if d, e := time.ParseDuration(v + "s"); e == nil && d > delay {
				delay = d
			} else if when, e := http.ParseTime(v); e == nil && time.Until(when) > delay {
				delay = time.Until(when)
			}
		}
		t.notBefore = time.Now().Add(delay)
		return fmt.Errorf("server returned status %d", response.StatusCode)
	}
	raw, err := io.ReadAll(io.LimitReader(response.Body, 1_000_001))
	if err != nil || len(raw) > 1_000_000 {
		return fmt.Errorf("response unavailable or oversized")
	}
	if json.Unmarshal(raw, out) != nil {
		return fmt.Errorf("malformed response")
	}
	return nil
}
func (t *Transport) Upload(i Identity, s *Spool) error {
	events, names, err := s.Batch()
	if err != nil || len(events) == 0 {
		return err
	}
	var out struct {
		Accepted []struct {
			EventID string `json:"event_id"`
			JobID   string `json:"job_id"`
		} `json:"accepted"`
	}
	if err = t.Call("POST", "/api/v1/endpoints/"+i.EndpointID+"/events", i.Credential, map[string]any{"events": events}, &out); err != nil {
		return err
	}
	if len(out.Accepted) != len(events) {
		return fmt.Errorf("incomplete acknowledgment")
	}
	for n, ack := range out.Accepted {
		if ack.EventID != events[n].EventID || ack.JobID == "" {
			return fmt.Errorf("mismatched acknowledgment")
		}
	}
	return s.Ack(names)
}
