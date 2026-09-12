package sensor

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"time"
)

type Counters struct {
	Sent       uint64 `json:"sent"`
	Dropped    uint64 `json:"dropped"`
	LastUpload string `json:"last_upload"`
}
type Spool struct {
	mu    sync.Mutex
	dir   string
	count int
	bytes int64
	age   time.Duration
	Stats Counters
}

func atomicWrite(path string, b []byte) error {
	f, err := os.CreateTemp(filepath.Dir(path), ".pending-")
	if err != nil {
		return err
	}
	name := f.Name()
	defer os.Remove(name)
	if err = f.Chmod(0600); err == nil {
		_, err = f.Write(b)
	}
	if err == nil {
		err = f.Sync()
	}
	closeErr := f.Close()
	if err != nil {
		return err
	}
	if closeErr != nil {
		return closeErr
	}
	return replaceFile(name, path)
}
func OpenSpool(c Config) (*Spool, error) {
	dir := filepath.Join(c.DataDir, "spool")
	if err := os.MkdirAll(dir, 0700); err != nil {
		return nil, err
	}
	s := &Spool{dir: dir, count: c.SpoolCount, bytes: c.SpoolBytes, age: time.Duration(c.SpoolHours) * time.Hour}
	b, err := os.ReadFile(filepath.Join(dir, "counters.json"))
	if err == nil {
		if json.Unmarshal(b, &s.Stats) != nil {
			return nil, fmt.Errorf("spool counters corrupt")
		}
	} else if !os.IsNotExist(err) {
		return nil, err
	}
	// An interrupted atomic write was never accepted; retain a loss indication.
	paths, _ := filepath.Glob(filepath.Join(dir, ".pending-*"))
	for _, p := range paths {
		s.Stats.Dropped++
		if err = s.save(); err != nil {
			return nil, err
		}
		if err = os.Remove(p); err != nil {
			return nil, err
		}
	}
	return s, s.trim()
}
func (s *Spool) save() error {
	b, _ := json.Marshal(s.Stats)
	return atomicWrite(filepath.Join(s.dir, "counters.json"), b)
}
func (s *Spool) files() ([]os.DirEntry, error) {
	entries, err := os.ReadDir(s.dir)
	if err != nil {
		return nil, err
	}
	out := []os.DirEntry{}
	for _, e := range entries {
		if !e.IsDir() && strings.HasSuffix(e.Name(), ".event") {
			out = append(out, e)
		}
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Name() < out[j].Name() })
	return out, nil
}
func (s *Spool) trim() error {
	files, err := s.files()
	if err != nil {
		return err
	}
	var size int64
	for _, f := range files {
		info, e := f.Info()
		if e != nil {
			return e
		}
		size += info.Size()
	}
	for len(files) > 0 {
		info, e := files[0].Info()
		if e != nil {
			return e
		}
		if len(files) <= s.count && size <= s.bytes && time.Since(info.ModTime()) <= s.age {
			break
		}
		// Count before removing: a crash may overcount, but cannot silently lose data.
		s.Stats.Dropped++
		if e = s.save(); e != nil {
			return e
		}
		if e = os.Remove(filepath.Join(s.dir, files[0].Name())); e != nil {
			return e
		}
		size -= info.Size()
		files = files[1:]
	}
	return nil
}
func (s *Spool) Add(event Event) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	b, err := json.Marshal(event)
	if err != nil {
		return err
	}
	if len(b) > 16384 {
		s.Stats.Dropped++
		return s.save()
	}
	name := fmt.Sprintf("%020d-%s.event", time.Now().UnixNano(), event.EventID)
	if err = atomicWrite(filepath.Join(s.dir, name), b); err != nil {
		return err
	}
	return s.trim()
}
func (s *Spool) Batch() ([]Event, []string, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if err := s.trim(); err != nil {
		return nil, nil, err
	}
	files, err := s.files()
	if err != nil {
		return nil, nil, err
	}
	events := []Event{}
	names := []string{}
	for _, f := range files {
		if len(events) == 50 {
			break
		}
		b, e := os.ReadFile(filepath.Join(s.dir, f.Name()))
		if e != nil {
			return nil, nil, e
		}
		var event Event
		if json.Unmarshal(b, &event) != nil {
			return nil, nil, fmt.Errorf("corrupt event; operator reconciliation required")
		}
		events = append(events, event)
		names = append(names, f.Name())
	}
	return events, names, nil
}
func (s *Spool) Ack(names []string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	for _, name := range names {
		if filepath.Base(name) != name || !strings.HasSuffix(name, ".event") {
			return fmt.Errorf("invalid acknowledgment")
		}
		if err := os.Remove(filepath.Join(s.dir, name)); err != nil {
			return err
		}
		s.Stats.Sent++
	}
	s.Stats.LastUpload = timestamp()
	return s.save()
}
func (s *Spool) Health() (int, Counters) {
	s.mu.Lock()
	defer s.mu.Unlock()
	f, _ := s.files()
	return len(f), s.Stats
}
