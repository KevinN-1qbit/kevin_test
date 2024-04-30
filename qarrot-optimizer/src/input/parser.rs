use std::io::Read;

use anyhow::{bail, Context};

use crate::{basis::Basis, operation::{angle::Angle, phase::Phase, Operation}};

use super::lexer::{TokenIterator, Token, Pauli};

// algorithm notes:
// the idea here is to try to read some number (the target buf size) of operations at once.
// this isn't always achievable (particularly in a repeat, where we need to keep around the entire repeated block to be able to iterate)
// the source is where we drain tokens from
// the operation buffer is where we're currently reading operations from
// the index is the index of the _next_ token to return
//
// if this is beyond the end of the buffer (index >= buffer len), we need to read more. cases:
// 
// (1) there are repeats remaining (repeats_remaining > 0)
// this means that we're in the middle of a repeat block
// decrement repeats_remaining and set index_in_operation_buf to 0
// (2) there are no repeats remaining
// this means that we've finished a block, either a repeat or non-repeat (doesn't matter)
// first, clear the buffer and set index_in_operation_buf to 0
// if shrink_buf_after_repeat, we compare the capacity (not size/len) of the current buffer
//   -> if larger than target, shrink it
//   (this lets us reduce memory usage outside of peak usage, at the cost of more allocations)
// read up to target_buf_size operations
// stop before that if:
//   (a) we find a repeat --- note to self: requires peeking
//   (b) we reach EOF
// continue more than that if the first block we read is a repeat

#[derive(Debug)]
pub struct InstructionIterator<R: Read, B: Basis> {
    source: TokenIterator<R>,
    target_buf_size: usize,
    shrink_after_repeat: bool,

    n_qubits: usize,

    // buffering, repeats
    operation_buf: Vec<Operation<B>>,
    index_in_operation_buf: usize,
    repeats_remaining: usize,
}


impl<R: Read, B: Basis> InstructionIterator<R, B> {
    pub fn new(n_qubits: usize, source: TokenIterator<R>, target_buf_size: usize, shrink_after_repeat: bool) -> Self {
        Self {
            source,
            target_buf_size,
            shrink_after_repeat,
            n_qubits,
            operation_buf: Vec::with_capacity(target_buf_size),
            index_in_operation_buf: 0,
            repeats_remaining: 0,
        }
    }

    pub fn prepend_repeat(&mut self, repeats: usize, op: Operation<B>) -> anyhow::Result<()> {
        if self.index_in_operation_buf != 0 || !self.operation_buf.is_empty() {
            panic!("Internal error: must prepend before reading from instruction iterator")
        }
        if repeats > 0 {
            self.read_repeat(repeats, Some(op)).context("while prepending repeat")?;
        }
        Ok(())
    }

    pub fn prepend_op(&mut self, op: Operation<B>) {
        if self.index_in_operation_buf != 0 || !self.operation_buf.is_empty() {
            panic!("Internal error: must prepend before reading from instruction iterator")
        }
        self.operation_buf.push(op);
    }

    fn read_next_chunk(&mut self) -> anyhow::Result<()> {
        self.index_in_operation_buf = 0;

        self.operation_buf.clear();

        let Some(first) = self.source.next() else {
            // all done, no more tokens
            return Ok(());
        };

        if self.shrink_after_repeat && (self.operation_buf.capacity() > self.target_buf_size) {
            self.operation_buf.shrink_to(self.target_buf_size);
        }

        match first {
            Token::Repeat(r) => {
                self.read_repeat(r as usize, None).context("while filling next chunk")?;
                return Ok(());
            },
            Token::End => {
                bail!("End found while not in repeat")
            },
            Token::Pauli(_) => {
                bail!("Internal error: Pauli found out of order")
            },
            Token::Rotate(a) => {
                let op = complete_rotation(self.n_qubits, &mut self.source, a.into())?;
                self.operation_buf.push(op);
            },
            Token::Measure(p) => {
                let op = complete_measurement(self.n_qubits, &mut self.source, p)?;
                self.operation_buf.push(op);
            },
        }
        // if we're here, we're not in a repeat
        // so we read until either we reach the target buffer size or until we find a repeat

        let mut op_count = 1;
        while op_count < self.target_buf_size {
            match self.source.peek().context("while filling parser buffer")? {
                None => break, // done
                Some(Token::Repeat(_)) => break, // read the repeat next time we fill the buffer,
                Some(Token::End) => panic!("error message here"),
                Some(_) => (), // read this now
            }
            let next = self.source.next().unwrap(); // can unwrap because we checked if it was none already
            let op = match next {
                Token::Measure(p) => complete_measurement(self.n_qubits, &mut self.source, p).unwrap(),
                Token::Rotate(a) => complete_rotation(self.n_qubits, &mut self.source, a.into()).unwrap(),
                _ => unreachable!()
            };
            op_count += 1;
            self.operation_buf.push(op);
        }

        Ok(())
    }

