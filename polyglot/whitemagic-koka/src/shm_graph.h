#ifndef SHM_GRAPH_H
#define SHM_GRAPH_H

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <kklib.h>

#define GRAPH_MAGIC 0x47525048
#define GRAPH_HEADER_SIZE 64
#define GRAPH_SLOT_SIZE 16

static inline int64_t kk_shm_graph_open(kk_string_t name, kk_integer_t size, kk_context_t* ctx) {
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


static inline kk_integer_t kk_shm_unmap(int64_t addr, kk_integer_t size, kk_context_t* ctx) {
    intptr_t sz = kk_integer_clamp_ssize_t(size, ctx);
    int res = munmap((void*)addr, sz);
    return kk_integer_from_int(res, ctx);
}

static inline kk_integer_t kk_shm_read_int(int64_t addr, kk_integer_t offset, kk_context_t* ctx) {
    intptr_t off = kk_integer_clamp_ssize_t(offset, ctx);
    int32_t val = *(int32_t*)(addr + off);
    return kk_integer_from_int(val, ctx);
}

#pragma GCC push_options

#pragma GCC optimize("O3,unroll-loops")
// A super simple graph walker in C over the SHM segment
// Returns JSON string with node traversal counts
static inline kk_string_t kk_shm_graph_walk(int64_t addr, kk_integer_t kk_count, kk_integer_t kk_start_id, kk_integer_t kk_hops, kk_context_t* ctx) {
    intptr_t count = kk_integer_clamp_ssize_t(kk_count, ctx);
    int32_t start_id = (int32_t)kk_integer_clamp_ssize_t(kk_start_id, ctx);
    int hops = (int)kk_integer_clamp_ssize_t(kk_hops, ctx);
    
    // In a real implementation we'd need an index (source -> offset)
    // Since edges are unsorted, walking is O(N) per hop unless we index it.
    // For this benchmark/prototype, let's just do a linear scan to find edges out of the current set of active nodes.
    
    int32_t* active_nodes = malloc(1000 * sizeof(int32_t));
    int32_t* next_nodes = malloc(1000 * sizeof(int32_t));
    int active_count = 1;
    active_nodes[0] = start_id;
    
    int traversed_edges = 0;
    
    for (int h = 0; h < hops; h++) {
        int next_count = 0;
        
        for (intptr_t i = 0; i < count; i++) {
            intptr_t offset = GRAPH_HEADER_SIZE + (i * GRAPH_SLOT_SIZE);
            int32_t src = *(int32_t*)(addr + offset);
            int32_t tgt = *(int32_t*)(addr + offset + 4);
            
            // Check if src is in active_nodes
            for (int a = 0; a < active_count; a++) {
                if (src == active_nodes[a]) {
                    if (next_count < 1000) {
                        next_nodes[next_count++] = tgt;
                    }
                    traversed_edges++;
                    break;
                }
            }
        }
        
        // Swap arrays
        memcpy(active_nodes, next_nodes, next_count * sizeof(int32_t));
        active_count = next_count;
    }
    
    free(active_nodes);
    free(next_nodes);
    
    char buf[256];
    snprintf(buf, sizeof(buf), "{\"nodes_visited\":%d,\"edges_traversed\":%d}", active_count, traversed_edges);
    return kk_string_alloc_from_utf8(buf, ctx);
}
#pragma GCC pop_options

#endif
