/// Shared-memory SPSC ring buffer for inter-trigram communication.
///
/// Lock-free single-producer single-consumer ring buffer using `/dev/shm`
/// for fast inter-thread communication between core-pinned trigram threads.
///
/// Layout: `[header (64 bytes, cache-line aligned)] [data buffer (capacity bytes)]`
///
/// Variable-length messages use a 4-byte length prefix followed by data.
/// Fixed-length mode skips the prefix for maximum throughput.
///
/// Usage:
/// ```no_run
/// use whitemagic_rust::inference::ring_buffer::RingBuffer;
///
/// // Producer side
/// let rb = RingBuffer::create("qian_to_li", 1024 * 1024).unwrap();
/// rb.try_write(b"hello world");
///
/// // Consumer side (separate thread / process)
/// let rb = RingBuffer::open("qian_to_li").unwrap();
/// let msg = rb.try_read(); // Some(Vec<u8>)
/// ```

use std::fs::OpenOptions;
use std::io::{self, Read};
use std::os::unix::io::AsRawFd;
use std::path::PathBuf;
use std::ptr::NonNull;
use std::sync::atomic::{AtomicU64, Ordering};

/// Magic number for validating shared memory regions.
const RING_BUFFER_MAGIC: u64 = 0x574D5F5242_0001;

/// Default SHM directory.
const SHM_DIR: &str = "/dev/shm";

/// Cache-line aligned header (64 bytes).
#[repr(C, align(64))]
pub struct RingBufferHeader {
    /// Magic number for validation.
    pub magic: u64,
    /// Total data capacity in bytes (excluding header).
    pub capacity: u64,
    /// Size of each element (0 = variable-length mode).
    pub element_size: u64,
    /// Producer write position (monotonic, wraps at capacity).
    pub write_pos: AtomicU64,
    /// Consumer read position (monotonic, wraps at capacity).
    pub read_pos: AtomicU64,
    /// Padding to fill the cache line.
    pub _padding: [u8; 16],
}

const HEADER_SIZE: usize = 64;

impl RingBufferHeader {
    fn new(capacity: u64, element_size: u64) -> Self {
        Self {
            magic: RING_BUFFER_MAGIC,
            capacity,
            element_size,
            write_pos: AtomicU64::new(0),
            read_pos: AtomicU64::new(0),
            _padding: [0u8; 16],
        }
    }
}

/// Errors that can occur when working with ring buffers.
#[derive(Debug)]
pub enum RingBufferError {
    IoError(io::Error),
    InvalidMagic,
    InvalidCapacity,
    MapError(String),
    AlreadyExists,
    NotFound,
}

impl std::fmt::Display for RingBufferError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::IoError(e) => write!(f, "IO error: {}", e),
            Self::InvalidMagic => write!(f, "Invalid magic number in ring buffer"),
            Self::InvalidCapacity => write!(f, "Invalid capacity (must be > 0)"),
            Self::MapError(s) => write!(f, "Memory map error: {}", s),
            Self::AlreadyExists => write!(f, "Ring buffer already exists"),
            Self::NotFound => write!(f, "Ring buffer not found"),
        }
    }
}

impl std::error::Error for RingBufferError {}

impl From<io::Error> for RingBufferError {
    fn from(e: io::Error) -> Self {
        Self::IoError(e)
    }
}

/// A shared-memory SPSC ring buffer.
pub struct RingBuffer {
    /// Mapped memory pointer (header + data).
    base: NonNull<u8>,
    /// Total mapped size (header + data).
    total_size: usize,
    /// SHM file path.
    shm_path: PathBuf,
    /// True if this instance created the buffer (producer).
    is_owner: bool,
    /// Buffer name (for identification).
    name: String,
}

// RingBuffer is Send because access is synchronized via atomics (SPSC).
unsafe impl Send for RingBuffer {}

impl RingBuffer {
    /// Create a new ring buffer in shared memory.
    ///
    /// Args:
    ///   name: Buffer name (creates `/dev/shm/wm_trigram_{name}`)
    ///   capacity: Data capacity in bytes (excluding 64-byte header)
    pub fn create(name: &str, capacity: usize) -> Result<Self, RingBufferError> {
        if capacity == 0 {
            return Err(RingBufferError::InvalidCapacity);
        }
        let path = Self::shm_path(name);
        if path.exists() {
            return Err(RingBufferError::AlreadyExists);
        }

        let total_size = HEADER_SIZE + capacity;
        let file = OpenOptions::new()
            .read(true)
            .write(true)
            .create_new(true)
            .open(&path)?;

        // Resize file to total size
        file.set_len(total_size as u64)?;

        // mmap the file
        let base = unsafe {
            let ptr = libc::mmap(
                std::ptr::null_mut(),
                total_size,
                libc::PROT_READ | libc::PROT_WRITE,
                libc::MAP_SHARED,
                file.as_raw_fd(),
                0,
            );
            if ptr == libc::MAP_FAILED {
                return Err(RingBufferError::MapError("mmap failed".to_string()));
            }
            NonNull::new(ptr as *mut u8).ok_or(RingBufferError::MapError(
                "mmap returned null".to_string(),
            ))?
        };

        // Initialize header
        let header = Self::header_mut(base);
        *header = RingBufferHeader::new(capacity as u64, 0); // 0 = variable-length

        // Don't close the fd — mmap keeps the mapping alive
        std::mem::forget(file);

        Ok(Self {
            base,
            total_size,
            shm_path: path,
            is_owner: true,
            name: name.to_string(),
        })
    }

