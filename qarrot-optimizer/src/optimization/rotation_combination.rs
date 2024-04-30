use crate::{basis::Basis, operation::{angle::Angle, Operation}};


#[derive(Clone, Copy, Debug)]
enum RotationCombineResult<B: Basis> {
    KeepNeither,
    KeepFirst,
    KeepLast,
    KeepBoth,
    CombineTo(Operation<B>),
}


#[inline(always)] // probably the RotationCombineResult type is elided completely
fn try_combine_rotations<'a, B: Basis>(op_1: &'a Operation<B>, op_2: &'a Operation<B>) -> RotationCombineResult<B> {
    // if either is not a rotation, keep both
    let Some(rotation_1) = op_1.as_rotation() else {
        return RotationCombineResult::KeepBoth;
    };
    let Some(rotation_2) = op_2.as_rotation() else {
        return RotationCombineResult::KeepBoth;
    };

    let is_identity_1 = rotation_1.is_identity();
    let is_identity_2 = rotation_2.is_identity();

    if is_identity_1 && is_identity_2 {
        return RotationCombineResult::KeepNeither;
    } else if is_identity_1 {
        return RotationCombineResult::KeepLast;
    } else if is_identity_2 {
        return RotationCombineResult::KeepFirst;
    }

    if (op_1.x != op_2.x) || (op_1.z != op_2.z) {
        return RotationCombineResult::KeepBoth;
    }

    let angle_1 = *rotation_1.angle;
    let angle_2 = *rotation_2.angle;
    let mut new_angle = angle_1 as isize + angle_2 as isize;

    if new_angle == 0 {
        // they combine to identity
        return RotationCombineResult::KeepNeither;
    }

    // if one is pi/2, the other must be pi/2 or -pi/4 to combine. the both pi/2 case is covered above (angle codes will sum to 0)
    if (angle_1 == Angle::Pi2 && angle_2 == Angle::MinusPi4) || (angle_2 == Angle::Pi2 && angle_1 == Angle::MinusPi4) {
        if new_angle == -2 {
            new_angle = 2;
        }
    } else if angle_1 == Angle::Pi2 || angle_2 == Angle::Pi2 {
        return RotationCombineResult::KeepBoth;
    }

    if new_angle.abs() == 3 {
        return RotationCombineResult::KeepBoth;
    }

    if new_angle.abs() == 4 {
        new_angle = 0;
    }

    let new_op = Operation::rotation(op_1.x.clone(), op_1.z.clone(), new_angle.into());

    RotationCombineResult::CombineTo(new_op)
}


#[inline(always)]
fn compute_next_index(slots: &[bool], mut index: usize) -> usize {
    loop {
        index += 1;
        if index >= slots.len() {
            return slots.len();
        } else {
            if slots[index] {
                return index;
            }
        }
    }
}


#[derive(Clone, Debug)]
pub struct OptimizeRotationsAdjacent<B: Basis, I: Iterator<Item = Operation<B>>> {
    source: I,
    source_is_done: bool,
    current: Option<Operation<B>>,
    pre_op_count: usize,
    // post_op_count: usize,
}


impl<B: Basis, I: Iterator<Item = Operation<B>>> OptimizeRotationsAdjacent<B, I> {
    pub fn new(iterator: I) -> Self {
        Self {
            source: iterator,
            source_is_done: false,
            current: None,
            pre_op_count: 0,
        }
    }

    pub fn pre_op_count(&self) -> usize {
        self.pre_op_count
    }
}


impl<B: Basis, I: Iterator<Item = Operation<B>>> Iterator for OptimizeRotationsAdjacent<B, I> {
    type Item = Option<Operation<B>>;

