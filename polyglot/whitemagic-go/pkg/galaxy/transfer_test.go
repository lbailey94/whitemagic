package galaxy

import (
	"bytes"
	"context"
	"encoding/binary"
	"strings"
	"testing"
)

func TestSerializeDeserializeGalaxy(t *testing.T) {
	galaxyID := "oracle"
	ipcBytes := []byte("fake arrow ipc data for testing")

	serialized, err := SerializeGalaxy(galaxyID, ipcBytes)
	if err != nil {
		t.Fatalf("SerializeGalaxy failed: %v", err)
	}

	gotID, gotIPC, err := DeserializeGalaxy(serialized)
	if err != nil {
		t.Fatalf("DeserializeGalaxy failed: %v", err)
	}

	if gotID != galaxyID {
		t.Errorf("galaxy ID mismatch: got %q, want %q", gotID, galaxyID)
	}

	if !bytes.Equal(gotIPC, ipcBytes) {
		t.Errorf("IPC bytes mismatch: got %d bytes, want %d bytes", len(gotIPC), len(ipcBytes))
	}
}

func TestSerializeGalaxyInvalidMagic(t *testing.T) {
	data := []byte("XXXX" + string([]byte{0, 5}) + "test" + string([]byte{0, 0, 0, 0, 0, 0, 0, 3}) + "abc")
	_, _, err := DeserializeGalaxy(data)
	if err == nil {
		t.Fatal("expected error for invalid magic header")
	}
	if !strings.Contains(err.Error(), "magic") {
		t.Errorf("expected magic error, got: %v", err)
	}
}

func TestSerializeGalaxyTooShort(t *testing.T) {
	_, _, err := DeserializeGalaxy([]byte("short"))
	if err == nil {
		t.Fatal("expected error for short data")
	}
}

func TestChunkGalaxy(t *testing.T) {
	gt := NewGalaxyTransfer()
	galaxyID := "insight"
	// Create data larger than one chunk
	ipcBytes := make([]byte, ChunkSize*2+1024)
	for i := range ipcBytes {
		ipcBytes[i] = byte(i % 256)
	}

	chunks, err := gt.ChunkGalaxy(galaxyID, ipcBytes)
	if err != nil {
		t.Fatalf("ChunkGalaxy failed: %v", err)
	}

	if len(chunks) < 3 {
		t.Errorf("expected at least 3 chunks, got %d", len(chunks))
	}

	// Verify last chunk is marked as last
	if !chunks[len(chunks)-1].IsLast {
		t.Error("last chunk should have IsLast=true")
	}

	// Verify all chunks have correct galaxy ID
	for i, chunk := range chunks {
		if chunk.GalaxyID != galaxyID {
			t.Errorf("chunk %d galaxy ID: got %q, want %q", i, chunk.GalaxyID, galaxyID)
		}
		if chunk.Index != uint32(i) {
			t.Errorf("chunk %d index: got %d, want %d", i, chunk.Index, i)
		}
	}
}

func TestReassembleGalaxy(t *testing.T) {
	gt := NewGalaxyTransfer()
	galaxyID := "creative_solutions"
	ipcBytes := []byte("test ipc data for reassembly test with enough data to chunk")

	chunks, err := gt.ChunkGalaxy(galaxyID, ipcBytes)
	if err != nil {
		t.Fatalf("ChunkGalaxy failed: %v", err)
	}

	gotID, gotIPC, err := gt.ReassembleGalaxy(chunks)
	if err != nil {
		t.Fatalf("ReassembleGalaxy failed: %v", err)
	}

	if gotID != galaxyID {
		t.Errorf("galaxy ID: got %q, want %q", gotID, galaxyID)
	}

	if !bytes.Equal(gotIPC, ipcBytes) {
		t.Errorf("IPC bytes mismatch: got %d, want %d bytes", len(gotIPC), len(ipcBytes))
	}
}

