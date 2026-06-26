// WhiteMagic Go Concurrent Prefetch Service
// ==========================================
// Uses goroutines for parallel pipeline warming of predicted tool calls.
// Communicates with Python via JSON stdio protocol.
//
// Commands:
//   prefetch  — Concurrently warm retrieval pipelines for predicted tools
//   status    — Get prefetch service status
package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"runtime"
	"sync"
	"time"
)

// PrefetchRequest represents a prefetch request from Python.
type PrefetchRequest struct {
	Command    string                   `json:"command"`
	Tools      []PrefetchTool           `json:"tools"`
	MaxWorkers int                      `json:"max_workers,omitempty"`
}

// PrefetchTool represents a single tool to prefetch.
type PrefetchTool struct {
	Name        string  `json:"name"`
	Gana        string  `json:"gana"`
	Probability float64 `json:"probability"`
}

// PrefetchResult represents the result of prefetching a single tool.
type PrefetchResult struct {
	Tool       string  `json:"tool"`
	Gana       string  `json:"gana"`
	Probability float64 `json:"probability"`
	Prefetched bool    `json:"prefetched"`
	DurationMs float64 `json:"duration_ms"`
	Error      string  `json:"error,omitempty"`
}

// PrefetchResponse is the full response to a prefetch request.
type PrefetchResponse struct {
	Status   string            `json:"status"`
	Results  []PrefetchResult  `json:"results,omitempty"`
	TotalMs  float64           `json:"total_ms"`
	Workers  int               `json:"workers"`
	Goroutines int             `json:"goroutines"`
}

// StatusResponse represents a status request response.
type StatusResponse struct {
	Status    string `json:"status"`
	Backend   string `json:"backend"`
	Version   string `json:"version"`
	GoVersion string `json:"go_version"`
	CPUs      int    `json:"cpus"`
}

// Search tools that involve memory retrieval (the expensive path).
var searchTools = map[string]bool{
	"search_memories":     true,
	"vector.search":       true,
	"read_memory":         true,
	"list_memories":       true,
	"fast_read_memory":    true,
	"batch_read_memories": true,
	"pattern_search":      true,
	"gnosis":              true,
}

// prefetchTool simulates warming the retrieval pipeline for a single tool.
// In production, this would call the Rust retrieval pipeline via FFI.
func prefetchTool(tool PrefetchTool) PrefetchResult {
	start := time.Now()

	result := PrefetchResult{
		Tool:        tool.Name,
		Gana:        tool.Gana,
		Probability: tool.Probability,
	}

	// Only prefetch tools that involve memory search
	if !searchTools[tool.Name] {
		result.Prefetched = false
		result.DurationMs = float64(time.Since(start).Microseconds()) / 1000.0
		return result
	}

	// Simulate pipeline warming (in production: call Rust FFI)
	// The actual warming is done by the Python side; Go just coordinates
	// the concurrent dispatch and collects results.
	time.Sleep(1 * time.Millisecond) // simulate minimal work

	result.Prefetched = true
	result.DurationMs = float64(time.Since(start).Microseconds()) / 1000.0
	return result
}

// handlePrefetch processes a concurrent prefetch request using goroutines.
func handlePrefetch(req PrefetchRequest) PrefetchResponse {
	start := time.Now()

	tools := req.Tools
	if len(tools) == 0 {
		return PrefetchResponse{
			Status: "ok",
			TotalMs: float64(time.Since(start).Microseconds()) / 1000.0,
			Workers: 0,
			Goroutines: 0,
		}
	}

	maxWorkers := req.MaxWorkers
	if maxWorkers <= 0 {
		maxWorkers = runtime.NumCPU()
	}
	if maxWorkers > len(tools) {
		maxWorkers = len(tools)
	}

	// Channel for results
	resultsCh := make(chan PrefetchResult, len(tools))

	// Semaphore to limit concurrent goroutines
	sem := make(chan struct{}, maxWorkers)

	var wg sync.WaitGroup
	for _, tool := range tools {
		wg.Add(1)
		go func(t PrefetchTool) {
			defer wg.Done()
			sem <- struct{}{} // acquire
			defer func() { <-sem }() // release
			resultsCh <- prefetchTool(t)
		}(tool)
	}

	// Close results channel after all goroutines complete
	go func() {
		wg.Wait()
		close(resultsCh)
	}()

	// Collect results
	var results []PrefetchResult
	for r := range resultsCh {
		results = append(results, r)
	}

	return PrefetchResponse{
		Status:     "ok",
		Results:    results,
		TotalMs:    float64(time.Since(start).Microseconds()) / 1000.0,
		Workers:    maxWorkers,
		Goroutines: len(tools),
	}
}

func main() {
	scanner := bufio.NewScanner(os.Stdin)
	scanner.Buffer(make([]byte, 1024*1024), 1024*1024) // 1MB buffer

	for scanner.Scan() {
		line := scanner.Text()
		if line == "" {
			continue
		}

		var req PrefetchRequest
		if err := json.Unmarshal([]byte(line), &req); err != nil {
			resp := map[string]string{"status": "error", "error": fmt.Sprintf("parse error: %v", err)}
			out, _ := json.Marshal(resp)
			fmt.Println(string(out))
			continue
		}

		var response interface{}
		switch req.Command {
		case "prefetch":
			response = handlePrefetch(req)
		case "status":
			response = StatusResponse{
				Status:    "ok",
				Backend:   "go_goroutine",
				Version:   "0.1.0",
				GoVersion: runtime.Version(),
				CPUs:      runtime.NumCPU(),
			}
		default:
			response = map[string]string{"status": "error", "error": "Unknown command: " + req.Command}
		}

		out, _ := json.Marshal(response)
		fmt.Println(string(out))
	}
}
