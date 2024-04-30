
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum Phase {
    Positive = 0,
    Negative = 1,
}


impl Phase {
    pub fn sign_bit(&self) -> bool {
        *self as u8 != 0
    }
}


impl From<bool> for Phase {
    fn from(value: bool) -> Self {
        if value {
            Self::Negative
        } else {
            Self::Positive
        }
    }
}


macro_rules! impl_to_from_phase {
    ($ty:ident) => {
        impl From<$ty> for Phase {
            fn from(val: $ty) -> Self {
                if val >= 0 {
                    Self::Positive
                } else {
                    Self::Negative
                }
            }
        }

        impl From<&$ty> for Phase {
            fn from(val: &$ty) -> Self {
                if *val >= 0 {
                    Self::Positive
                } else {
                    Self::Negative
                }
            }
        }
    };
    ($ty:ident, $($tys:ident),+) => {
        impl_to_from_phase!($ty);
        impl_to_from_phase!($($tys),+);
    }
}


impl_to_from_phase!(i8, i16, i32, i64, i128, isize);
