use crate::basis::Basis;
use std::{fmt::Debug, ops::BitXorAssign};

#[derive(Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct Symplectic<B: Basis> {
    pub(crate) sign: bool,
    pub(crate) x: B,
    pub(crate) z: B,
}

impl<B: Basis> Debug for Symplectic<B> {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_fmt(format_args!("Symplectic {{ {} | {:?} | {:?} }}", self.sign as u8, self.x, self.z))
    }
}

impl<B: Basis> Symplectic<B> {
    pub fn dbg(&self, buf: &mut String, n_qubits: usize) {
        use std::fmt::Write;
        buf.write_fmt(format_args!("Symplectic{} {{ {} | 0b", self.x.bit_capacity(), self.sign as u8)).unwrap();
        for bit in 0..n_qubits {
            buf.write_char(if self.x.get_bit(bit) {
                '1'
            } else {
                '0'
            }).unwrap();
        }
        buf.write_str(" | 0b").unwrap();
        for bit in 0..n_qubits {
            buf.write_char(if self.z.get_bit(bit) {
                '1'
            } else {
                '0'
            }).unwrap();
        }
        buf.write_str(" }").unwrap();
    }

    pub fn dbg_out(&self, n_qubits: usize) -> String {
        let mut buf = String::with_capacity(128);
        self.dbg(&mut buf, n_qubits);
        buf
    }

    pub fn count_i(&self) -> usize {
        self.x
            .and(&self.z)
            .popcnt()
    }

    pub fn zero(n_qubits: usize) -> Self {
        Self {
            sign: false,
            x: B::zero(n_qubits),
            z: B::zero(n_qubits),
        }
    }

    pub fn set_zero(&mut self) {
        self.sign = false;
        self.x.set_zero();
        self.z.set_zero();
    }

    pub fn from_indexes(n_qubits: usize, sign: bool, x_i: &[usize], z_i: &[usize]) -> Self {
        let mut x = B::zero(n_qubits);
        let mut z = B::zero(n_qubits);

        for i in x_i {
            x.set_bit_true(*i);
        }

        for i in z_i {
            z.set_bit_true(*i);
        }

        Self {
            sign,
            x,
            z,
        }
    }

    pub fn from_bitstring(n_qubits: usize, sign: u8, x: &str, z: &str) -> Self {
        let mut new = Self::zero(n_qubits);
        new.sign = sign > 0;

        for i in 0..n_qubits {
            let x_i = x.as_bytes()[i];
            if x_i == '1' as u8 {
                new.x.set_bit_true(i);
            }

            let z_i = z.as_bytes()[i];
            if z_i == '1' as u8 {
                new.z.set_bit_true(i);
            }
        }

        new
    }

    pub fn commutes_with(&self, rhs: &Self) -> bool {
        (self.z.and(&rhs.x).popcnt() + self.x.and(&rhs.z).popcnt()) % 2 == 0
    }

    // only valid when they don't commute
    pub fn mul_by(&mut self, rhs: &Self) {
        let p_i = self.count_i();
        let q_i = rhs.count_i();

        let theta_c = ((
            self.z.and(&rhs.x).popcnt() + // | x_z & z_x | +
            rhs.x.and(&self.z).and(&rhs.z).and(&self.x).popcnt() // | x_x & z_z & x_z & z_x |
        ) % 2) != 0; // % 2

        *self ^= rhs;

        let mut phase_sum = (p_i + q_i + 1) as isize;
        phase_sum -= self.count_i() as isize;
        phase_sum = phase_sum.abs();
        debug_assert!(phase_sum % 2 == 0);
        phase_sum /= 2;

        self.sign ^= phase_sum != 0;
        self.sign ^= theta_c;
    }

    pub fn mul(&self, rhs: &Self) -> Self {
        let mut new = self.clone();
        new.mul_by(rhs);
        new
    }
}

impl<'a, B: Basis> BitXorAssign<&'a Symplectic<B>> for Symplectic<B> {
    fn bitxor_assign(&mut self, rhs: &'a Symplectic<B>) {
        self.sign.bitxor_assign(rhs.sign);
        self.x.bitxor_assign(&rhs.x);
        self.z.bitxor_assign(&rhs.z);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::basis::{*};

    fn test_multiplication<B: Basis>(qbits: usize, spread: usize) {
        // XZIIXXZZ
        let test_1 = Symplectic::<B>::from_indexes(qbits, false, &[0 * spread, 4 * spread, 5 * spread], &[1 * spread, 6 * spread, 7 * spread]);
        // IIXZXZXZ
        let test_2 = Symplectic::<B>::from_indexes(qbits, false, &[2 * spread, 4 * spread, 6 * spread], &[3 * spread, 5 * spread, 7 * spread]);

        if !test_1.commutes_with(&test_2) {
            let res = test_1.mul(&test_2);
            dbg!(&res);
            assert_eq!(res, Symplectic::from_indexes(8, false, &[0, 2, 5, 6], &[1, 3, 5, 6]));
        }
    }

    #[test]
    fn test_multiplication_8() {
        test_multiplication::<Basis8>(8, 1);
    }

    #[test]
    fn test_multiplication_16() {
        test_multiplication::<Basis16>(16, 2);
    }

    #[test]
    fn test_multiplication_32() {
        test_multiplication::<Basis32>(32, 4);
    }

    #[test]
    fn test_multiplication_64() {
        test_multiplication::<Basis64>(64, 8);
    }

    #[test]
    fn test_multiplication_128() {
        test_multiplication::<Basis128>(128, 16);
    }

    // #[test]
    // fn test_multiplication_dyn() {
    //     test_multiplication::<DBasis>(256, 32);
    // }

    // #[test]
    // fn test_XZ() {
    //     let mut x_basis = Basis8::zero(1);
    //     x_basis.set_bit(0, true);
    //     let x = Symplectic {
    //         sign: false,
    //         x: x_basis,
    //         z: Basis8::zero(1)
    //     };
    //     let z = Symplectic {
    //         sign: false,
    //         x: Basis8::zero(1),
    //         z: x_basis,
    //     };
    //     let xz = x.mul(&z, 1);
    //     // panic!("{:?}", xz);

    //     let zx = z.mul(&x, 1);
    //     // panic!("{:?}", zx);
    // }
}
