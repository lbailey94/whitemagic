#ifndef SHM_CONSUMER_H
#define SHM_CONSUMER_H

#include <kklib.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdint.h>

static inline int64_t kk_shm_open_map(kk_string_t name, kk_integer_t size, kk_context_t* ctx) {
    const char* c_name = kk_string_cbuf_borrow(name, NULL, ctx);
    int fd = shm_open(c_name, O_RDWR, 0666);
    kk_string_drop(name, ctx);
    if (fd < 0) return 0;
    
    intptr_t sz = kk_integer_clamp_ssize_t(size, ctx);
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

static inline int64_t kk_shm_read_int64(int64_t addr, kk_integer_t offset, kk_context_t* ctx) {
    intptr_t off = kk_integer_clamp_ssize_t(offset, ctx);
    return *(int64_t*)(addr + off);
}

static inline double kk_shm_read_double(int64_t addr, kk_integer_t offset, kk_context_t* ctx) {
    intptr_t off = kk_integer_clamp_ssize_t(offset, ctx);
    return *(double*)(addr + off);
}

#endif\n