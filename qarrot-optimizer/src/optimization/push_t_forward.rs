use log::trace;

use crate::{basis::Basis, clifford::Clifford, operation::{angle::Angle, Operation, OperationKind}};

// returns result (did_change, number_of_t_gates)
// pub fn push_t_forward<B: Basis>(output: &mut Vec<Operation<B>>, circuit: &[Operation<B>], n_qubits: usize) -> anyhow::Result<(bool, usize)> {
//     trace!("pushing T gates forwards. current circuit length {}.", circuit.len());
//     let mut changed_last_iteration = false;
//     let mut accumulator = Clifford::identity(n_qubits);
//     let mut clifford_buf = Clifford::identity(n_qubits);

//     let mut t_gate_count = 0;
//     for op in circuit.iter() {
//         let (did_change, was_t_gate, new_operation) = push_accumulator(&mut accumulator, &mut clifford_buf, op);
//         changed_last_iteration |= did_change;
//         if was_t_gate {
//             t_gate_count += 1;
//         }
//         if let Some(new_operation) = new_operation {
//             output.push(new_operation);
//         }
//     }

//     trace!("done pushing T gates forward ({} t gates); new length {}", t_gate_count, output.len());

//     Ok((changed_last_iteration, t_gate_count))
// }


pub fn push_t_forward_inplace<B: Basis>(circuit: &mut Vec<Operation<B>>, n_qubits: usize) -> (bool, usize) {
    trace!("pushing T gates forwards. current circuit length {}.", circuit.len());

    let mut changed_last_iteration = false;
    let mut accumulator = Clifford::identity(n_qubits);
    let mut clifford_buf = Clifford::identity(n_qubits);

    let mut t_gate_count = 0;

    let mut out_index = 0;

    for op_index in 0..circuit.len() {
        debug_assert!(out_index <= op_index);
        let (did_change, was_t_gate, new_operation) = push_accumulator(&mut accumulator, &mut clifford_buf, &circuit[op_index]);
        changed_last_iteration |= did_change;
        if was_t_gate {
            t_gate_count += 1;
        }
        if let Some(new_operation) = new_operation {
            circuit[out_index] = new_operation;
            out_index += 1;
        }
    }

    circuit.truncate(out_index);

    trace!("done pushing T gates forward ({} t gates); new length {}", t_gate_count, circuit.len());

    (changed_last_iteration, t_gate_count)
}


// returns (did_change, was_t_gate, new_operation)
#[inline(always)]
pub fn push_accumulator<B: Basis>(accumulator: &mut Clifford<B>, clifford_buf: &mut Clifford<B>, op: &Operation<B>) -> (bool, bool, Option<Operation<B>>) {
    match op.kind {
        OperationKind::Nop => {
            panic!("nop found while pushing T gates forward")
        },
        OperationKind::Measurement { phase } => {
            let new_symplectic = accumulator.conjugate(phase.sign_bit(), &op.x, &op.z);
            let changed_last_iteration = (new_symplectic.x != op.x) || (new_symplectic.z != op.z) || (new_symplectic.sign != phase.sign_bit());
            let new_measurement = Operation::measurement(new_symplectic.x, new_symplectic.z, new_symplectic.sign.into());
            (changed_last_iteration, false, Some(new_measurement))
        },
        OperationKind::Rotation { angle } => match angle {
            Angle::PlusPi8 | Angle::MinusPi8 => {
                let new_symplectic = accumulator.conjugate(angle.sign_bit(), &op.x, &op.z);
                let changed_last_iteration = (new_symplectic.x != op.x) || (new_symplectic.z != op.z);
                (changed_last_iteration, true, Some(Operation::rotation(new_symplectic.x, new_symplectic.z, angle.use_sign_bit(new_symplectic.sign))))
            },
            Angle::Pi2 => {
                clifford_buf.from_pi2(angle.sign_bit(), &op.x, &op.z);
                *clifford_buf *= &accumulator;
                accumulator.set_to(&clifford_buf);
                (true, false, None)
            },
            Angle::PlusPi4 | Angle::MinusPi4 => {
                clifford_buf.from_pi4(angle.sign_bit(), &op.x, &op.z);
                *clifford_buf *= &accumulator; // todo: fix this operation order
                accumulator.set_to(&clifford_buf);
                (true, false, None)
            },
        },
    }
}