    /// Open an existing ring buffer.
    ///
    /// Args:
    ///   name: Buffer name (opens `/dev/shm/wm_trigram_{name}`)
    pub fn open(name: &str) -> Result<Self, RingBufferError> {
        let path = Self::shm_path(name);
        if !path.exists() {
            return Err(RingBufferError::NotFound);
        }

        let file = OpenOptions::new().read(true).write(true).open(&path)?;

        // Read capacity from header to determine total size
        let mut header_buf = [0u8; HEADER_SIZE];
        let mut f = std::fs::File::open(&path)?;
        f.read_exact(&mut header_buf)?;

        let magic = u64::from_le_bytes(header_buf[0..8].try_into().unwrap());
        if magic != RING_BUFFER_MAGIC {
            return Err(RingBufferError::InvalidMagic);
        }
        let capacity = u64::from_le_bytes(header_buf[8..16].try_into().unwrap());

        let total_size = HEADER_SIZE + capacity as usize;

        let base = unsafe {
            let ptr = libc::mmap(
                std::ptr::null_mut(),
                total_size,
                libc::PROT_READ | libc::PROT_WRITE,
                libc::MAP_SHARED,
                file.as_raw_fd(),
                0,
            );
            if ptr == libc::MAP_FAILED {
                return Err(RingBufferError::MapError("mmap failed".to_string()));
            }
            NonNull::new(ptr as *mut u8).ok_or(RingBufferError::MapError(
                "mmap returned null".to_string(),
            ))?
        };

        std::mem::forget(file);

        Ok(Self {
            base,
            total_size,
            shm_path: path,
            is_owner: false,
            name: name.to_string(),
        })
    }

    /// Get the SHM path for a given buffer name.
    fn shm_path(name: &str) -> PathBuf {
        PathBuf::from(format!("{}/wm_trigram_{}", SHM_DIR, name))
    }

    /// Get a reference to the header.
    fn header<'a>(base: NonNull<u8>) -> &'a RingBufferHeader {
        unsafe { &*(base.as_ptr() as *const RingBufferHeader) }
    }

    /// Get a mutable reference to the header.
    fn header_mut<'a>(base: NonNull<u8>) -> &'a mut RingBufferHeader {
        unsafe { &mut *(base.as_ptr() as *mut RingBufferHeader) }
    }

    /// Get the data region pointer.
    fn data_ptr(&self) -> *mut u8 {
        unsafe { self.base.as_ptr().add(HEADER_SIZE) }
    }

    /// Get the capacity of the data region.
    pub fn capacity(&self) -> u64 {
        Self::header(self.base).capacity
    }

    /// Try to write variable-length data to the buffer.
    ///
    /// Format: 4-byte LE length prefix + data bytes.
    ///
    /// Returns `false` if there isn't enough contiguous space.
    pub fn try_write(&self, data: &[u8]) -> bool {
        let header = Self::header(self.base);
        let cap = header.capacity as usize;
        let msg_len = 4 + data.len(); // length prefix + data
        if msg_len > cap {
            return false; // Message too large for buffer
        }

        let write_pos = header.write_pos.load(Ordering::Relaxed) as usize;
        let read_pos = header.read_pos.load(Ordering::Acquire) as usize;

        // Calculate available space (accounting for wraparound)
        let available = if write_pos >= read_pos {
            cap - (write_pos - read_pos)
        } else {
            read_pos - write_pos
        };

        // Need at least 1 byte free to distinguish full from empty
        if available <= msg_len {
            return false;
        }

        let data_ptr = self.data_ptr();

        // Write length prefix (4 bytes, little-endian)
        let len_bytes = (data.len() as u32).to_le_bytes();
        for (i, &byte) in len_bytes.iter().enumerate() {
            unsafe {
                *data_ptr.add((write_pos + i) % cap) = byte;
            }
        }

        // Write data
        for (i, &byte) in data.iter().enumerate() {
            unsafe {
                *data_ptr.add((write_pos + 4 + i) % cap) = byte;
            }
        }

        // Update write position
        let new_write_pos = (write_pos + msg_len) % cap;
        header.write_pos.store(new_write_pos as u64, Ordering::Release);

        true
    }

