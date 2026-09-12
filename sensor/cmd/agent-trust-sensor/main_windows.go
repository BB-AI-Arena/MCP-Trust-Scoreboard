//go:build windows

package main

import (
	"context"
	"crypto/sha256"
	"encoding/json"
	"flag"
	"fmt"
	"github.com/BB-AI-Arena/MCP-Trust-Scoreboard/sensor/internal/sensor"
	"golang.org/x/sys/windows"
	"golang.org/x/sys/windows/svc"
	"golang.org/x/sys/windows/svc/mgr"
	"os"
	"os/signal"
	"path/filepath"
	"regexp"
	"strings"
	"time"
)

type service struct{ config sensor.Config }

func (s *service) failure(err error) {
	if err == nil {
		return
	}
	// Bounded diagnostic contains only a fixed error class/message; never tokens.
	_ = os.WriteFile(filepath.Join(s.config.DataDir, "service-startup.error"), []byte(err.Error()), 0600)
}

func (s *service) Execute(args []string, requests <-chan svc.ChangeRequest, status chan<- svc.Status) (bool, uint32) {
	status <- svc.Status{State: svc.StartPending, WaitHint: 30000}
	// Diagnostics retain only argument count/length/hash, never argument values.
	meta := make([]map[string]any, len(args))
	for i, arg := range args {
		h := sha256.Sum256([]byte(arg))
		meta[i] = map[string]any{"length": len(arg), "sha256_prefix": fmt.Sprintf("%x", h[:4])}
	}
	mb, _ := json.Marshal(meta)
	_ = os.WriteFile(filepath.Join(s.config.DataDir, "service-args.json"), mb, 0600)
	// Report Running before enrollment so SCM does not block on network I/O.
	// Enrollment remains explicit and failure still terminates the service.
	status <- svc.Status{State: svc.Running, Accepts: svc.AcceptStop | svc.AcceptShutdown}
	// Ephemeral StartService input, never ImagePath/process arguments or config.
	// Only an explicit operator start enrolls. Recovery never reenrolls.
	var bootstrap string
	for _, arg := range args {
		if len(arg) >= 32 && !strings.HasPrefix(arg, "-") && !strings.ContainsAny(arg, `\\/:.`) {
			bootstrap = arg
			break
		}
	}
	if bootstrap != "" {
		if err := sensor.Enroll(s.config, bootstrap); err != nil {
			s.failure(err)
			return false, 3
		}
	}
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	done := make(chan error, 1)
	go func() { done <- sensor.Run(ctx, s.config) }()
	for {
		select {
		case err := <-done:
			if err != nil {
				s.failure(err)
				return false, 1
			}
			return false, 0
		case request := <-requests:
			switch request.Cmd {
			case svc.Interrogate:
				status <- request.CurrentStatus
			case svc.Stop, svc.Shutdown:
				status <- svc.Status{State: svc.StopPending}
				cancel()
				select {
				case <-done:
					return false, 0
				case <-time.After(15 * time.Second):
					return false, 2
				}
			}
		}
	}
}
func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, "sensor:", err)
		os.Exit(1)
	}
}
func run() error {
	if len(os.Args) < 2 {
		return fmt.Errorf("command required: version, enroll, run, service, install-service, uninstall-service")
	}
	command := os.Args[1]
	if command == "version" {
		v := windows.RtlGetVersion()
		return json.NewEncoder(os.Stdout).Encode(map[string]any{"sensor": sensor.Version, "application": sensor.ApplicationVersion, "commit": sensor.Commit, "windows_build": v.BuildNumber, "architecture": "amd64", "observe_only": true})
	}
	flags := flag.NewFlagSet(command, flag.ContinueOnError)
	path := flags.String("config", "", "private configuration path")
	name := flags.String("name", "AgentTrustEndpoint", "sensor-owned service name")
	seconds := flags.Int("seconds", 0, "bounded foreground runtime, 0 until stopped")
	if err := flags.Parse(os.Args[2:]); err != nil {
		return err
	}
	if !regexp.MustCompile(`^AgentTrustEndpoint[-A-Za-z0-9]*$`).MatchString(*name) {
		return fmt.Errorf("invalid service name")
	}
	if command == "uninstall-service" {
		m, e := mgr.Connect()
		if e != nil {
			return fmt.Errorf("service manager unavailable")
		}
		defer m.Disconnect()
		s, e := m.OpenService(*name)
		if e != nil {
			return e
		}
		defer s.Close()
		cfg, e := s.Config()
		exe, _ := os.Executable()
		argv, parseErr := windows.DecomposeCommandLine(cfg.BinaryPathName)
		if e != nil || parseErr != nil || len(argv) != 6 || !strings.EqualFold(argv[0], exe) || argv[1] != "service" || argv[2] != "--config" || argv[4] != "--name" || argv[5] != *name {
			return fmt.Errorf("refusing unrelated service removal")
		}
		state, e := s.Query()
		if e != nil {
			return e
		}
		if state.State != svc.Stopped {
			if _, e = s.Control(svc.Stop); e != nil {
				return e
			}
			deadline := time.Now().Add(30 * time.Second)
			for state.State != svc.Stopped && time.Now().Before(deadline) {
				time.Sleep(200 * time.Millisecond)
				state, e = s.Query()
				if e != nil {
					return e
				}
			}
			if state.State != svc.Stopped {
				return fmt.Errorf("service stop timed out")
			}
		}
		return s.Delete()
	}
	c, err := sensor.LoadConfig(*path)
	if err != nil {
		return err
	}
	switch command {
	case "enroll":
		secret := os.Getenv("AGENT_TRUST_ENROLLMENT_SECRET")
		os.Unsetenv("AGENT_TRUST_ENROLLMENT_SECRET")
		return sensor.Enroll(c, secret)
	case "run":
		ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt)
		defer stop()
		if *seconds > 0 {
			var cancel context.CancelFunc
			ctx, cancel = context.WithTimeout(ctx, time.Duration(*seconds)*time.Second)
			defer cancel()
		}
		return sensor.Run(ctx, c)
	case "service":
		return svc.Run(*name, &service{c})
	case "install-service":
		exe, e := os.Executable()
		if e != nil {
			return e
		}
		config, e := filepath.Abs(*path)
		if e != nil {
			return e
		}
		m, e := mgr.Connect()
		if e != nil {
			return e
		}
		defer m.Disconnect()
		s, e := m.CreateService(*name, exe, mgr.Config{DisplayName: "Agent Trust Endpoint Sensor (observe-only)", StartType: mgr.StartAutomatic, ServiceStartName: `NT SERVICE\` + *name}, "service", "--config", config, "--name", *name)
		if e != nil {
			return e
		}
		defer s.Close()
		if e = s.SetRecoveryActions([]mgr.RecoveryAction{{Type: mgr.ServiceRestart, Delay: 5 * time.Second}, {Type: mgr.ServiceRestart, Delay: 30 * time.Second}, {Type: mgr.NoAction}}, 86400); e != nil {
			s.Delete()
			return e
		}
		if e = s.SetRecoveryActionsOnNonCrashFailures(true); e != nil {
			s.Delete()
			return e
		}
		return nil
	default:
		return fmt.Errorf("unsupported command")
	}
}
