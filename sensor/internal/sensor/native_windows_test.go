//go:build windows

package sensor

import (
	"bytes"
	"os"
	"path/filepath"
	"testing"
)

func TestWindowsDPAPIAndInstanceLock(t *testing.T) {
	plain := []byte("synthetic-private-credential")
	protected, e := Protect(plain)
	if e != nil || bytes.Contains(protected, plain) {
		t.Fatal("DPAPI protection failed", e)
	}
	out, e := Unprotect(protected)
	if e != nil || !bytes.Equal(out, plain) {
		t.Fatal("DPAPI roundtrip failed", e)
	}
	dir := t.TempDir()
	unlock, e := LockInstance(dir)
	if e != nil {
		t.Fatal(e)
	}
	if second, e := LockInstance(dir); e == nil {
		second()
		t.Fatal("concurrent spool owner allowed")
	}
	unlock()
}
func TestWindowsNativeProcessAndFileIdentity(t *testing.T) {
	ps, _, e := Processes()
	if e != nil {
		t.Fatal(e)
	}
	p, ok := ps[uint32(os.Getpid())]
	if !ok || p.Executable == "" || p.Key == "" || p.ParentPID == 0 {
		t.Fatal("missing actual process", p)
	}
	if _, e = Connections(); e != nil {
		t.Fatal(e)
	}
	c := config(t)
	repo := Repository{ID: ID(), Path: c.DataDir, Classification: "Restricted"}
	path := filepath.Join(repo.Path, "benign.txt")
	os.WriteFile(path, []byte("benign"), 0600)
	old, e := RepositorySnapshot(c, repo)
	if e != nil {
		t.Fatal(e)
	}
	os.Rename(path, filepath.Join(repo.Path, "renamed.txt"))
	next, e := RepositorySnapshot(c, repo)
	if e != nil {
		t.Fatal(e)
	}
	changes := Changes(old, next)
	if len(changes) != 1 || changes[0].Kind != "file_renamed" {
		t.Fatal("Windows file ID rename correlation", changes)
	}
	os.Remove(filepath.Join(repo.Path, "renamed.txt"))
	next, _ = RepositorySnapshot(c, repo)
	if Changes(old, next)[0].Kind != "file_deleted" {
		t.Fatal("delete")
	}
}

func TestEnrollmentPreservesExistingDirectory(t *testing.T) {
	c := config(t)
	path := filepath.Join(c.DataDir, "operator-file.txt")
	os.WriteFile(path, []byte("preserve"), 0600)
	if Enroll(c, "fixture-bootstrap-not-real-1234567890") == nil {
		t.Fatal("nonempty directory accepted")
	}
	b, e := os.ReadFile(path)
	if e != nil || string(b) != "preserve" {
		t.Fatal("existing data altered")
	}
	if BoundedHash(`\\server\share\file.exe`) != "" {
		t.Fatal("remote executable opened")
	}
}
