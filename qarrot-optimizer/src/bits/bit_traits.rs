//! Traits for logical operations, including in-place logical negation

use core::ops::*;

use num_traits::PrimInt;

/// In-place logical negation. Should be equivalent to `x = ~x` for any `x` which impl's `Neg`.
pub trait LNeg {
    fn lneg(&mut self);
}

// impl LNeg for any T which is Copy and has normal logical negation which returns T
impl<T: Copy + Not<Output=T> + PrimInt> LNeg for T {
    fn lneg(&mut self) {
        *self = !(*self);
    }
}


pub trait RefAnd {
    fn and(&self, rhs: &Self) -> Self;
}

pub trait RefOr {
    fn or(&self, rhs: &Self) -> Self;
}

pub trait RefXor {
    fn xor(&self, rhs: &Self) -> Self;
}

impl<B: BitAnd<Output = B> + Copy> RefAnd for B {
    fn and(&self, rhs: &Self) -> Self {
        *self & *rhs
    }
}

impl<B: BitOr<Output = B> + Copy> RefOr for B {
    fn or(&self, rhs: &Self) -> Self {
        *self | *rhs
    }
}

impl<B: BitXor<Output = B> + Copy> RefXor for B {
    fn xor(&self, rhs: &Self) -> Self {
        *self ^ *rhs
    }
}


pub trait BitOps: Sized + 
    // Not<Output = Self> + LNeg +
    BitAnd<Output = Self> + BitOr<Output = Self> + BitXor<Output = Self> +
    for<'a> BitAndAssign<&'a Self> + for<'a> BitOrAssign<&'a Self> + for<'a> BitXorAssign<&'a Self> +
    BitAndAssign + BitOrAssign + BitXorAssign +
    Eq + RefAnd + RefOr + RefXor { }
// pub trait RefBitOps<'a, B: BitOps + 'a>: Not<Output = Self> + BitAnd<&'a B, Output = B> + BitOr<&'a B, Output = B> + BitXor<&'a B, Output = B> {}

impl<T: Sized +
    // Not<Output = Self> + LNeg +
    RefAnd + RefOr + RefXor +
    BitAnd<Output = Self> + BitOr<Output = Self> + BitXor<Output = Self> +
    BitAndAssign + BitOrAssign + BitXorAssign +
    for<'a> BitAndAssign<&'a Self> + for<'a> BitOrAssign<&'a Self> + for<'a> BitXorAssign<&'a Self> +
    Eq> BitOps for T { }
