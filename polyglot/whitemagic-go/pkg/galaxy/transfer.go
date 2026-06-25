package galaxy

import (
	"bytes"
	"context"
	"encoding/binary"
	"fmt"
	"io"
	"sync"
)

// ChunkSize is the default chunk size for galaxy transfer (1 MB).
const ChunkSize = 1024 * 1024

// MagicHeader identifies WhiteMagic galaxy transfer streams.
var MagicHeader = []byte("WMGX") // WhiteMagic Galaxy eXchange

// GalaxyTransfer handles chunked transfer of galaxy Arrow IPC data.
// It supports both streaming (for gRPC) and chunked (for UDP/QUIC) modes.
type GalaxyTransfer struct {
	mu sync.Mutex
	// Progress callback called after each chunk
	OnProgress func(transferred, total int64)
}

// NewGalaxyTransfer creates a new transfer handler.
func NewGalaxyTransfer() *GalaxyTransfer {
	return &GalaxyTransfer{}
}

// GalaxyChunk represents a single chunk of galaxy data.
type GalaxyChunk struct {
	Index    uint32
	Offset   int64
	Size     int32
	Data     []byte
	IsLast   bool
	GalaxyID string
}

// GalaxyMetadata describes a galaxy being transferred.
type GalaxyMetadata struct {
	GalaxyID    string `json:"galaxy_id"`
	MemoryCount int64  `json:"memory_count"`
	TotalBytes  int64  `json:"total_bytes"`
	ChunkCount  uint32 `json:"chunk_count"`
	Checksum    string `json:"checksum"`
}

// SerializeGalaxy wraps Arrow IPC bytes with galaxy metadata header.
// Format: [MAGIC(4)] [galaxy_id_len(2)] [galaxy_id(N)] [total_len(8)] [ipc_bytes...]
func SerializeGalaxy(galaxyID string, ipcBytes []byte) ([]byte, error) {
	if len(galaxyID) > 65535 {
		return nil, fmt.Errorf("galaxy ID too long: %d bytes", len(galaxyID))
	}

	var buf bytes.Buffer
	buf.Write(MagicHeader)

	idLen := uint16(len(galaxyID))
	if err := binary.Write(&buf, binary.BigEndian, idLen); err != nil {
		return nil, fmt.Errorf("write galaxy_id_len: %w", err)
	}
	buf.WriteString(galaxyID)

	totalLen := int64(len(ipcBytes))
	if err := binary.Write(&buf, binary.BigEndian, totalLen); err != nil {
		return nil, fmt.Errorf("write total_len: %w", err)
	}
	buf.Write(ipcBytes)

	return buf.Bytes(), nil
}

// DeserializeGalaxy extracts galaxy ID and Arrow IPC bytes from a serialized stream.
func DeserializeGalaxy(data []byte) (galaxyID string, ipcBytes []byte, err error) {
	if len(data) < len(MagicHeader)+2+8 {
		return "", nil, fmt.Errorf("data too short: %d bytes", len(data))
	}

	if !bytes.HasPrefix(data, MagicHeader) {
		return "", nil, fmt.Errorf("invalid magic header")
	}

	pos := len(MagicHeader)
	idLen := binary.BigEndian.Uint16(data[pos:])
	pos += 2

	if pos+int(idLen) > len(data) {
		return "", nil, fmt.Errorf("galaxy ID truncated")
	}
	galaxyID = string(data[pos : pos+int(idLen)])
	pos += int(idLen)

	totalLen := int64(binary.BigEndian.Uint64(data[pos:]))
	pos += 8

	if pos+int(totalLen) > len(data) {
		return "", nil, fmt.Errorf("IPC data truncated: expected %d, got %d", totalLen, len(data)-pos)
	}

	ipcBytes = data[pos : pos+int(totalLen)]
	return galaxyID, ipcBytes, nil
}

// ChunkGalaxy splits serialized galaxy data into chunks for streaming.
func (gt *GalaxyTransfer) ChunkGalaxy(galaxyID string, ipcBytes []byte) ([]GalaxyChunk, error) {
	serialized, err := SerializeGalaxy(galaxyID, ipcBytes)
	if err != nil {
		return nil, err
	}

	var chunks []GalaxyChunk
	totalSize := int64(len(serialized))
	offset := int64(0)
	index := uint32(0)

	for offset < totalSize {
		end := offset + int64(ChunkSize)
		if end > totalSize {
			end = totalSize
		}

		chunk := GalaxyChunk{
			Index:    index,
			Offset:   offset,
			Size:     int32(end - offset),
			Data:     serialized[offset:end],
			IsLast:   end >= totalSize,
			GalaxyID: galaxyID,
		}
		chunks = append(chunks, chunk)

		offset = end
		index++
	}

	return chunks, nil
}

