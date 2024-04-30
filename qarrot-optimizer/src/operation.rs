use crate::{basis::Basis, output::fmt_operation};

pub mod angle;
pub mod phase;
use angle::Angle;
use phase::Phase;
use rand::Rng;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum OperationKind {
    Nop,
    Measurement {
        phase: Phase,
    },
    Rotation {
        angle: Angle,
    },
}


impl OperationKind {
    pub fn is_measurement(&self) -> bool {
        matches!(self, Self::Measurement { phase: _ })
    }

    pub fn is_rotation(&self) -> bool {
        matches!(self, Self::Rotation { angle: _ })
    }
}


#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Measurement<'a, B: Basis> {
    pub this: &'a Operation<B>,
    pub phase: &'a Phase,
}


#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Rotation<'a, B: Basis> {
    pub this: &'a Operation<B>,
    pub angle: &'a Angle,
}


impl<'a, B: Basis> Rotation<'a, B> {
    pub fn is_identity(&self) -> bool {
        (self.this.x.popcnt() == 0) & (self.this.z.popcnt() == 0)
    }
}


#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Operation<B: Basis> {
    pub x: B,
    pub z: B,
    pub kind: OperationKind,
}


#[derive(Copy, Clone, PartialEq, Eq, Debug, Hash)]
pub enum Pauli {
    X = 0b01,
    Z = 0b10,
    Y = 0b11,
}

impl Pauli {
    pub fn has_x(&self) -> bool {
        !matches!(self, Pauli::Z)
    }

    pub fn has_z(&self) -> bool {
        !matches!(self, Pauli::X)
    }
}


pub fn basis<B: Basis>(n_qubits: usize, qubit: usize, pauli: Pauli) -> (B, B) {
    let x = if pauli.has_x() {
        B::bit_k(n_qubits, qubit)
    } else {
        B::zero(n_qubits)
    };

    let z = if pauli.has_z() {
        B::bit_k(n_qubits, qubit)
    } else {
        B::zero(n_qubits)
    };

    (x, z)
}


impl<B: Basis> Operation<B> {
    pub fn measurement(x: B, z: B, phase: Phase) -> Self {
        Self {
            x, z,
            kind: OperationKind::Measurement { phase }
        }
    }

    pub fn rotation(x: B, z: B, angle: Angle) -> Self {
        Self {
            x, z, 
            kind: OperationKind::Rotation { angle }
        }
    }

    #[inline(always)]
    pub fn is_identity(&self) -> bool {
        (self.x.popcnt() == 0) && (self.z.popcnt() == 0) && !matches!(self.kind, OperationKind::Nop)
    }

    #[inline(always)]
    pub fn is_nop(&self) -> bool {
        matches!(self.kind, OperationKind::Nop)
    }

    pub fn is_measurement(&self) -> bool {
        self.kind.is_measurement()
    }

    pub fn is_rotation(&self) -> bool {
        self.kind.is_rotation()
    }

    #[inline(always)]
    pub fn set_nop(&mut self) {
        self.kind = OperationKind::Nop;
    }

    #[inline(always)]
    pub fn commutes_with(&self, rhs: &Self) -> bool {
        (self.z.and(&rhs.x).popcnt() + self.x.and(&rhs.z).popcnt()) % 2 == 0
        // !(self.z.and(&rhs.x).parity() ^ self.x.and(&rhs.z).parity())
    }

    #[inline(always)]
    pub fn commutes_with_likely(&self, rhs: &Self) -> bool {
        let zx = self.z.and(&rhs.x);
        let xz = self.x.and(&rhs.z);
        // fast return if they don't share a basis (or are identity)
        if xz.is_zero() && zx.is_zero() {
            return true;
        }
        (zx.popcnt() + xz.popcnt()) % 2 == 0
    }

    pub fn as_measurement(&self) -> Option<Measurement<'_, B>> {
        match &self.kind {
            OperationKind::Measurement { phase } => Some(Measurement {
                this: self,
                phase,
            }),
            _ => None,
        }
    }

    pub fn as_rotation(&self) -> Option<Rotation<'_, B>> {
        match &self.kind {
            OperationKind::Rotation { angle } => Some(Rotation {
                this: self,
                angle,
            }),
            _ => None,
        }
    }

    pub fn pauli_angle(pauli: Pauli, angle: Angle, n_qubits: usize, qubit: usize) -> Self {
        let (x, z) = basis::<B>(n_qubits, qubit, pauli);
        Self {
            x, z, kind: OperationKind::Rotation { angle }
        }
    }

    pub fn pretty_print(&self) {
        if let Some(measurement) = self.as_measurement() {
            // todo: speed this up
            // this will be slow; Rust doesn't buffer printing by default
            print!("Measurement {{ x: ");
            self.x.pretty_print();
            print!(", z: ");
            self.z.pretty_print();
            print!(", phase: {:?} }}", measurement.phase);
            return;
        }
        let rotation = self.as_rotation().unwrap();
        print!("Rotation {{ x: ");
        self.x.pretty_print();
        print!(", z: ");
        self.z.pretty_print();
        print!(", angle: {:?} }}", rotation.angle);
    }

    pub fn as_string(&self, n_qubits: usize) -> String {
        let mut buf = String::new();
        fmt_operation(&mut buf, n_qubits, &self).unwrap();
        buf.pop();
        buf
    }

    pub fn rand(n_qubits: usize, rng: &mut impl Rng) -> Self {
        if rng.gen() {
            Self::measurement(
                B::rand(n_qubits, rng),
                B::rand(n_qubits, rng),
                if rng.gen() { Phase::Negative } else { Phase::Positive },
            )
        } else {
            Self::rotation(
                B::rand(n_qubits, rng),
                B::rand(n_qubits, rng),
                Angle::rand(rng),
            )
        }
    }
}
