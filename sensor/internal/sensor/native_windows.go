//go:build windows

package sensor

import (
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"fmt"
	"io"
	"net"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"unsafe"

	"golang.org/x/sys/windows"
	"golang.org/x/sys/windows/registry"
)

func replaceFile(from, to string) error {
	a, e := windows.UTF16PtrFromString(from)
	if e != nil {
		return e
	}
	b, e := windows.UTF16PtrFromString(to)
	if e != nil {
		return e
	}
	return windows.MoveFileEx(a, b, windows.MOVEFILE_REPLACE_EXISTING|windows.MOVEFILE_WRITE_THROUGH)
}
func Protect(b []byte) ([]byte, error) {
	var out windows.DataBlob
	in := windows.DataBlob{Size: uint32(len(b)), Data: &b[0]}
	if e := windows.CryptProtectData(&in, nil, nil, 0, nil, windows.CRYPTPROTECT_UI_FORBIDDEN, &out); e != nil {
		return nil, fmt.Errorf("credential protection failed")
	}
	defer windows.LocalFree(windows.Handle(unsafe.Pointer(out.Data)))
	return append([]byte(nil), unsafe.Slice(out.Data, out.Size)...), nil
}
func Unprotect(b []byte) ([]byte, error) {
	if len(b) == 0 {
		return nil, fmt.Errorf("empty identity")
	}
	var out windows.DataBlob
	in := windows.DataBlob{Size: uint32(len(b)), Data: &b[0]}
	if e := windows.CryptUnprotectData(&in, nil, nil, 0, nil, windows.CRYPTPROTECT_UI_FORBIDDEN, &out); e != nil {
		return nil, fmt.Errorf("credential unavailable under this account")
	}
	defer windows.LocalFree(windows.Handle(unsafe.Pointer(out.Data)))
	return append([]byte(nil), unsafe.Slice(out.Data, out.Size)...), nil
}
func RestrictDirectory(path string) error {
	token, err := windows.OpenCurrentProcessToken()
	if err != nil {
		return err
	}
	defer token.Close()
	user, err := token.GetTokenUser()
	if err != nil {
		return err
	}
	sd, err := windows.SecurityDescriptorFromString("D:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)(A;OICI;FA;;;" + user.User.Sid.String() + ")")
	if err != nil {
		return err
	}
	acl, _, err := sd.DACL()
	if err != nil {
		return err
	}
	return windows.SetNamedSecurityInfo(path, windows.SE_FILE_OBJECT, windows.DACL_SECURITY_INFORMATION|windows.PROTECTED_DACL_SECURITY_INFORMATION, nil, nil, acl, nil)
}
func LockInstance(path string) (func(), error) {
	// A no-sharing file handle fences all sessions/path aliases. The OS releases
	// the handle after process death; the zero-byte lock file is not a stale lock.
	name, err := windows.UTF16PtrFromString(filepath.Join(path, "sensor.lock"))
	if err != nil {
		return nil, err
	}
	h, err := windows.CreateFile(name, windows.GENERIC_READ|windows.GENERIC_WRITE, 0, nil, windows.OPEN_ALWAYS, windows.FILE_ATTRIBUTE_NORMAL, 0)
	if err != nil {
		if h != 0 {
			windows.CloseHandle(h)
		}
		return nil, fmt.Errorf("sensor already running or lock unavailable")
	}
	return func() { windows.CloseHandle(h) }, nil
}

type ProcessInfo struct {
	Key              string
	PID              uint32
	ParentPID        uint32
	ParentKey        string
	Executable       string
	ParentExecutable string
	Session          uint32
	SID              string
	Hash             string
}

func (p ProcessInfo) Data() map[string]any {
	return map[string]any{"observation": "first_seen_snapshot", "process_key": p.Key, "pid": p.PID, "parent_pid": p.ParentPID, "parent_key": p.ParentKey, "executable": p.Executable, "parent_executable": p.ParentExecutable, "session_id": p.Session, "user_sid": p.SID, "sha256": p.Hash}
}
func Processes() (map[uint32]ProcessInfo, int, error) {
	h, e := windows.CreateToolhelp32Snapshot(windows.TH32CS_SNAPPROCESS, 0)
	if e != nil {
		return nil, 0, e
	}
	defer windows.CloseHandle(h)
	pe := windows.ProcessEntry32{Size: uint32(unsafe.Sizeof(windows.ProcessEntry32{}))}
	out := map[uint32]ProcessInfo{}
	denied := 0
	for e = windows.Process32First(h, &pe); e == nil; e = windows.Process32Next(h, &pe) {
		if len(out) >= 4096 {
			return out, denied, fmt.Errorf("process snapshot limit")
		}
		p := ProcessInfo{PID: pe.ProcessID, ParentPID: pe.ParentProcessID}
		handle, err := windows.OpenProcess(windows.PROCESS_QUERY_LIMITED_INFORMATION, false, pe.ProcessID)
		if err != nil {
			denied++
			continue
		}
		var create, exit, kernel, user windows.Filetime
		if windows.GetProcessTimes(handle, &create, &exit, &kernel, &user) != nil {
			windows.CloseHandle(handle)
			denied++
			continue
		}
		p.Key = strconv.FormatUint(uint64(p.PID), 10) + ":" + strconv.FormatUint(uint64(create.HighDateTime)<<32|uint64(create.LowDateTime), 10)
		buf := make([]uint16, 1024)
		n := uint32(len(buf))
		if windows.QueryFullProcessImageName(handle, 0, &buf[0], &n) == nil {
			p.Executable = windows.UTF16ToString(buf[:n])
		}
		windows.NewLazySystemDLL("kernel32.dll").NewProc("ProcessIdToSessionId").Call(uintptr(p.PID), uintptr(unsafe.Pointer(&p.Session)))
		var token windows.Token
		if windows.OpenProcessToken(handle, windows.TOKEN_QUERY, &token) == nil {
			if u, err := token.GetTokenUser(); err == nil {
				p.SID = u.User.Sid.String()
			}
			token.Close()
		}
		windows.CloseHandle(handle)
		out[p.PID] = p
	}
	if e != windows.ERROR_NO_MORE_FILES {
		return out, denied, e
	}
	for id, p := range out {
		if parent, ok := out[p.ParentPID]; ok { // Creation times fence PID reuse; unknown parent remains unknown.
			var childBorn, parentBorn uint64
			fmt.Sscanf(p.Key, "%d:%d", new(uint32), &childBorn)
			fmt.Sscanf(parent.Key, "%d:%d", new(uint32), &parentBorn)
			if parentBorn <= childBorn {
				p.ParentKey = parent.Key
				p.ParentExecutable = parent.Executable
				out[id] = p
			}
		}
	}
	return out, denied, nil
}
func BoundedHash(path string) string {
	if !filepath.IsAbs(path) || strings.HasPrefix(path, `\\`) {
		return ""
	}
	f, e := os.Open(path)
	if e != nil {
		return ""
	}
	defer f.Close()
	st, e := f.Stat()
	if e != nil || !st.Mode().IsRegular() || st.Size() > 16<<20 {
		return ""
	}
	h := sha256.New()
	if _, e = io.Copy(h, io.LimitReader(f, 16<<20)); e != nil {
		return ""
	}
	return hex.EncodeToString(h.Sum(nil))
}

