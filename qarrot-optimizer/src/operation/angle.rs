use std::{mem, ops::Neg};

use rand::Rng;


#[repr(i8)]
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum Angle {
    Pi2 = 0,
    PlusPi8 = 1,
    MinusPi8 = -1,
    PlusPi4 = 2,
    MinusPi4 = -2,
}


impl Angle {
    pub fn sign_bit(&self) -> bool {
        match self {
            Angle::Pi2 => false,
            Angle::PlusPi8 => false,
            Angle::MinusPi8 => true,
            Angle::PlusPi4 => false,
            Angle::MinusPi4 => true,
        }
    }

    pub fn use_sign_bit(&self, new_sign_bit: bool) -> Self {
        let new_sign_bit = new_sign_bit ^ self.sign_bit();
        let this_angle = *self as i8;

        let sign_flip = if new_sign_bit {
            -1i8
        } else {
            1i8
        };
        (this_angle * sign_flip).into()
    }

    pub fn is_pi8(&self) -> bool {
        matches!(self, Self::PlusPi8 | Self::MinusPi8)
    }

    pub fn rand(rng: &mut impl Rng) -> Self {
        let val = rng.gen_range(-2..=2);
        Self::from(val)
    }
}


macro_rules! impl_to_from_angle {
    ($ty:ident) => {
        impl Into<$ty> for Angle {
            fn into(self) -> $ty {
                self as $ty
            }
        }

        impl Into<$ty> for &Angle {
            fn into(self) -> $ty {
                *self as $ty
            }
        }

        impl From<$ty> for Angle {
            fn from(value: $ty) -> Self {
                match value {
                    0 => Self::Pi2,
                    1 => Self::PlusPi8,
                    2 => Self::PlusPi4,
                    -1 => Self::MinusPi8,
                    -2 => Self::MinusPi4,
                    _ => panic!("invalid rotation code {} (must be 0, +/- 1, or +/- 2)", value)
                }
            }
        }

        impl From<&$ty> for Angle {
            fn from(value: &$ty) -> Self {
                match value {
                    0 => Self::Pi2,
                    1 => Self::PlusPi8,
                    2 => Self::PlusPi4,
                    -1 => Self::MinusPi8,
                    -2 => Self::MinusPi4,
                    _ => panic!("invalid rotation code {} (must be 0, +/- 1, or +/- 2)", value)
                }
            }
        }
    };
    ($ty:ident, $($tys:ident),+) => {
        impl_to_from_angle!($ty);
        impl_to_from_angle!($($tys),+);
    };
}


impl_to_from_angle!(i8, i16, i32, i64, i128, isize);


impl AsRef<i8> for Angle {
    fn as_ref(&self) -> &i8 {
        // safety: every valid Angle is a valid i8
        // note that implementing AsMut would **not** be safe, and that not every valid i8 is a valid Angle
        unsafe {
            mem::transmute(self)
        }
    }
}


impl Neg for Angle {
    type Output = Self;

    fn neg(self) -> Self::Output {
        // safety: every valid Angle is a valid i8 with an absolute value leq 2
        // every valid i8 with an absolute value leq 2 is a valid Angle
        // multiplying by negative one does not change the absolute value
        // therefore, these transmutes are safe
        unsafe {
            let repr: i8 = mem::transmute(self);
            mem::transmute(-repr)
        }
    }
}


#[cfg(test)]
mod tests {
    use super::Angle;

    #[test]
    fn test_sign_bit_assign() {
        let angle1 = Angle::PlusPi8;
        let angle2 = Angle::MinusPi8;
        
        assert_eq!(angle1.use_sign_bit(true), Angle::MinusPi8);
        assert_eq!(angle1.use_sign_bit(false), Angle::PlusPi8);

        assert_eq!(angle2.use_sign_bit(true), Angle::MinusPi8);
        assert_eq!(angle2.use_sign_bit(false), Angle::PlusPi8);
    }
}
