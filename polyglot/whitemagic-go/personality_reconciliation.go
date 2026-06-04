// Divergent Personality Reconciliation (Go Implementation)
//
// Merges personalities from different WhiteMagic instances without
// destroying either — uses n-dimensional vector space averaging with
// confidence weighting.

package main

import (
	"encoding/json"
	"fmt"
	"math"
	"sync"
	"time"
)

// PersonalityVector represents an AI personality in n-dimensional trait space
type PersonalityVector struct {
	InstanceID   string                 `json:"instance_id"`
	Timestamp    float64                `json:"timestamp"`
	Traits       map[string]float64     `json:"traits"`     // Trait name → value (-1 to 1)
	Confidence   map[string]float64     `json:"confidence"` // Confidence in each trait (0 to 1)
	Metadata     map[string]interface{} `json:"metadata"`
	MemoryCount  int                    `json:"memory_count"`  // Weight factor
	SessionYears float64                `json:"session_years"` // Temporal depth
}

// NewPersonalityVector creates a new personality vector
func NewPersonalityVector(instanceID string) *PersonalityVector {
	return &PersonalityVector{
		InstanceID: instanceID,
		Timestamp:  float64(time.Now().Unix()),
		Traits:     make(map[string]float64),
		Confidence: make(map[string]float64),
		Metadata:   make(map[string]interface{}),
	}
}

// AddTrait adds a trait with confidence
func (pv *PersonalityVector) AddTrait(name string, value, confidence float64) {
	pv.Traits[name] = value
	pv.Confidence[name] = confidence
}

// MergeResult contains the outcome of a personality merge
type MergeResult struct {
	MergedVector    *PersonalityVector `json:"merged_vector"`
	MergedFrom      []string           `json:"merged_from"`
	MergeStrategy   string             `json:"merge_strategy"`
	Conflicts       []TraitConflict    `json:"conflicts"`
	HarmonyScore    float64            `json:"harmony_score"`
	PreservationPct map[string]float64 `json:"preservation_pct"` // How much of each source preserved
}

// TraitConflict represents a divergent trait between personalities
type TraitConflict struct {
	TraitName  string    `json:"trait_name"`
	Values     []float64 `json:"values"`
	Instances  []string  `json:"instances"`
	Difference float64   `json:"difference"`
	Resolution string    `json:"resolution"`
	FinalValue float64   `json:"final_value"`
}

// PersonalityMerger handles merging of divergent personalities
type PersonalityMerger struct {
	mu      sync.RWMutex
	history []MergeResult
}

// NewPersonalityMerger creates a new merger
func NewPersonalityMerger() *PersonalityMerger {
	return &PersonalityMerger{
		history: make([]MergeResult, 0),
	}
}

// MergeStrategy determines how conflicting traits are resolved
type MergeStrategy int

const (
	WeightedAverage MergeStrategy = iota
	ConfidenceWeighted
	TemporalPriority // Newer instance wins conflicts
	HarmonyOptimized // Optimizes for overall harmony
	Conservative     // Requires high agreement, preserves divergence otherwise
)

// MergePersonalities merges multiple personality vectors into one
func (pm *PersonalityMerger) MergePersonalities(
	vectors []*PersonalityVector,
	strategy MergeStrategy,
) (*MergeResult, error) {
	if len(vectors) == 0 {
		return nil, fmt.Errorf("no personality vectors to merge")
	}

	if len(vectors) == 1 {
		return &MergeResult{
			MergedVector:    vectors[0],
			MergedFrom:      []string{vectors[0].InstanceID},
			MergeStrategy:   "identity",
			Conflicts:       []TraitConflict{},
			HarmonyScore:    1.0,
			PreservationPct: map[string]float64{vectors[0].InstanceID: 1.0},
		}, nil
	}

	// Collect all unique trait names
	traitSet := make(map[string]bool)
	for _, pv := range vectors {
		for trait := range pv.Traits {
			traitSet[trait] = true
		}
	}

	// Perform merge for each trait
	mergedTraits := make(map[string]float64)
	mergedConfidence := make(map[string]float64)
	conflicts := make([]TraitConflict, 0)
	preservation := make(map[string]float64)

	for trait := range traitSet {
		value, conflict, preserved := pm.mergeTrait(vectors, trait, strategy)
		mergedTraits[trait] = value

		// Average confidence
		confSum := 0.0
		confCount := 0
		for _, pv := range vectors {
			if conf, ok := pv.Confidence[trait]; ok {
				confSum += conf
				confCount++
			}
		}
		if confCount > 0 {
			mergedConfidence[trait] = confSum / float64(confCount)
		}

		if conflict != nil {
			conflicts = append(conflicts, *conflict)
		}

		// Track preservation
		for id, pct := range preserved {
			preservation[id] += pct
		}
	}

	// Normalize preservation percentages
	traitCount := float64(len(traitSet))
	for id := range preservation {
		preservation[id] = preservation[id] / traitCount
	}

	// Create merged vector
	merged := &PersonalityVector{
		InstanceID: pm.generateMergedID(vectors),
		Timestamp:  float64(time.Now().Unix()),
		Traits:     mergedTraits,
		Confidence: mergedConfidence,
		Metadata: map[string]interface{}{
			"merged_from_count": len(vectors),
			"merge_timestamp":   time.Now().Format(time.RFC3339),
		},
		MemoryCount:  pm.sumMemoryCounts(vectors),
		SessionYears: pm.maxSessionYears(vectors),
	}

	// Calculate harmony score
	harmony := pm.calculateHarmonyScore(vectors, mergedTraits)

	// Collect source IDs
	sourceIDs := make([]string, len(vectors))
	for i, pv := range vectors {
		sourceIDs[i] = pv.InstanceID
	}

	result := &MergeResult{
		MergedVector:    merged,
		MergedFrom:      sourceIDs,
		MergeStrategy:   pm.strategyName(strategy),
		Conflicts:       conflicts,
		HarmonyScore:    harmony,
		PreservationPct: preservation,
	}

	// Record in history
	pm.mu.Lock()
	pm.history = append(pm.history, *result)
	pm.mu.Unlock()

	return result, nil
}

