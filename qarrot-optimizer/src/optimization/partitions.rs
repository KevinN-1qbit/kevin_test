use std::ops::Index;


#[derive(Clone, PartialEq, Eq, Debug)]
pub struct Partitions {
    indexes: Vec<usize>,
    boundaries: Vec<usize>,
}


impl Partitions {
    pub fn new() -> Self {
        Self {
            indexes: Vec::new(),
            boundaries: Vec::new(),
        }
    }

    pub fn with_capacity(capacity: usize) -> Self {
        Self {
            indexes: Vec::with_capacity(capacity),
            boundaries: Vec::with_capacity(capacity),
        }
    }

    pub fn len(&self) -> usize {
        self.boundaries.len()
    }

    pub fn clear(&mut self) {
        self.indexes.clear();
        self.boundaries.clear();
    }

    pub fn init_one_per_t_gate(&mut self, t_gates: usize) {
        self.clear();
        self.indexes.reserve_exact(t_gates);
        self.boundaries.reserve_exact(t_gates);
        self.indexes.extend(0..t_gates);
        self.boundaries.extend(0..t_gates);
    }

    fn partition_range(&self, partition: usize) -> (usize, usize) {
        let start = self.boundaries[partition];
        let end = self.boundaries.get(partition + 1).copied().unwrap_or(self.indexes.len());
        (start, end)
    }

    fn start_of_partition(&self, partition: usize) -> usize {
        self.boundaries[partition]
    }

    pub fn length_of_partition(&self, partition: usize) -> usize {
        let (start, end) = self.partition_range(partition);
        end - start
    }

    // F: takes the previous partition and the index being investigated
    //    returns whether or not the index should be in a new partition
    pub fn init<F>(&mut self, t_gates: usize, for_t_gate: F)
    where F: Fn(&[usize], usize) -> bool {
        self.clear();

        if t_gates == 0 {
            return;
        }

        self.indexes.extend(0..t_gates);
        self.boundaries.push(0);

        for index in 1..t_gates {
            let last_partition = &self.indexes[*self.boundaries.last().unwrap()..index];
            let new_partition = for_t_gate(last_partition, index);
            if new_partition {
                self.boundaries.push(index);
            }
        }
    }

    // function takes (comparing partition, new index) and returns true if the index should be merged
    pub fn swap_down<F>(&mut self, when: F) -> bool
    where F: Fn(&[usize], usize) -> bool {
        let mut changed = false;

        for partition_index in 1..self.len() {

            let mut index_index = 0;
            while index_index < self.length_of_partition(partition_index) {
                let prev_partition = &self[partition_index - 1];
                let cmp_index = self[partition_index][index_index];

                if when(prev_partition, cmp_index) {
                    changed = true;
                    let swap_with = self.start_of_partition(partition_index);
                    // move the index which should be merged with the previous partition to the start
                    // this will reorder the elements of the partition but that's fine
                    self.indexes.swap(swap_with + index_index, swap_with);
                    // now, move the boundary forwards
                    self.boundaries[partition_index] += 1;
                    // this reduces the size of the partition by one, so we don't increment index_index
                    // that's also why we won't check the first index of the partition again (the one we just swapped)
                } else {
                    index_index += 1;
                }
            }
        }

        // remove empty partitions
        // to avoid accidental quadratics, remove them by swapping down (O(1))
        // and then sort (O(n log n))
        // let mut index = self.boundaries.len() - 1;
        // while index > 0 {
        //     if self.boundaries[index - 1] == self.boundaries[index] || self.boundaries[index] >= self.indexes.len() {
        //         self.boundaries.swap_remove(index);
        //     }
        //     index -= 1;
        // }
        // self.boundaries.sort_unstable();

        let mut i = 1;
        while i < self.boundaries.len() {
            if self.boundaries[i - 1] == self.boundaries[i] || self.boundaries[i] >= self.indexes.len() {
                self.boundaries.remove(i);
            } else {
                i += 1;
            }
        }

        changed
    }

    pub fn iter<'a>(&'a self) -> PartitionIter<'a> {
        PartitionIter {
            partition: &self,
            index: 0,
        }
    }
}


// get the i'th partition
impl Index<usize> for Partitions {
    type Output = [usize];

    fn index(&self, index: usize) -> &Self::Output {
        let (start, end) = self.partition_range(index);
        &self.indexes[start..end]
    }
}


#[derive(Clone, Debug)]
pub struct PartitionIter<'a> {
    partition: &'a Partitions,
    index: usize,
}


impl<'a> Iterator for PartitionIter<'a> {
    type Item = &'a [usize];

    fn next(&mut self) -> Option<Self::Item> {
        if self.index >= self.partition.len() {
            None
        } else {
            let ret = Some(&self.partition[self.index]);
            self.index += 1;
            ret
        }
    }

    fn size_hint(&self) -> (usize, Option<usize>) {
        let remaining = self.partition.len() - self.index;
        (remaining, Some(remaining))
    }
}

impl<'a> ExactSizeIterator for PartitionIter<'a> {}


#[cfg(test)]
mod tests {
    use super::Partitions;

    #[test]
    fn test_basic() {
        let mut new = Partitions::new();
        new.init_one_per_t_gate(5);
        assert_eq!(new.len(), 5);
        assert_eq!(&new.indexes, &[0, 1, 2, 3, 4]);
        assert_eq!(&new.boundaries, &[0, 1, 2, 3, 4]);
        assert_eq!(&new[0], &[0]);
        assert_eq!(&new[1], &[1]);
        assert_eq!(&new[2], &[2]);
        assert_eq!(&new[3], &[3]);
        assert_eq!(&new[4], &[4]);
    }

    #[test]
    fn test_init() {
        let mut new = Partitions::new();
        new.init(2, |_last_partition, _this_index| { false });
        assert_eq!(new.len(), 1);
        assert_eq!(&new.boundaries, &[0]);
        assert_eq!(&new[0], &[0, 1]);

        let mut new = Partitions::new();
        new.init(3, |_last_partition, _this_index| { false });
        assert_eq!(new.len(), 1);
        assert_eq!(&new.boundaries, &[0]);
        assert_eq!(&new[0], &[0, 1, 2]);

        let mut new = Partitions::new();
        new.init(3, |_last_partition: &[usize], this_index| { this_index == 2 });
        assert_eq!(new.len(), 2);
        assert_eq!(&new.boundaries, &[0, 2]);
        assert_eq!(&new[0], &[0, 1]);
        assert_eq!(&new[1], &[2]);
    }

    #[test]
    fn test_swap_down_single() {
        let mut new = Partitions::new();
        new.init(3, |_last_partition: &[usize], this_index| { this_index == 2 });
        dbg!(&new);
        new.swap_down(|_, _| true);
        dbg!(&new);
        assert_eq!(new.len(), 1);
        assert_eq!(&new.boundaries, &[0]);
    }

    #[test]
    fn test_swap_down_1_of_2() {
        let mut new = Partitions::new();
        new.init_one_per_t_gate(3);
        dbg!(&new);
        new.swap_down(|_, i| i == 2);
        assert_eq!(new.len(), 2);
        assert_eq!(&new.boundaries, &[0, 1]);
        new.swap_down(|_, _| true);
        assert_eq!(new.len(), 1);
        assert_eq!(&new.boundaries, &[0]);
    }
}