    /// Try to read variable-length data from the buffer.
    ///
    /// Returns `None` if the buffer is empty.
    pub fn try_read(&self) -> Option<Vec<u8>> {
        let header = Self::header(self.base);
        let cap = header.capacity as usize;

        let write_pos = header.write_pos.load(Ordering::Acquire) as usize;
        let read_pos = header.read_pos.load(Ordering::Relaxed) as usize;

        if write_pos == read_pos {
            return None; // Empty
        }

        let data_ptr = self.data_ptr();

        // Read length prefix (4 bytes, little-endian)
        let mut len_bytes = [0u8; 4];
        for i in 0..4 {
            unsafe {
                len_bytes[i] = *data_ptr.add((read_pos + i) % cap);
            }
        }
        let msg_len = u32::from_le_bytes(len_bytes) as usize;
        let total_len = 4 + msg_len;

        // Read data
        let mut result = Vec::with_capacity(msg_len);
        for i in 0..msg_len {
            unsafe {
                result.push(*data_ptr.add((read_pos + 4 + i) % cap));
            }
        }

        // Update read position
        let new_read_pos = (read_pos + total_len) % cap;
        header.read_pos.store(new_read_pos as u64, Ordering::Release);

        Some(result)
    }

    /// Try to write a fixed-size element (no length prefix).
    ///
    /// Args:
    ///   data: Byte slice with exactly `element_size` bytes.
    ///
    /// Returns `false` if the buffer is full or data length doesn't match.
    pub fn try_write_fixed(&self, data: &[u8]) -> bool {
        let header = Self::header(self.base);
        let cap = header.capacity as usize;
        let elem_size = header.element_size as usize;

        if elem_size == 0 || data.len() != elem_size {
            return false;
        }

        let write_pos = header.write_pos.load(Ordering::Relaxed) as usize;
        let read_pos = header.read_pos.load(Ordering::Acquire) as usize;

        let available = if write_pos >= read_pos {
            cap - (write_pos - read_pos)
        } else {
            read_pos - write_pos
        };

        if available <= elem_size {
            return false;
        }

        let data_ptr = self.data_ptr();
        for (i, &byte) in data.iter().enumerate() {
            unsafe {
                *data_ptr.add((write_pos + i) % cap) = byte;
            }
        }

        let new_write_pos = (write_pos + elem_size) % cap;
        header.write_pos.store(new_write_pos as u64, Ordering::Release);

        true
    }

    /// Try to read a fixed-size element (no length prefix).
    ///
    /// Returns `None` if the buffer is empty.
    pub fn try_read_fixed(&self) -> Option<Vec<u8>> {
        let header = Self::header(self.base);
        let cap = header.capacity as usize;
        let elem_size = header.element_size as usize;

        if elem_size == 0 {
            return None;
        }

        let write_pos = header.write_pos.load(Ordering::Acquire) as usize;
        let read_pos = header.read_pos.load(Ordering::Relaxed) as usize;

        if write_pos == read_pos {
            return None;
        }

        let data_ptr = self.data_ptr();
        let mut result = Vec::with_capacity(elem_size);
        for i in 0..elem_size {
            unsafe {
                result.push(*data_ptr.add((read_pos + i) % cap));
            }
        }

        let new_read_pos = (read_pos + elem_size) % cap;
        header.read_pos.store(new_read_pos as u64, Ordering::Release);

        Some(result)
    }

    /// Get the current fill level as a fraction (0.0 to 1.0).
    pub fn fill_level(&self) -> f32 {
        let header = Self::header(self.base);
        let cap = header.capacity as usize;
        let write_pos = header.write_pos.load(Ordering::Relaxed) as usize;
        let read_pos = header.read_pos.load(Ordering::Relaxed) as usize;

        let used = if write_pos >= read_pos {
            write_pos - read_pos
        } else {
            cap - read_pos + write_pos
        };

        used as f32 / cap as f32
    }

    /// Get the number of bytes available to read.
    pub fn available(&self) -> u64 {
        let header = Self::header(self.base);
        let cap = header.capacity as usize;
        let write_pos = header.write_pos.load(Ordering::Relaxed) as usize;
        let read_pos = header.read_pos.load(Ordering::Relaxed) as usize;

        let used = if write_pos >= read_pos {
            write_pos - read_pos
        } else {
            cap - read_pos + write_pos
        };

        used as u64
    }

