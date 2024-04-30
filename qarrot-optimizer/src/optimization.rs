
pub mod push_t_forward;
use anyhow::Context;
use fs2::FileExt;
use log::{trace, warn};
pub use push_t_forward::*;

pub mod partitions;

pub mod partition;
pub use partition::*;

pub mod rotation_combination;
pub use rotation_combination::*;

use crate::{basis::Basis, clifford::Clifford, operation::Operation, output::Output, RunConfig};

use core::slice;
use std::{fmt::Debug, fs, io::{Read, Seek, Write}, mem};

use self::partitions::Partitions;


#[derive(Clone, Copy, Debug)]
pub struct Stats {
    pub total_operations: usize,
    pub t_gates: usize,
}


impl Stats {
    fn zero() -> Self {
        Stats {
            total_operations: 0,
            t_gates: 0,
        }
    }
}


pub trait Optimizer<B: Basis, Ops: Iterator<Item = Operation<B>> + Debug>: Sized + Debug {
    fn new(n_qubits: usize, instructions: Ops, run_config: &RunConfig) -> anyhow::Result<Self>;
    fn initial_circuit_length(&self) -> Option<usize>; // may not be known
    fn post_reduction_length(&self) -> Option<usize>;
    fn latest_stats(&self) -> Option<Stats>;
    fn current_heap_usage(&self) -> (usize, usize); // allocated, used
    fn push_t_forward(&mut self) -> anyhow::Result<(bool, Stats)>; // changed, t_gate_count
    fn partition(&mut self) -> anyhow::Result<(bool, Stats)>;
    fn write_to_output(self, output: impl Output) -> anyhow::Result<()>;
}


#[derive(Debug)]
pub struct InMemoryOptimizer<B: Basis> {
    n_qubits: usize,
    circuit: Vec<Operation<B>>,
    initial_circuit_length: usize,
    post_reduction_length: usize,
    partitions: Partitions,
    full_partitioning: bool,
    latest_stats: Option<Stats>,
}

impl<B: Basis, Ops: Iterator<Item = Operation<B>> + Debug> Optimizer<B, Ops> for InMemoryOptimizer<B> {
    fn new(n_qubits: usize, instructions: Ops, run_config: &RunConfig) -> anyhow::Result<Self> {
        let prealloc = if let Some(num_operations) = run_config.num_operations {
            if num_operations > super::MAX_PREALLOC_OPERATIONS {
                warn!("number of operations given ({}) is larger than allowed default {}; using max allowed", num_operations, super::MAX_PREALLOC_OPERATIONS);
                super::MAX_PREALLOC_OPERATIONS
            } else {
                num_operations
            }
        } else {
            1024
        };
        let mut circuit = Vec::with_capacity(prealloc);

        let mut reducer = OptimizeRotationsAdjacent::new(instructions);

        while let Some(next) = reducer.next() {
            if let Some(next) = next {
                circuit.push(next);
            }
        }

        for i in 0..n_qubits {
            let z = B::one_bit(n_qubits, i);
            circuit.push(Operation::measurement(B::zero(n_qubits), z, false.into()))
        }

        if run_config.shrink_buffer_after_repeat {
            circuit.shrink_to_fit();
        }

        let initial_circuit_length = reducer.pre_op_count();

        Ok(Self {
            post_reduction_length: circuit.len(),
            latest_stats: None, // todo: can be determined
            n_qubits,
            circuit,
            initial_circuit_length,
            partitions: Partitions::new(),
            full_partitioning: run_config.full_partitioning,
        })
    }

    fn initial_circuit_length(&self) -> Option<usize> {
        Some(self.initial_circuit_length)
    }

    fn post_reduction_length(&self) -> Option<usize> {
        Some(self.post_reduction_length)
    }

    fn latest_stats(&self) -> Option<Stats> {
        self.latest_stats
    }

