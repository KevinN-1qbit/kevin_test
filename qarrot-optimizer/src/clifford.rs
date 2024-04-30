use std::{fmt::Debug, ops::{BitXorAssign, MulAssign}};

use crate::{basis::Basis, symplectic::Symplectic};


#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Clifford<B: Basis> {
    x_rows: Vec<Symplectic<B>>,
    z_rows: Vec<Symplectic<B>>,
    n_qubits: usize,
}


impl<B: Basis> Clifford<B> {
    pub fn identity(n_qubits: usize) -> Self {
        let mut new = Clifford {
            x_rows: Vec::with_capacity(n_qubits),
            z_rows: Vec::with_capacity(n_qubits),
            n_qubits
        };

        for i in 0..n_qubits {
            let mut x = Symplectic { sign: false, x: B::zero(n_qubits), z: B::zero(n_qubits) };
            let mut z = x.clone();

            x.x.set_bit_true(i);
            z.z.set_bit_true(i);

            new.x_rows.push(x);
            new.z_rows.push(z);
        }

        new
    }

    pub fn set_identity(&mut self) {
        for (i, row) in self.x_rows.iter_mut().enumerate() {
            row.set_zero();
            row.x.set_bit_true(i);
        }

        for (i, row) in self.z_rows.iter_mut().enumerate() {
            row.set_zero();
            row.z.set_bit_true(i);
        }
    }

    pub fn set_to(&mut self, other: &Self) {
        debug_assert!(self.n_qubits == other.n_qubits);

        for (i, row) in self.x_rows.iter_mut().enumerate() {
            *row = other.x_rows[i].clone();
        }

        for (i, row) in self.z_rows.iter_mut().enumerate() {
            *row = other.z_rows[i].clone();
        }
    }

    #[inline(always)]
    fn _conj(rows: &[Symplectic<B>], n_qubits: usize, old: &B) -> (Symplectic<B>, usize) {
        // let zero = Symplectic::zero(n_qubits);
        let mut ans: Symplectic<B> = Symplectic::zero(n_qubits);
        let mut i_count = 0;

        // let mut current_y = B::zero(n_qubits);

        for i in 0..n_qubits {
            if !old.get_bit(i) {
                continue; // worth reprofiling on x86, surprising to me that popcnt is so expensive
            }
            let xor_with = &rows[i];

            i_count += xor_with.x.and(&xor_with.z).popcnt();
            let n_commutations = ans.z.and(&xor_with.x).popcnt();
            i_count += 2 * n_commutations;
            ans.bitxor_assign(xor_with);
        }

        (ans, i_count)
    }

    pub fn conjugate(&self, sign: bool, x: &B, z: &B) -> Symplectic<B> {
        let n_i_i = x.and(z).popcnt(); // | x & z |

        let (new_x, new_x_i) = Self::_conj(&self.x_rows, self.n_qubits, x);
        let (new_z, new_z_i) = Self::_conj(&self.z_rows, self.n_qubits, z);

        let theta_c = ((
            new_x.z.and(&new_z.x).popcnt() // | x_z & z_x | +
            // new_x.x.and(&new_z.z).and(&new_x.z).and(&new_z.x).popcnt(self.n_qubits) // | x_x & z_z & x_z & z_x |
        ) % 2) != 0; // % 2
        let n_i_m = new_x_i + new_z_i;

        let mut new = new_x;
        new ^= &new_z;

        let n_i_f = new.count_i();
        let n_diff = (n_i_i as isize + n_i_m as isize - n_i_f as isize).abs();
        debug_assert!(n_diff % 2 == 0);
        let theta_i = (n_diff / 2) % 2 != 0;

        new.sign ^= theta_c;
        new.sign ^= theta_i;
        new.sign ^= sign;

        new
    }

    pub fn from_pi4(&mut self, sign: bool, x: &B, z: &B) {
        self.set_identity();

        let input = Symplectic { sign, x: x.clone(), z: z.clone() };

        for row in self.x_rows.iter_mut() {
            if !row.commutes_with(&input) {
                // row.mul_by(&input, self.n_qubits);
                let mul = input.mul(row);
                *row = mul;
            }
        }

        for row in self.z_rows.iter_mut() {
            if !row.commutes_with(&input) {
                // row.mul_by(&input, self.n_qubits);
                let mul = input.mul(row);
                *row = mul;
            }
        }
    }

    pub fn from_pi2(&mut self, sign: bool, x: &B, z: &B) {
        self.set_identity();

        let input = Symplectic { sign, x: x.clone(), z: z.clone() };

        for row in self.x_rows.iter_mut() {
            if !row.commutes_with(&input) {
                row.sign = true;
            }
        }

        for row in self.z_rows.iter_mut() {
            if !row.commutes_with(&input) {
                row.sign = true;
            }
        }
    }
}


impl<B: Basis> MulAssign<&Clifford<B>> for Clifford<B> {
    fn mul_assign(&mut self, rhs: &Clifford<B>) {
        for row in self.x_rows.iter_mut() {
            *row = rhs.conjugate(row.sign, &row.x, &row.z);
        }
        for row in self.z_rows.iter_mut() {
            *row = rhs.conjugate(row.sign, &row.x, &row.z);
        }
    }
}