func TestReassembleGalaxyMissingChunk(t *testing.T) {
	gt := NewGalaxyTransfer()
	galaxyID := "universal"
	ipcBytes := make([]byte, ChunkSize*2)

	chunks, err := gt.ChunkGalaxy(galaxyID, ipcBytes)
	if err != nil {
		t.Fatalf("ChunkGalaxy failed: %v", err)
	}

	// Remove middle chunk
	if len(chunks) < 2 {
		t.Skip("not enough chunks to test missing")
	}
	chunks = append(chunks[:1], chunks[2:]...)

	_, _, err = gt.ReassembleGalaxy(chunks)
	if err == nil {
		t.Fatal("expected error for missing chunk")
	}
}

func TestReassembleGalaxyEmpty(t *testing.T) {
	gt := NewGalaxyTransfer()
	_, _, err := gt.ReassembleGalaxy(nil)
	if err == nil {
		t.Fatal("expected error for empty chunks")
	}
}

func TestStreamAndReceiveGalaxy(t *testing.T) {
	gt := NewGalaxyTransfer()
	progressCalls := 0
	gt.OnProgress = func(transferred, total int64) {
		progressCalls++
	}

	galaxyID := "self_learning"
	ipcBytes := make([]byte, ChunkSize*2+512)
	for i := range ipcBytes {
		ipcBytes[i] = byte(i % 256)
	}

	// Stream to a buffer
	var buf bytes.Buffer
	err := gt.StreamGalaxy(context.Background(), galaxyID, ipcBytes, &buf)
	if err != nil {
		t.Fatalf("StreamGalaxy failed: %v", err)
	}

	if progressCalls == 0 {
		t.Error("OnProgress was never called")
	}

	// Receive from the buffer
	gotID, gotIPC, err := gt.ReceiveGalaxy(context.Background(), &buf)
	if err != nil {
		t.Fatalf("ReceiveGalaxy failed: %v", err)
	}

	if gotID != galaxyID {
		t.Errorf("galaxy ID: got %q, want %q", gotID, galaxyID)
	}

	if !bytes.Equal(gotIPC, ipcBytes) {
		t.Errorf("IPC bytes mismatch after roundtrip: got %d, want %d bytes", len(gotIPC), len(ipcBytes))
	}
}

func TestStreamGalaxyContextCancel(t *testing.T) {
	gt := NewGalaxyTransfer()
	galaxyID := "oracle"
	ipcBytes := make([]byte, ChunkSize*10)

	ctx, cancel := context.WithCancel(context.Background())
	cancel() // Cancel immediately

	var buf bytes.Buffer
	err := gt.StreamGalaxy(ctx, galaxyID, ipcBytes, &buf)
	if err == nil {
		t.Fatal("expected error for cancelled context")
	}
}

func TestSerializeGalaxyLargeID(t *testing.T) {
	// Galaxy ID over 65535 bytes should fail
	longID := strings.Repeat("x", 70000)
	_, err := SerializeGalaxy(longID, []byte("data"))
	if err == nil {
		t.Fatal("expected error for galaxy ID too long")
	}
}

func TestRoundtripSmallData(t *testing.T) {
	gt := NewGalaxyTransfer()
	galaxyID := "universal"
	ipcBytes := []byte("tiny")

	chunks, err := gt.ChunkGalaxy(galaxyID, ipcBytes)
	if err != nil {
		t.Fatalf("ChunkGalaxy failed: %v", err)
	}

	if len(chunks) != 1 {
		t.Errorf("expected 1 chunk for tiny data, got %d", len(chunks))
	}

	gotID, gotIPC, err := gt.ReassembleGalaxy(chunks)
	if err != nil {
		t.Fatalf("ReassembleGalaxy failed: %v", err)
	}

	if gotID != galaxyID || !bytes.Equal(gotIPC, ipcBytes) {
		t.Error("roundtrip mismatch for small data")
	}
}

func TestGalaxyMetadataSerialization(t *testing.T) {
	// Verify the binary format is stable
	galaxyID := "test"
	ipcBytes := []byte("data")

	serialized, _ := SerializeGalaxy(galaxyID, ipcBytes)

	// Check magic header
	if !bytes.HasPrefix(serialized, MagicHeader) {
		t.Fatal("missing magic header")
	}

	// Check galaxy ID length field
	pos := len(MagicHeader)
	idLen := binary.BigEndian.Uint16(serialized[pos:])
	if int(idLen) != len(galaxyID) {
		t.Errorf("ID length: got %d, want %d", idLen, len(galaxyID))
	}
}