    fn current_heap_usage(&self) -> (usize, usize) {
        let allocated = self.circuit.capacity() * mem::size_of::<Operation<B>>();
        let used = self.circuit.len() * mem::size_of::<Operation<B>>();
        (allocated, used)
    }

    fn push_t_forward(&mut self) -> anyhow::Result<(bool, Stats)> {
        // let (changed, t_gates) = push_t_forward(&mut self.buffer, &self.circuit, self.n_qubits)?;
        // mem::swap(&mut self.buffer, &mut self.circuit);
        // self.buffer.clear();

        let (changed, t_gates) = push_t_forward_inplace(&mut self.circuit, self.n_qubits);

        let stats = Stats {
            total_operations: self.circuit.len(),
            t_gates,
        };

        self.latest_stats = Some(stats);

        Ok((changed, stats))
    }

    fn partition(&mut self) -> anyhow::Result<(bool, Stats)> {
        let t_gate_count = self.latest_stats.unwrap().t_gates;

        let changed = if self.full_partitioning {
            partition_t_gates(&mut self.partitions, &mut self.circuit, t_gate_count)
        } else {
            let (changed, stats) = approximate_partition_t_gates(&mut self.circuit);
            self.latest_stats = Some(stats);
            changed
        };

        Ok((changed, self.latest_stats.unwrap()))
    }

    fn write_to_output(self, mut output: impl Output) -> anyhow::Result<()> {
        for op in &self.circuit {
            output.write_operation(self.n_qubits, op)?;
        }
        output.flush()
    }
}


#[derive(Debug)]
// struct for swapping between one option which is "read" and one which is "write"
struct ReadWriteSwap {
    a: fs::File,
    b: fs::File,
    a_is_read: bool,
}


impl ReadWriteSwap {
    fn new(a: fs::File, b: fs::File) -> Self {
        Self {
            a,
            b,
            a_is_read: true,
        }
    }

    fn swap(&mut self) {
        trace!("swapping file buffers");
        if self.a_is_read {
            // now, a will be write
            self.a_is_read = false;
            self.a.rewind().unwrap();
            self.a.set_len(0).unwrap();
            self.b.rewind().unwrap();
        } else {
            self.a_is_read = true;
            self.b.rewind().unwrap();
            self.b.set_len(0).unwrap();
            self.a.rewind().unwrap();
        }
    }

    fn read(&mut self) -> &mut fs::File {
        if self.a_is_read {
            &mut self.a
        } else {
            &mut self.b
        }
    }

    fn write(&mut self) -> &mut fs::File {
        if self.a_is_read {
            &mut self.b
        } else {
            &mut self.a
        }
    }
}


#[derive(Debug)]
pub struct FileOptimizer<Ops: Iterator<Item = Operation<B>> + Debug, B: Basis> {
    n_qubits: usize,
    target_buffer_length: usize,
    circuit_buffer: Vec<Operation<B>>,
    instructions: Option<OptimizeRotationsAdjacent<B, Ops>>,
    initial_circuit_length: Option<usize>,
    post_reduction_length: Option<usize>,
    latest_stats: Option<Stats>,
    files: ReadWriteSwap,
}