    fn next(&mut self) -> Option<Self::Item> {
        // possible return values:
        // - Some(Some(value)): the next value
        // - Some(None): we need more calls to next() before there are results
        // - None: done iterating
        if self.source_is_done {
            if let Some(current) = &self.current {
                let ret = current.clone();
                self.current = None;
                return Some(Some(ret));
            } else {
                return None;
            }
        }

        if let Some(next) = self.source.next() {
            self.pre_op_count += 1;
            if let Some(current) = &self.current {
                match try_combine_rotations(&current, &next) {
                    RotationCombineResult::KeepNeither => {
                        self.current = None;
                        Some(None)
                    },
                    RotationCombineResult::KeepFirst => {
                        Some(None)
                    },
                    RotationCombineResult::KeepLast => {
                        self.current = Some(next);
                        Some(None)
                    },
                    RotationCombineResult::KeepBoth => {
                        let current = current.clone();
                        self.current = Some(next);
                        Some(Some(current))
                    },
                    RotationCombineResult::CombineTo(new_op) => {
                        self.current = Some(new_op);
                        Some(None)
                    },
                }
            } else {
                self.current = Some(next);
                Some(None)
            }
        } else {
            self.source_is_done = true;
            if let Some(current) = &self.current {
                let current = current.clone();
                self.current = None;
                Some(Some(current))
            } else {
                None
            }
        }
    }
}


fn inner_reduce_rotations_no_ordering<B: Basis>(operations: &mut Vec<Operation<B>>, keep_indexes: &mut Vec<bool>) -> bool {
    keep_indexes.clear();
    
    if operations.is_empty() {
        return false;
    } else if operations.len() == 1 {
        if operations[0].is_identity() {
            operations.clear();
            return true;
        } else {
            return false;
        }
    }

    keep_indexes.resize(operations.len(), true);

    let mut index1 = 0;
    let mut index2 = 1;
    let mut changed = false;

    'outer: while index1 < operations.len() {
        // println!("------");
        // dbg!((index1, index2));
        // dbg!(&keep_indexes);
        // dbg!(&operations[index1]);
        // dbg!(&operations[index2]);
        // try to combine
        let res = try_combine_rotations(&operations[index1], &operations[index2]);
        // dbg!(&res);
        match res {
            RotationCombineResult::KeepNeither => {
                keep_indexes[index1] = false;
                keep_indexes[index2] = false;
                index1 = compute_next_index(&keep_indexes, index1);
                index2 = compute_next_index(&keep_indexes, index2);
                if index2 <= index1 {
                    index2 = compute_next_index(&keep_indexes, index1);
                }
                changed = true;
            },
            RotationCombineResult::KeepFirst => {
                keep_indexes[index2] = false;
                index2 = compute_next_index(&keep_indexes, index2);
                changed = true;
            },
            RotationCombineResult::KeepLast => {
                keep_indexes[index1] = false;
                index1 = compute_next_index(&keep_indexes, index1);
                changed = true;
            },
            RotationCombineResult::KeepBoth => {
                // find the next index2
                // if there aren't any, set it to operations.len()
                index2 = compute_next_index(&keep_indexes, index2);
            },
            RotationCombineResult::CombineTo(new_op) => {
                operations[index1] = new_op;
                keep_indexes[index2] = false;
                index2 = compute_next_index(&keep_indexes, index2);
                changed = true;
            },
        }

        while index2 >= keep_indexes.len() {
            index1 = compute_next_index(&keep_indexes, index1);
            index2 = compute_next_index(&keep_indexes, index1);
            if index1 >= keep_indexes.len() {
                break 'outer;
            }
        }
    }

    let mut keep_iter = keep_indexes.iter();
    operations.retain(|_| *keep_iter.next().unwrap());

    changed
}


pub fn reduce_rotations_no_ordering<B: Basis>(operations: &mut Vec<Operation<B>>, keep_indexes: &mut Vec<bool>) -> bool {
    let mut changed = inner_reduce_rotations_no_ordering(operations, keep_indexes);
    let overall_changed = changed;

    while changed {
        changed = inner_reduce_rotations_no_ordering(operations, keep_indexes);
    }

    overall_changed
}


#[inline(always)]
fn compute_next_index_slice<B: Basis>(operations: &[Operation<B>], mut index: usize) -> usize {
    loop {
        index += 1;
        if index >= operations.len() {
            return operations.len();
        } else {
            if !operations[index].is_nop() {
                return index;
            }
        }
    }
}


