//! Unfortunately, dealing with memory-mapped files seems to be a weak point right now in Rust.
//! 
//! This module exists to provide a safe Vec-like abstraction over a virtual memory region, which can either be actual RAM or it can be a memory-mapped file.
//! 
//! We need this in order to efficiently deal with streaming our in-progress results to files.
//! 
//! Why can't we just use `Vec::from_raw_parts`? The requirements on that function (and `from_raw_parts_in`) require reallocation to be possible, which it isn't for us!
//!  

use std::{fs, mem, ops::{Index, IndexMut}};
use anyhow::bail;
use fs2::FileExt;
use memmap2::MmapMut;

enum BufferBack<T> {
    File(fs::File, MmapMut),
    Vec(Vec<T>),
}

pub struct Buffer<T> {
    pointer: *mut T,
    length: usize,
    capacity: usize,
    // this field exists so that we correctly drop the allocation/file handles
    // we don't actually interact with it at all
    #[allow(dead_code)]
    backing: BufferBack<T>,
}

impl<T> Buffer<T> {
    /// This function is unsafe because it's UB for a file to be changed while mmap'd. We lock the file, but that just
    /// tries to prevent other processes from manipulating it.
    /// We also use the default tempfile crate permissions of 0o600 on Unix. I'm not sure how/if that changes on Windows.
    pub unsafe fn new_from_tempfile(capacity: usize) -> anyhow::Result<Self> {
        if mem::size_of::<T>() == 0 {
            bail!("Buffer does not support ZSTs.");
        }
        if capacity == 0 {
            bail!("Zero capacity")
        }
        let file = tempfile::tempfile()?;
        file.try_lock_exclusive()?;

        // resize
        // we need to allocate slightly more space than strictly needed in order to guarantee alignment
        let alignment_overalloc = (mem::align_of::<T>() + mem::size_of::<T>()) * 2;
        let alloc_size = (mem::size_of::<T>() * capacity) + alignment_overalloc;
        file.set_len(alloc_size as u64)?;
        // get memory map
        let mut map = MmapMut::map_mut(&file)?;
        let (_, aligned_raw_slice, _) = map.align_to_mut::<T>();

        if aligned_raw_slice.len() < capacity {
            bail!("Did not allocate enough memory ({} < {})", aligned_raw_slice.len(), capacity);
        }

        Ok(Buffer {
            pointer: aligned_raw_slice.as_mut_ptr(),
            length: 0,
            capacity: aligned_raw_slice.len(),
            backing: BufferBack::File(file, map),
        })
    }

    pub fn new_in_memory(capacity: usize) -> anyhow::Result<Self> {
        if mem::size_of::<T>() == 0 {
            bail!("Buffer does not support ZSTs.");
        }
        if capacity == 0 {
            bail!("Zero capacity")
        }

        let mut back = Vec::<T>::with_capacity(capacity);

        Ok(Buffer {
            pointer: back.as_mut_ptr(),
            length: 0,
            capacity: back.capacity(),
            backing: BufferBack::Vec(back),
        })
    }

    /// Advice the kernel that the memory allocated will be accessed sequentially.
    /// 
    /// This only has an effect on file-backed buffers on Unix. Errors are ignored.
    pub fn advice_sequential(&self) {
        if let BufferBack::File(_, mmap) = &self.backing {
            let _ = mmap.advise(memmap2::Advice::Sequential);
        }
    }

    /// Advice the kernel that the memory allocated will be accessed in a random order.
    /// 
    /// This only has an effect on file-backed buffers on Unix. Errors are ignored.
    pub fn advice_random(&self) {
        if let BufferBack::File(_, mmap) = &self.backing {
            let _ = mmap.advise(memmap2::Advice::Random);
        }
    }

    pub fn push(&mut self, val: T) {
        assert!(self.length + 1 <= self.capacity);
        self.length += 1;
        *self.index_mut(self.length - 1) = val;
    }

    pub fn len(&self) -> usize {
        self.length
    }

    pub fn capacity(&self) -> usize {
        self.capacity
    }

    pub fn unused_capacity(&self) -> usize {
        self.capacity - self.length
    }

    pub fn clear(&mut self) {
        debug_assert!(self.length <= self.capacity);

        for i in 0..self.len() {
            unsafe {
                let ptr = self.pointer.add(i);
                ptr.drop_in_place();
            }
        }
        self.length = 0;
    }
}


impl<T: Clone> Buffer<T> {
    pub fn copy_into(&self, other: &mut Self) -> anyhow::Result<()> {
        if other.unused_capacity() < self.len() {
            bail!("Not enough space in target");
        }

        for i in 0..self.len() {
            other.push(self[i].clone());
        }

        Ok(())
    }
}


impl<T> Index<usize> for Buffer<T> {
    type Output = T;

    fn index(&self, index: usize) -> &Self::Output {
        debug_assert!(self.length <= self.capacity);
        assert!(index < self.length);
        unsafe {
            let pointer_to_element = self.pointer.add(index);
            mem::transmute(pointer_to_element)
        }
    }
}


impl<T> IndexMut<usize> for Buffer<T> {
    fn index_mut(&mut self, index: usize) -> &mut Self::Output {
        debug_assert!(self.length <= self.capacity);
        assert!(index < self.length);
        unsafe {
            let pointer_to_element = self.pointer.add(index);
            mem::transmute(pointer_to_element)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_buf(mut buf: Buffer<usize>) {
        for i in 0..1024 {
            buf.push(i);
        }

        assert_eq!(buf.len(), 1024);

        for i in 0..1024 {
            assert_eq!(buf[i], i);
        }

        buf.clear();
        assert_eq!(buf.len(), 0);
    }

    #[test]
    fn test_buf_file() {
        unsafe {
            let buf = Buffer::new_from_tempfile(1024).unwrap();
            test_buf(buf);
        }
    }

    #[test]
    fn test_buf_vec() {
        let buf = Buffer::new_in_memory(1024).unwrap();
        test_buf(buf);
    }
}