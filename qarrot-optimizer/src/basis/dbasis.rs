use crate::bits::{n_chunks, bit_traits::{RefAnd, RefOr, RefXor}};

use super::*;

type B = u128;

#[derive(Clone, Debug, Hash, PartialEq, Eq)]
pub struct DBasis {
    bits: Vec<B>,
    len: usize,
}


impl PartialOrd for DBasis {
    fn partial_cmp(&self, other: &Self) -> Option<std::cmp::Ordering> {
        Some(self.cmp(other))
    }
}


impl Ord for DBasis {
    fn cmp(&self, other: &Self) -> std::cmp::Ordering {
        self.bits.iter()
            .rev()
            .zip(other.bits.iter().rev())
            .fold(std::cmp::Ordering::Equal, |acc, x| acc.then(x.0.cmp(x.1)))
    }
}


impl BasisCore for DBasis {
    fn _bit_capacity(&self) -> usize {
        <B as Bits>::BITS * self.bits.len()
    }

    fn assert_same_length(&self, other: &Self) {
        if self.len != other.len {
            panic!("Mismatched DBasis lengths: {} and {}", self.len, other.len);
        }
    }

    unsafe fn bitand_unchecked(&mut self, rhs: &Self) {
        debug_assert!(self.len == rhs.len);
        for i in 0..self.bits.len() {
            unsafe {
                self.bits.get_unchecked_mut(i).bitand_assign(rhs.bits.get_unchecked(i));
            }
        }
    }

    unsafe fn bitor_unchecked(&mut self, rhs: &Self) {
        debug_assert!(self.len == rhs.len);
        for i in 0..self.bits.len() {
            unsafe {
                self.bits.get_unchecked_mut(i).bitor_assign(rhs.bits.get_unchecked(i));
            }
        }
    }

    unsafe fn bitxor_unchecked(&mut self, rhs: &Self) {
        debug_assert!(self.len == rhs.len);
        for i in 0..self.bits.len() {
            unsafe {
                self.bits.get_unchecked_mut(i).bitxor_assign(rhs.bits.get_unchecked(i));
            }
        }
    }

    // fn _lneg(&mut self) {
    //     for chunk in self.bits.iter_mut() {
    //         chunk.lneg();
    //     }
    // }
}

macro_rules! basis_impl_bitops {
    ($t:ident, $trait:ident, $trait_fn:ident, $assign_trait:ident, $assign_fn:ident, $unsafe_fn:ident) => {
        impl $trait for $t {
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

        impl $assign_trait for $t {
            fn $assign_fn(&mut self, rhs: Self) {
                self.assert_same_length(&rhs);
                unsafe {
                    self.$unsafe_fn(&rhs);
                }
            }
        }

        impl $assign_trait<&$t> for $t {
            fn $assign_fn(&mut self, rhs: &Self) {
                self.assert_same_length(rhs);
                unsafe {
                    self.$unsafe_fn(rhs);
                }
            }
        }
    };
    (ref $t:ident, $trait:ident, $trait_fn:ident, $unsafe_fn:ident) => {
        impl $trait for $t {
            fn $trait_fn(&self, rhs: &Self) -> Self {
                self.assert_same_length(rhs);
                let mut new = self.clone();
                unsafe {
                    new.$unsafe_fn(rhs);
                }
                new
            }
        }
    };
    ($t:ident) => {
        basis_impl_bitops!($t, BitAnd, bitand, BitAndAssign, bitand_assign, bitand_unchecked);
        basis_impl_bitops!($t, BitOr, bitor, BitOrAssign, bitor_assign, bitor_unchecked);
        basis_impl_bitops!($t, BitXor, bitxor, BitXorAssign, bitxor_assign, bitxor_unchecked);

        basis_impl_bitops!(ref $t, RefAnd, and, bitand_unchecked);
        basis_impl_bitops!(ref $t, RefOr, or, bitor_unchecked);
        basis_impl_bitops!(ref $t, RefXor, xor, bitxor_unchecked);

        // impl LNeg for $t {
        //     #[inline(always)]
        //     fn lneg(&mut self) {
        //         self._lneg();
        //     }
        // }

        // impl Not for $t {
        //     type Output = Self;

        //     #[inline(always)]
        //     fn not(self) -> Self::Output {
        //         let mut new = self.clone();
        //         new._lneg();
        //         new
        //     }
        // }

        // impl Not for &$t {
        //     type Output = $t;

        //     #[inline(always)]
        //     fn not(self) -> Self::Output {
        //         todo!()
        //     }
        // }
    };
}

basis_impl_bitops!(DBasis);


impl Basis for DBasis {
    type B = B;
    fn n_chunks(&self) -> usize {
        self.bits.len()
    }

    fn zero(bit_length: usize) -> Self {
        Self {
            bits: vec![B::ZERO; n_chunks::<B>(bit_length)],
            len: bit_length,
        }
    }

    fn set_zero(&mut self) {
        for bit in self.bits.iter_mut() {
            *bit = B::ZERO;
        }
    }

    fn size_descriptor() -> &'static str {
        "dynamic"
    }

    fn chunk(&self, i: usize) -> B {
        self.bits[i]
    }

    fn chunk_mut(&mut self, i: usize) -> &mut B {
        &mut self.bits[i]
    }

    fn for_chunks<F>(&self, f: F)
            where F: Fn(usize, &B) {
        for (i, ch) in self.bits.iter().enumerate() {
            f(i, ch);
        }
    }

    fn for_chunks_mut<F>(&mut self, mut f: F)
            where F: FnMut(usize, &mut B) {
        for (i, ch) in self.bits.iter_mut().enumerate() {
            f(i, ch);
        }
    }

    fn map_chunks<F, T>(&self, f: F) -> Vec<T>
            where F: Fn(usize, &B) -> T {
        self.bits
            .iter()
            .enumerate()
            .map(|(i, ch)| f(i, ch))
            .collect()
    }

    fn popcnt(&self) -> usize {
        self.bits.iter().map(|bits| bits.popcnt()).sum()
    }

    fn pretty_print(&self) {
        // todo: make more efficient
        print!("DBasis {{ ");
        for (i, bits) in self.bits.iter().enumerate() {
            if i != 0 {
                print!(", ");
            }
            print!("({}) {:b}", i, bits);
        }
        print!(" }}");
    }
    
    fn is_zero(&self) -> bool {
        self.bits.iter().all(|b| b == &B::ZERO)
    }
    
    fn parity(&self) -> bool {
        self.bits.iter().map(|b| b.parity()).reduce(|l, r| l ^ r).unwrap_or(false)
    }
}
