use std::ops::{BitXorAssign, BitAndAssign, BitOrAssign, BitXor, BitAnd, BitOr};

use crate::bits::{chunk_bit, Bits, Bits256, bit_traits::*};

mod sbasis;
mod dbasis;

pub use dbasis::DBasis;
use rand::Rng;
pub use sbasis::SBasis;

pub const LARGEST_STATIC_BASIS: usize = 256;


#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum BasisSize {
    Basis8,
    Basis16,
    Basis32,
    Basis64,
    Basis128,
    Basis256,
    BasisDyn,
}


impl BasisSize {
    pub fn from_size(size: usize) -> Self {
        match size {
            0..=8 => BasisSize::Basis8,
            9..=16 => BasisSize::Basis16,
            17..=32 => BasisSize::Basis32,
            33..=64 => BasisSize::Basis64,
            65..=128 => BasisSize::Basis128,
            129..=256 => BasisSize::Basis256,
            _ => BasisSize::BasisDyn,
        }
    }

    pub fn bits(&self) -> &'static str {
        match self {
            BasisSize::Basis8 => "8",
            BasisSize::Basis16 => "16",
            BasisSize::Basis32 => "32",
            BasisSize::Basis64 => "64",
            BasisSize::Basis128 => "128",
            BasisSize::Basis256 => "256",
            BasisSize::BasisDyn => "dyn",
        }
    }
}


pub type Basis8 = SBasis<u8>;
pub type Basis16 = SBasis<u16>;
pub type Basis32 = SBasis<u32>;
pub type Basis64 = SBasis<u64>;
pub type Basis128 = SBasis<u128>;
pub type Basis256 = SBasis<Bits256>;


pub trait BasisCore: Clone + std::fmt::Debug {
    fn _bit_capacity(&self) -> usize;

    fn assert_same_length(&self, other: &Self);

    unsafe fn bitand_unchecked(&mut self, rhs: &Self);
    unsafe fn bitor_unchecked(&mut self, rhs: &Self);
    unsafe fn bitxor_unchecked(&mut self, rhs: &Self);
    // fn _lneg(&mut self);
}


pub trait Basis: Clone + std::fmt::Debug + BitOps + BasisCore + Sync + Ord {
    type B: Bits;

    fn bit_capacity(&self) -> usize {
        self._bit_capacity()
    }

    fn is_zero(&self) -> bool;

    fn size_descriptor() -> &'static str;

    fn n_chunks(&self) -> usize;

    fn for_chunks<F>(&self, f: F)
        where F: Fn(usize, &Self::B);

    fn map_chunks<F, T>(&self, f: F) -> Vec<T>
        where F: Fn(usize, &Self::B) -> T;

    fn for_chunks_mut<F>(&mut self, f: F)
        where F: FnMut(usize, &mut Self::B);

    fn zero(bit_length: usize) -> Self;
    fn one(bit_length: usize) -> Self {
        // todo: speed this up
        let mut new = Self::zero(bit_length);
        for bit in 0..bit_length {
            new.set_bit_true(bit);
        }
        new
    }

    fn one_bit(bit_length: usize, bit: usize) -> Self {
        debug_assert!(bit < bit_length);
        let mut new = Self::zero(bit_length);
        new.set_bit_true(bit);
        new
    }

    fn set_zero(&mut self);

    fn rand(bit_length: usize, rng: &mut impl Rng) -> Self {
        // could be WAY faster by generating random integers of the right size but this is probably fast enough for unit tests
        let mut new = Self::zero(bit_length);
        for i in 0..bit_length {
            new.set_bit(i, rng.gen());
        }
        new
    }

    #[inline(always)]
    fn bit_k(bit_length: usize, bit: usize) -> Self {
        debug_assert!(bit_length >= bit);
        let mut bits = Self::zero(bit_length);
        bits.set_bit_true(bit);

        bits
    }

    fn with_true_bits(bit_length: usize, bits: &[usize]) -> Self {
        let mut new = Self::zero(bit_length);
        for bit in bits {
            new.set_bit(*bit, true);
        }
        new
    }

    fn chunk(&self, i: usize) -> Self::B;
    fn chunk_mut(&mut self, i: usize) -> &mut Self::B;

    #[inline(always)]
    fn set_bit(&mut self, bit: usize, to: bool) {
        let (chunk, bit) = chunk_bit::<Self::B>(bit);
        let chunk_ref = self.chunk_mut(chunk);

        if to {
            *chunk_ref |= Self::B::bit_k(bit);
        } else {
            *chunk_ref &= !Self::B::bit_k(bit);
        }
    }

    #[inline(always)]
    fn set_bit_true(&mut self, bit: usize) {
        let (chunk, bit) = chunk_bit::<Self::B>(bit);
        *self.chunk_mut(chunk) |= Self::B::bit_k(bit);        
    }

    #[inline(always)]
    fn set_bit_false(&mut self, bit: usize) {
        let (chunk, bit) = chunk_bit::<Self::B>(bit);
        *self.chunk_mut(chunk) &= !Self::B::bit_k(bit);  
    }

    #[inline(always)]
    fn get_bit(&self, bit: usize) -> bool {
        let (chunk, bit) = chunk_bit::<Self::B>(bit);
        let chunk_ref = self.chunk(chunk);
        (chunk_ref & Self::B::bit_k(bit)) != Self::B::ZERO
    }

    fn popcnt(&self) -> usize;

    fn parity(&self) -> bool;

    fn pretty_print(&self);
}


#[cfg(test)]
pub mod tests {
    // use super::*;

    // fn test_simple<B: Basis>() {
    //     let mut b = B::zero(8);
    //     for i in 0..8 {
    //         assert_eq!(b.get_bit(i), false);
    //     }
    //     assert_eq!(b.popcnt(8), 0);
    //     for i in 0..4 {
    //         b.set_bit(i, true);
    //         assert_eq!(b.popcnt(8), i + 1);
    //         assert_eq!(b.get_bit(i), true);
    //         b.set_bit(i, false);
    //         assert_eq!(b.get_bit(i), false);
    //         b.set_bit(i, true);
    //     }

    //     let mut not_b = b.clone();
    //     not_b.for_chunks_mut(|_, chunk| chunk.lneg());
    //     assert_eq!(not_b.popcnt(8), 4);

    //     assert_eq!((not_b.clone() & b.clone()).popcnt(8), 0);
    //     assert_eq!((not_b.clone() | b.clone()).popcnt(8), 8);
    //     assert_eq!((not_b.clone() ^ b.clone()).popcnt(8), 8);

    //     assert_eq!((not_b.and(&b)).popcnt(8), 0);
    //     assert_eq!((not_b.or(&b)).popcnt(8), 8);
    //     assert_eq!((not_b.xor(&b)).popcnt(8), 8);
    // }

    // #[test]
    // fn test_simple_b8() {
    //     test_simple::<Basis8>();
    // }

    // #[test]
    // fn test_simple_b16() {
    //     test_simple::<Basis16>();
    // }

    // #[test]
    // fn test_simple_b32() {
    //     test_simple::<Basis32>();
    // }

    // #[test]
    // fn test_simple_b64() {
    //     test_simple::<Basis64>();
    // }

    // #[test]
    // fn test_simple_b128() {
    //     test_simple::<Basis128>();
    // }

    // #[test]
    // fn test_simple_d() {
    //     test_simple::<DBasis>();
    // }
}