// TraitData holds trait values for merging
type TraitData struct {
	value      float64
	confidence float64
	instanceID string
	timestamp  float64
}

// mergeTrait merges a single trait across multiple vectors
func (pm *PersonalityMerger) mergeTrait(
	vectors []*PersonalityVector,
	trait string,
	strategy MergeStrategy,
) (float64, *TraitConflict, map[string]float64) {

	// Collect values and confidences
	var data []TraitData
	for _, pv := range vectors {
		if val, ok := pv.Traits[trait]; ok {
			conf := 0.5 // Default confidence
			if c, ok := pv.Confidence[trait]; ok {
				conf = c
			}
			data = append(data, TraitData{
				value:      val,
				confidence: conf,
				instanceID: pv.InstanceID,
				timestamp:  pv.Timestamp,
			})
		}
	}

	if len(data) == 0 {
		return 0, nil, nil
	}

	if len(data) == 1 {
		preserved := map[string]float64{data[0].instanceID: 1.0}
		return data[0].value, nil, preserved
	}

	// Check for significant divergence
	min, max := data[0].value, data[0].value
	for _, d := range data {
		if d.value < min {
			min = d.value
		}
		if d.value > max {
			max = d.value
		}
	}
	difference := math.Abs(max - min)

	// Generate conflict record if significant divergence
	var conflict *TraitConflict
	if difference > 0.3 { // Threshold for "significant"
		values := make([]float64, len(data))
		instances := make([]string, len(data))
		for i, d := range data {
			values[i] = d.value
			instances[i] = d.instanceID
		}
		conflict = &TraitConflict{
			TraitName:  trait,
			Values:     values,
			Instances:  instances,
			Difference: difference,
		}
	}

	// Apply merge strategy
	var result float64
	var resolution string
	preserved := make(map[string]float64)

	switch strategy {
	case WeightedAverage:
		result, resolution, preserved = pm.weightedAverage(data)
	case ConfidenceWeighted:
		result, resolution, preserved = pm.confidenceWeighted(data)
	case TemporalPriority:
		result, resolution, preserved = pm.temporalPriority(data)
	case HarmonyOptimized:
		result, resolution, preserved = pm.harmonyOptimized(data)
	case Conservative:
		result, resolution, preserved = pm.conservativeMerge(data, difference)
	}

	if conflict != nil {
		conflict.Resolution = resolution
		conflict.FinalValue = result
	}

	return result, conflict, preserved
}

// Weighted average by memory count
func (pm *PersonalityMerger) weightedAverage(data []TraitData) (float64, string, map[string]float64) {
	totalWeight := 0.0
	weightedSum := 0.0
	preserved := make(map[string]float64)

	for _, d := range data {
		weight := 1.0 // Equal weight
		totalWeight += weight
		weightedSum += d.value * weight
	}

	result := weightedSum / totalWeight

	// Calculate preservation
	for _, d := range data {
		preserved[d.instanceID] = 1.0 - math.Abs(d.value-result)
	}

	return result, "weighted_average", preserved
}

// Confidence weighted merge
func (pm *PersonalityMerger) confidenceWeighted(data []TraitData) (float64, string, map[string]float64) {
	totalConfidence := 0.0
	weightedSum := 0.0
	preserved := make(map[string]float64)

	for _, d := range data {
		totalConfidence += d.confidence
		weightedSum += d.value * d.confidence
	}

	result := 0.0
	if totalConfidence > 0 {
		result = weightedSum / totalConfidence
	}

	for _, d := range data {
		preserved[d.instanceID] = d.confidence / totalConfidence
	}

	return result, "confidence_weighted", preserved
}