impl<Ops: Iterator<Item = Operation<B>> + Debug, B: Basis> FileOptimizer<Ops, B> {
    /// Returns number of instructions read
    /// None if we're done
    fn read_from_source(&mut self) -> Option<usize> {
        self.circuit_buffer.clear();
        if let Some(instructions) = &mut self.instructions {
            trace!("reading from reducer");
            loop {
                if let Some(next) = instructions.next() {
                    if let Some(next) = next {
                        self.circuit_buffer.push(next);
                    }
                    if self.circuit_buffer.len() >= self.target_buffer_length {
                        break;
                    }
                } else {
                    trace!("reducer done");
                    self.initial_circuit_length = Some(instructions.pre_op_count());
                    self.instructions = None;

                    // todo: do this better
                    // this might cause us to realloc the circuit buffer
                    for i in 0..self.n_qubits {
                        let z = B::one_bit(self.n_qubits, i);
                        self.circuit_buffer.push(Operation::measurement(B::zero(self.n_qubits), z, false.into()))
                    }

                    break;
                }
            }

            if self.circuit_buffer.is_empty() {
                trace!("read 0");
                None
            } else {
                trace!("read {}", self.circuit_buffer.len());
                Some(self.circuit_buffer.len())
            }
        } else {
            let read_file = self.files.read();
            trace!("reading from file");

            // very unsafe!
            // we need to cast the circuit buffer to a mutable slice of bytes
            // this can lead to undefined behaviour if e.g. the OperationType enum reads an invalid bit pattern
            // this should NOT be used to load operations between files
            // the exact bits are not guaranteed to be the same between operating systems, Rust versions, or even separate invocations of the program
            // this should ONLY be used to load operations that we saved in the exact same manner
            // and special care must be taken to ensure correct pointer alignment and seek positioning
            // otherwise, Bad Things can happen (the BEST case scenario is a segfault)

            debug_assert!(self.circuit_buffer.capacity() >= self.target_buffer_length);
            let buf = self.circuit_buffer.as_mut_ptr();

            let slice = unsafe {
                let buf_as_bytes: *mut u8 = buf as *mut _ as *mut u8;
                slice::from_raw_parts_mut(buf_as_bytes, self.target_buffer_length * mem::size_of::<Operation<B>>())
            };

            debug_assert!(slice.len() == mem::size_of::<Operation<B>>() * self.circuit_buffer.capacity());

            let bytes_read = read_file.read(slice).context("while filling buffer from file in FileOptimizer").unwrap();

            if bytes_read % mem::size_of::<Operation<B>>() != 0 {
                panic!("read in a number of bytes not compatible with operation size");
            }

            let operations_read = bytes_read / mem::size_of::<Operation<B>>();

            debug_assert!(operations_read <= self.target_buffer_length);

            unsafe {
                self.circuit_buffer.set_len(operations_read);
            }

            if operations_read == 0 {
                trace!("read 0");
                None
            } else {
                trace!("read {}", operations_read);
                Some(operations_read)
            }
        }
    }

    fn write_to_sink(&mut self) {
        let write_file = self.files.write();

        // on its own, this is less unsafe (the main thing is to get the slice length correct)
        // HOWEVER, it needs to be precisely correct for the above read function to be correct

        debug_assert!(self.circuit_buffer.capacity() >= self.target_buffer_length);
        let buf = self.circuit_buffer.as_ptr();

        trace!("writing {} ops to sink", self.circuit_buffer.len());

        let slice = unsafe {
            let buf_as_bytes: *const u8 = buf as *const _ as *const u8;
            slice::from_raw_parts(buf_as_bytes, self.circuit_buffer.len() * mem::size_of::<Operation<B>>())
        };

        debug_assert!(slice.len() == mem::size_of::<Operation<B>>() * self.circuit_buffer.len());

        let bytes_written = write_file.write(slice).unwrap();
        if bytes_written != slice.len() {
            panic!("could not write entire buffer");
        }
    }

    fn write_buf_to_sink(&mut self, buffer: &[Operation<B>]) {
        let write_file = self.files.write();

        // on its own, this is less unsafe (the main thing is to get the slice length correct)
        // HOWEVER, it needs to be precisely correct for the above read function to be correct

        let buf = buffer.as_ptr();

        let slice = unsafe {
            let buf_as_bytes: *const u8 = buf as *const _ as *const u8;
            slice::from_raw_parts(buf_as_bytes, buffer.len() * mem::size_of::<Operation<B>>())
        };

        debug_assert!(slice.len() == mem::size_of::<Operation<B>>() * buffer.len());

        let bytes_written = write_file.write(slice).unwrap();
        if bytes_written != slice.len() {
            panic!("could not write entire buffer");
        }
    }

