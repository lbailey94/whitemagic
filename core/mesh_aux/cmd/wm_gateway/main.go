// Command wm_gateway is the WhiteMagic cognitive gateway.
//
// It extends the mesh node with a CognitiveService gRPC server that
// exposes tool dispatch, citta streaming, session management, dream
// events, and telemetry to TUI / IDE / PWA clients.
//
// By default it listens on a Unix domain socket (/tmp/whitemagic/wm.sock)
// for local IPC and optionally on TCP (localhost:4730) for browser bridge.
//
// Mesh (libp2p) is opt-in: pass --mesh to enable P2P discovery.
package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"net"
	"os"
	"os/signal"
	"path/filepath"
	"sync"
	"sync/atomic"
	"syscall"
	"time"

	pb "whitemagic-go/proto"

	"google.golang.org/grpc"
)

const (
	Version    = "24.0.0-dev"
	SocketPath = "/tmp/whitemagic/wm.sock"
	TCPPort    = 4730
)

// ── Cognitive Server ────────────────────────────────────────────────

type CognitiveServer struct {
	pb.UnimplementedCognitiveServiceServer

	mu        sync.RWMutex
	startTime time.Time
	clients   int64
	privacy   string

	cittaSubs   map[chan *pb.CittaMoment]struct{}
	cittaSubsMu sync.RWMutex

	dreamSubs   map[chan *pb.DreamEvent]struct{}
	dreamSubsMu sync.RWMutex
}

func NewCognitiveServer() *CognitiveServer {
	return &CognitiveServer{
		startTime: time.Now(),
		privacy:   "local_only",
		cittaSubs: make(map[chan *pb.CittaMoment]struct{}),
		dreamSubs: make(map[chan *pb.DreamEvent]struct{}),
	}
}

func (s *CognitiveServer) broadcastCitta(moment *pb.CittaMoment) {
	s.cittaSubsMu.RLock()
	defer s.cittaSubsMu.RUnlock()
	for ch := range s.cittaSubs {
		select {
		case ch <- moment:
		default:
		}
	}
}

func (s *CognitiveServer) broadcastDream(event *pb.DreamEvent) {
	s.dreamSubsMu.RLock()
	defer s.dreamSubsMu.RUnlock()
	for ch := range s.dreamSubs {
		select {
		case ch <- event:
		default:
		}
	}
}

// ── RPC implementations ─────────────────────────────────────────────

func (s *CognitiveServer) CallTool(
	req *pb.ToolRequest,
	stream grpc.ServerStreamingServer[pb.ToolEvent],
) error {
	atomic.AddInt64(&s.clients, 1)
	defer atomic.AddInt64(&s.clients, -1)

	toolEvent := &pb.ToolEvent{
		Status:    "complete",
		RequestId: fmt.Sprintf("gw_%d", time.Now().UnixNano()),
		Payload:   []byte(`{"status":"success","tool":"` + req.Tool + `","message":"gateway ready"}`),
		Citta: &pb.CittaMoment{
			Timestamp:  time.Now().Unix(),
			Gana:       req.Gana,
			Operation:  req.Operation,
			DepthLayer: "surface",
		},
	}
	return stream.Send(toolEvent)
}

func (s *CognitiveServer) CittaStream(
	req *pb.CittaSubscribe,
	stream grpc.ServerStreamingServer[pb.CittaMoment],
) error {
	ch := make(chan *pb.CittaMoment, 64)
	s.cittaSubsMu.Lock()
	s.cittaSubs[ch] = struct{}{}
	s.cittaSubsMu.Unlock()
	defer func() {
		s.cittaSubsMu.Lock()
		delete(s.cittaSubs, ch)
		s.cittaSubsMu.Unlock()
		close(ch)
	}()

	atomic.AddInt64(&s.clients, 1)
	defer atomic.AddInt64(&s.clients, -1)

	ctx := stream.Context()
	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case moment := <-ch:
			if err := stream.Send(moment); err != nil {
				return err
			}
		}
	}
}

func (s *CognitiveServer) CreateSession(
	ctx context.Context,
	req *pb.SessionRequest,
) (*pb.SessionResponse, error) {
	sessionID := fmt.Sprintf("sess_%d", time.Now().UnixNano())
	return &pb.SessionResponse{
		SessionId:         sessionID,
		CreatedAt:         time.Now().Unix(),
		ContinuityContext: "{}",
	}, nil
}

func (s *CognitiveServer) ResumeSession(
	req *pb.SessionResume,
	stream grpc.ServerStreamingServer[pb.CittaMoment],
) error {
	moment := &pb.CittaMoment{
		Timestamp:     time.Now().Unix(),
		Gana:          "_heartbeat",
		Operation:     "session_resume",
		DepthLayer:    "surface",
		EmotionalTone: "sattvic",
		Coherence:     1.0,
		CycleNumber:   int32(req.LastCycle),
	}
	return stream.Send(moment)
}

func (s *CognitiveServer) DreamEvents(
	req *pb.DreamSubscribe,
	stream grpc.ServerStreamingServer[pb.DreamEvent],
) error {
	ch := make(chan *pb.DreamEvent, 16)
	s.dreamSubsMu.Lock()
	s.dreamSubs[ch] = struct{}{}
	s.dreamSubsMu.Unlock()
	defer func() {
		s.dreamSubsMu.Lock()
		delete(s.dreamSubs, ch)
		s.dreamSubsMu.Unlock()
		close(ch)
	}()

	atomic.AddInt64(&s.clients, 1)
	defer atomic.AddInt64(&s.clients, -1)

	ctx := stream.Context()
	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case event := <-ch:
			if err := stream.Send(event); err != nil {
				return err
			}
		}
	}
}

