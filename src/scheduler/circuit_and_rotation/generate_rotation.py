""" Functions for loading quantum circuits in Pi8 format
 and processing them into commuting layers of instructions """

import os.path as osp
from typing import Literal, Optional, cast

from scheduler.circuit_and_rotation import circuit
from scheduler.circuit_and_rotation.circuit import (
    PI8,
    PI4,
    MEASUREMENT,
    Rotation,
)
from helpers import paths
from parsimonious import Grammar


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


def parse_rotations(circuit_dir: str, split_y: bool) -> circuit.Circuit:
    """Loads a circuit from "path".

    If "path" is the full path to a file, it is used.

    If "path" is one of the filenames below from the "/tests/circuits" dir,
    then the directory path is prepended to the filename.

    Compiled_grover7_20210708-22-35.txt
    Compiled_qfe_10_3_20210715-19-21.txt
    Compiled_qfe_35_5_20210720-09-03.txt
    Compiled_qfe_35_25_20210720-09-53.txt
    Compiled_QFT8_before_20210706-17-11.txt
    Compiled_QFT16_before_20210706-18-38.txt
    Compiled_QFTAdd8_before_20210708-22-57.txt
    Compiled_random_walk_512_20210714-00-02.txt
    testMultipleSections.txt
    testSingleSection.txt

    Returns:
        a circuit.Circuit object
    """

    gr = Grammar(GRAMMAR)

    rotations: list[Rotation] = []

    index = 0

    num_qubits: Optional[int] = None

    circuit_name = osp.basename(circuit_dir)
    if not osp.exists(circuit_dir):
        circuit_dir = osp.join(paths.get_benchmark_circuits_dir(), circuit_dir)
        assert osp.exists(circuit_dir)

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
                match child.text:
                    case "I":
                        pass
                    case "X":
                        set_x.add(i)
                    case "Y":
                        if split_y:
                            list_y.append(i)
                        else:
                            set_y.add(i)
                    case "Z":
                        set_z.add(i)

            match parsed.expr_name:
                case "rotate":
                    number = int(parsed.children[2].text)
                    sign = "+" if number >= 0 else "-"
                    angle = PI8 if number in {-1, 1} else PI4
                case "measure":
                    sign = cast(Literal["+", "-"], parsed.children[2].text)
                    angle = MEASUREMENT
                case _:
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

    return circuit.Circuit(rotations, num_qubits, circuit_name)


def convert_Y_operators(
    _circuit_: circuit.Circuit, non_corner_patches: set
) -> circuit.Circuit:
    """Convert Y operators into X and Z operators

    Args:
        _circuit_ (circuit.Circuit): old circuit with Y operators

    Returns:
        circuit.Circuit: new circuit with only X and Z operators
    """

    new_rotations: list[circuit.Rotation] = []
    index = 0

    for r in _circuit_.rotations:
        # get qubits assigned to non-corner data qubit patches
        y_change = set()
        for y in r.y:
            # get non-corner qubits in Y
            if y in non_corner_patches:
                y_change.add(y)

        # get qubits assigned to corner data qubit patches
        y_keep = r.y - y_change

        # update rotations
        if len(y_change) > 0:
            if len(y_change) % 2 == 0:
                new_rotations.append(
                    circuit.Rotation(index, PI4, "+", set(), set(), y_change[0])
                )
                index += 1
                new_rotations.append(
                    circuit.Rotation(index, PI4, "+", set(), set(), y_change[1:])
                )
                index += 1
                new_rotations.append(
                    circuit.Rotation(
                        index, PI8, "+", r.x | y_change | y_keep, set(), r.z | y_keep
                    )
                )
                index += 1
                new_rotations.append(
                    circuit.Rotation(index, PI4, "-", set(), set(), y_change[0])
                )
                index += 1
                new_rotations.append(
                    circuit.Rotation(index, PI4, "-", set(), set(), y_change[1:])
                )
                index += 1
            else:
                new_rotations.append(
                    circuit.Rotation(index, PI4, "+", set(), set(), y_change)
                )
                index += 1
                new_rotations.append(
                    circuit.Rotation(
                        index, PI8, "+", r.x | y_change | y_keep, set(), r.z | y_keep
                    )
                )
                index += 1
                new_rotations.append(
                    circuit.Rotation(index, PI4, "-", set(), set(), y_change)
                )
                index += 1
        elif len(y_keep) > 0:
            new_rotations.append(
                circuit.Rotation(
                    r.ind,
                    r.operation_type,
                    r.operation_sign,
                    r.x | y_keep,
                    set(),
                    r.z | y_keep,
                )
            )
            index += 1
        else:
            new_rotations.append(r)
            index += 1

    _new_circuit_ = circuit.Circuit(new_rotations, _circuit_.num_qubits, _circuit_.name)
    _new_circuit_.update_assignments(_circuit_.assignments)

    for q in _new_circuit_.rotations:
        assert len(q.y) == 0, "Must remove all Y operators from the new circuit"

    return _new_circuit_