    /// Get the buffer name.
    pub fn name(&self) -> &str {
        &self.name
    }

    /// Check if this instance is the owner (creator/producer).
    pub fn is_owner(&self) -> bool {
        self.is_owner
    }

    /// Close the ring buffer and unmap memory.
    /// If this is the owner, optionally unlink the SHM file.
    pub fn close(self) -> Result<(), RingBufferError> {
        unsafe {
            libc::munmap(self.base.as_ptr() as *mut libc::c_void, self.total_size);
        }

        if self.is_owner {
            std::fs::remove_file(&self.shm_path)?;
        }

        Ok(())
    }
}

impl Drop for RingBuffer {
    fn drop(&mut self) {
        unsafe {
            libc::munmap(self.base.as_ptr() as *mut libc::c_void, self.total_size);
        }
        // Don't unlink on drop — only on explicit close() by owner.
        // This allows the consumer to still access the buffer if the
        // producer drops its handle without calling close().
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::thread;

    #[test]
    fn test_create_and_basic_io() {
        let name = format!("test_rb_io_{}", std::process::id());
        let rb = RingBuffer::create(&name, 4096).unwrap();

        // Buffer should be empty
        assert_eq!(rb.fill_level(), 0.0);
        assert!(rb.try_read().is_none());

        // Write a message
        assert!(rb.try_write(b"hello"));
        assert!(rb.fill_level() > 0.0);

        // Read it back
        let msg = rb.try_read().unwrap();
        assert_eq!(msg, b"hello");

        // Buffer should be empty again
        assert_eq!(rb.fill_level(), 0.0);

        rb.close().unwrap();
    }

    #[test]
    fn test_multiple_messages() {
        let name = format!("test_rb_multi_{}", std::process::id());
        let rb = RingBuffer::create(&name, 4096).unwrap();

        for i in 0..10 {
            let msg = format!("message_{}", i);
            assert!(rb.try_write(msg.as_bytes()));
        }

        for i in 0..10 {
            let msg = rb.try_read().unwrap();
            assert_eq!(msg, format!("message_{}", i).as_bytes());
        }

        assert!(rb.try_read().is_none());
        rb.close().unwrap();
    }

    #[test]
    fn test_producer_consumer() {
        let name = format!("test_rb_pc_{}", std::process::id());
        let producer = RingBuffer::create(&name, 64 * 1024).unwrap();
        let consumer = RingBuffer::open(&name).unwrap();

        let messages: Vec<Vec<u8>> = (0..50)
            .map(|i| format!("msg_{:04}", i).into_bytes())
            .collect();

        let msgs_clone = messages.clone();
        let handle = thread::spawn(move || {
            let mut received = Vec::new();
            let mut idx = 0;
            while idx < msgs_clone.len() {
                if let Some(data) = consumer.try_read() {
                    received.push(data);
                    idx += 1;
                } else {
                    std::thread::yield_now();
                }
            }
            received
        });

        for msg in &messages {
            while !producer.try_write(msg) {
                std::thread::yield_now();
            }
        }

        let received = handle.join().unwrap();
        assert_eq!(received, messages);

        producer.close().unwrap();
    }

    #[test]
    fn test_wraparound() {
        let name = format!("test_rb_wrap_{}", std::process::id());
        // Small buffer to force wraparound
        let rb = RingBuffer::create(&name, 128).unwrap();

        // Write and read in a loop to force position wraparound
        for i in 0..100 {
            let msg = format!("m{}", i);
            while !rb.try_write(msg.as_bytes()) {
                // Read to make space
                if rb.try_read().is_none() {
                    std::thread::yield_now();
                }
            }
            let read = rb.try_read().unwrap();
            assert_eq!(read, msg.as_bytes());
        }

        rb.close().unwrap();
    }

    #[test]
    fn test_full_buffer() {
        let name = format!("test_rb_full_{}", std::process::id());
        let rb = RingBuffer::create(&name, 64).unwrap();

        // Fill the buffer
        let mut written = 0;
        while rb.try_write(b"x") {
            written += 1;
        }
        assert!(written > 0);

        // Further writes should fail
        assert!(!rb.try_write(b"x"));

        rb.close().unwrap();
    }

    #[test]
    fn test_invalid_open() {
        let result = RingBuffer::open("nonexistent_rb_test_12345");
        assert!(matches!(result, Err(RingBufferError::NotFound)));
    }

    #[test]
    fn test_double_create() {
        let name = format!("test_rb_double_{}", std::process::id());
        let rb = RingBuffer::create(&name, 1024).unwrap();
        let result = RingBuffer::create(&name, 1024);
        assert!(matches!(result, Err(RingBufferError::AlreadyExists)));
        rb.close().unwrap();
    }
}