#[cfg(test)]
mod tests {
    use rand::{rngs::SmallRng, Rng, SeedableRng};

    use crate::basis::{Basis128, Basis16, Basis8};

    use super::*;
    
    #[test]
    fn test_conj_identity() {
        let mut rng = SmallRng::seed_from_u64(1234);

        let mut rots = vec![
            Symplectic {
                sign: false,
                x: Basis8::zero(8),
                z: Basis8::zero(8),
            },
            Symplectic {
                sign: true,
                x: Basis8::one(8),
                z: Basis8::one(8),
            },
        ];

        let mut y = Basis8::zero(8);
        y.set_bit(0, true);

        rots.push(
            Symplectic { sign: true, x: y.clone(), z: y }
        );

        for _ in 0..64 {
            rots.push(Symplectic {
                sign: rng.gen(),
                x: Basis8::rand(8, &mut rng),
                z: Basis8::rand(8, &mut rng),
            })
        }

        let ident = Clifford::identity(8);
        for p in &rots {
            println!("-----------\nConjugating {:?}", p);
            let res = ident.conjugate(p.sign, &p.x, &p.z);
            dbg!(&res);
            assert_eq!(res.sign, p.sign);
            assert_eq!(res.x, p.x);
            assert_eq!(res.z, p.z);
        }
    }

    #[test]
    fn test_build_pi4() {
        // just tests that we don't panic

        let mut rng = SmallRng::seed_from_u64(13579);
        let mut clifford = Clifford::identity(8);
        for _ in 0..128 {
            let pi4 = Symplectic {
                sign: rng.gen(),
                x: Basis8::rand(8, &mut rng),
                z: Basis8::rand(8, &mut rng),
            };

            clifford.from_pi4(pi4.sign, &pi4.x, &pi4.z);
        }
    }

    #[test]
    fn test_mul_ident() {
        let ident = Clifford::identity(128);
        let mut pi4 = Clifford::identity(128);
        let mut out;
        let mut rng = SmallRng::seed_from_u64(2468);
        for _ in 0..128 {
            let sign = rng.gen();
            let x = Basis128::rand(128, &mut rng);
            let z = Basis128::rand(128, &mut rng);
            pi4.from_pi4(sign, &x, &z);
            out = pi4.clone();
            out *= &ident;

            assert_eq!(&out, &pi4);
        }
    }

    #[test]
    fn test_dbg() {
        let mut clifford: Clifford<Basis16> = Clifford::identity(9);
        clifford.x_rows[0] = Symplectic::from_bitstring(9, 1, "1000000000000000", "1001000000000000");
        clifford.x_rows[1] = Symplectic::from_bitstring(9, 0, "0000000000000000", "0110110000000000");
        clifford.x_rows[2] = Symplectic::from_bitstring(9, 0, "0110000000000000", "0110110000000000");
        clifford.x_rows[3] = Symplectic::from_bitstring(9, 0, "0000110010000000", "0001101000000000");
        clifford.x_rows[4] = Symplectic::from_bitstring(9, 1, "0101010010000000", "1110011000000000");
        clifford.x_rows[5] = Symplectic::from_bitstring(9, 1, "0100010010000000", "0110100010000000");
        clifford.x_rows[6] = Symplectic::from_bitstring(9, 1, "0001000100000000", "1000100100000000");
        clifford.x_rows[7] = Symplectic::from_bitstring(9, 1, "0000111010000000", "0000001100000000");
        clifford.x_rows[8] = Symplectic::from_bitstring(9, 0, "0000000000000000", "0000010010000000");
        
        clifford.z_rows[0] = Symplectic::from_bitstring(9, 0, "0000000000000000", "1000000000000000");
        clifford.z_rows[1] = Symplectic::from_bitstring(9, 0, "0100000000000000", "0010110000000000");
        clifford.z_rows[2] = Symplectic::from_bitstring(9, 0, "0000000000000000", "0010000000000000");
        clifford.z_rows[3] = Symplectic::from_bitstring(9, 0, "0001110010000000", "1001101000000000");
        clifford.z_rows[4] = Symplectic::from_bitstring(9, 0, "0001001100000000", "1000000100000000");
        clifford.z_rows[5] = Symplectic::from_bitstring(9, 0, "0001001100000000", "1000110100000000");
        clifford.z_rows[6] = Symplectic::from_bitstring(9, 1, "0000000100000000", "0000001000000000");
        clifford.z_rows[7] = Symplectic::from_bitstring(9, 0, "0001000000000000", "1000100000000000");
        clifford.z_rows[8] = Symplectic::from_bitstring(9, 0, "0001001110000000", "1000110100000000");

        dbg!(&clifford);
        let measurement: Symplectic<Basis16> = Symplectic::from_bitstring(9, 1, "0000110110000000", "0000010000000000");

        let result = clifford.conjugate(measurement.sign, &measurement.x, &measurement.z);

        assert!(!result.sign);
    }
}