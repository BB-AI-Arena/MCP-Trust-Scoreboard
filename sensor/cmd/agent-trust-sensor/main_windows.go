//go:build windows

package main

import (
	"context"
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

func (s *service) Execute(_ []string, requests <-chan svc.ChangeRequest, status chan<- svc.Status) (bool, uint32) {
	status <- svc.Status{State: svc.StartPending}
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	done := make(chan error, 1)
	go func() { done <- sensor.Run(ctx, s.config) }()
	status <- svc.Status{State: svc.Running, Accepts: svc.AcceptStop | svc.AcceptShutdown}
	for {
		select {
		case err := <-done:
			if err != nil {
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
		if e != nil || !strings.Contains(strings.ToLower(cfg.BinaryPathName), strings.ToLower(exe)) {
			return fmt.Errorf("refusing unrelated service removal")
		}
		state, e := s.Query()
		if e != nil || state.State != svc.Stopped {
			return fmt.Errorf("stop sensor before uninstalling")
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
	case "install-service": // No account credentials accepted/stored. Operator selects account later.
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
		s, e := m.CreateService(*name, exe, mgr.Config{DisplayName: "Agent Trust Endpoint Sensor (observe-only)", StartType: mgr.StartManual}, "service", "--config", config, "--name", *name)
		if e != nil {
			return e
		}
		defer s.Close()
		return nil
	default:
		return fmt.Errorf("unsupported command")
	}
}