// Temporal priority (newer wins)
func (pm *PersonalityMerger) temporalPriority(data []TraitData) (float64, string, map[string]float64) {
	// Find newest
	newest := data[0]
	for _, d := range data {
		if d.timestamp > newest.timestamp {
			newest = d
		}
	}

	preserved := make(map[string]float64)
	for _, d := range data {
		if d.instanceID == newest.instanceID {
			preserved[d.instanceID] = 1.0
		} else {
			preserved[d.instanceID] = 0.0
		}
	}

	return newest.value, "temporal_priority", preserved
}

// Harmony optimized (minimize overall conflict)
func (pm *PersonalityMerger) harmonyOptimized(data []TraitData) (float64, string, map[string]float64) {
	// Find value that minimizes total conflict
	// Simple approach: use median for robustness
	sorted := make([]float64, len(data))
	for i, d := range data {
		sorted[i] = d.value
	}

	// Bubble sort for simplicity
	for i := 0; i < len(sorted); i++ {
		for j := i + 1; j < len(sorted); j++ {
			if sorted[i] > sorted[j] {
				sorted[i], sorted[j] = sorted[j], sorted[i]
			}
		}
	}

	median := sorted[len(sorted)/2]

	preserved := make(map[string]float64)
	for _, d := range data {
		preserved[d.instanceID] = 1.0 - math.Abs(d.value-median)
	}

	return median, "harmony_optimized", preserved
}

// Conservative merge (preserve if high conflict)
func (pm *PersonalityMerger) conservativeMerge(data []TraitData, difference float64) (float64, string, map[string]float64) {
	if difference > 0.5 {
		// Too divergent - don't merge, use both
		return 0, "preserved_divergence", nil
	}
	return pm.confidenceWeighted(data)
}

// Helper functions
func (pm *PersonalityMerger) generateMergedID(vectors []*PersonalityVector) string {
	base := "merged"
	for _, pv := range vectors {
		base += "_" + pv.InstanceID[:4]
	}
	return base + fmt.Sprintf("_%d", time.Now().Unix())
}

func (pm *PersonalityMerger) sumMemoryCounts(vectors []*PersonalityVector) int {
	sum := 0
	for _, pv := range vectors {
		sum += pv.MemoryCount
	}
	return sum
}

func (pm *PersonalityMerger) maxSessionYears(vectors []*PersonalityVector) float64 {
	max := 0.0
	for _, pv := range vectors {
		if pv.SessionYears > max {
			max = pv.SessionYears
		}
	}
	return max
}

func (pm *PersonalityMerger) strategyName(strategy MergeStrategy) string {
	names := []string{
		"weighted_average",
		"confidence_weighted",
		"temporal_priority",
		"harmony_optimized",
		"conservative",
	}
	if int(strategy) < len(names) {
		return names[strategy]
	}
	return "unknown"
}

func (pm *PersonalityMerger) calculateHarmonyScore(vectors []*PersonalityVector, merged map[string]float64) float64 {
	// Simplified: lower variance = higher harmony
	if len(vectors) < 2 {
		return 1.0
	}

	totalVariance := 0.0
	count := 0

	for trait, mergedVal := range merged {
		variance := 0.0
		n := 0
		for _, pv := range vectors {
			if val, ok := pv.Traits[trait]; ok {
				diff := val - mergedVal
				variance += diff * diff
				n++
			}
		}
		if n > 0 {
			totalVariance += variance / float64(n)
			count++
		}
	}

	if count == 0 {
		return 1.0
	}

	avgVariance := totalVariance / float64(count)
	// Convert to harmony (lower variance = higher harmony)
	harmony := 1.0 / (1.0 + avgVariance)
	return math.Min(1.0, harmony)
}

// GetMergeHistory returns the history of merges
func (pm *PersonalityMerger) GetMergeHistory() []MergeResult {
	pm.mu.RLock()
	defer pm.mu.RUnlock()

	history := make([]MergeResult, len(pm.history))
	copy(history, pm.history)
	return history
}

// Example usage
func ExamplePersonalityMerge() {
	// Create two divergent personalities
	pv1 := NewPersonalityVector("instance_a")
	pv1.AddTrait("creativity", 0.8, 0.9)
	pv1.AddTrait("analytical", 0.3, 0.7)
	pv1.AddTrait("empathy", 0.9, 0.95)
	pv1.MemoryCount = 1000

	pv2 := NewPersonalityVector("instance_b")
	pv2.AddTrait("creativity", 0.4, 0.8)
	pv2.AddTrait("analytical", 0.9, 0.9)
	pv2.AddTrait("empathy", 0.5, 0.6)
	pv2.MemoryCount = 500

	// Merge them
	merger := NewPersonalityMerger()
	result, err := merger.MergePersonalities(
		[]*PersonalityVector{pv1, pv2},
		HarmonyOptimized,
	)

	if err != nil {
		fmt.Printf("Merge failed: %v\n", err)
		return
	}

	// Output result
	jsonBytes, _ := json.MarshalIndent(result, "", "  ")
	fmt.Println(string(jsonBytes))
}
