/*
#cgo CFLAGS: -I.
#cgo LDFLAGS: -L. -lasync

#include <stdlib.h>

// Go-exported function signatures
extern int GoWorkerPool_New(int workerCount);
extern void GoWorkerPool_Start(int poolID);
extern void GoWorkerPool_Stop(int poolID);
extern int GoWorkerPool_Submit(int poolID, void* taskID);
extern int GoBatchProcessor_New(int concurrency, int batchSize);
extern void GoBatchProcessor_Start(int procID);
extern void GoBatchProcessor_Stop(int procID);
extern int GoIdleMonitor_New(int idleThresholdSec, int checkIntervalSec);
extern void GoIdleMonitor_Start(int monitorID);
extern void GoIdleMonitor_Stop(int monitorID);
extern void GoIdleMonitor_RecordActivity(int monitorID);
*/
package async

/*
#include <stdlib.h>

// Go-exported function signatures
extern int GoWorkerPool_New(int workerCount);
extern void GoWorkerPool_Start(int poolID);
extern void GoWorkerPool_Stop(int poolID);
extern int GoWorkerPool_Submit(int poolID, void* taskID);
extern int GoBatchProcessor_New(int concurrency, int batchSize);
extern void GoBatchProcessor_Start(int procID);
extern void GoBatchProcessor_Stop(int procID);
extern int GoIdleMonitor_New(int idleThresholdSec, int checkIntervalSec);
extern void GoIdleMonitor_Start(int monitorID);
extern void GoIdleMonitor_Stop(int monitorID);
extern void GoIdleMonitor_RecordActivity(int monitorID);

*/
import "C"

import (
	"fmt"
	"sync"
	"time"
	"unsafe"
)

var (
	pools      = make(map[int]*WorkerPool)
	processors = make(map[int]*BatchProcessor)
	monitors   = make(map[int]*IdleMonitor)
	nextID     = 1
	mu         sync.Mutex
)

//export GoWorkerPool_New
func GoWorkerPool_New(workerCount C.int) C.int {
	mu.Lock()
	defer mu.Unlock()

	id := nextID
	nextID++
	pools[id] = NewWorkerPool(int(workerCount))
	return C.int(id)
}

//export GoWorkerPool_Start
func GoWorkerPool_Start(poolID C.int) {
	mu.Lock()
	defer mu.Unlock()

	if pool, ok := pools[int(poolID)]; ok {
		pool.Start()
	}
}

//export GoWorkerPool_Stop
func GoWorkerPool_Stop(poolID C.int) {
	mu.Lock()
	defer mu.Unlock()

	if pool, ok := pools[int(poolID)]; ok {
		pool.Stop()
		delete(pools, int(poolID))
	}
}

//export GoWorkerPool_Submit
func GoWorkerPool_Submit(poolID C.int, taskID unsafe.Pointer) C.int {
	mu.Lock()
	defer mu.Unlock()

	if _, ok := pools[int(poolID)]; ok {
		// In a real implementation, this would queue the task
		// For now, return success
		return C.int(0)
	}
	return C.int(-1)
}

//export GoBatchProcessor_New
func GoBatchProcessor_New(concurrency, batchSize C.int) C.int {
	mu.Lock()
	defer mu.Unlock()

	id := nextID
	nextID++
	processors[id] = NewBatchProcessor(int(concurrency), int(batchSize))
	return C.int(id)
}

//export GoBatchProcessor_Start
func GoBatchProcessor_Start(procID C.int) {
	mu.Lock()
	defer mu.Unlock()

	if proc, ok := processors[int(procID)]; ok {
		proc.Start()
	}
}

//export GoBatchProcessor_Stop
func GoBatchProcessor_Stop(procID C.int) {
	mu.Lock()
	defer mu.Unlock()

	if proc, ok := processors[int(procID)]; ok {
		proc.Stop()
		delete(processors, int(procID))
	}
}

//export GoIdleMonitor_New
func GoIdleMonitor_New(idleThresholdSec, checkIntervalSec C.int) C.int {
	mu.Lock()
	defer mu.Unlock()

	id := nextID
	nextID++
	monitors[id] = NewIdleMonitor(
		time.Duration(idleThresholdSec)*time.Second,
		time.Duration(checkIntervalSec)*time.Second,
	)
	return C.int(id)
}

//export GoIdleMonitor_Start
func GoIdleMonitor_Start(monitorID C.int) {
	mu.Lock()
	defer mu.Unlock()

	if monitor, ok := monitors[int(monitorID)]; ok {
		monitor.Start()
	}
}

//export GoIdleMonitor_Stop
func GoIdleMonitor_Stop(monitorID C.int) {
	mu.Lock()
	defer mu.Unlock()

	if monitor, ok := monitors[int(monitorID)]; ok {
		monitor.Stop()
		delete(monitors, int(monitorID))
	}
}

//export GoIdleMonitor_RecordActivity
func GoIdleMonitor_RecordActivity(monitorID C.int) {
	mu.Lock()
	defer mu.Unlock()

	if monitor, ok := monitors[int(monitorID)]; ok {
		monitor.RecordActivity()
	}
}

func main() {
	// This is a library, main is not used
	fmt.Println("Go async runtime library loaded")
}