type Connection struct {
	PID       uint32
	IP        string
	Port      uint16
	Key       string
	Direction string
}

func Connections() ([]Connection, error) {
	out := []Connection{}
	proc := windows.NewLazySystemDLL("iphlpapi.dll").NewProc("GetExtendedTcpTable")
	for _, af := range []uint32{2, 23} {
		var size uint32
		r, _, _ := proc.Call(0, uintptr(unsafe.Pointer(&size)), 0, uintptr(af), 5, 0)
		if r != 122 && r != 0 {
			return out, fmt.Errorf("TCP table unavailable")
		}
		if size < 4 || size > 4<<20 {
			return out, fmt.Errorf("TCP table limit")
		}
		b := make([]byte, size)
		r, _, _ = proc.Call(uintptr(unsafe.Pointer(&b[0])), uintptr(unsafe.Pointer(&size)), 0, uintptr(af), 5, 0)
		if r != 0 {
			return out, fmt.Errorf("TCP table changed; retry next poll")
		}
		count := int(binary.LittleEndian.Uint32(b[:4]))
		width := 24
		if af == 23 {
			width = 56
		}
		if count > 10000 || 4+count*width > len(b) {
			return out, fmt.Errorf("TCP table invalid")
		}
		for n := 0; n < count; n++ {
			row := b[4+n*width : 4+(n+1)*width]
			var state, pid uint32
			var ip net.IP
			var port, localPort uint16
			if af == 2 {
				state = binary.LittleEndian.Uint32(row[:4])
				pid = binary.LittleEndian.Uint32(row[20:24])
				ip = net.IP(row[12:16])
				port = binary.BigEndian.Uint16(row[16:18])
				localPort = binary.BigEndian.Uint16(row[8:10])
			} else {
				state = binary.LittleEndian.Uint32(row[48:52])
				pid = binary.LittleEndian.Uint32(row[52:56])
				ip = net.IP(row[24:40])
				port = binary.BigEndian.Uint16(row[44:46])
				localPort = binary.BigEndian.Uint16(row[20:22])
			}
			if (state != 5 && state != 2) || port == 0 {
				continue
			}
			direction := "unknown"
			if state == 2 {
				direction = "outbound_candidate"
			}
			out = append(out, Connection{pid, ip.String(), port, fmt.Sprintf("%d:%d:%s:%d", pid, localPort, ip.String(), port), direction})
		}
	}
	return out, nil
}
func Inventory() ([]map[string]any, error) {
	v := windows.RtlGetVersion()
	out := []map[string]any{{"product": "Windows", "version": fmt.Sprintf("%d.%d.%d", v.MajorVersion, v.MinorVersion, v.BuildNumber), "source": "os"}}
	failures := 0
	for _, root := range []registry.Key{registry.LOCAL_MACHINE, registry.CURRENT_USER} {
		for _, view := range []uint32{registry.WOW64_64KEY, registry.WOW64_32KEY} {
			k, e := registry.OpenKey(root, `SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall`, registry.READ|view)
			if e != nil {
				failures++
				continue
			}
			names, e := k.ReadSubKeyNames(500)
			if e != nil && e != io.EOF {
				failures++
			}
			for _, name := range names {
				sub, e := registry.OpenKey(k, name, registry.READ|view)
				if e != nil {
					continue
				}
				product, _, _ := sub.GetStringValue("DisplayName")
				version, _, _ := sub.GetStringValue("DisplayVersion")
				sub.Close()
				if product != "" && len(product) <= 128 && len(version) <= 128 {
					out = append(out, map[string]any{"product": product, "version": version, "source": "registry"})
				}
			}
			k.Close()
		}
	}
	if failures > 0 {
		return out, fmt.Errorf("some inventory keys unavailable or truncated")
	}
	return out, nil
}