// ReassembleGalaxy reassembles chunks back into serialized galaxy data.
func (gt *GalaxyTransfer) ReassembleGalaxy(chunks []GalaxyChunk) (galaxyID string, ipcBytes []byte, err error) {
	if len(chunks) == 0 {
		return "", nil, fmt.Errorf("no chunks provided")
	}

	// Sort chunks by index (simple bubble sort for small chunk counts)
	gt.mu.Lock()
	defer gt.mu.Unlock()

	sorted := make([]GalaxyChunk, len(chunks))
	copy(sorted, chunks)
	for i := 0; i < len(sorted)-1; i++ {
		for j := i + 1; j < len(sorted); j++ {
			if sorted[j].Index < sorted[i].Index {
				sorted[i], sorted[j] = sorted[j], sorted[i]
			}
		}
	}

	// Reassemble
	var buf bytes.Buffer
	for i, chunk := range sorted {
		if chunk.Index != uint32(i) {
			return "", nil, fmt.Errorf("missing chunk %d (got %d)", i, chunk.Index)
		}
		buf.Write(chunk.Data)
	}

	return DeserializeGalaxy(buf.Bytes())
}

// StreamGalaxy streams galaxy data through a reader, calling OnProgress for each chunk.
func (gt *GalaxyTransfer) StreamGalaxy(ctx context.Context, galaxyID string, ipcBytes []byte, writer io.Writer) error {
	chunks, err := gt.ChunkGalaxy(galaxyID, ipcBytes)
	if err != nil {
		return fmt.Errorf("chunk galaxy: %w", err)
	}

	totalBytes := int64(len(ipcBytes))
	transferred := int64(0)

	for _, chunk := range chunks {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}

		n, err := writer.Write(chunk.Data)
		if err != nil {
			return fmt.Errorf("write chunk %d: %w", chunk.Index, err)
		}
		if n != len(chunk.Data) {
			return fmt.Errorf("short write on chunk %d: wrote %d, expected %d", chunk.Index, n, len(chunk.Data))
		}

		transferred += int64(n)
		if gt.OnProgress != nil {
			gt.OnProgress(transferred, totalBytes)
		}
	}

	return nil
}

// ReceiveGalaxy reads chunked galaxy data from a reader and reassembles it.
func (gt *GalaxyTransfer) ReceiveGalaxy(ctx context.Context, reader io.Reader) (galaxyID string, ipcBytes []byte, err error) {
	// Read magic header
	magic := make([]byte, len(MagicHeader))
	if _, err := io.ReadFull(reader, magic); err != nil {
		return "", nil, fmt.Errorf("read magic: %w", err)
	}
	if !bytes.Equal(magic, MagicHeader) {
		return "", nil, fmt.Errorf("invalid magic header")
	}

	// Read galaxy ID length
	var idLen uint16
	if err := binary.Read(reader, binary.BigEndian, &idLen); err != nil {
		return "", nil, fmt.Errorf("read id_len: %w", err)
	}

	// Read galaxy ID
	idBytes := make([]byte, idLen)
	if _, err := io.ReadFull(reader, idBytes); err != nil {
		return "", nil, fmt.Errorf("read galaxy_id: %w", err)
	}
	galaxyID = string(idBytes)

	// Read total IPC length
	var totalLen int64
	if err := binary.Read(reader, binary.BigEndian, &totalLen); err != nil {
		return "", nil, fmt.Errorf("read total_len: %w", err)
	}

	// Read IPC bytes with progress tracking
	ipcBytes = make([]byte, totalLen)
	transferred := int64(0)
	buf := make([]byte, ChunkSize)

	for transferred < totalLen {
		select {
		case <-ctx.Done():
			return "", nil, ctx.Err()
		default:
		}

		remaining := totalLen - transferred
		readSize := int64(ChunkSize)
		if remaining < readSize {
			readSize = remaining
		}

		n, err := io.ReadFull(reader, buf[:readSize])
		if err != nil {
			return "", nil, fmt.Errorf("read ipc data at offset %d: %w", transferred, err)
		}
		copy(ipcBytes[transferred:], buf[:n])
		transferred += int64(n)

		if gt.OnProgress != nil {
			gt.OnProgress(transferred, totalLen)
		}
	}

	return galaxyID, ipcBytes, nil
}
