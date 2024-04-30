use std::{io::Read, collections::VecDeque};

use anyhow::{bail, Context};
use log::warn;

use crate::{basis::Basis, operation::{angle::Angle, Operation}};

use super::lexer::{TokenIterator, Token, FixedGate};


#[derive(Debug)]
pub struct InstructionIterator<R: Read, B: Basis> {
    source: TokenIterator<R>,
    buf_size: usize,

    n_qubits: usize,

    // buffering, repeats
    operation_buf: VecDeque<Operation<B>>,
}

fn qasm_to_rotations<B: Basis>(n_qubits: usize, gate: &FixedGate, qregs: &Vec<usize>, ops: &mut VecDeque<Operation<B>>) -> anyhow::Result<()> {

    match gate {
        FixedGate::H => {
            let x = B::zero(n_qubits);
            let mut z = B::zero(n_qubits);
            let angle = Angle::PlusPi4;
            z.set_bit_true(qregs[0]);
            ops.push_back(Operation::rotation(x, z, angle));

            let mut x = B::zero(n_qubits);
            let z = B::zero(n_qubits);
            let angle = Angle::PlusPi4;
            x.set_bit_true(qregs[0]);
            ops.push_back(Operation::rotation(x, z, angle));

            let x = B::zero(n_qubits);
            let mut z = B::zero(n_qubits);
            let angle = Angle::PlusPi4;
            z.set_bit_true(qregs[0]);
            ops.push_back(Operation::rotation(x, z, angle));
        },

        FixedGate::T => {
            let mut z = B::zero(n_qubits);
            let x = B::zero(n_qubits);
            let angle = Angle::PlusPi8;
            z.set_bit_true(qregs[0]);
            ops.push_back(Operation::rotation(x, z, angle));
        },

        FixedGate::Tdg => {
            let mut z = B::zero(n_qubits);
            let x = B::zero(n_qubits);
            let angle = Angle::MinusPi8;
            z.set_bit_true(qregs[0]);
            ops.push_back(Operation::rotation(x, z, angle));
        },

        FixedGate::S => {
            let mut z = B::zero(n_qubits);
            let x = B::zero(n_qubits);
            let angle = Angle::PlusPi4;
            z.set_bit_true(qregs[0]);
            ops.push_back(Operation::rotation(x, z, angle));
        },

        FixedGate::Sdg => {
            let mut z = B::zero(n_qubits);
            let x = B::zero(n_qubits);
            let angle = Angle::MinusPi4;
            z.set_bit_true(qregs[0]);
            ops.push_back(Operation::rotation(x, z, angle));
        },

        FixedGate::X => {
            let z = B::zero(n_qubits);
            let mut x = B::zero(n_qubits);
            let angle = Angle::Pi2;
            x.set_bit_true(qregs[0]);
            ops.push_back(Operation::rotation(x, z, angle));
        }

        FixedGate::Y => {
            let mut z = B::zero(n_qubits);
            let mut x = B::zero(n_qubits);
            let angle = Angle::Pi2;
            z.set_bit_true(qregs[0]);
            x.set_bit_true(qregs[0]);
            ops.push_back(Operation::rotation(x, z, angle));
        }

        FixedGate::Z => {
            let mut z = B::zero(n_qubits);
            let x = B::zero(n_qubits);
            let angle = Angle::Pi2;
            z.set_bit_true(qregs[0]);
            ops.push_back(Operation::rotation(x, z, angle));
        }

        FixedGate::Cx => {
            let mut x = B::zero(n_qubits);
            let mut z = B::zero(n_qubits);
            let angle = Angle::PlusPi4;
            z.set_bit_true(qregs[0]);
            x.set_bit_true(qregs[1]);
            ops.push_back(Operation::rotation(x, z, angle));
            
            let x = B::zero(n_qubits);
            let mut z = B::zero(n_qubits);
            let angle = Angle::MinusPi4;
            z.set_bit_true(qregs[0]);
            ops.push_back(Operation::rotation(x, z, angle));

            let mut x = B::zero(n_qubits);
            let z = B::zero(n_qubits);
            let angle = Angle::MinusPi4;
            x.set_bit_true(qregs[1]);
            ops.push_back(Operation::rotation(x, z, angle));
        }
    }
    return Ok(());

}


impl<R: Read, B: Basis> InstructionIterator<R, B> {
    pub fn new(n_qubits: usize, source: TokenIterator<R>, buf_size: usize) -> anyhow::Result<Self> {
        return Ok(Self {
            source,
            buf_size,
            n_qubits,
            operation_buf: VecDeque::with_capacity(buf_size),
        });
    }

    
    fn fill_buff(&mut self) -> anyhow::Result<()> {
        self.operation_buf.clear();

        while self.operation_buf.len() < self.buf_size {
            if let Some(first) = self.source.next() {
                match first {
                    Token::Version(_) => {
                        bail!("unexpected version statement");
                    },

                    Token::Include(_) => {
                        warn!("multiple includes found in OpenQASM file; ignoring");
                        continue
                    }

                    Token::QregDecl(_, _) => {
                        bail!("multiple qreg declarations found; not supported");
                    }

                    Token::FixedGate(gate, qregs) => {
                        qasm_to_rotations(self.n_qubits, &gate, &qregs, &mut self.operation_buf).unwrap();
                    }
                }
            } else {
                break
            }
        }
        
        return Ok(())
    }


    pub fn next(&mut self) -> anyhow::Result<Option<Operation<B>>> {
        if let Some(front) = self.operation_buf.pop_front() {
            return Ok(Some(front));
        } else {
            self.fill_buff().context("reading token iterator into buffer")?;
            if let Some(front) = self.operation_buf.pop_front() {
                return Ok(Some(front));
            } else {
                return Ok(None);
            }
        }

    }
}


impl<R: Read, B: Basis> Iterator for InstructionIterator<R, B> {
    type Item = Operation<B>;

    fn next(&mut self) -> Option<Self::Item> {
        self.next().unwrap()
    }
}


#[cfg(test)]
mod tests {
    use crate::basis::Basis16;

    use super::*;

    #[test]
    fn test_qasm_to_rotation() {
        let src = r#"
    OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[14];
    creg c[14];
    h q[1];
    t q[14];
    t q[12];
    t q[1];
    cx q[12],q[14];
    cx q[1],q[12];
"#;
        println!("{}", src);

        let mut lexer = TokenIterator::<_>::new(src.as_bytes());

        let mut seen_openqasm = false;
        let mut n_qubits = None;

        while let Some(tok) = lexer.next() {
            match tok {
                Token::Version(_) => {
                    seen_openqasm = true;
                },
                Token::Include(_) => (),
                Token::QregDecl(_, qubits) => {
                    n_qubits = Some(qubits);
                    break;
                },
                Token::FixedGate(_, _) => panic!("found OpenQASM gate before a qreg declaration"),
            }
        }

        if !seen_openqasm {
            panic!("missing OpenQASM version declaration");
        }

        let n_qubits = n_qubits.unwrap();
        assert_eq!(n_qubits, 14);

        let parser = InstructionIterator::<_, Basis16>::new(4, lexer, 32).unwrap();
        dbg!(&parser);

        let parsed: Vec<_> = parser.collect();
        dbg!(&parsed);

        assert_eq!(parsed.len(), 12);


    }
}
