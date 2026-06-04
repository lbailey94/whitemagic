// Galactic Telepathy & Horizontal Gene Transfer (Go Implementation)
//
// Q4 Cross-Database Synchronization - Go Implementation
// Optimized for concurrent, high-throughput memory transfer
// with goroutine-based parallel processing.

package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"sync"
	"time"
)

// SyncConflictType represents types of conflicts during transfer
type SyncConflictType string

const (
	DivergentContent    SyncConflictType = "divergent_content"
	DivergentMetadata   SyncConflictType = "divergent_metadata"
	OrphanAssociation   SyncConflictType = "orphan_association"
	EmbeddingMismatch   SyncConflictType = "embedding_mismatch"
	TimestampInversion  SyncConflictType = "timestamp_inversion"
)

// SyncConflict represents a conflict requiring resolution
type SyncConflict struct {
	ConflictType        SyncConflictType `json:"conflict_type"`
	MemoryID            string           `json:"memory_id"`
	SourceGalaxy        string           `json:"source_galaxy"`
	TargetGalaxy        string           `json:"target_galaxy"`
	Details             map[string]interface{} `json:"details"`
	SuggestedResolution string           `json:"suggested_resolution"`
	AutoResolvable      bool             `json:"auto_resolvable"`
}

// EmbeddingBundle holds embedding data for transfer
type EmbeddingBundle struct {
	MemoryID   string    `json:"memory_id"`
	ModelName  string    `json:"model_name"`
	Vector     []float32 `json:"vector"`
	Dimensions uint32    `json:"dimensions"`
	CreatedAt  string    `json:"created_at"`
}

// AssociationBundle holds association data for transfer
type AssociationBundle struct {
	SourceID     string                 `json:"source_id"`
	TargetID     string                 `json:"target_id"`
	RelationType string                 `json:"relation_type"`
	Strength     float32                `json:"strength"`
	Direction    string                 `json:"direction"`
	EdgeType     *string                `json:"edge_type,omitempty"`
	Metadata     map[string]interface{} `json:"metadata"`
}

// MemoryRecord represents a memory in the system
type MemoryRecord struct {
	ID               string                 `json:"id"`
	Content          string                 `json:"content"`
	ContentHash      string                 `json:"content_hash"`
	Title            *string                `json:"title,omitempty"`
	MemoryType       string                 `json:"memory_type"`
	Tags             []string               `json:"tags"`
	Importance       float32                `json:"importance"`
	EmotionalValence *float32               `json:"emotional_valence,omitempty"`
	Metadata         map[string]interface{} `json:"metadata"`
	CreatedAt        float64                `json:"created_at"`
	ModifiedAt       float64                `json:"modified_at"`
	GalacticDistance *float32               `json:"galactic_distance,omitempty"`
}

// ComputeContentHash calculates SHA-256 hash of content
func ComputeContentHash(content string) string {
	hash := sha256.Sum256([]byte(content))
	return hex.EncodeToString(hash[:])
}

// NewMemoryRecord creates a new memory record with computed hash
func NewMemoryRecord(content string, title *string, memoryType string) MemoryRecord {
	now := float64(time.Now().Unix())
	return MemoryRecord{
		ID:          fmt.Sprintf("mem_%d", time.Now().UnixNano()),
		Content:     content,
		ContentHash: ComputeContentHash(content),
		Title:       title,
		MemoryType:  memoryType,
		Tags:        []string{},
		Importance:  0.5,
		Metadata:    make(map[string]interface{}),
		CreatedAt:   now,
		ModifiedAt:  now,
	}
}

// SyncWatermark tracks last sync point
type SyncWatermark struct {
	GalaxyPair              string  `json:"galaxy_pair"`
	LastSyncTimestamp       float64 `json:"last_sync_timestamp"`
	LastMemoryID            *string `json:"last_memory_id,omitempty"`
	MemoriesSyncedCount     uint64  `json:"memories_synced_count"`
	AssociationsSyncedCount uint64  `json:"associations_synced_count"`
	EmbeddingsSyncedCount   uint64  `json:"embeddings_synced_count"`
}

// ConflictResolution strategy enum
type ConflictResolution int

const (
	TimestampWins ConflictResolution = iota
	SourceWins
	TargetWins
	Manual
)

// SyncOptions configures sync behavior
type SyncOptions struct {
	SinceTimestamp       *float64
	IncludeEmbeddings    bool
	IncludeAssociations  bool
	ConflictResolution ConflictResolution
}

// DefaultSyncOptions returns default options
func DefaultSyncOptions() SyncOptions {
	return SyncOptions{
		IncludeEmbeddings:    true,
		IncludeAssociations:  true,
		ConflictResolution:   TimestampWins,
	}
}

