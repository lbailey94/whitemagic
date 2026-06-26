// WhiteMagic Go Concurrent Test Runner
// =====================================
// Shards tests across multiple Python processes for true parallelism.
// Uses a two-phase approach:
//  1. Collect individual test IDs via pytest --collect-only
//  2. Shard test IDs across N workers (round-robin for even distribution)
//  3. Run each shard as a separate pytest process via goroutines
//
// This eliminates both GIL contention and the straggler problem
// that limits file-level sharding when one file has many slow tests.
//
// Usage:
//
//	./test_runner -dir ../../core/tests/unit -workers 8
//	./test_runner -dir ../../core/tests/unit -workers 4 -tb short -json
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
	"sync"
	"time"
)

// TestShard represents a group of test IDs assigned to one worker.
type TestShard struct {
	WorkerID  int      `json:"worker_id"`
	TestIDs   []string `json:"test_ids"`
	TestCount int      `json:"test_count"`
}

// ShardResult represents the result of running one shard.
type ShardResult struct {
	WorkerID    int      `json:"worker_id"`
	Passed      int      `json:"passed"`
	Failed      int      `json:"failed"`
	Errors      int      `json:"errors"`
	Skipped     int      `json:"skipped"`
	Duration    float64  `json:"duration_seconds"`
	FailedTests []string `json:"failed_tests,omitempty"`
	Error       string   `json:"error,omitempty"`
	ExitCode    int      `json:"exit_code"`
}

// TestRunResult is the aggregated result of all shards.
type TestRunResult struct {
	TotalPassed   int           `json:"total_passed"`
	TotalFailed   int           `json:"total_failed"`
	TotalErrors   int           `json:"total_errors"`
	TotalSkipped  int           `json:"total_skipped"`
	TotalTests    int           `json:"total_tests"`
	TotalDuration float64       `json:"total_duration_seconds"`
	Workers       int           `json:"workers"`
	Shards        []ShardResult `json:"shards"`
	FailedTests   []string      `json:"failed_tests,omitempty"`
	Backend       string        `json:"backend"`
}

// collectTestFiles finds all test_*.py files under the given directory.
func collectTestFiles(dir string) ([]string, error) {
	var files []string
	err := filepath.Walk(dir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if !info.IsDir() && strings.HasPrefix(info.Name(), "test_") && strings.HasSuffix(info.Name(), ".py") {
			files = append(files, path)
		}
		return nil
	})
	return files, err
}

// collectTestIDs runs pytest --collect-only to get individual test IDs.
func collectTestIDs(files []string, pythonBin string, workDir string) []string {
	args := []string{"-m", "pytest", "--collect-only", "-q", "--no-header"}
	args = append(args, files...)

	cmd := exec.Command(pythonBin, args...)
	cmd.Dir = workDir
	var stdout strings.Builder
	cmd.Stdout = &stdout
	cmd.Stderr = nil

	_ = cmd.Run()

	var ids []string
	for _, line := range strings.Split(stdout.String(), "\n") {
		line = strings.TrimSpace(line)
		// Test IDs contain "::" (e.g. tests/unit/test_foo.py::TestClass::test_method)
		// Exclude lines that are summary/count lines
		if strings.Contains(line, "::") && !strings.Contains(line, "test(s)") && !strings.Contains(line, "collected") {
			ids = append(ids, line)
		}
	}
	return ids
}

// shardTestIDs distributes test IDs across workers using round-robin.
// Sorting by ID groups tests from the same file together where possible.
func shardTestIDs(ids []string, numWorkers int) []TestShard {
	if numWorkers < 1 {
		numWorkers = 1
	}
	sort.Strings(ids)

	shards := make([]TestShard, numWorkers)
	for i, id := range ids {
		idx := i % numWorkers
		shards[idx].TestIDs = append(shards[idx].TestIDs, id)
	}
	for i := range shards {
		shards[i].WorkerID = i
		shards[i].TestCount = len(shards[i].TestIDs)
	}
	return shards
}

