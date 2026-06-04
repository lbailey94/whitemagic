// Package async provides goroutine-based async processing for WhiteMagic
// Replaces Python asyncio patterns with efficient Go goroutines
package async

import (
	"context"
	"sync"
	"time"
)

// WorkerPool manages a pool of goroutines for concurrent processing
type WorkerPool struct {
	workerCount int
	taskQueue   chan Task
	wg          sync.WaitGroup
	ctx         context.Context
	cancel      context.CancelFunc
}

// Task represents a unit of work
type Task func() error

// NewWorkerPool creates a new worker pool with the specified number of workers
func NewWorkerPool(workerCount int) *WorkerPool {
	ctx, cancel := context.WithCancel(context.Background())
	return &WorkerPool{
		workerCount: workerCount,
		taskQueue:   make(chan Task, 1000),
		ctx:         ctx,
		cancel:      cancel,
	}
}

// Start begins processing tasks from the queue
func (wp *WorkerPool) Start() {
	for i := 0; i < wp.workerCount; i++ {
		wp.wg.Add(1)
		go wp.worker()
	}
}

// Stop gracefully shuts down the worker pool
func (wp *WorkerPool) Stop() {
	wp.cancel()
	close(wp.taskQueue)
	wp.wg.Wait()
}

// worker processes tasks from the queue
func (wp *WorkerPool) worker() {
	defer wp.wg.Done()
	for {
		select {
		case <-wp.ctx.Done():
			return
		case task, ok := <-wp.taskQueue:
			if !ok {
				return
			}
			if task != nil {
				task()
			}
		}
	}
}

// Submit adds a task to the queue
func (wp *WorkerPool) Submit(task Task) error {
	select {
	case wp.taskQueue <- task:
		return nil
	case <-wp.ctx.Done():
		return wp.ctx.Err()
	}
}

// BatchProcessor processes items in batches with concurrency control
type BatchProcessor struct {
	pool      *WorkerPool
	batchSize int
	semaphore chan struct{}
}

// NewBatchProcessor creates a new batch processor
func NewBatchProcessor(concurrency, batchSize int) *BatchProcessor {
	return &BatchProcessor{
		pool:      NewWorkerPool(concurrency),
		batchSize: batchSize,
		semaphore: make(chan struct{}, concurrency),
	}
}

// Start begins the batch processor
func (bp *BatchProcessor) Start() {
	bp.pool.Start()
}

// Stop stops the batch processor
func (bp *BatchProcessor) Stop() {
	bp.pool.Stop()
}

// ProcessBatch processes a batch of string items with the given processor function
func (bp *BatchProcessor) ProcessBatch(items []string, processor func(string) error) []error {
	results := make([]error, len(items))
	var wg sync.WaitGroup

	for i := 0; i < len(items); i += bp.batchSize {
		end := i + bp.batchSize
		if end > len(items) {
			end = len(items)
		}
		batch := items[i:end]

		batchIdx := i
		for _, item := range batch {
			wg.Add(1)
			idx := batchIdx
			bp.semaphore <- struct{}{}
			go func(itm string) {
				defer wg.Done()
				defer func() { <-bp.semaphore }()
				results[idx] = processor(itm)
			}(item)
			batchIdx++
		}
	}

	wg.Wait()
	return results
}

// AsyncMap applies a function to each item concurrently
func AsyncMap[T any, R any](items []T, fn func(T) (R, error), concurrency int) ([]R, []error) {
	results := make([]R, len(items))
	errors := make([]error, len(items))
	semaphore := make(chan struct{}, concurrency)
	var wg sync.WaitGroup

	for i, item := range items {
		wg.Add(1)
		semaphore <- struct{}{}
		go func(idx int, itm T) {
			defer wg.Done()
			defer func() { <-semaphore }()
			result, err := fn(itm)
			results[idx] = result
			errors[idx] = err
		}(i, item)
	}

	wg.Wait()
	return results, errors
}

// IdleMonitor monitors for idle periods and triggers callbacks
type IdleMonitor struct {
	idleThreshold time.Duration
	checkInterval time.Duration
	lastActivity  time.Time
	mu            sync.Mutex
	callbacks     []func()
	stopChan      chan struct{}
}

// NewIdleMonitor creates a new idle monitor
func NewIdleMonitor(idleThreshold, checkInterval time.Duration) *IdleMonitor {
	return &IdleMonitor{
		idleThreshold: idleThreshold,
		checkInterval: checkInterval,
		lastActivity:  time.Now(),
		stopChan:      make(chan struct{}),
	}
}

// Start begins monitoring for idle periods
func (im *IdleMonitor) Start() {
	go im.monitor()
}

// Stop stops the idle monitor
func (im *IdleMonitor) Stop() {
	close(im.stopChan)
}

// RecordActivity updates the last activity timestamp
func (im *IdleMonitor) RecordActivity() {
	im.mu.Lock()
	defer im.mu.Unlock()
	im.lastActivity = time.Now()
}

// AddCallback adds a callback to invoke on idle detection
func (im *IdleMonitor) AddCallback(callback func()) {
	im.mu.Lock()
	defer im.mu.Unlock()
	im.callbacks = append(im.callbacks, callback)
}

// monitor checks for idle periods and invokes callbacks
func (im *IdleMonitor) monitor() {
	ticker := time.NewTicker(im.checkInterval)
	defer ticker.Stop()

	for {
		select {
		case <-im.stopChan:
			return
		case <-ticker.C:
			im.mu.Lock()
			idleTime := time.Since(im.lastActivity)
			im.mu.Unlock()

			if idleTime >= im.idleThreshold {
				im.mu.Lock()
				callbacks := im.callbacks
				im.mu.Unlock()
				for _, cb := range callbacks {
					cb()
				}
			}
		}
	}
}