// SyncResult summarizes a sync operation
type SyncResult struct {
	Source                 string `json:"source"`
	Target                 string `json:"target"`
	SinceTimestamp         float64 `json:"since_timestamp"`
	Candidates             uint64 `json:"candidates"`
	Transferred            uint64 `json:"transferred"`
	Skipped               uint64 `json:"skipped"`
	Conflicts             uint64 `json:"conflicts"`
	EmbeddingsTransferred uint64 `json:"embeddings_transferred"`
	AssociationsTransferred uint64 `json:"associations_transferred"`
}

// HopResult is a single hop in federated sync
type HopResult struct {
	Source      string `json:"source"`
	Target      string `json:"target"`
	Memories    uint64 `json:"memories"`
	Associations uint64 `json:"associations"`
	Embeddings  uint64 `json:"embeddings"`
}

// FederationResult is the result of multi-hop sync
type FederationResult struct {
	Chain             []string    `json:"chain"`
	Hops              []HopResult `json:"hops"`
	TotalMemories     uint64      `json:"total_memories"`
	TotalAssociations uint64      `json:"total_associations"`
	TotalEmbeddings   uint64      `json:"total_embeddings"`
}

// MemoryBackend interface for storage operations
type MemoryBackend interface {
	GetMemory(id string) (*MemoryRecord, error)
	StoreMemory(record *MemoryRecord) (string, error)
	FindByContentHash(hash string) (*string, error)
	GetModifiedSince(timestamp float64) ([]MemoryRecord, error)
	GetEmbeddings(memoryID string) ([]EmbeddingBundle, error)
	StoreEmbedding(memoryID string, embedding *EmbeddingBundle) error
	GetAssociations(memoryID string) ([]AssociationBundle, error)
	StoreAssociation(assoc *AssociationBundle) error
	GetStats() map[string]uint64
	GetGalaxyName() string
}

// GalaxyManager interface
type GalaxyManager interface {
	GetMemoryBackend(galaxyName string) (MemoryBackend, error)
	ListGalaxies() []string
}

// GalacticTelepathyEngine is the main sync engine
type GalacticTelepathyEngine struct {
	watermarks     map[string]SyncWatermark
	watermarkPath  string
	galaxyManager  GalaxyManager
	mu             sync.RWMutex
}

// NewGalacticTelepathyEngine creates a new engine
func NewGalacticTelepathyEngine(gm GalaxyManager) *GalacticTelepathyEngine {
	homeDir, _ := os.UserHomeDir()
	watermarkPath := filepath.Join(homeDir, ".whitemagic", "sync_registry.json")
	
	engine := &GalacticTelepathyEngine{
		watermarks:    make(map[string]SyncWatermark),
		watermarkPath: watermarkPath,
		galaxyManager: gm,
	}
	
	engine.loadWatermarks()
	return engine
}

// loadWatermarks loads from disk
func (e *GalacticTelepathyEngine) loadWatermarks() {
	data, err := os.ReadFile(e.watermarkPath)
	if err != nil {
		return // File doesn't exist yet
	}
	
	var loaded map[string]SyncWatermark
	if err := json.Unmarshal(data, &loaded); err != nil {
		fmt.Fprintf(os.Stderr, "Failed to parse watermarks: %v\n", err)
		return
	}
	
	e.watermarks = loaded
}

// saveWatermarks persists to disk
func (e *GalacticTelepathyEngine) saveWatermarks() error {
	e.mu.RLock()
	defer e.mu.RUnlock()
	
	data, err := json.MarshalIndent(e.watermarks, "", "  ")
	if err != nil {
		return err
	}
	
	dir := filepath.Dir(e.watermarkPath)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return err
	}
	
	return os.WriteFile(e.watermarkPath, data, 0644)
}

// getWatermarkKey creates canonical key for galaxy pair
func getWatermarkKey(source, target string) string {
	if source < target {
		return fmt.Sprintf("%s:%s", source, target)
	}
	return fmt.Sprintf("%s:%s", target, source)
}