// shardFiles distributes test files across workers using greedy size-based balancing.
func shardFiles(files []string, numWorkers int) []TestShard {
	if numWorkers < 1 {
		numWorkers = 1
	}

	type fileInfo struct {
		path string
		size int64
	}
	var fileInfos []fileInfo
	for _, f := range files {
		info, err := os.Stat(f)
		if err != nil {
			fileInfos = append(fileInfos, fileInfo{f, 0})
			continue
		}
		fileInfos = append(fileInfos, fileInfo{f, info.Size()})
	}
	sort.Slice(fileInfos, func(i, j int) bool {
		return fileInfos[i].size > fileInfos[j].size
	})

	shardSizes := make([]int64, numWorkers)
	shardFilesList := make([][]string, numWorkers)
	for _, fi := range fileInfos {
		minIdx := 0
		for i := 1; i < numWorkers; i++ {
			if shardSizes[i] < shardSizes[minIdx] {
				minIdx = i
			}
		}
		shardFilesList[minIdx] = append(shardFilesList[minIdx], fi.path)
		shardSizes[minIdx] += fi.size
	}

	shards := make([]TestShard, numWorkers)
	for i := 0; i < numWorkers; i++ {
		shards[i] = TestShard{
			WorkerID:  i,
			TestIDs:   shardFilesList[i],
			TestCount: len(shardFilesList[i]),
		}
	}
	return shards
}

// runShard executes pytest for a single shard of test IDs.
func runShard(shard TestShard, pythonBin string, extraArgs []string, workDir string) ShardResult {
	start := time.Now()
	result := ShardResult{WorkerID: shard.WorkerID}

	if len(shard.TestIDs) == 0 {
		result.Duration = time.Since(start).Seconds()
		return result
	}

	args := []string{"-m", "pytest", "-q", "--tb=line", "--no-header"}
	args = append(args, extraArgs...)
	args = append(args, shard.TestIDs...)

	cmd := exec.Command(pythonBin, args...)
	cmd.Dir = workDir
	var stdout strings.Builder
	cmd.Stdout = &stdout
	cmd.Stderr = nil

	err := cmd.Run()
	result.ExitCode = cmd.ProcessState.ExitCode()
	result.Duration = time.Since(start).Seconds()

	if err != nil && result.ExitCode != 0 && result.ExitCode != 1 {
		result.Error = fmt.Sprintf("pytest exited with code %d", result.ExitCode)
		result.Errors = 1
	}

	// Parse the summary line from pytest output
	lines := strings.Split(strings.TrimSpace(stdout.String()), "\n")
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if strings.Contains(line, "passed") || strings.Contains(line, "failed") || strings.Contains(line, "error") || strings.Contains(line, "skipped") {
			parseSummary(line, &result)
		}
	}

	// Fallback: estimate from exit code
	if result.Passed == 0 && result.Failed == 0 && result.Errors == 0 && result.Skipped == 0 {
		if result.ExitCode == 0 {
			result.Passed = shard.TestCount
		} else if result.ExitCode == 1 {
			result.Failed = 1
		}
	}
	return result
}

// parseSummary extracts pass/fail/error/skip counts from pytest summary line.
func parseSummary(line string, result *ShardResult) {
	parts := strings.Split(line, ",")
	for _, part := range parts {
		part = strings.TrimSpace(part)
		var count int
		var label string
		fmt.Sscanf(part, "%d %s", &count, &label)
		switch label {
		case "passed", "passed,":
			result.Passed = count
		case "failed", "failed,":
			result.Failed = count
		case "errors", "error", "errors,":
			result.Errors = count
		case "skipped", "skipped,":
			result.Skipped = count
		}
	}
}

