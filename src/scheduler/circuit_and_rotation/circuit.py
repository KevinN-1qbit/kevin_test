"""
Contains:

1) a Rotation class for a single rotation or measurement, and
2) a Circuit class representing an entire quantum algorithm by an ordered
sequence of Pi8 rotations, Pi4 rotations and measurements.
"""
from __future__ import annotations

from typing import Literal, Iterator, Iterable
import functools
import dataclasses
import pprint
import textwrap

from attr import field

PI8 = 1
PI4 = 2
MEASUREMENT = -1
TURN = 3
RotationType = Literal[-1, 1, 2, 3]


@dataclasses.dataclass(frozen=False)
class Rotation:
    """For a single rotation"""

    ind: int  # Index of the rotation in the original circuit
    operation_type: RotationType  # Pi8, Pi4, or Measurement
    operation_sign: Literal["+", "-"]

    # The numbers of the qubits where the X/Z edges are required.
    # I.e. if x={3, 8}, then the X-edges of qubits 3 and 8 are required.
    # If z={5, 8} also, then we see that we are using both X and Z edges
    # of qubit 8, meaning an operation on Y.
    x: set[int]
    y: set[int]
    z: set[int]

    @staticmethod
    def from_iterables(
        ind: int,
        type_: RotationType,
        sign_,
        x: Iterable[int],
        y: Iterable[int],
        z: Iterable[int],
    ) -> Rotation:
        return Rotation(ind, type_, sign_, set(x), set(y), set(z))

    @property
    def rotation_active_edges(self) -> set[tuple[str, Literal["X", "Z"]]]:
        """Returns something like {(3, "X"), (8, "X"), (5, "Z"), (8, "Z")}

        Specifically, if:
            x={3, 8} and z={5, 8},
        Then it would return:
            {(3, "X"), (8, "X"), (5, "Z"), (8, "Z")}
        """
        active_edges: set[tuple[str, Literal["X", "Z"]]] = {
            ("q" + str(qb), "X") for qb in self.x | self.y
        }
        active_edges |= {("q" + str(qb), "Z") for qb in self.z | self.y}
        return active_edges

    @property
    def active_qubit(self) -> set[int]:
        return self.x | self.y | self.z

    def __str__(self) -> str:
        s = ""
        s += f"\nind={self.ind}"
        s += f"\ntype={self.operation_type}"
        s += f"\nx={self.x}"
        s += f"\nz={self.z}"
        return s


@dataclasses.dataclass(frozen=True)
class Circuit:
    """Contains Many rotations"""

    rotations: list[Rotation]
    num_qubits: int
    name: str
    assignments: dict = dataclasses.field(default_factory=dict)

    def __getitem__(self, key: int) -> Rotation:
        """A convenience, to easily access rotations"""
        return self.rotations[key]

    def __iter__(self) -> Iterator[Rotation]:
        return iter(self.rotations)

    def __post_init__(self):
        new_assignments = {qubit: qubit for qubit in range(self.num_qubits)}
        self.update_assignments(new_assignments)

    @functools.cached_property
    def inds_all(self) -> range:
        return range(len(self.rotations))

    @functools.cached_property
    def inds_pi8_rots(self) -> set[int]:
        return {r.ind for r in self.rotations if r.operation_type == PI8}

    @functools.cached_property
    def inds_pi4_rots(self) -> set[int]:
        return {r.ind for r in self.rotations if r.operation_type == PI4}

    @functools.cached_property
    def inds_meas(self) -> set[int]:
        return {r.ind for r in self.rotations if r.operation_type == MEASUREMENT}

    @property
    def inds_turn(self) -> set[int]:
        return {r.ind for r in self.rotations if r.operation_type == TURN}

    @functools.cached_property
    def inds_pi4_rots_and_meas(self) -> set[int]:
        return self.inds_pi4_rots | self.inds_meas

    def __str__(self) -> str:
        rotation_str = textwrap.indent(pprint.pformat(self.rotations), "\t")
        s = ""
        s += f"\nrotations=\n{rotation_str}"
        s += f"\ninds_pi8_rots={self.inds_pi8_rots}"
        s += f"\ninds_pi4_rots={self.inds_pi4_rots}"
        s += f"\ninds_meas={self.inds_meas}"
        return s

    def update_rotations(self, new_rotations: list[Rotation]):
        object.__setattr__(self, "rotations", new_rotations)

    def update_assignments(self, new_assignments: dict):
        object.__setattr__(self, "assignments", new_assignments)

    def add_turn_qubits(self, qubits: dict):
        # get initial angle each qubit is facing the bus tiles
        current_angle = {}
        for id, q in qubits.items():
            current_angle[id] = q

        output_rotations = list()
        index = 0
        for rotation in self.rotations:
            for qubit in rotation.rotation_active_edges:
                if qubit[1] == "X" and current_angle[qubit[0]] == "Z":
                    output_rotations.append(
                        Rotation(index, TURN, "+", {int(qubit[0][1:])}, set(), set())
                    )
                    index += 1
                    current_angle[qubit[0]] = "X"
                elif qubit[1] == "Z" and current_angle[qubit[0]] == "X":
                    output_rotations.append(
                        Rotation(index, TURN, "+", set(), set(), {int(qubit[0][1:])})
                    )
                    index += 1
                    current_angle[qubit[0]] = "Z"
            output_rotations.append(
                Rotation(
                    index,
                    rotation.operation_type,
                    rotation.operation_sign,
                    rotation.x,
                    set(),
                    rotation.z,
                )
            )
            index += 1
        self.update_rotations(output_rotations)

    def update_patches_in_rotations(self, assignments: dict):
        """Update the patches for the new assignments in the rotations"""
        # update assignments container
        self.update_assignments(assignments)

        for idx, r in enumerate(self.rotations):
            new_set = set()
            for q in r.x:
                new_set.add(assignments[q])
            self.rotations[idx].x.clear()
            self.rotations[idx].x.update(new_set)

            new_set.clear()
            for q in r.y:
                new_set.add(assignments[q])
            self.rotations[idx].y.clear()
            self.rotations[idx].y.update(new_set)

            new_set.clear()
            for q in r.z:
                new_set.add(assignments[q])
            self.rotations[idx].z.clear()
            self.rotations[idx].z.update(new_set)
