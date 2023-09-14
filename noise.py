import stim, dataclasses
from math import exp
from typing import Dict, Optional, Tuple

units = {"ns": 1e-9, "μs": 1e-6, "ms": 1e-3, "None": 1}


@dataclasses.dataclass(frozen=True)
class NoiseParams:
    ps: Dict["str", float]
    t1: float
    t2: float
    tM: float
    tP: float
    tR: float

    @staticmethod
    def transmon(params) -> "NoiseParams":
        get_value = lambda value_unit: value_unit["value"] * units[value_unit["unit"]]

        t1 = get_value(params["hadamard_gate_time"])
        t2 = get_value(params["cnot_gate_time"])
        tM = get_value(params["qubit_measurement_time"])
        tP = get_value(params["qubit_preparation_time"])
        tR = get_value(params["qubit_reset_time"])

        T1 = get_value(params["T1_relaxation_time"])
        T2 = get_value(params["T2_dephasing_time"])

        F1 = get_value(params["hadamard_gate_fidelity"])
        F2 = get_value(params["cnot_gate_fidelity"])
        FM = get_value(params["measurement_fidelity"])
        FP = get_value(params["preparation_fidelity"])
        FR = get_value(params["reset_fidelity"])

        ps = {}
        ps["idle_1"] = NoiseParams.p_idling(t1, T1, T2)
        ps["idle_2"] = NoiseParams.p_idling(t2, T1, T2)
        ps["idle_M"] = NoiseParams.p_idling(tM, T1, T2)
        ps["idle_R"] = NoiseParams.p_idling(tR, T1, T2)
        ps["idle_P"] = NoiseParams.p_idling(tP, T1, T2)
        ps["gate_1"] = NoiseParams.F_to_p(F1)
        ps["gate_2"] = NoiseParams.F_to_p(F2)
        ps["P"] = NoiseParams.F_to_p(FP)
        ps["M"] = NoiseParams.F_to_p(FM)
        ps["R"] = NoiseParams.F_to_p(FR)
        ps["MR"] = ps["M"] + ps["R"]

        return NoiseParams(ps, t1, t2, tM, tP, tR)

    @staticmethod
    def F_to_p(F):
        return 2 * (1 - F)

    @staticmethod
    def p_idling(t, T1, T2):
        inf = 1 / 2 - 1 / 6 * exp(-t / T1) - 1 / 3 * exp(-t / T2)
        return NoiseParams.F_to_p(1 - inf)


ANY_CLIFFORD_1_OPS = {"H", "I"}
ANY_CLIFFORD_2_OPS = {"CX"}
RESET_OPS = {"R", "RX", "RY"}
MEASURE_OPS = {"M", "MX", "MY", "MR"}
ANNOTATION_OPS = {
    "OBSERVABLE_INCLUDE",
    "DETECTOR",
    "SHIFT_COORDS",
    "QUBIT_COORDS",
    "TICK",
}