    fn read_repeat(&mut self, r: usize, prepend: Option<Operation<B>>) -> anyhow::Result<()> {
        self.repeats_remaining = r - 1;

        self.index_in_operation_buf = 0;

        self.operation_buf.clear();

        if let Some(op) = prepend {
            self.operation_buf.push(op);
        }

        if self.shrink_after_repeat && (self.operation_buf.capacity() > self.target_buf_size) {
            self.operation_buf.shrink_to(self.target_buf_size);
        }

        loop {
            match self.source.peek().context("while filling parser buffer (repeat)")? {
                None => bail!("unexpected end of file while in repeat block"),
                Some(Token::Repeat(_)) => bail!("found nested repeat block"),
                Some(Token::End) => {
                    // drop the token, but we're done
                    self.source.next().unwrap();
                    break;
                },
                Some(_) => (), // read this now
            }
            let next = self.source.next().unwrap(); // can unwrap because we checked if it was none already
            let op = match next {
                Token::Measure(p) => complete_measurement(self.n_qubits, &mut self.source, p).unwrap(),
                Token::Rotate(a) => complete_rotation(self.n_qubits, &mut self.source, a.into()).unwrap(),
                _ => unreachable!()
            };
            self.operation_buf.push(op);
        }

        Ok(())
    }

    pub fn next(&mut self) -> anyhow::Result<Option<&Operation<B>>> {
        if self.index_in_operation_buf < self.operation_buf.len() {
            self.index_in_operation_buf += 1;
            return Ok(Some(&self.operation_buf[self.index_in_operation_buf - 1]));
        }

        if self.repeats_remaining > 0 {
            // this means we are in a repeat block
            // go back to the start and decrement repeat counter
            self.repeats_remaining -= 1;
            self.index_in_operation_buf = 1;
            Ok(Some(&self.operation_buf[0]))
        } else {
            // we are not in a repeat block, or we just finished one
            // so now we need to read in the next chunk
            self.read_next_chunk().context("while fetching next operation")?;
            if self.operation_buf.is_empty() {
                Ok(None)
            } else {
                self.index_in_operation_buf += 1;
                Ok(self.operation_buf.first())
            }
        }
    }
}


impl<R: Read, B: Basis> Iterator for InstructionIterator<R, B> {
    type Item = Operation<B>;

    fn next(&mut self) -> Option<Self::Item> {
        self.next().map(|op| op.cloned()).unwrap()
    }
}


fn paulis<R: Read, B: Basis>(n_qubits: usize, source: &mut TokenIterator<R>) -> anyhow::Result<(B, B)> {
    let mut x = B::zero(n_qubits);
    let mut z = B::zero(n_qubits);

    for qb in 0..n_qubits {
        let Some(tok) = source.next() else {
            bail!("Unexpected EOF (only found {}/{} Paulis)", qb, n_qubits);
        };
        let Token::Pauli(p) = tok else {
            bail!("Unexpected token {:?} (only found {}/{} Paulis)", tok, qb, n_qubits);
        };
        if matches!(p, Pauli::X | Pauli::Y) {
            x.set_bit_true(qb);
        }
        if matches!(p, Pauli::Z | Pauli::Y) {
            z.set_bit_true(qb);
        }
    }

    Ok((x, z))
}

pub(crate) fn complete_measurement<R: Read, B: Basis>(n_qubits: usize, source: &mut TokenIterator<R>, phase: Phase) -> anyhow::Result<Operation<B>> {
    let (x, z) = paulis(n_qubits, source).context("while reading measurement")?;

    Ok(Operation::measurement(x, z, phase))
}

pub(crate) fn complete_rotation<R: Read, B: Basis>(n_qubits: usize, source: &mut TokenIterator<R>, angle: Angle) -> anyhow::Result<Operation<B>> {
    let (x, z) = paulis(n_qubits, source).context("while reading rotation")?;

    Ok(Operation::rotation(x, z, angle))
}

pub(crate) fn complete_op<B: Basis>(n_qubits: usize, tokens: &[Token]) -> anyhow::Result<Operation<B>> {
    if tokens.len() <= 1 {
        bail!("internal error: too few tokens given while building operation");
    }
    let mut x = B::zero(n_qubits);
    let mut z = B::zero(n_qubits);

    for qb in 0..n_qubits {
        let Some(tok) = tokens.get(qb + 1) else {
            bail!("Unexpected EOF (only found {}/{} Paulis)", qb, n_qubits);
        };
        let Token::Pauli(p) = tok else {
            bail!("Unexpected token {:?} (only found {}/{} Paulis)", tok, qb, n_qubits);
        };
        if matches!(p, Pauli::X | Pauli::Y) {
            x.set_bit_true(qb);
        }
        if matches!(p, Pauli::Z | Pauli::Y) {
            z.set_bit_true(qb);
        }
    }

    match tokens[0] {
        Token::Measure(phase) => {
            Ok(Operation::measurement(x, z, phase))
        }
        Token::Rotate(angle) => {
            Ok(Operation::rotation(x, z, angle.into()))
        }
        _ => bail!("Internal error: invalid token to start operation")
    }
}
