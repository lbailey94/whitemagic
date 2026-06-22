#ifndef SHM_RING_CONSUMER_H
#define SHM_RING_CONSUMER_H

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <kklib.h>

#define RING_MAGIC 0x52494E47
#define RING_HEADER_SIZE 64
#define RING_SLOT_SIZE 256

static inline int64_t kk_shm_ring_open(kk_string_t name, kk_integer_t size, kk_context_t* ctx) {
    const char* n = kk_string_cbuf_borrow(name, NULL, ctx);
    intptr_t sz = kk_integer_clamp_ssize_t(size, ctx);
    
    int fd = shm_open(n, O_RDWR, 0666);
    kk_string_drop(name, ctx);
    if (fd < 0) return 0;
    
    void* addr = mmap(NULL, sz, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    close(fd);
    if (addr == MAP_FAILED) return 0;
    return (int64_t)addr;
}

// Reads the next event from the ring buffer if available, updates tail.
// Returns a JSON string or empty string if no event.
static inline kk_string_t kk_shm_ring_poll(int64_t addr, kk_context_t* ctx) {
    int32_t magic = *(int32_t*)addr;
    if (magic != RING_MAGIC) return kk_string_empty(ctx);
    
    int32_t head = *(int32_t*)(addr + 4);
    int32_t tail = *(int32_t*)(addr + 8);
    int32_t capacity = *(int32_t*)(addr + 12);
    
    if (head == tail) {
        return kk_string_empty(ctx); // empty
    }
    
    intptr_t offset = RING_HEADER_SIZE + (tail * RING_SLOT_SIZE);
    
    int32_t event_type = *(int32_t*)(addr + offset);
    int32_t sender_hash = *(int32_t*)(addr + offset + 4);
    double timestamp = *(double*)(addr + offset + 8);
    
    const char* payload = (const char*)(addr + offset + 16);
    
    char buf[512];
    snprintf(buf, sizeof(buf), "{\"event_type\":%d,\"sender_hash\":%d,\"timestamp\":%f,\"payload\":\"%s\"}", 
             event_type, sender_hash, timestamp, payload);
             
    // Update tail
    int32_t next_tail = (tail + 1) % capacity;
    *(int32_t*)(addr + 8) = next_tail;
    
    return kk_string_alloc_from_utf8(buf, ctx);
}

#endif
