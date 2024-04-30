
use super::*;

use std::fmt::Debug;


#[allow(private_bounds)]
#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub struct SBasis<B: Bits> {
    bits: B,
}

impl<B: Bits> Debug for SBasis<B> {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_fmt(format_args!("SBasis{}{{ 0b{:016b} }}", B::BITS, self.bits))
        // for 
    }
}

impl<B: Bits> BasisCore for SBasis<B> {
    fn _bit_capacity(&self) -> usize {
        B::BITS
    }

    fn assert_same_length(&self, _: &Self) {
    }

    unsafe fn bitand_unchecked(&mut self, rhs: &Self) {
        self.bits &= rhs.bits;
    }

    unsafe fn bitor_unchecked(&mut self, rhs: &Self) {
        self.bits |= rhs.bits;
    }

    unsafe fn bitxor_unchecked(&mut self, rhs: &Self) {
        self.bits ^= rhs.bits;
    }

    // fn _lneg(&mut self) {
    //     self.bits.lneg();
    // }
}

impl<B: Bits> Default for SBasis<B> {
    fn default() -> Self {
        Self {
            bits: B::ZERO,
        }
    }
    
}

macro_rules! basis_impl_bitops {
    ($t:ident, $trait:ident, $trait_fn:ident, $assign_trait:ident, $assign_fn:ident, $unsafe_fn:ident) => {
        impl<B: Bits> $trait for $t<B> {
            type Output = Self;

            fn $trait_fn(self, rhs: Self) -> Self::Output {
                self.assert_same_length(&rhs);
                let mut new = self.clone();
                unsafe {
                    new.$unsafe_fn(&rhs);
                }
                new
            }
        }

        impl<B: Bits> $assign_trait for $t<B> {
            fn $assign_fn(&mut self, rhs: Self) {
                self.assert_same_length(&rhs);
                unsafe {
                    self.$unsafe_fn(&rhs);
                }
            }
        }

        impl<B: Bits> $assign_trait<&$t<B>> for $t<B> {
            fn $assign_fn(&mut self, rhs: &Self) {
                self.assert_same_length(rhs);
                unsafe {
                    self.$unsafe_fn(rhs);
                }
            }
        }
    };
    ($t:ident) => {
        basis_impl_bitops!($t, BitAnd, bitand, BitAndAssign, bitand_assign, bitand_unchecked);
        basis_impl_bitops!($t, BitOr, bitor, BitOrAssign, bitor_assign, bitor_unchecked);
        basis_impl_bitops!($t, BitXor, bitxor, BitXorAssign, bitxor_assign, bitxor_unchecked);

        // impl<B: Bits> LNeg for $t<B> {
        //     #[inline(always)]
        //     fn lneg(&mut self) {
        //         self._lneg();
        //     }
        // }

        // impl<B: Bits> Not for $t<B> {
        //     type Output = Self;

        //     #[inline(always)]
        //     fn not(self) -> Self::Output {
        //         let mut new = self.clone();
        //         new._lneg();
        //         new
        //     }
        // }

        // impl<B: Bits> Not for &$t<B> {
        //     type Output = $t<B>;

        //     #[inline(always)]
        //     fn not(self) -> Self::Output {
        //         todo!()
        //     }
        // }
    };
}


basis_impl_bitops!(SBasis);


impl<B: Bits> Basis for SBasis<B> {
    type B = B;

    fn n_chunks(&self) -> usize {
        1
    }

    #[inline(always)]
    fn is_zero(&self) -> bool {
        self.bits == B::ZERO
    }

    #[inline(always)]
    fn zero(bit_length: usize) -> Self {
        assert!(bit_length <= B::BITS);
        assert!(bit_length <= u8::MAX as usize);
        Self {
            bits: B::ZERO,
        }
    }

    fn set_zero(&mut self) {
        self.bits = B::ZERO;
    }

    fn size_descriptor() -> &'static str {
        B::SIZE_DESCRIPTOR
    }

    fn chunk(&self, i: usize) -> B {
        assert!(i == 0);
        self.bits
    }

    fn chunk_mut(&mut self, i: usize) -> &mut B {
        assert!(i == 0);
        &mut self.bits
    }

    fn for_chunks<F>(&self, f: F)
            where F: Fn(usize, &B) {
        f(0, &self.bits);
    }

    fn for_chunks_mut<F>(&mut self, mut f: F)
            where F: FnMut(usize, &mut B) {
        f(0, &mut self.bits);
    }

    fn map_chunks<F, T>(&self, f: F) -> Vec<T>
            where F: Fn(usize, &B) -> T {
        vec![f(0, &self.bits)]
    }

    #[inline(always)]
    fn popcnt(&self) -> usize {
        // (self.bits & B::mask_not_last_k(self._bit_capacity() - num_bits)).popcnt()
        self.bits.popcnt()
    }

    #[inline(always)]
    fn parity(&self) -> bool {
        self.bits.parity()
    }

    #[inline(always)]
    fn bit_k(bit_length: usize, bit: usize) -> Self {
        debug_assert!(bit_length >= bit);
        debug_assert!(bit <= B::BITS);
        Self {
            bits: B::bit_k(bit)
        }
    }

    #[inline(always)]
    fn get_bit(&self, bit: usize) -> bool {
        (self.bits & Self::B::bit_k(bit)) != Self::B::ZERO
    }

    #[inline(always)]
    fn set_bit(&mut self, bit: usize, to: bool) {
        if to {
            self.bits |= Self::B::bit_k(bit);
        } else {
            self.bits &= !Self::B::bit_k(bit);
        }
    }

    #[inline(always)]
    fn set_bit_true(&mut self, bit: usize) {
        self.bits |= Self::B::bit_k(bit);        
    }

    #[inline(always)]
    fn set_bit_false(&mut self, bit: usize) {
        self.bits &= !Self::B::bit_k(bit);  
    }

    fn pretty_print(&self) {
        self.bits.pretty_print();
    }
}