func main() {
	var (
		testDir     string
		workers     int
		pythonBin   string
		jsonOutput  bool
		tbArg       string
		skipCollect bool
	)
	flag.StringVar(&testDir, "dir", "../../core/tests/unit", "Test directory")
	flag.IntVar(&workers, "workers", runtime.NumCPU(), "Number of parallel workers")
	flag.StringVar(&pythonBin, "python", "python", "Python binary path")
	flag.BoolVar(&jsonOutput, "json", false, "Output results as JSON")
	flag.StringVar(&tbArg, "tb", "line", "Traceback format (line/short/long/no)")
	flag.BoolVar(&skipCollect, "skip-collect", false, "Skip test ID collection, shard by file instead")
	flag.Parse()

	absDir, err := filepath.Abs(testDir)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error resolving path: %v\n", err)
		os.Exit(2)
	}

	files, err := collectTestFiles(absDir)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error collecting test files: %v\n", err)
		os.Exit(2)
	}
	if len(files) == 0 {
		fmt.Fprintf(os.Stderr, "No test files found in %s\n", absDir)
		os.Exit(2)
	}

	var shards []TestShard
	workDir := filepath.Dir(filepath.Dir(absDir))
	if skipCollect {
		shards = shardFiles(files, workers)
	} else {
		fmt.Fprintf(os.Stderr, "Collecting test IDs from %d files...\n", len(files))
		cStart := time.Now()
		ids := collectTestIDs(files, pythonBin, workDir)
		fmt.Fprintf(os.Stderr, "Collected %d test IDs in %.2fs\n", len(ids), time.Since(cStart).Seconds())
		if len(ids) == 0 {
			fmt.Fprintf(os.Stderr, "No test IDs collected, falling back to file sharding\n")
			shards = shardFiles(files, workers)
		} else {
			shards = shardTestIDs(ids, workers)
		}
	}

	extraArgs := []string{fmt.Sprintf("--tb=%s", tbArg)}

	start := time.Now()
	results := make([]ShardResult, workers)
	var wg sync.WaitGroup

	for i, shard := range shards {
		wg.Add(1)
		go func(s TestShard, idx int) {
			defer wg.Done()
			results[idx] = runShard(s, pythonBin, extraArgs, workDir)
		}(shard, i)
	}
	wg.Wait()
	totalDuration := time.Since(start).Seconds()

	agg := TestRunResult{
		TotalDuration: totalDuration,
		Workers:       workers,
		Shards:        results,
		Backend:       "go_goroutine_test_shard",
	}
	for _, r := range results {
		agg.TotalPassed += r.Passed
		agg.TotalFailed += r.Failed
		agg.TotalErrors += r.Errors
		agg.TotalSkipped += r.Skipped
		agg.FailedTests = append(agg.FailedTests, r.FailedTests...)
	}
	agg.TotalTests = agg.TotalPassed + agg.TotalFailed + agg.TotalErrors + agg.TotalSkipped

	if jsonOutput {
		out, _ := json.MarshalIndent(agg, "", "  ")
		fmt.Println(string(out))
	} else {
		fmt.Printf("\n=== WhiteMagic Go Concurrent Test Runner ===\n")
		fmt.Printf("Workers: %d | Duration: %.2fs\n", workers, totalDuration)
		fmt.Printf("Shards:\n")
		for _, r := range results {
			status := "PASS"
			if r.Failed > 0 || r.Errors > 0 {
				status = "FAIL"
			}
			fmt.Printf("  Worker %d: %s (%.2fs, %d passed, %d failed, exit=%d)\n",
				r.WorkerID, status, r.Duration, r.Passed, r.Failed, r.ExitCode)
		}
		fmt.Printf("\nSummary: %d passed, %d failed, %d errors, %d skipped\n",
			agg.TotalPassed, agg.TotalFailed, agg.TotalErrors, agg.TotalSkipped)
		if len(agg.FailedTests) > 0 {
			fmt.Printf("Failed tests:\n")
			for _, t := range agg.FailedTests {
				fmt.Printf("  - %s\n", t)
			}
		}
	}

	if agg.TotalFailed > 0 || agg.TotalErrors > 0 {
		os.Exit(1)
	}
	os.Exit(0)
}
