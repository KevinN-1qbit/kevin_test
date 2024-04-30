use std::{fs, io::{self, BufReader}, path};

use flate2::read::GzDecoder;
use fs2::FileExt;
use log::{trace, warn};
use memmap2::MmapMut;

pub mod lexer;
pub mod parser;


pub struct LockingFileReference {
    mmap: MmapMut,
    file_handle: fs::File,
    write: bool,
}


impl LockingFileReference {
    pub fn read(path: impl AsRef<path::Path>) -> anyhow::Result<Self> {
        let path = path.as_ref();
        let file_handle = fs::File::open(path)?;
        trace!("locking file {:?}", path);
        file_handle.lock_exclusive()?;
        warn!("The file at {:?} is now memory mapped! Writing to this file will cause undefined behaviour and incorrect results.", path);
        let mmap = unsafe { MmapMut::map_mut(&file_handle)? };
        Ok(Self {
            mmap,
            file_handle,
            write: false,
        })
    }

    pub fn as_bytes(&self) -> &[u8] {
        &self.mmap
    }
}


impl Drop for LockingFileReference {
    fn drop(&mut self) {
        if self.write {
            trace!("file reference opened with write permissions; flushing memory mapped changes");
            self.mmap.flush().unwrap();
        }
        trace!("unlocking file");
        self.file_handle.unlock().unwrap();
    }
}


#[derive(Debug)]
pub enum Input {
    // Buffer(&'a [u8]),
    File(BufReader<fs::File>),
    GZip(GzDecoder<BufReader<fs::File>>),
    Stdin(io::Stdin),
}


impl io::Read for Input {
    fn read(&mut self, buf: &mut [u8]) -> io::Result<usize> {
        match self {
            // Input::Buffer(b) => b.read(buf),
            Input::File(f) => f.read(buf),
            Input::GZip(g) => g.read(buf),
            Input::Stdin(s) => s.read(buf),
        }
    }
}


impl Input {
    pub fn new(path: impl AsRef<path::Path>) -> anyhow::Result<Self> {
        let path = path.as_ref();
        let file = fs::File::open(path)?;
        Ok(Self::File(BufReader::new(file)))
    }
    
    pub fn new_gzip(path: impl AsRef<path::Path>) -> anyhow::Result<Self> {
        let path = path.as_ref();
        let file = fs::File::open(path)?;
        Ok(Self::GZip(GzDecoder::new(BufReader::new(file))))
    }

    pub fn stdin() -> anyhow::Result<Self> {
        Ok(Self::Stdin(io::stdin()))
    }
}
