
// NOTE: this cannot in general be cast to SIMD types, as the alignment is not guaranteed
// make sure you use an unaligned load 


pub struct IterChunks<'a, T, const CHUNK_SIZE: usize> {
    slice: &'a [T],
    index: usize,
}

impl<'a, T, const CHUNK_SIZE: usize> IterChunks<'a, T, CHUNK_SIZE> {
    #[inline(always)]
    pub fn new(slice: &'a [T]) -> Self {
        Self {
            slice, 
            index: 0,
        }
    }

    #[inline(always)]
    pub fn next_chunk(&mut self) -> Option<&'a [T; CHUNK_SIZE]> {
        let start = self.index;
        let end = self.index + CHUNK_SIZE;
        if end >= self.slice.len() {
            None
        } else {
            self.index += CHUNK_SIZE;
            Some(<&'a [T; CHUNK_SIZE]>::try_from(&self.slice[start..end]).unwrap())
        }
    }

    #[inline(always)]
    pub fn remainder(&mut self) -> &'a [T] {
        if self.index >= self.slice.len() {
            &[]
        } else {
            let ret = &self.slice[self.index..self.slice.len()];
            self.index = self.slice.len();
            ret
        }
    }
}


impl<'a, T: Clone, const CHUNK_SIZE: usize> IterChunks<'a, T, CHUNK_SIZE> {
    #[inline(always)]
    pub fn next_chunk_into(&mut self, chunk: &mut [T; CHUNK_SIZE]) -> bool {
        let start = self.index;
        let end = self.index + CHUNK_SIZE;
        if end >= self.slice.len() {
            false
        } else {
            self.index += CHUNK_SIZE;
            // this should optimize to a memcpy
            chunk
                .iter_mut()
                .zip((&self.slice[start..end]).iter())
                .for_each(|(dst, src)| *dst = src.clone());
            true
        }
    }
}


pub fn chunks<const CHUNK_SIZE: usize, T>(slice: &[T]) -> IterChunks<'_, T, CHUNK_SIZE> {
    IterChunks::new(slice)
}


#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_chunks() {
        let arr = [1, 2, 3, 4, 4, 5, 6, 7, 8, 9, 10];
        let mut iter = chunks::<4, _>(&arr);
        assert_eq!(iter.next_chunk(), Some(&[1, 2, 3, 4]));
        assert_eq!(iter.next_chunk(), Some(&[4, 5, 6, 7]));
        assert_eq!(iter.next_chunk(), None);
        assert_eq!(iter.remainder(), &[8, 9, 10]);
        assert_eq!(iter.remainder(), &[]);
    }

    #[test]
    fn test_chunks_into() {
        let arr = [1usize, 2, 3, 4, 4, 5, 6, 7, 8, 9, 10];
        let mut buf = [0usize; 4];
        let mut iter = chunks::<4, _>(&arr);
        assert!(iter.next_chunk_into(&mut buf));
        assert_eq!(&buf, &[1, 2, 3, 4]);
        assert!(iter.next_chunk_into(&mut buf));
        assert_eq!(&buf, &[4, 5, 6, 7]);
        assert!(!iter.next_chunk_into(&mut buf));
        assert_eq!(iter.remainder(), &[8, 9, 10]);
        assert_eq!(iter.remainder(), &[]);
    }
}