    #[allow(dead_code)] // used in tests
    fn init_test(n_qubits: usize) -> Self {
        let file_a = tempfile::tempfile().unwrap();
        file_a.try_lock_exclusive().unwrap();

        let file_b = tempfile::tempfile().unwrap();
        file_b.try_lock_exclusive().unwrap();

        Self {
            n_qubits,
            target_buffer_length: 32,
            circuit_buffer: Vec::with_capacity(32),
            instructions: None,
            initial_circuit_length: None,
            post_reduction_length: None,
            latest_stats: None,
            files: ReadWriteSwap::new(file_a, file_b),
        }
    }
}


impl<Ops: Iterator<Item = Operation<B>> + Debug, B: Basis> Optimizer<B, Ops> for FileOptimizer<Ops, B> {
    fn new(n_qubits: usize, instructions: Ops, run_config: &RunConfig) -> anyhow::Result<Self> {
        let circuit_buffer = Vec::with_capacity(run_config.target_buffer_length);
        let reducer = OptimizeRotationsAdjacent::new(instructions);

        trace!("creating and locking tempfiles");

        let file_a = tempfile::tempfile()?;
        file_a.try_lock_exclusive()?;
        // let push_t_forward_meta = push_t_forward_file.metadata().context("while getting metadata on tempfile")?;

        let file_b = tempfile::tempfile()?;
        file_b.try_lock_exclusive()?;
        // let partition_file_meta = push_t_forward_file.metadata().context("while getting metadata on tempfile")?;

        trace!("files created");

        Ok(Self {
            n_qubits,
            target_buffer_length: run_config.target_buffer_length,
            circuit_buffer,
            initial_circuit_length: None,
            post_reduction_length: None,
            instructions: Some(reducer),
            latest_stats: None,
            files: ReadWriteSwap::new(file_a, file_b),
        })
    }

    fn initial_circuit_length(&self) -> Option<usize> {
        self.initial_circuit_length
    }

    fn post_reduction_length(&self) -> Option<usize> {
        self.post_reduction_length
    }

    fn latest_stats(&self) -> Option<Stats> {
        self.latest_stats
    }

    fn current_heap_usage(&self) -> (usize, usize) {
        let (used, alloc) = (self.circuit_buffer.len(), self.circuit_buffer.capacity());
        (used, alloc)
    }

    fn push_t_forward(&mut self) -> anyhow::Result<(bool, Stats)> {
        let mut changed = false;
        let mut stats = Stats::zero();

        let mut accumulator = Clifford::identity(self.n_qubits);
        let mut clifford_buf = Clifford::identity(self.n_qubits);

        // in a loop:
        // - fill the buffer from the current read source
        // - push T forward through the buffer
        // - write the result in the buffer to the current write sink
        while let Some(operations_read) = self.read_from_source() {
            stats.total_operations += operations_read;

            let mut out_index = 0;

            for op_index in 0..self.circuit_buffer.len() {
                debug_assert!(out_index <= op_index);
                let (did_change, was_t_gate, new_operation) = push_accumulator(&mut accumulator, &mut clifford_buf, &self.circuit_buffer[op_index]);
                changed |= did_change;
                if was_t_gate {
                    stats.t_gates += 1;
                }
                if let Some(new_operation) = new_operation {
                    self.circuit_buffer[out_index] = new_operation;
                    out_index += 1;
                }
            }

            self.circuit_buffer.truncate(out_index);
            self.write_to_sink();
        }

        self.files.swap();

        self.latest_stats = Some(stats);

        Ok((changed, stats))
    }

