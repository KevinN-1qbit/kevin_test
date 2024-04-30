use super::*;
use super::bit_traits::*;
use std::{cmp, fmt, ops::*};

// little-endian
// this should ideally be replaced by an impl using AVX2 on x86
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(align(32))] // align to 256 bits
pub struct Bits256 {
    bits: [u64; 4],
}


impl Bits256 {
    #[inline(always)]
    pub const fn new(bits: [u64; 4]) -> Self {
        Self {
            bits
        }
    }
}


impl PartialOrd for Bits256 {
    #[inline(always)]
    fn partial_cmp(&self, other: &Self) -> Option<std::cmp::Ordering> {
        Some(self.cmp(other))
    }
}


impl Ord for Bits256 {
    #[inline(always)]
    fn cmp(&self, other: &Self) -> std::cmp::Ordering {
        self.bits[3].cmp(&other.bits[3])
            .then(self.bits[2].cmp(&other.bits[2]))
            .then(self.bits[1].cmp(&other.bits[1]))
            .then(self.bits[0].cmp(&other.bits[0]))
    }
}


impl fmt::Binary for Bits256 {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        fmt::Binary::fmt(&self.bits[0], f)?;
        fmt::Binary::fmt(&self.bits[1], f)?;
        fmt::Binary::fmt(&self.bits[2], f)?;
        fmt::Binary::fmt(&self.bits[3], f)
    }
}


impl Not for Bits256 {
    type Output = Self;

    fn not(self) -> Self::Output {
        let mut new = self;
        new.lneg();
        new
    }
}


impl LNeg for Bits256 {
    fn lneg(&mut self) {
        self.bits[0].lneg();
        self.bits[1].lneg();
        self.bits[2].lneg();
        self.bits[3].lneg();
    }
}


macro_rules! impl_binary {
    ($trait:ident, $op:ident) => {
        impl $trait for Bits256 {
            type Output = Self;

            #[inline(always)]
            fn $op(self, rhs: Self) -> Self::Output {
                Self {
                    bits: [
                        self.bits[0].$op(rhs.bits[0]),
                        self.bits[1].$op(rhs.bits[1]),
                        self.bits[2].$op(rhs.bits[2]),
                        self.bits[3].$op(rhs.bits[3]),
                    ]
                }
            }
        }
    };
    (assign $trait:ident, $op:ident) => {
        impl $trait for Bits256 {
            #[inline(always)]
            fn $op(&mut self, rhs: Self) {
                self.bits[0].$op(rhs.bits[0]);
                self.bits[1].$op(rhs.bits[1]);
                self.bits[2].$op(rhs.bits[2]);
                self.bits[3].$op(rhs.bits[3]);
            }
        }

        impl<'a> $trait<&'a Self> for Bits256 {
            #[inline(always)]
            fn $op(&mut self, rhs: &Self) {
                self.bits[0].$op(rhs.bits[0]);
                self.bits[1].$op(rhs.bits[1]);
                self.bits[2].$op(rhs.bits[2]);
                self.bits[3].$op(rhs.bits[3]);
            }
        }
    };
}


impl_binary!(BitAnd, bitand);
impl_binary!(BitOr, bitor);
impl_binary!(BitXor, bitxor);
impl_binary!(assign BitAndAssign, bitand_assign);
impl_binary!(assign BitOrAssign, bitor_assign);
impl_binary!(assign BitXorAssign, bitxor_assign);
// impl_binary!(assign ref RefAnd, and);
// impl_binary!(assign ref RefOr, or);
// impl_binary!(assign ref RefXor, xor);


#[inline(always)]
fn clamping_sub<B: Sub<Output = B> + Ord + Copy>(a: B, b: B) -> B {
    a - cmp::min(a, b)
}


impl Bits for Bits256 {
    const BITS: usize = 256;

    const ZERO: Self = Self::new([0; 4]);

    const ONE: Self = Self::new([1, 0, 0, 0]);

    const MAX: Self = Self::new([u64::MAX; 4]);

    const SIZE_DESCRIPTOR: &'static str = "static 256";

    fn mask_first_k(k: usize) -> Self {
        Self {
            bits: [
                u64::mask_first_k(cmp::min(clamping_sub(k, 3 * 64), 64)),
                u64::mask_first_k(cmp::min(clamping_sub(k, 2 * 64), 64)),
                u64::mask_first_k(cmp::min(clamping_sub(k, 1 * 64), 64)),
                u64::mask_first_k(cmp::min(k, 64))
            ]
        }
    }

    fn mask_not_last_k(k: usize) -> Self {
        Self {
            bits: [
                u64::mask_not_last_k(cmp::min(clamping_sub(k, 3 * 64), 64)),
                u64::mask_not_last_k(cmp::min(clamping_sub(k, 2 * 64), 64)),
                u64::mask_not_last_k(cmp::min(clamping_sub(k, 1 * 64), 64)),
                u64::mask_not_last_k(cmp::min(k, 64))
            ]
        }
    }

    fn bit_k(k: usize) -> Self {
        Self {
            bits: [
                u64::bit_k(cmp::min(clamping_sub(k, 3 * 64), 63)) & u64::splat((k >= 3 * 64) & (k < (4*64))),
                u64::bit_k(cmp::min(clamping_sub(k, 2 * 64), 63)) & u64::splat((k >= 2 * 64) & (k < (3*64))),
                u64::bit_k(cmp::min(clamping_sub(k, 1 * 64), 63)) & u64::splat((k >= 1 * 64) & (k < (2*64))),
                u64::bit_k(cmp::min(k, 63)) & u64::splat(k < 64)
            ]
        }
    }

    fn popcnt(&self) -> usize {
        self.bits.iter().map(|i| i.count_ones() as usize).sum()
    }

    fn pretty_print(&self) {
        print!("{:b}", self)
    }
}


#[cfg(test)]
mod tests {
    use crate::bits::b256::clamping_sub;

    #[test]
    fn test_clamping_sub() {
        assert_eq!(clamping_sub(5, 4), 1);
        assert_eq!(clamping_sub(5, 5), 0);
        assert_eq!(clamping_sub(5, 6), 0);
    }
}
