
use std::ops::Not;

mod b256;
pub use b256::Bits256;


pub mod bit_traits;

use bit_traits::{BitOps, LNeg};


#[inline(always)]
pub const fn n_chunks<B: Bits>(n_bits: usize) -> usize {
    (n_bits + B::BITS - 1) / B::BITS
}

#[inline(always)]
pub const fn chunk_bit<B: Bits>(bit: usize) -> (usize, usize) {
    (bit / B::BITS, bit % B::BITS)
}

pub trait Bits: Sized + Copy + BitOps + Not<Output = Self> + LNeg + std::fmt::Debug + std::fmt::Binary + Sync + Ord {
    const BITS: usize;
    const ZERO: Self;
    const ONE: Self;
    const MAX: Self;
    const SIZE_DESCRIPTOR: &'static str;

    /// Returns a bitset with the first K most significant bits set to 1, and all others set to 0. 
    fn mask_first_k(k: usize) -> Self;

    /// Returns a bitset with the K least significant bits set to 0, and all others set to 1.
    fn mask_not_last_k(k: usize) -> Self;

    fn bit_k(k: usize) -> Self;

    fn popcnt(&self) -> usize;

    fn pretty_print(&self);

    fn parity(&self) -> bool {
        // it seems like this usually optimizes well (into parity flag check)
        self.popcnt() % 2 != 0
    }

    #[inline(always)]
    fn splat(val: bool) -> Self {
        if val {
            Self::MAX
        } else {
            Self::ZERO
        }
    }
}

macro_rules! impl_bits_prim {
    ($u:ident, $sz:expr) => {
        impl Bits for $u {
            const BITS: usize = $u::BITS as usize;
            const ZERO: Self = 0;
            const ONE: Self = 1;
            const MAX: Self = Self::MAX;
            const SIZE_DESCRIPTOR: &'static str = $sz;

            #[inline(always)]
            fn mask_first_k(k: usize) -> Self {
                Self::MAX.checked_shl((<Self as Bits>::BITS - k) as u32).unwrap_or(Self::ZERO)
            }

            #[inline(always)]
            fn mask_not_last_k(k: usize) -> Self {
                Self::MAX.checked_shl(k as u32).unwrap_or(Self::ZERO)
            }

            #[inline(always)]
            fn bit_k(k: usize) -> Self {
                (1 as Self).checked_shl(Self::BITS - k as u32 - 1).unwrap_or(Self::ZERO)
            }

            #[inline(always)]
            fn popcnt(&self) -> usize {
                self.count_ones() as usize
            }

            #[inline(always)]
            fn pretty_print(&self) {
                print!("{:b}", self)
            }
        }
    };
}


impl_bits_prim!(u8, "static 8");
impl_bits_prim!(u16, "static 16");
impl_bits_prim!(u32, "static 32");
impl_bits_prim!(u64, "static 64");
impl_bits_prim!(u128, "static 128");


#[cfg(test)]
mod tests {
    use std::ops::*;

    use super::*;

    #[test]
    fn test_hi_bit() {
        assert_eq!(Bits256::bit_k(255), Bits256::ONE);
        assert_eq!(u128::bit_k(127), 1);
        assert_eq!(u64::bit_k(63), 1);
        assert_eq!(u32::bit_k(31), 1);
        assert_eq!(u16::bit_k(15), 1);
        assert_eq!(u8::bit_k(7), 1);
    }

    #[test]
    fn test_lo_bit() {
        assert_eq!(u128::bit_k(0), 2u128.pow(127));
        assert_eq!(u64::bit_k(0), 2u64.pow(63));
        assert_eq!(u32::bit_k(0), 2u32.pow(31));
        assert_eq!(u16::bit_k(0), 2u16.pow(15));
        assert_eq!(u8::bit_k(0), 2u8.pow(7));
    }

    fn _test_all_bits<T: Bits + BitOrAssign>() -> T {
        let mut res = T::ZERO;

        for i in 0..T::BITS {
            res |= T::bit_k(i);
        }

        res
    }

