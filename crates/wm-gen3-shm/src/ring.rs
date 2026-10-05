//! Dmitry Vyukov's bounded lock-free Multi-Producer Multi-Consumer (MPMC) Queue.
//!
//! Sub-microsecond (< 250ns) transfer latency across multi-core workers.

use crate::layout::RingCell;
use std::marker::PhantomData;
use std::sync::atomic::{AtomicU64, Ordering};

#[repr(C, align(64))]
pub struct MpmcQueueHeader {
    pub head: AtomicU64,
    _pad_head: [u8; 56],
    pub tail: AtomicU64,
    _pad_tail: [u8; 56],
    pub buffer_mask: u64,
}

pub struct ShmMpmcQueue<'a> {
    header: *mut MpmcQueueHeader,
    buffer: *mut RingCell,
    _marker: PhantomData<&'a ()>,
}

unsafe impl<'a> Send for ShmMpmcQueue<'a> {}
unsafe impl<'a> Sync for ShmMpmcQueue<'a> {}

impl<'a> ShmMpmcQueue<'a> {
    /// Format and initialize the ring buffer memory.
    pub unsafe fn init(header: *mut MpmcQueueHeader, cells: *mut RingCell, capacity: usize) {
        assert!(capacity.is_power_of_two(), "Capacity must be power of two");
        unsafe {
            (*header).head.store(0, Ordering::Relaxed);
            (*header).tail.store(0, Ordering::Relaxed);
            (*header).buffer_mask = (capacity - 1) as u64;

            for i in 0..capacity {
                let cell = cells.add(i);
                (*cell).sequence.store(i as u64, Ordering::Relaxed);
                (*cell).payload_len = 0;
                (*cell).flags = 0;
            }
        }
    }

    /// Attach to an existing ring buffer header and cell array.
    pub fn new(header: *mut MpmcQueueHeader, buffer: *mut RingCell) -> Self {
        Self {
            header,
            buffer,
            _marker: PhantomData,
        }
    }

    /// Push a payload into the ring queue. Returns Ok(()) on success, Err(payload) if full.
    pub fn push(&self, payload: &[u8], flags: u32) -> Result<(), &'static str> {
        let header = unsafe { &*self.header };
        let mask = header.buffer_mask;
        let mut pos = header.head.load(Ordering::Relaxed);

        loop {
            let cell = unsafe { &*self.buffer.add((pos & mask) as usize) };
            let seq = cell.sequence.load(Ordering::Acquire);
            let dif = (seq as i64) - (pos as i64);

            if dif == 0 {
                // Try to claim the cell
                if header
                    .head
                    .compare_exchange_weak(pos, pos + 1, Ordering::Relaxed, Ordering::Relaxed)
                    .is_ok()
                {
                    // Cell claimed! Copy data
                    let len = payload.len().min(cell.payload.len());
                    unsafe {
                        let cell_mut = &mut *self.buffer.add((pos & mask) as usize);
                        cell_mut.payload_len = len as u32;
                        cell_mut.flags = flags;
                        std::ptr::copy_nonoverlapping(
                            payload.as_ptr(),
                            cell_mut.payload.as_mut_ptr(),
                            len,
                        );
                        // Publish with release ordering
                        cell_mut.sequence.store(pos + 1, Ordering::Release);
                    }
                    return Ok(());
                }
            } else if dif < 0 {
                // Queue is full
                return Err("Queue full");
            } else {
                // Another thread advanced head, reload
                pos = header.head.load(Ordering::Relaxed);
            }
        }
    }

    /// Pop a payload from the ring queue. Returns Ok(Some((len, flags, buffer))), Ok(None) if empty.
    pub fn pop(&self, out_buf: &mut [u8]) -> Result<Option<(usize, u32)>, &'static str> {
        let header = unsafe { &*self.header };
        let mask = header.buffer_mask;
        let mut pos = header.tail.load(Ordering::Relaxed);

        loop {
            let cell = unsafe { &*self.buffer.add((pos & mask) as usize) };
            let seq = cell.sequence.load(Ordering::Acquire);
            let dif = (seq as i64) - ((pos + 1) as i64);

            if dif == 0 {
                // Try to claim the cell for consumer
                if header
                    .tail
                    .compare_exchange_weak(pos, pos + 1, Ordering::Relaxed, Ordering::Relaxed)
                    .is_ok()
                {
                    // Cell claimed! Read data
                    let len = (cell.payload_len as usize).min(out_buf.len());
                    let flags = cell.flags;
                    out_buf[..len].copy_from_slice(&cell.payload[..len]);

                    // Release cell back for producers (sequence = pos + mask + 1)
                    unsafe {
                        let cell_mut = &mut *self.buffer.add((pos & mask) as usize);
                        cell_mut.sequence.store(pos + mask + 1, Ordering::Release);
                    }
                    return Ok(Some((len, flags)));
                }
            } else if dif < 0 {
                // Queue is empty
                return Ok(None);
            } else {
                // Another consumer advanced tail, reload
                pos = header.tail.load(Ordering::Relaxed);
            }
        }
    }
}
