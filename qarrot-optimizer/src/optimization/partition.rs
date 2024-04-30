use log::trace;

use crate::{basis::Basis, operation::Operation, optimization::{partitions::Partitions, reduce_rotations_no_ordering}, reduce_rotations_no_ordering_slice, Stats};


pub fn update_t_gate_partitions<B: Basis>(circuit: &[Operation<B>], partitions: &mut Partitions) -> bool {
    let mut partitions_changed = true;
    while partitions_changed {
        partitions_changed = false;
        // for each partition (other than the last)
        
        partitions_changed |= partitions.swap_down(|prev_partition, this_rotation| {
            let mut commutes_with_all = true;

            for prev_index in prev_partition {
                if !circuit[this_rotation].commutes_with_likely(&circuit[*prev_index]) {
                    commutes_with_all = false;
                    break;
                }
            }

            commutes_with_all
        });
    }
    partitions_changed
}


fn merge_partitions<B: Basis>(circuit: &mut Vec<Operation<B>>, partitions: &Partitions, t_gate_count: usize, original_len: usize) -> bool {
    trace!("merging {} partitions", partitions.len());
    // reduce within each partition
    // this buffer should be unnecessary, and there's a bunch of unneeded copies here
    // again this can be significantly optimized but time
    let mut layer_buf = Vec::new();
    let mut combined_t_gates = Vec::new();
    let mut index_buf = Vec::new();
    let mut changed = false;

    for partition in partitions.iter() {
        layer_buf.clear();
        let partition: &[usize] = &partition;
        for element in partition {
            layer_buf.push(circuit[*element].clone());
        }
        changed |= reduce_rotations_no_ordering(&mut layer_buf, &mut index_buf);

        combined_t_gates.append(&mut layer_buf);
    }

    // to avoid accidental n^2 while removing, we'll first copy all the non-T-gates into the buffer we have
    layer_buf.clear();
    layer_buf.reserve(circuit.len() - t_gate_count);
    // TODO: verify this turns into a memcpy
    for i in t_gate_count..circuit.len() {
        layer_buf.push(circuit[i].clone());
    }

    // reset the original circuit
    circuit.clear();
    // copy over the optimized t gates
    circuit.append(&mut combined_t_gates);
    // and then everything past the original t gates
    circuit.append(&mut layer_buf);
    debug_assert!(circuit.len() <= original_len);
    trace!("final operation count: {} (changed: {})", circuit.len(), changed);

    changed
}


pub fn partition_t_gates<B: Basis>(partitions: &mut Partitions, circuit: &mut Vec<Operation<B>>, t_gate_count: usize) -> bool {
    let original_len = circuit.len();
    trace!("starting t gate partition with {} operations", original_len);

    if t_gate_count == 0 {
        trace!("no t gates, returning");
        return false;
    }

    partitions.clear();
    partitions.init_one_per_t_gate(t_gate_count);

    let mut rounds = 1;

    let mut partitions_changed = true;

    while partitions_changed {
        trace!("partitions changed (currently {}); running partition round {}", partitions.len(), rounds + 1);
        partitions_changed = update_t_gate_partitions(circuit, partitions);
        rounds += 1;
    }

    trace!("done creating {} partitions", partitions.len());
    merge_partitions(circuit, &partitions, t_gate_count, original_len)
}


// pub fn approximate_partition_t_gates<B: Basis>(partitions: &mut Partitions, circuit: &mut Vec<Operation<B>>, t_gate_count: usize) -> bool {
//     let original_len = circuit.len();
//     trace!("starting t gate partition (approximate) with {} operations", original_len);

//     if t_gate_count == 0 {
//         trace!("no t gates, returning");
//         return false;
//     }

//     // try to improve initial conditions by reducing initial number of partitions
//     partitions.clear();
//     partitions.init(t_gate_count, |current_partition, new_index| {
//         let mut commutes_with_all = true;

//         for prev_index in current_partition {
//             if !circuit[new_index].commutes_with_likely(&circuit[*prev_index]) {
//                 commutes_with_all = false;
//                 break;
//             }
//         }

//         !commutes_with_all
//     });

//     trace!("done creating {} partitions", partitions.len());
//     merge_partitions(circuit, &partitions, t_gate_count, original_len)
// }



pub fn approximate_partition_t_gates<B: Basis>(circuit: &mut Vec<Operation<B>>) -> (bool, Stats) {
    let original_len = circuit.len();
    trace!("starting whole circuit t gate partition (approximate) with {} operations", original_len);

    let mut partition_start = None;
    let mut partitions = 0usize;
    let mut last_rotation_index = 0usize;

    let mut changed = false;

    for new_index in 0..circuit.len() {
        if !circuit[new_index].is_rotation() {
            if let Some(partition_start) = partition_start {
                changed |= reduce_rotations_no_ordering_slice(&mut circuit[partition_start..new_index]);
            }
            partition_start = None;
            continue;
        }
        last_rotation_index = new_index;
        if partition_start.is_none() {
            partition_start = Some(new_index);
            continue;
        }

        let mut commutes_with_all = true;

        for prev_index in partition_start.unwrap()..new_index {
            if !circuit[new_index].commutes_with_likely(&circuit[prev_index]) {
                commutes_with_all = false;
                break;
            }
        }

        if !commutes_with_all {
            partitions += 1;
            changed |= reduce_rotations_no_ordering_slice(&mut circuit[partition_start.unwrap()..new_index]);
            partition_start = Some(new_index);
        }
    }

    if let Some(partition_start) = partition_start {
        changed |= reduce_rotations_no_ordering_slice(&mut circuit[partition_start..last_rotation_index]);
    }

    trace!("done partitioning ({} partitions) and reducing. cleaning removed rotations…", partitions);

    circuit.retain(|op| {
        !op.is_nop()
    });

    let mut stats = Stats {
        total_operations: circuit.len(),
        t_gates: 0,
    };

    for op in circuit.iter() {
        if let Some(r) = op.as_rotation() {
            if r.angle.is_pi8() {
                stats.t_gates += 1;
            }
        }
    }

    (changed, stats)
}