    #[test]
    fn test_all_bits() {
        assert_eq!(_test_all_bits::<Bits256>(), Bits256::MAX);
        assert_eq!(_test_all_bits::<u128>(), u128::MAX);
        assert_eq!(_test_all_bits::<u64>(), u64::MAX);
        assert_eq!(_test_all_bits::<u32>(), u32::MAX);
        assert_eq!(_test_all_bits::<u16>(), u16::MAX);
        assert_eq!(_test_all_bits::<u8>(), u8::MAX);
    }

    #[test]
    fn test_mask_first_k() {
        let b = u8::mask_first_k(3);
        assert_eq!(b, 0b11100000);
        assert_eq!(b.popcnt(), 3);
    }

    #[test]
    fn test_parity_u8() {
        for byte in u8::MIN..=u8::MAX {
            let expected_parity = (byte.count_ones() % 2) != 0;
            assert_eq!(byte.parity(), expected_parity);
        }
    }

    #[test]
    fn test_parity_u16() {
        for byte in u16::MIN..=u16::MAX {
            let expected_parity = (byte.count_ones() % 2) != 0;
            assert_eq!(byte.parity(), expected_parity);
        }
    }

    fn test_first_k<B: Bits>() {
        for k in 0..B::BITS {
            let b = B::mask_first_k(k);
            assert_eq!(b.popcnt(), k);
        }
    }

    fn test_not_last_k<B: Bits>() {
        for k in 0..B::BITS {
            let b = B::mask_not_last_k(k);
            assert_eq!(b.popcnt(), B::BITS - k);
        }
    }

    fn test_bit_k<B: Bits>() {
        for k in 0..B::BITS {
            let b = B::bit_k(k);
            println!("k={}; b={:b}", k, b);
            assert_eq!(b.popcnt(), 1);
        }
    }

    #[test]
    fn test_first_k_u8() {
        test_first_k::<u8>();
    }

    #[test]
    fn test_first_k_u16() {
        test_first_k::<u16>();
    }

    #[test]
    fn test_first_k_u32() {
        test_first_k::<u32>();
    }

    #[test]
    fn test_first_k_u64() {
        test_first_k::<u64>();
    }

    #[test]
    fn test_first_k_u128() {
        test_first_k::<u128>();
    }

    #[test]
    fn test_first_k_u256() {
        test_first_k::<Bits256>();
    }

    #[test]
    fn test_not_last_k_u8() {
        test_not_last_k::<u8>();
    }

    #[test]
    fn test_not_last_k_u16() {
        test_not_last_k::<u16>();
    }

    #[test]
    fn test_not_last_k_u32() {
        test_not_last_k::<u32>();
    }

    #[test]
    fn test_not_last_k_u64() {
        test_not_last_k::<u64>();
    }

    #[test]
    fn test_not_last_k_u128() {
        test_not_last_k::<u128>();
    }

    #[test]
    fn test_not_last_k_u256() {
        test_not_last_k::<Bits256>();
    }

    #[test]
    fn test_bit_k_u8() {
        test_bit_k::<u8>();
    }

    #[test]
    fn test_bit_k_u16() {
        test_bit_k::<u16>();
    }

    #[test]
    fn test_bit_k_u32() {
        test_bit_k::<u32>();
    }

    #[test]
    fn test_bit_k_u64() {
        test_bit_k::<u64>();
    }

    #[test]
    fn test_bit_k_u128() {
        test_bit_k::<u128>();
    }

    #[test]
    fn test_bit_k_u256() {
        test_bit_k::<Bits256>();
    }

    // #[test]
    // fn test_parity_u32() {
    //     for byte in u32::MIN..=u32::MAX {
    //         let expected_parity = (byte.count_ones() % 2) != 0;
    //         assert_eq!(byte.parity(), expected_parity);
    //     }
    // }
}
