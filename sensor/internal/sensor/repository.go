package sensor

import (
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
)

type Snapshot map[string]os.FileInfo

func RepositorySnapshot(c Config, r Repository) (Snapshot, error) {
	out := Snapshot{}
	if !c.Allowed(r.Path) {
		return out, fmt.Errorf("repository outside local approval")
	}
	count := 0
	err := filepath.WalkDir(r.Path, func(path string, d fs.DirEntry, e error) error {
		if e != nil {
			return e
		}
		count++
		if count > 3000 {
			return fmt.Errorf("repository entry limit")
		}
		if path != r.Path && (d.Name() == ".git" || d.Name() == "node_modules") {
			if d.IsDir() {
				return filepath.SkipDir
			}
			return nil
		}
		if d.Type()&os.ModeSymlink != 0 {
			return nil
		}
		if !c.Allowed(path) {
			if d.IsDir() {
				return filepath.SkipDir
			}
			return nil
		}
		if d.IsDir() {
			return nil
		}
		info, e := d.Info()
		if e != nil {
			return e
		}
		if info.Mode().IsRegular() {
			rel, _ := filepath.Rel(r.Path, path)
			out[rel] = info
		}
		return nil
	})
	return out, err
}

type Change struct {
	Kind     string
	Path     string
	Previous string
	Size     int64
}

func Changes(old, next Snapshot) []Change {
	out := []Change{}
	removed := map[string]os.FileInfo{}
	for name, info := range old {
		if _, ok := next[name]; !ok {
			removed[name] = info
		}
	}
	for name, info := range next {
		previous, ok := old[name]
		if ok {
			if info.ModTime() != previous.ModTime() || info.Size() != previous.Size() {
				out = append(out, Change{"file_modified", name, "", info.Size()})
			}
			continue
		}
		renamed := ""
		for nameOld, infoOld := range removed {
			if os.SameFile(infoOld, info) {
				renamed = nameOld
				delete(removed, nameOld)
				break
			}
		}
		kind := "file_created"
		if renamed != "" {
			kind = "file_renamed"
		}
		out = append(out, Change{kind, name, renamed, info.Size()})
	}
	for name, info := range removed {
		out = append(out, Change{"file_deleted", name, "", info.Size()})
	}
	return out
}
