#ifndef UNIFIED_FAST_BRAIN_H
#define UNIFIED_FAST_BRAIN_H

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <kklib.h>

#include <sys/time.h>
static inline double kk_unified_time_ms(kk_context_t* ctx) {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return (tv.tv_sec * 1000.0) + (tv.tv_usec / 1000.0);
}


// --- Ring Buffer Definitions ---
#define RING_MAGIC 0x52494E47
#define RING_HEADER_SIZE 64
#define RING_SLOT_SIZE 256

static inline int64_t kk_unified_ring_open(kk_string_t name, kk_integer_t size, kk_context_t* ctx) {
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

static inline kk_string_t kk_unified_ring_poll(int64_t addr, kk_context_t* ctx) {
    int32_t magic = *(int32_t*)addr;
    if (magic != RING_MAGIC) return kk_string_empty(ctx);
    
    int32_t head = *(int32_t*)(addr + 4);
    int32_t tail = *(int32_t*)(addr + 8);
    int32_t capacity = *(int32_t*)(addr + 12);
    
    if (head == tail) return kk_string_empty(ctx);
    
    intptr_t offset = RING_HEADER_SIZE + (tail * RING_SLOT_SIZE);
    
    int32_t event_type = *(int32_t*)(addr + offset);
    int32_t sender_hash = *(int32_t*)(addr + offset + 4);
    double timestamp = *(double*)(addr + offset + 8);
    const char* payload = (const char*)(addr + offset + 16);
    
    char buf[512];
    snprintf(buf, sizeof(buf), "{\"event_type\":%d,\"sender_hash\":%d,\"timestamp\":%f,\"payload\":%s}", 
             event_type, sender_hash, timestamp, payload);
             
    *(int32_t*)(addr + 8) = (tail + 1) % capacity;
    
    return kk_string_alloc_from_utf8(buf, ctx);
}

// --- Vector Embeddings Definitions ---
#define EMBED_MAGIC 0x454D4244
#define VEC_DIM 384
#define MAX_VECS 100000
#define EMBED_HEADER_SIZE 32
#define EMBED_SLOT_SIZE (36 + (VEC_DIM * 4)) // 36 bytes string + 1536 bytes vec = 1572 bytes

static inline int64_t kk_unified_embed_open(kk_string_t name, kk_context_t* ctx) {
    const char* n = kk_string_cbuf_borrow(name, NULL, ctx);
    int fd = shm_open(n, O_RDWR, 0666);
    kk_string_drop(name, ctx);
    if (fd < 0) return 0;
    
    intptr_t sz = EMBED_HEADER_SIZE + (MAX_VECS * EMBED_SLOT_SIZE);
    void* addr = mmap(NULL, sz, PROT_READ, MAP_SHARED, fd, 0);
    close(fd);
    if (addr == MAP_FAILED) return 0;
    return (int64_t)addr;
}

// Mocking the search for now, to return a random internal node ID we can walk from
static inline kk_integer_t kk_unified_embed_search(int64_t addr, kk_context_t* ctx) {
    if (addr == 0) return kk_integer_from_int(0, ctx);
    int32_t count = *(int32_t*)(addr + 8);
    if (count == 0) return kk_integer_from_int(0, ctx);
    // Just return node 1 for the benchmark/prototype 
    // In reality this calls the AVX2 dot product search over `count` vectors
    return kk_integer_from_int(1, ctx); 
}

// --- Graph Topology Definitions ---
#define GRAPH_MAGIC 0x47525048
#define GRAPH_HEADER_SIZE 64
#define GRAPH_SLOT_SIZE 16

static inline int64_t kk_unified_graph_open(kk_string_t name, kk_integer_t size, kk_context_t* ctx) {
    const char* n = kk_string_cbuf_borrow(name, NULL, ctx);
    intptr_t sz = kk_integer_clamp_ssize_t(size, ctx);
    
    int fd = shm_open(n, O_RDWR, 0666);
    kk_string_drop(name, ctx);
    if (fd < 0) return 0;
    
    void* addr = mmap(NULL, sz, PROT_READ, MAP_SHARED, fd, 0);
    close(fd);
    if (addr == MAP_FAILED) return 0;
    return (int64_t)addr;
}

#pragma GCC push_options
#pragma GCC optimize("O3,unroll-loops")
static inline kk_string_t kk_unified_graph_walk(int64_t addr, kk_integer_t kk_start_id, kk_integer_t kk_hops, kk_context_t* ctx) {
    int32_t start_id = (int32_t)kk_integer_clamp_ssize_t(kk_start_id, ctx);
    int hops = (int)kk_integer_clamp_ssize_t(kk_hops, ctx);
    
    if (addr == 0 || start_id == 0) return kk_string_alloc_from_utf8("{\"nodes_visited\":0,\"edges_traversed\":0}", ctx);
    
    int32_t count = *(int32_t*)(addr + 12);
    if (count == 0) return kk_string_alloc_from_utf8("{\"nodes_visited\":0,\"edges_traversed\":0}", ctx);
    
    int32_t* active_nodes = malloc(1000 * sizeof(int32_t));
    int32_t* next_nodes = malloc(1000 * sizeof(int32_t));
    int active_count = 1;
    active_nodes[0] = start_id;
    
    int traversed_edges = 0;
    int total_nodes_visited = 1;
    
    for (int h = 0; h < hops; h++) {
        int next_count = 0;
        
        for (intptr_t i = 0; i < count; i++) {
            intptr_t offset = GRAPH_HEADER_SIZE + (i * GRAPH_SLOT_SIZE);
            int32_t src = *(int32_t*)(addr + offset);
            int32_t tgt = *(int32_t*)(addr + offset + 4);
            
            for (int a = 0; a < active_count; a++) {
                if (src == active_nodes[a]) {
                    int already_in = 0;
                    for (int n = 0; n < next_count; n++) {
                        if (next_nodes[n] == tgt) { already_in = 1; break; }
                    }
                    if (!already_in && next_count < 1000) {
                        next_nodes[next_count++] = tgt;
                    }
                    traversed_edges++;
                    break;
                }
            }
        }
        
        memcpy(active_nodes, next_nodes, next_count * sizeof(int32_t));
        active_count = next_count;
        total_nodes_visited += active_count;
        
        if (active_count == 0) break;
    }
    
    free(active_nodes);
    free(next_nodes);
    
    char buf[256];
    snprintf(buf, sizeof(buf), "{\"nodes_visited\":%d,\"edges_traversed\":%d}", total_nodes_visited, traversed_edges);
    return kk_string_alloc_from_utf8(buf, ctx);
}
#pragma GCC pop_options

#endif
