//go:build !windows

package sensor

import "os"

func replaceFile(from, to string) error { return os.Rename(from, to) }