@dataclasses.dataclass(frozen=True)
class NoiseModel:
    idle: float
    measure_reset_idle: float
    noisy_gates: Dict[str, float]
    any_gate_1: Optional[float] = None
    any_gate_2: Optional[float] = None

    @staticmethod
    def transmon(ps) -> "NoiseModel":
        return NoiseModel(
            idle=ps["idle_2"],
            measure_reset_idle=ps["idle_M"],
            noisy_gates={
                "CX": ps["gate_2"],
                "H": ps["gate_1"],
                "R": ps["R"],
                "M": ps["M"],
                "MR": ps["M"],
                "P": ps["P"],
            },
        )

    def noisy_op(
        self, op: stim.CircuitInstruction, p: float
    ) -> Tuple[stim.Circuit, stim.Circuit, stim.Circuit]:
        pre = stim.Circuit()
        mid = stim.Circuit()
        post = stim.Circuit()
        targets = op.targets_copy()
        args = op.gate_args_copy()
        if p > 0:
            if op.name in ANY_CLIFFORD_1_OPS:
                post.append_operation("DEPOLARIZE1", targets, p)

            elif op.name in ANY_CLIFFORD_2_OPS:
                post.append_operation("DEPOLARIZE2", targets, p)

            elif op.name in RESET_OPS or op.name in MEASURE_OPS:
                if op.name in RESET_OPS:
                    post.append_operation(
                        "Z_ERROR" if op.name.endswith("X") else "X_ERROR", targets, p
                    )

                if op.name in MEASURE_OPS:
                    pre.append_operation(
                        "Z_ERROR" if op.name.endswith("X") else "X_ERROR", targets, p
                    )

            else:
                raise NotImplementedError(repr(op))

        mid.append_operation(op.name, targets, args)
        return pre, mid, post

    def noisy_circuit(self, circuit: stim.Circuit) -> stim.Circuit:
        result = stim.Circuit()

        current_moment_pre = stim.Circuit()
        current_moment_mid = stim.Circuit()
        current_moment_post = stim.Circuit()

        measured_or_reset_qubits = set()
        used_qubits = set()
        qs = set(range(circuit.num_qubits))

        def flush():
            nonlocal result
            if not current_moment_mid:
                return

            # Apply idle depolarization rules.
            idle_qubits = sorted(qs - used_qubits)
            if used_qubits and idle_qubits and self.idle > 0:
                current_moment_post.append_operation(
                    "DEPOLARIZE1", idle_qubits, self.idle
                )

            idle_qubits = sorted(qs - measured_or_reset_qubits)
            if measured_or_reset_qubits and idle_qubits and self.measure_reset_idle > 0:
                current_moment_post.append_operation(
                    "DEPOLARIZE1", idle_qubits, self.measure_reset_idle
                )

            # Move current noisy moment into result.
            result += current_moment_pre
            result += current_moment_mid
            result += current_moment_post

            used_qubits.clear()
            current_moment_pre.clear()
            current_moment_mid.clear()
            current_moment_post.clear()
            measured_or_reset_qubits.clear()

        for op in circuit:
            if isinstance(op, stim.CircuitRepeatBlock):
                flush()
                result += self.noisy_circuit(op.body_copy(), qs=qs) * op.repeat_count

            elif isinstance(op, stim.CircuitInstruction):
                if op.name == "TICK":
                    flush()
                    result.append_operation("TICK", [])
                    continue

                if op.name in self.noisy_gates:
                    p = self.noisy_gates[op.name]

                elif self.any_gate_1 is not None and op.name in ANY_CLIFFORD_1_OPS:
                    p = self.any_gate_1

                elif self.any_gate_1 is not None and op.name in ANY_CLIFFORD_2_OPS:
                    p = self.any_gate_2

                elif op.name in ANNOTATION_OPS:
                    p = 0
                else:
                    raise NotImplementedError(repr(op))

                pre, mid, post = self.noisy_op(op, p)
                current_moment_pre += pre
                current_moment_mid += mid
                current_moment_post += post

                # Ensure the circuit is not touching qubits multiple times per tick.
                touched_qubits = {
                    t.value
                    for t in op.targets_copy()
                    if t.is_x_target
                    or t.is_y_target
                    or t.is_z_target
                    or t.is_qubit_target
                }
                if op.name in ANNOTATION_OPS:
                    touched_qubits.clear()
                # Hack: turn off this assertion off for now since correlated errors are built into circuit.
                assert touched_qubits.isdisjoint(used_qubits), repr(
                    current_moment_pre + current_moment_mid + current_moment_post
                )
                if op.name in ANY_CLIFFORD_1_OPS or op.name in ANY_CLIFFORD_2_OPS:
                    used_qubits |= touched_qubits

                if op.name in MEASURE_OPS or op.name in RESET_OPS:
                    measured_or_reset_qubits |= touched_qubits
            else:
                raise NotImplementedError(repr(op))
        flush()

        return result