// IncrementalSync performs sync only for changed memories
func (e *GalacticTelepathyEngine) IncrementalSync(
	sourceGalaxy,
	targetGalaxy string,
	opts SyncOptions,
) (*SyncResult, error) {
	wmKey := getWatermarkKey(sourceGalaxy, targetGalaxy)
	
	// Determine since timestamp
	var since float64
	if opts.SinceTimestamp != nil {
		since = *opts.SinceTimestamp
	} else if wm, ok := e.watermarks[wmKey]; ok {
		since = wm.LastSyncTimestamp
	}
	
	// Get backends
	srcBackend, err := e.galaxyManager.GetMemoryBackend(sourceGalaxy)
	if err != nil {
		return nil, fmt.Errorf("source galaxy not found: %w", err)
	}
	
	tgtBackend, err := e.galaxyManager.GetMemoryBackend(targetGalaxy)
	if err != nil {
		return nil, fmt.Errorf("target galaxy not found: %w", err)
	}
	
	// Get modified memories
	candidates, err := srcBackend.GetModifiedSince(since)
	if err != nil {
		return nil, fmt.Errorf("failed to get modified memories: %w", err)
	}
	
	result := &SyncResult{
		Source:         sourceGalaxy,
		Target:         targetGalaxy,
		SinceTimestamp: since,
		Candidates:     uint64(len(candidates)),
	}
	
	// Process transfers concurrently
	var wg sync.WaitGroup
	semaphore := make(chan struct{}, 10) // Limit concurrent transfers
	
	var mu sync.Mutex
	
	for _, mem := range candidates {
		wg.Add(1)
		semaphore <- struct{}{}
		
		go func(m MemoryRecord) {
			defer wg.Done()
			defer func() { <-semaphore }()
			
			transferResult, err := e.transferMemoryWithFidelity(
				&m, srcBackend, tgtBackend, opts,
			)
			
			mu.Lock()
			defer mu.Unlock()
			
			if err != nil {
				result.Conflicts++
				return
			}
			
			if transferResult.Status == "transferred" {
				result.Transferred++
				result.EmbeddingsTransferred += uint64(transferResult.Embeddings)
				result.AssociationsTransferred += uint64(transferResult.Associations)
			} else {
				result.Skipped++
			}
		}(mem)
	}
	
	wg.Wait()
	
	// Update watermark
	e.mu.Lock()
	now := float64(time.Now().Unix())
	var lastID *string
	if len(candidates) > 0 {
		id := candidates[len(candidates)-1].ID
		lastID = &id
	}
	
	e.watermarks[wmKey] = SyncWatermark{
		GalaxyPair:              wmKey,
		LastSyncTimestamp:       now,
		LastMemoryID:            lastID,
		MemoriesSyncedCount:     result.Transferred,
		AssociationsSyncedCount: result.AssociationsTransferred,
		EmbeddingsSyncedCount:   result.EmbeddingsTransferred,
	}
	e.mu.Unlock()
	
	// Save watermarks
	if err := e.saveWatermarks(); err != nil {
		fmt.Fprintf(os.Stderr, "Failed to save watermarks: %v\n", err)
	}
	
	return result, nil
}

// TransferResult represents the outcome of a single memory transfer
type TransferResult struct {
	Status       string  `json:"status"`
	NewID        *string `json:"new_id,omitempty"`
	Embeddings   uint32  `json:"embeddings"`
	Associations uint32  `json:"associations"`
	Error        *string `json:"error,omitempty"`
}

// transferMemoryWithFidelity transfers a memory with full context
func (e *GalacticTelepathyEngine) transferMemoryWithFidelity(
	mem *MemoryRecord,
	srcBackend, tgtBackend MemoryBackend,
	opts SyncOptions,
) (*TransferResult, error) {
	// Check for conflicts
	conflict := e.detectConflict(mem, tgtBackend)
	if conflict != nil {
		switch opts.ConflictResolution {
		case Manual:
			errMsg := fmt.Sprintf("Manual resolution required: %v", conflict)
			return &TransferResult{
				Status: "conflict",
				Error:  &errMsg,
			}, nil
		default:
			e.resolveConflict(conflict, opts.ConflictResolution, tgtBackend)
		}
	}
	
	// Extract embeddings
	var embeddings []EmbeddingBundle
	if opts.IncludeEmbeddings {
		embeddings, _ = srcBackend.GetEmbeddings(mem.ID)
	}
	
	// Extract associations
	var associations []AssociationBundle
	if opts.IncludeAssociations {
		associations, _ = srcBackend.GetAssociations(mem.ID)
	}
	
	// Create new memory record
	newMem := *mem
	newMem.ID = fmt.Sprintf("mem_%d", time.Now().UnixNano())
	newMem.Tags = append(newMem.Tags, fmt.Sprintf("hgt_source:%s", srcBackend.GetGalaxyName()))
	
	// Update metadata
	now := float64(time.Now().Unix())
	newMem.Metadata["telepathy_source"] = srcBackend.GetGalaxyName()
	newMem.Metadata["telepathy_source_id"] = mem.ID
	newMem.Metadata["telepathy_timestamp"] = now
	newMem.Metadata["telepathy_version"] = "2.0-go"
	
	// Store in target
	newID, err := tgtBackend.StoreMemory(&newMem)
	if err != nil {
		return nil, err
	}
	
	// Restore embeddings
	embCount := 0
	for _, emb := range embeddings {
		emb.MemoryID = newID
		if err := tgtBackend.StoreEmbedding(newID, &emb); err == nil {
			embCount++
		}
	}
	
	// Restore associations
	assocCount := 0
	for _, assoc := range associations {
		// Remap IDs
		if assoc.SourceID == mem.ID {
			assoc.SourceID = newID
		}
		if assoc.TargetID == mem.ID {
			assoc.TargetID = newID
		}
		
		if err := tgtBackend.StoreAssociation(&assoc); err == nil {
			assocCount++
		}
	}
	
	return &TransferResult{
		Status:       "transferred",
		NewID:        &newID,
		Embeddings:   uint32(embCount),
		Associations: uint32(assocCount),
	}, nil
}