    fn partition(&mut self) -> anyhow::Result<(bool, Stats)> {
        debug_assert!(self.instructions.is_none());

        let mut last_partition = Vec::with_capacity(self.target_buffer_length);
        let mut changed = false;
        let mut stats = Stats::zero();
        // buffer writes to avoid many tiny syscalls
        let mut write_buf = Vec::with_capacity(self.target_buffer_length);
        let target_buffer_length = self.target_buffer_length;

        let update = |changed: &mut bool, last_partition: &mut Vec<Operation<B>>, write_buf: &mut Vec<Operation<B>>, this: &mut Self, stats: &mut Stats| {
            *changed |= reduce_rotations_no_ordering_slice(last_partition);
            for op in last_partition.iter() {
                if !op.is_nop() {
                    write_buf.push(op.clone());
                    stats.total_operations += 1;
                    if let Some(rot) = op.as_rotation() {
                        stats.t_gates += rot.angle.is_pi8() as usize;
                    }
                }
            }
            last_partition.clear();
            if write_buf.len() >= target_buffer_length {
                this.write_buf_to_sink(&write_buf);
                write_buf.clear();
            }
        }; 

        while let Some(_) = self.read_from_source() {
            'ops: for op_idx in 0..self.circuit_buffer.len() {
                if !self.circuit_buffer[op_idx].is_rotation() {
                    last_partition.push(self.circuit_buffer[op_idx].clone());
                    update(&mut changed, &mut last_partition, &mut write_buf, self, &mut stats);
                    continue 'ops;
                }

                let mut commutes_with_all = true;
                'commutation_check: for cmp in &last_partition {
                    if !cmp.commutes_with_likely(&self.circuit_buffer[op_idx]) {
                        commutes_with_all = false;
                        break 'commutation_check;
                    }
                }

                if !commutes_with_all {
                    update(&mut changed, &mut last_partition, &mut write_buf, self, &mut stats);
                }

                last_partition.push(self.circuit_buffer[op_idx].clone());
            }
        }

        if !last_partition.is_empty() {
            update(&mut changed, &mut last_partition, &mut write_buf, self, &mut stats);
        }
        self.write_buf_to_sink(&write_buf);

        self.files.swap();

        self.latest_stats = Some(stats);

        Ok((changed, stats))
    }

    fn write_to_output(mut self, mut output: impl Output) -> anyhow::Result<()> {
        while let Some(_) = self.read_from_source() {
            for op in &self.circuit_buffer {
                output.write_operation(self.n_qubits, op)?;
            }
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use std::marker::PhantomData;

    use rand::{rngs::SmallRng, SeedableRng};

    use super::*;

    use crate::basis::*;

    struct EmptyIter<B: Basis> {
        phantom: PhantomData<B>,
    }

    impl<B: Basis> EmptyIter<B> {
        #[allow(dead_code)]
        pub fn new() -> Self {
            Self {
                phantom: PhantomData { }
            }
        }
    }

    impl<B: Basis> Iterator for EmptyIter<B> {
        type Item = Operation<B>;
    
        fn next(&mut self) -> Option<Self::Item> {
            None
        }
    }

    impl<B: Basis> Debug for EmptyIter<B> {
        fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
            f.debug_struct("EmptyIter").field("phantom", &self.phantom).finish()
        }
    }

    fn test_rw<B: Basis>(n_qubits: usize, ops: &[Operation<B>]) {
        let mut opt = FileOptimizer::<EmptyIter<B>, B>::init_test(n_qubits);

        opt.write_buf_to_sink(ops);
        opt.files.swap();
        opt.read_from_source();

        assert_eq!(opt.circuit_buffer.len(), ops.len());

        for op_idx in 0..ops.len() {
            assert_eq!(ops[op_idx], opt.circuit_buffer[op_idx]);
        }

        // now, write fewer

        opt.write_buf_to_sink(&ops[0..(ops.len()/2)]);
        opt.files.swap();
        opt.read_from_source();
        assert_eq!(opt.circuit_buffer.len(), ops.len() / 2);
    }

    #[test]
    fn test_rw_b8() {
        let n_qubits = 8;

        let mut rng = SmallRng::seed_from_u64(123);

        let mut ops = vec![
            Operation::<Basis8>::rand(n_qubits, &mut rng),
        ];

        test_rw(n_qubits, &ops);

        for _ in 0..10 {
            ops.push(Operation::<Basis8>::rand(n_qubits, &mut rng));
        }

        test_rw(n_qubits, &ops);
    }
}