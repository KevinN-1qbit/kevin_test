use std::{collections::BTreeSet, io};

use crate::{basis::Basis, input::{lexer::TokenIterator, parser::InstructionIterator}, symplectic::Symplectic};


#[derive(Debug)]
pub struct Tester<'a, R: io::Read, B: Basis> {
    n_qubits: usize,
    cmp: InstructionIterator<R, B>,
    this: InstructionIterator<&'a [u8], B>,
    reference_set: BTreeSet<Symplectic<B>>,
    this_set: BTreeSet<Symplectic<B>>,
    counter: usize,
}


impl<'a, R: io::Read, B: Basis> Tester<'a, R, B> {
    pub fn new(cmp: R, this: &'a [u8], n_qubits: usize) -> Self {
        Self {
            n_qubits,
            cmp: InstructionIterator::new(n_qubits, TokenIterator::new(cmp), 1024, false),
            this: InstructionIterator::new(n_qubits, TokenIterator::new(this), 1024, false),
            reference_set: BTreeSet::new(),
            this_set: BTreeSet::new(),
            counter: 0,
        }
    }
}

fn dbg_out<B: Basis>(set: &BTreeSet<Symplectic<B>>, n_qubits: usize) -> String {
    use std::fmt::Write;

    let mut buf = String::with_capacity(1024);
    buf.write_str("BTreeSet { \n").unwrap();
    for (_i, element) in set.iter().enumerate() {
        buf.write_char('\t').unwrap();
        element.dbg(&mut buf, n_qubits);
        buf.write_str(",\n").unwrap();
    }

    buf.write_str(" }").unwrap();

    buf
}


impl<'a, R: io::Read, B: Basis> Tester<'a, R, B> {
    fn finalize_sets(&mut self) {
        if self.this_set != self.reference_set {
            panic!("Divergence in pi/8 rotations found before line {}. The difference is between {} (remaining reference) and {} (remaining program output)", self.counter, dbg_out(&self.reference_set, self.n_qubits), dbg_out(&self.this_set, self.n_qubits));
        }
    }

    // returns is_done
    pub fn test_next(&mut self) -> bool {
        let reference = self.cmp.next().unwrap();
        let this = self.this.next().unwrap();
        self.counter += 1;

        if reference.is_none() && this.is_none() {
            self.finalize_sets();
            return true;
        }
        let Some(reference) = reference else {
            panic!("The reference source contains fewer lines than the program output (divergence at line {})", self.counter);
        };
        let Some(this) = this else {
            panic!("The reference source contains more lines than the program output (divergence at line {})", self.counter);
        };

        // if one is a rotation, both should be
        if let Some(reference_r) = reference.as_rotation() {
            let Some(this_r) = this.as_rotation() else {
                panic!("At line {}: should be {} but was {}.", self.counter, reference.as_string(self.n_qubits), this.as_string(self.n_qubits));
            };

            if reference_r.angle.is_pi8() && this_r.angle.is_pi8() {
                let reference_s = Symplectic {
                    sign: reference_r.angle.sign_bit(),
                    x: reference_r.this.x.clone(),
                    z: reference_r.this.z.clone(),
                };

                let this_s = Symplectic {
                    sign: this_r.angle.sign_bit(),
                    x: this_r.this.x.clone(),
                    z: this_r.this.z.clone(),
                };

                if self.this_set.is_empty() && self.reference_set.is_empty() {
                    if this_s == reference_s {
                        return false;
                    }
                    self.this_set.insert(this_s);
                    self.reference_set.insert(reference_s);
                    return false;
                }

                let mut reference_commutes_with_all = true;
                'commute_check: for op in &self.reference_set {
                    if !reference_s.commutes_with(op) {
                        reference_commutes_with_all = false;
                        break 'commute_check;
                    }
                }

                let mut this_commutes_with_all = true;
                'commute_check: for op in &self.this_set {
                    if !this_s.commutes_with(op) {
                        this_commutes_with_all = false;
                        break 'commute_check;
                    }
                }

                if reference_commutes_with_all && this_commutes_with_all {
                    if self.this_set.contains(&reference_s) {
                        self.this_set.remove(&reference_s);
                    } else {
                        self.reference_set.insert(reference_s);
                    }

                    if self.reference_set.contains(&this_s) {
                        self.reference_set.remove(&this_s);
                    } else {
                        self.this_set.insert(this_s);
                    }
                } else if reference_commutes_with_all || this_commutes_with_all {
                    let ref_fmt = reference_s.dbg_out(self.n_qubits);
                    let this_fmt = this_s.dbg_out(self.n_qubits);
                    panic!(
                        "Divergence in pi/8 rotations (commutes {}|{} r|t) found before line {}. The difference is between {} (remaining reference) and {} (remaining program output) with {} (reference) and {} (actual) not added.",
                        reference_commutes_with_all as u8, this_commutes_with_all as u8,
                        self.counter, dbg_out(&self.reference_set, self.n_qubits), dbg_out(&self.this_set, self.n_qubits), ref_fmt, this_fmt);
                } else {
                    if self.this_set != self.reference_set {
                        panic!("Divergence in pi/8 rotations (neither commutes) found before line {}. The difference is between {} (remaining reference) and {} (remaining program output)", self.counter, dbg_out(&self.reference_set, self.n_qubits), dbg_out(&self.this_set, self.n_qubits));
                    }
                    self.this_set.clear();
                    self.reference_set.clear();
                    self.this_set.insert(this_s);
                    self.reference_set.insert(reference_s);
                }
            } else if reference_r.angle.is_pi8() || this_r.angle.is_pi8() {
                panic!("At line {}: should be `{}` but was `{}`.", self.counter, reference.as_string(self.n_qubits), this.as_string(self.n_qubits));
            } else {
                // horrible hack, oops
                // but the whole state is in self so we can't hold these references past the call to finalize_sets
                let fmt = format!("At line {}: should be `{}` but was `{}`.", self.counter, reference.as_string(self.n_qubits), this.as_string(self.n_qubits));
                let do_panic = reference_r != this_r;
                self.finalize_sets();

                if do_panic {
                    panic!("{}", fmt);
                }
            }
        } else {
            let reference_m = reference.as_measurement().unwrap();
            let Some(this_m) = this.as_measurement() else {
                panic!("At line {}: should be `{}` but was `{}`.", self.counter, reference.as_string(self.n_qubits), this.as_string(self.n_qubits));
            };

            let fmt = format!("At line {}: should be `{}` but was `{}`.", self.counter, reference.as_string(self.n_qubits), this.as_string(self.n_qubits));
            let do_panic = reference_m != this_m;

            self.finalize_sets();

            if do_panic {
                panic!("{}", fmt);
            }
        }

        false
    }

    pub fn test_all(&mut self) {
        while !self.test_next() {}
    }
}