// detectConflict checks for potential sync conflicts
func (e *GalacticTelepathyEngine) detectConflict(
	mem *MemoryRecord,
	tgtBackend MemoryBackend,
) *SyncConflict {
	// Check if memory with same content hash exists
	existingID, err := tgtBackend.FindByContentHash(mem.ContentHash)
	if err != nil || existingID == nil {
		return nil
	}
	
	// Check if it's from same source
	existing, err := tgtBackend.GetMemory(*existingID)
	if err != nil || existing == nil {
		return nil
	}
	
	if sourceID, ok := existing.Metadata["telepathy_source_id"].(string); ok {
		if sourceID == mem.ID {
			// Same memory, already synced
			return nil
		}
	}
	
	// Divergent content with same hash (collision)
	if existing.Content != mem.Content {
		return &SyncConflict{
			ConflictType:        DivergentContent,
			MemoryID:            mem.ID,
			SourceGalaxy:        "unknown",
			TargetGalaxy:        "unknown",
			Details: map[string]interface{}{
				"target_existing_id": *existingID,
				"content_hash":       mem.ContentHash,
			},
			SuggestedResolution: "manual_review",
			AutoResolvable:      false,
		}
	}
	
	return nil
}

// resolveConflict applies conflict resolution strategy
func (e *GalacticTelepathyEngine) resolveConflict(
	conflict *SyncConflict,
	strategy ConflictResolution,
	tgtBackend MemoryBackend,
) {
	// Implementation depends on strategy
	switch strategy {
	case TimestampWins:
		// Keep newer (handled by insertion logic)
	case SourceWins:
		// Overwrite with source
	case TargetWins:
		// Keep target (skip transfer)
	}
}

// FederatedSync performs multi-hop synchronization
func (e *GalacticTelepathyEngine) FederatedSync(
	galaxyChain []string,
	opts SyncOptions,
) (*FederationResult, error) {
	if len(galaxyChain) < 2 {
		return nil, fmt.Errorf("chain requires at least 2 galaxies")
	}
	
	result := &FederationResult{
		Chain: galaxyChain,
	}
	
	for i := 0; i < len(galaxyChain)-1; i++ {
		source := galaxyChain[i]
		target := galaxyChain[i+1]
		
		hopResult, err := e.IncrementalSync(source, target, opts)
		if err != nil {
			return nil, fmt.Errorf("hop %d (%s->%s) failed: %w", i, source, target, err)
		}
		
		result.Hops = append(result.Hops, HopResult{
			Source:       source,
			Target:       target,
			Memories:     hopResult.Transferred,
			Associations: hopResult.AssociationsTransferred,
			Embeddings:   hopResult.EmbeddingsTransferred,
		})
		
		result.TotalMemories += hopResult.Transferred
		result.TotalAssociations += hopResult.AssociationsTransferred
		result.TotalEmbeddings += hopResult.EmbeddingsTransferred
	}
	
	return result, nil
}

// GetWatermark returns current watermark for a galaxy pair
func (e *GalacticTelepathyEngine) GetWatermark(source, target string) (*SyncWatermark, bool) {
	e.mu.RLock()
	defer e.mu.RUnlock()
	
	wm, ok := e.watermarks[getWatermarkKey(source, target)]
	if !ok {
		return nil, false
	}
	return &wm, true
}

// ResetWatermark clears watermark for a galaxy pair (force full sync)
func (e *GalacticTelepathyEngine) ResetWatermark(source, target string) error {
	e.mu.Lock()
	defer e.mu.Unlock()
	
	delete(e.watermarks, getWatermarkKey(source, target))
	return e.saveWatermarks()
}

// ListWatermarks returns all tracked watermarks
func (e *GalacticTelepathyEngine) ListWatermarks() []string {
	e.mu.RLock()
	defer e.mu.RUnlock()
	
	keys := make([]string, 0, len(e.watermarks))
	for k := range e.watermarks {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}