fn inner_reduce_rotations_no_ordering_slice<B: Basis>(operations: &mut [Operation<B>]) -> bool {
    if operations.is_empty() {
        return false;
    } else if operations.len() == 1 {
        if operations[0].is_identity() {
            operations[0].set_nop();
            return true;
        } else {
            return false;
        }
    }

    let mut changed = false;

    let mut index1 = 0;
    while operations[index1].is_nop() {
        index1 += 1;
        if index1 >= operations.len() {
            return false;
        }
    }
    let mut index2 = compute_next_index_slice(operations, index1);
    if index2 >= operations.len() {
        return false;
    }

    'outer: while index1 < operations.len() {
        // try to combine
        let res = try_combine_rotations(&operations[index1], &operations[index2]);
        // dbg!(&res);
        match res {
            RotationCombineResult::KeepNeither => {
                operations[index1].set_nop();
                operations[index2].set_nop();
                index1 = compute_next_index_slice(operations, index1);
                index2 = compute_next_index_slice(operations, index2);
                if index2 <= index1 {
                    index2 = compute_next_index_slice(operations, index1);
                }
                changed = true;
            },
            RotationCombineResult::KeepFirst => {
                operations[index2].set_nop();
                index2 = compute_next_index_slice(operations, index2);
                changed = true;
            },
            RotationCombineResult::KeepLast => {
                operations[index1].set_nop();
                index1 = compute_next_index_slice(operations, index1);
                changed = true;
            },
            RotationCombineResult::KeepBoth => {
                // find the next index2
                // if there aren't any, set it to operations.len()
                index2 = compute_next_index_slice(operations, index2);
            },
            RotationCombineResult::CombineTo(new_op) => {
                operations[index1] = new_op;
                operations[index2].set_nop();
                index2 = compute_next_index_slice(operations, index2);
                changed = true;
            },
        }

        while index2 >= operations.len() {
            index1 = compute_next_index_slice(operations, index1);
            index2 = compute_next_index_slice(operations, index1);
            if index1 >= operations.len() {
                break 'outer;
            }
        }
    }

    changed
}

pub fn reduce_rotations_no_ordering_slice<B: Basis>(operations: &mut [Operation<B>]) -> bool {
    let mut changed = inner_reduce_rotations_no_ordering_slice(operations);
    let overall_changed = changed;

    while changed {
        changed = inner_reduce_rotations_no_ordering_slice(operations);
    }

    overall_changed
}


#[cfg(test)]
mod tests {
    use crate::basis::*;
    use super::*;

    #[test]
    fn test_reduce_none() {
        let mut operations = Vec::new();
        let changed = reduce_rotations_no_ordering::<Basis8>(&mut operations, &mut Vec::new());
        assert!(operations.is_empty());
        assert!(!changed);
    }

    #[test]
    fn test_reduce_one() {
        let mut basis = Basis8::zero(5);
        basis.set_bit(2, true);

        let mut operations = vec![
            Operation::rotation(basis.clone(), basis.clone(), Angle::PlusPi8),
        ];
        let op = operations[0].clone();
        let changed = reduce_rotations_no_ordering::<Basis8>(&mut operations, &mut Vec::new());
        assert_eq!(operations.len(), 1);
        assert!(operations[0] == op);
        assert!(!changed);
    }

    #[test]
    fn test_reduce_i() {
        let mut basis = Basis8::zero(5);
        basis.set_bit(2, true);

        let mut operations = vec![
            Operation::rotation(basis.clone(), basis.clone(), Angle::PlusPi4),
            Operation::rotation(basis.clone(), basis.clone(), Angle::MinusPi4),
        ];

        let changed = reduce_rotations_no_ordering(&mut operations, &mut Vec::new());
        assert!(operations.is_empty());
        assert!(changed);
    }

    #[test]
    fn test_reduce_single() {
        let mut basis = Basis8::zero(5);
        basis.set_bit(2, true);

        let mut operations = vec![
            Operation::rotation(basis.clone(), basis.clone(), Angle::PlusPi8),
            Operation::rotation(basis.clone(), basis.clone(), Angle::PlusPi8),
        ];

        let changed = reduce_rotations_no_ordering(&mut operations, &mut Vec::new());
        assert_eq!(operations.len(), 1);
        assert!(operations[0].is_rotation());
        assert!(operations[0].as_rotation().unwrap().angle == &Angle::PlusPi4);
        assert!(changed);
    }

