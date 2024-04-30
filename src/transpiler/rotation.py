""" Contains a Rotation class for a single rotation or measurement
and the function to generate the rotations from an external file circuit.
"""
from __future__ import annotations

import os.path as osp
from typing import Literal, Optional, cast, Iterable
import dataclasses
from parsimonious import Grammar

PI8 = 1
PI4 = 2
MEASUREMENT = -1
TURN = 3
RotationType = Literal[-1, 1, 2, 3]

GRAMMAR = r"""
expr = rotate / measure

literal_rotate  = "Rotate"
literal_measure = "Measure"

colon = ":"

signed_number = ~"[-+]?[0-9]+"
sign          = ~"[-+]"

pauli = ~"[IXYZ]"

whitespace = ~"\\s*"

rotate  = literal_rotate  whitespace signed_number whitespace colon whitespace pauli+ whitespace
measure = literal_measure whitespace sign          whitespace colon whitespace pauli+ whitespace
"""
#         0               1          2             3          4     5          6      7


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


def parse_rotations(circuit_dir: str, split_y: bool) -> tuple[list[Rotation], int, str]:
    """Loads a circuit from "path".

    If "path" is the full path to a file, it is used.

    If "path" is one of the filenames in the "/tests/circuits_benchmark" dir,
    then the directory path is prepended to the filename.

    Returns:
        a list of rotations, the number of qubits, and the name of the circuit
    """

    gr = Grammar(GRAMMAR)

    rotations: list[Rotation] = []

    index = 0

    num_qubits: Optional[int] = None

    circuit_name = osp.basename(circuit_dir)

    with open(circuit_dir, "r") as f:
        for line in f:
            parsed = gr.parse(line).children[0]

            set_x: set[int] = set()
            set_y: set[int] = set()
            set_z: set[int] = set()

            list_y: list[int] = list()

            if num_qubits is None:
                num_qubits = len(parsed.children[6].children)
            else:
                assert num_qubits == len(parsed.children[6].children)

            for i, child in enumerate(parsed.children[6].children):
                if child.text == "I":
                    pass 
                elif child.text == "X":
                    set_x.add(i)
                elif child.text == "Y":
                    if split_y:
                        list_y.append(i)
                    else:
                        set_y.add(i)
                elif child.text == "Z":
                    set_z.add(i)


            if parsed.expr_name == "rotate":
                number = int(parsed.children[2].text)
                sign = "+" if number >= 0 else "-"
                angle = PI8 if number in {-1, 1} else PI4
            elif parsed.expr_name == "measure":
                sign = cast(Literal["+", "-"], parsed.children[2].text)
                angle = MEASUREMENT
            else:
                raise ValueError("This should be unreachable")

            if split_y and list_y:
                if (len(list_y) % 2) == 0:
                    rotations.append(
                        Rotation(
                            index,
                            PI4,
                            "+",
                            set(),
                            set(),
                            {list_y[0]},
                        )
                    )
                    index += 1

                    rotations.append(
                        Rotation(index, PI4, "+", set(), set(), set(list_y[1:]))
                    )
                    index += 1

                    rotations.append(
                        Rotation(index, PI8, "+", set_x | set(list_y), set(), set_z)
                    )
                    index += 1

                    rotations.append(
                        Rotation(
                            index,
                            PI4,
                            "+",
                            set(),
                            set(),
                            {list_y[0]},
                        )
                    )
                    index += 1

                    rotations.append(
                        Rotation(index, PI4, "+", set(), set(), set(list_y[1:]))
                    )
                    index += 1
                else:
                    rotations.append(
                        Rotation(index, PI4, "+", set(), set(), set(list_y))
                    )
                    index += 1

                    rotations.append(
                        Rotation(index, PI8, "+", set_x | set(list_y), set(), set_z)
                    )
                    index += 1

                    rotations.append(
                        Rotation(index, PI4, "-", set(), set(), set(list_y))
                    )
                    index += 1
            else:
                rotations.append(
                    Rotation(
                        index,
                        angle,
                        sign,
                        set_x,
                        set_y,
                        set_z,
                    )
                )
                index += 1

    if num_qubits is None:
        raise ValueError("There were no valid rotations in the file given")

    return (rotations, num_qubits, circuit_name)
