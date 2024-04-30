"""Contains a Circuit class representing an entire quantum algorithm by an ordered
sequence of Pi8 rotations, Pi4 rotations and measurements.
"""

from __future__ import annotations
import dataclasses

from src.transpiler.rotation import (
    Rotation,
    parse_rotations,
    PI8,
    PI4,
    MEASUREMENT,
    TURN,
)


class Circuit:
    pi8: int  # num of PI8 rotations in the circuit
    pi4: int  # num of PI4 rotations in the circuit
    measurements: int  # num of measurements in the circuit (must be equal to num_qubits)
    rotations: list[Rotation]
    name: str

    def __init__(self, circuit_dir: str):
        """Read input circuit from external file"""
        self.rotations, self.num_qubits, self.name = parse_rotations(
            circuit_dir=circuit_dir, split_y=False
        )

    @property
    def total_operations(self):
        """Total number of operations in the circuit"""
        return self.pi8 + self.pi4 + self.measurements + self.turns

    @property
    def pi8(self) -> int:
        """Number of PI8 rotations in the circuit"""
        return len({r.ind for r in self.rotations if r.operation_type == PI8})

    @property
    def pi4(self) -> int:
        """Number of PI4 rotations in the circuit"""
        return len({r.ind for r in self.rotations if r.operation_type == PI4})

    @property
    def measurements(self) -> int:
        """Number of measurements in the circuit (must be equal to num_qubits)"""
        return len({r.ind for r in self.rotations if r.operation_type == MEASUREMENT})

    @property
    def turns(self) -> int:
        """Number of measurements in the circuit (must be equal to num_qubits)"""
        return len({r.ind for r in self.rotations if r.operation_type == TURN})