    #[test]
    fn test_reduce_cannot() {
        let mut basis1 = Basis8::zero(5);
        basis1.set_bit(2, true);

        let mut basis2 = Basis8::zero(5);
        basis2.set_bit(3, true);

        let mut operations = vec![
            Operation::rotation(basis1.clone(), basis1.clone(), Angle::PlusPi8),
            Operation::rotation(basis2.clone(), basis2.clone(), Angle::MinusPi8),
        ];

        let op1 = operations[0].clone();
        let op2 = operations[1].clone();

        let changed = reduce_rotations_no_ordering(&mut operations, &mut Vec::new());

        assert_eq!(operations.len(), 2);

        assert_eq!(operations[0], op1);
        assert_eq!(operations[1], op2);
        assert!(!changed);
    }

    #[test]
    fn test_reduce_three_two() {
        let mut basis = Basis8::zero(5);
        basis.set_bit(2, true);

        let mut basis2 = Basis8::zero(5);
        basis2.set_bit(3, true);

        let mut operations = vec![
            Operation::rotation(basis.clone(), basis.clone(), Angle::PlusPi8),
            Operation::rotation(basis.clone(), basis.clone(), Angle::PlusPi8),
            Operation::rotation(basis2.clone(), basis2.clone(), Angle::PlusPi8),
        ];

        let op = operations[2].clone();

        let changed = reduce_rotations_no_ordering(&mut operations, &mut Vec::new());
        assert_eq!(operations.len(), 2);
        assert!(changed);
        assert!(operations[0].is_rotation());
        assert!(operations[0].as_rotation().unwrap().angle == &Angle::PlusPi4);
        assert_eq!(operations[1], op);
    }

    #[test]
    fn test_reduce_three_two_swap() {
        let mut basis = Basis8::zero(5);
        basis.set_bit(2, true);

        let mut basis2 = Basis8::zero(5);
        basis2.set_bit(3, true);

        let mut operations = vec![
            Operation::rotation(basis2.clone(), basis2.clone(), Angle::PlusPi8),
            Operation::rotation(basis.clone(), basis.clone(), Angle::PlusPi8),
            Operation::rotation(basis.clone(), basis.clone(), Angle::PlusPi8),
        ];

        let op = operations[0].clone();

        let changed = reduce_rotations_no_ordering(&mut operations, &mut Vec::new());
        dbg!(&operations);
        assert_eq!(operations.len(), 2);
        assert!(changed);
        assert!(operations[1].is_rotation());
        assert!(operations[1].as_rotation().unwrap().angle == &Angle::PlusPi4);
        assert_eq!(operations[0], op);
    }

    #[test]
    fn test_reduce_half() {
        let basisn = |which| {
            let mut basis = Basis8::zero(8);
            basis.set_bit(which, true);
            basis
        };

        // group 1
        let basis_y_0 = basisn(0);

        // group 2
        let basis_y_1 = basisn(1);

        let mut operations = vec![
            // group 1 (combine to identity)
            Operation::rotation(basis_y_0, basis_y_0, Angle::PlusPi8),
            Operation::rotation(basis_y_0, basis_y_0, Angle::MinusPi8),
            // non combinable
            Operation::rotation(basisn(2), basisn(2), Angle::PlusPi4),
            Operation::rotation(basisn(3), basisn(3), Angle::PlusPi4),
            // group 2 (combine to pi/2)
            Operation::rotation(basis_y_1, basis_y_1, Angle::PlusPi4),
            Operation::rotation(basis_y_1, basis_y_1, Angle::PlusPi4),
            // non combinable
            Operation::rotation(basisn(4), basisn(4), Angle::Pi2),
            Operation::rotation(basisn(5), basisn(5), Angle::MinusPi4),
        ];

        let changed = reduce_rotations_no_ordering(&mut operations, &mut Vec::new());
        assert!(changed);
        assert_eq!(operations.len(), 5);
        
    }
}