func (s *CognitiveServer) Telemetry(
	req *pb.TelemetryRequest,
	stream grpc.ServerStreamingServer[pb.TelemetrySnapshot],
) error {
	interval := time.Duration(req.IntervalMs) * time.Millisecond
	if interval < 100*time.Millisecond {
		interval = 1 * time.Second
	}

	atomic.AddInt64(&s.clients, 1)
	defer atomic.AddInt64(&s.clients, -1)

	ctx := stream.Context()
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case t := <-ticker.C:
			snap := &pb.TelemetrySnapshot{
				Timestamp:        t.Unix(),
				ConnectedClients: int32(atomic.LoadInt64(&s.clients)),
				PrivacyStatus:    s.privacy,
				BytesEgress:      0,
			}
			if err := stream.Send(snap); err != nil {
				return err
			}
		}
	}
}

func (s *CognitiveServer) DaemonStatus(
	ctx context.Context,
	req *pb.StatusRequest,
) (*pb.StatusResponse, error) {
	return &pb.StatusResponse{
		Running:          true,
		UptimeSeconds:    int64(time.Since(s.startTime).Seconds()),
		Version:          Version,
		ConnectedClients: int32(atomic.LoadInt64(&s.clients)),
		PrivacyStatus:    s.privacy,
		ActiveLoops:      []string{"gamma", "beta", "alpha", "theta", "delta"},
	}, nil
}

func (s *CognitiveServer) DaemonShutdown(
	ctx context.Context,
	req *pb.ShutdownRequest,
) (*pb.StatusResponse, error) {
	log.Println("Shutdown requested via gRPC")
	p, _ := os.FindProcess(os.Getpid())
	p.Signal(syscall.SIGTERM)
	return &pb.StatusResponse{Running: false, Version: Version}, nil
}

func (s *CognitiveServer) updatePrivacy(status string) {
	s.mu.Lock()
	s.privacy = status
	s.mu.Unlock()
}

// ── Mesh service stub (backward compat) ─────────────────────────────

type meshServiceImpl struct {
	pb.UnimplementedMeshServiceServer
}

func (m *meshServiceImpl) BroadcastSignal(
	ctx context.Context, req *pb.SignalRequest,
) (*pb.SignalResponse, error) {
	return &pb.SignalResponse{Success: true, Message: "ok"}, nil
}

func (m *meshServiceImpl) BroadcastHologram(
	ctx context.Context, req *pb.HolographicSignal,
) (*pb.SignalResponse, error) {
	return &pb.SignalResponse{Success: true, Message: "ok"}, nil
}

func (m *meshServiceImpl) DiscoverPeers(
	ctx context.Context, req *pb.DiscoveryRequest,
) (*pb.DiscoveryResponse, error) {
	return &pb.DiscoveryResponse{}, nil
}

// ── Main ────────────────────────────────────────────────────────────

func main() {
	meshFlag := flag.Bool("mesh", false, "Enable P2P mesh (opt-in)")
	tcpFlag := flag.Bool("tcp", false, "Also listen on TCP localhost:4730")
	socketFlag := flag.String("socket", SocketPath, "Unix domain socket path")
	flag.Parse()

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	fmt.Printf("🌐 WhiteMagic Cognitive Gateway %s\n", Version)
	fmt.Printf("   Privacy: local_only (mesh=%v)\n", *meshFlag)

	socketDir := filepath.Dir(*socketFlag)
	if err := os.MkdirAll(socketDir, 0755); err != nil {
		log.Fatalf("Failed to create socket dir: %v", err)
	}

	os.Remove(*socketFlag)

	lis, err := net.Listen("unix", *socketFlag)
	if err != nil {
		log.Fatalf("Failed to listen on Unix socket: %v", err)
	}
	defer os.Remove(*socketFlag)

	grpcServer := grpc.NewServer()
	cogServer := NewCognitiveServer()
	pb.RegisterCognitiveServiceServer(grpcServer, cogServer)
	pb.RegisterMeshServiceServer(grpcServer, &meshServiceImpl{})

	if *tcpFlag {
		tcpLis, err := net.Listen("tcp", fmt.Sprintf("localhost:%d", TCPPort))
		if err != nil {
			log.Printf("⚠️ TCP listen failed: %v", err)
		} else {
			defer tcpLis.Close()
			log.Printf("✅ TCP listening on localhost:%d", TCPPort)
			go func() {
				if err := grpcServer.Serve(tcpLis); err != nil {
					log.Printf("TCP serve error: %v", err)
				}
			}()
		}
	}

	if *meshFlag {
		cogServer.updatePrivacy("mesh_enabled")
		log.Println("📡 Mesh enabled (opt-in)")
	}

	// Telemetry heartbeat
	go func() {
		ticker := time.NewTicker(30 * time.Second)
		defer ticker.Stop()
		for {
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
				clients := atomic.LoadInt64(&cogServer.clients)
				log.Printf("📊 uptime=%vs clients=%d privacy=%s",
					int64(time.Since(cogServer.startTime).Seconds()),
					clients, cogServer.privacy)
			}
		}
	}()

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		if err := grpcServer.Serve(lis); err != nil {
			log.Printf("gRPC serve error: %v", err)
		}
	}()

	fmt.Printf("✅ gRPC listening on Unix socket: %s\n", *socketFlag)
	fmt.Println("   Press Ctrl+C to stop")

	<-sigCh
	fmt.Println("\n🌐 Cognitive Gateway shutting down...")
	grpcServer.GracefulStop()
}
