"""tests parse.py"""

import itertools as it

from pytest import mark

from utils import parse as m
from utils import paths


def test_ParseQasm_test_all_gates() -> None:
    filename = paths.get_abs_path_to_input_file(
        "test_circuits/qasm_test_all_gates.qasm"
    )
    parse_command = m.ParseQasm(filename)

    assert parse_command.instructions == [
        # u3(0.1) q[0]
        ("u3(0.1)", [0]),
        # u2(0.4) q[1]
        ("u2(0.4)", [1]),
        # u1(0.6) q[2]
        ("u1(0.6)", [2]),
        # cx q[0], q[1]
        ("cx", [0, 1]),
        # cx q[1],q[2]
        ("cx", [1, 2]),
        # id q[2]
        ("id", [2]),
        # x q[0]
        ("x", [0]),
        # y q[1]
        ("y", [1]),
        # z q[2]
        ("z", [2]),
        # h q[0]
        ("h", [0]),
        # s q[1]
        ("s", [1]),
        # sdg q[2]
        ("sdg", [2]),
        # t q[0]
        ("t", [0]),
        # tdg q[1]
        ("tdg", [1]),
        # rx(0.7) q[0]
        ("rx(0.7)", [0]),
        # ry(0.8) q[1]
        ("ry(0.8)", [1]),
        # rz(0.5*pi) q[1]
        ("s", [1]),
        # rz(pi) q[2]
        ("s", [2]),
        ("s", [2]),
        # cz q[0], q[1]
        ("cz", [0, 1]),
        # cy q[1], q[2]
        ("cy", [1, 2]),
        # ch q[2], q[0]
        ("ch", [2, 0]),
        # crz(pi) q[0], q[1]
        ("s", [0, 1]),
        ("s", [0, 1]),
        # cu1(1.1) q[1], q[2]
        ("cu1(1.1)", [1, 2]),
        # cu3(1.2) q[2], q[0]
        ("cu3(1.2)", [2, 0]),
        # ccx q[0],q[1], q[2]
        ("h", [2]),
        ("cx", [1, 2]),
        ("tdg", [2]),
        ("cx", [0, 2]),
        ("t", [2]),
        ("cx", [1, 2]),
        ("tdg", [2]),
        ("cx", [0, 2]),
        ("t", [1]),
        ("t", [2]),
        ("h", [2]),
        ("cx", [0, 1]),
        ("t", [0]),
        ("tdg", [1]),
        ("cx", [0, 1]),
        # swap q[0],q[1]
        # cswap q[0],q[1],q[2]
        # measure q[0] -> c[0]
        # barrier q[0],q[1],q[2]
    ]

    assert parse_command.num_qubits == 3

    print(f"\n\ntest_ParseQasm_test_all_gates passed\n\n\n")


# if __name__ == "__main__":
#     test_ParseQasm_test_all_gates()


# pylint: disable=invalid-name
# noinspection PyPep8Naming
def test_ParseQasm_qubit_renumbering() -> None:
    filename = paths.get_abs_path_to_input_file("test_circuits/qasm_test_10_lines.qasm")
    parse_command = m.ParseQasm(filename)

    assert parse_command.instructions == [
        ("h", [0]),
        ("t", [2]),
        ("t", [1]),
        ("t", [0]),
        ("cx", [1, 2]),
        ("cx", [0, 1]),
    ]

    print(f"\n\ntest_ParseQasm_qubit_renumbering passed\n\n\n")


# if __name__ == "__main__":
#     test_ParseQasm_qubit_renumbering()


# pylint: disable=invalid-name
# noinspection PyPep8Naming
@mark.parametrize(
    "rel_path,n_qubits",
    [
        ("test_circuits/qasm_test_5_lines.qasm", 1),
        ("test_circuits/qasm_test_10_lines.qasm", 3),
        ("test_circuits/qasm_test_50_lines.qasm", 5),
    ],
)
def test_ParseQasm_qubit_renumbering_range(rel_path: str, n_qubits: int) -> None:
    filename = paths.get_abs_path_to_input_file(rel_path)

    parse_command = m.ParseQasm(filename)

    # Something like: [('h', [0]), ('t', [2]), ('t', [1]),
    #                  ('t', [0]), ('cx', [1, 2]), ('cx', [0, 1])]
    # pylint: disable=unsubscriptable-object
    instructions: list[tuple[str, list[int]]] = parse_command.instructions

    num_qubits: int = parse_command.num_qubits

    assert num_qubits == n_qubits
    qubit_numbers = set(
        it.chain.from_iterable(instruction[1] for instruction in instructions)
    )
    assert list(sorted(qubit_numbers)) == list(range(num_qubits))

    print(f"\n\ntest_ParseQasm_qubit_renumbering_range passed\n\n\n")


# pylint: disable=line-too-long
# if __name__ == '__main__': test_ParseQasm_qubit_renumbering_range("data/input/data_stats_test_folder/qasm_test_5_lines.qasm", 1)
# if __name__ == '__main__': test_ParseQasm_qubit_renumbering_range("data/input/data_stats_test_folder/qasm_test_10_lines.qasm", 3)
# if __name__ == '__main__': test_ParseQasm_qubit_renumbering_range("data/input/data_stats_test_folder/qasm_test_50_lines.qasm", 5)


# pylint: disable=bad-whitespace
# noinspection PyPep8Naming
def test_ParseQasm_with_rz_gates() -> None:
    filename = paths.get_abs_path_to_input_file(
        "test_circuits/qasm_test_10_lines_with_rz.qasm"
    )
    parse_command = m.ParseQasm(filename)

    # There are 2 additional rz(pi) gates added in qasm_test_10_lines_with_rz.qasm
    # rz(pi) is decomposed into 2 ('s') gates
    assert parse_command.instructions == [
        ("h", [0]),
        ("t", [2]),
        ("s", [1]),
        ("s", [1]),
        ("t", [1]),
        ("t", [0]),
        ("cx", [1, 2]),
        ("s", [2]),
        ("s", [2]),
        ("cx", [0, 1]),
    ]

    assert parse_command.num_qubits == 3


# pylint: disable=bad-whitespace
# noinspection PyPep8Naming
def test_ParseProjectQ() -> None:
    abs_path = paths.get_abs_path_to_input_file
    test_file = abs_path("test_circuits/projectq_measure_anc.txt")
    test_file_short = abs_path("test_circuits/projectq_measure_anc_short.txt")
    test_file_short_with_rz = abs_path(
        "test_circuits/projectq_measure_anc_short_with_rz.txt"
    )

    # Create an empty ProjectQ parser object
    projectq_parser = m.ParseProjectQ(test_file)

    # call the process_input(file_path) method
    gates, data_qubits = projectq_parser.process_input(test_file)
    expected_data_qubits = [0, 1, 2, 3, 4]
    expected_gates = [  # the first 10 lines of the file
        ("allocate", [5]),
        ("h", [5]),
        ("allocate", [0]),
        ("cx", [0, 5]),
        ("t", [0]),
        ("tdg", [5]),
        ("allocate", [1]),
        ("cx", [1, 5]),
        ("t", [5]),
        ("cx", [1, 0]),
    ]
    assert expected_data_qubits == sorted(data_qubits)
    assert expected_gates == gates[:10]
    assert projectq_parser.max_width == 7
    assert projectq_parser.num_qubits == 7

    # Create an empty ProjectQ parser object
    projectq_parser2 = m.ParseProjectQ(test_file_short)
    # call the break_into_sections() method
    expected_gate_count = 18
    expected_width = 4
    expected_result = [
        [
            ("h", [2]),
            ("cx", [0, 2]),
            ("t", [0]),
            ("tdg", [2]),
            ("cx", [1, 2]),
            ("t", [2]),
            ("measure", [2]),
        ],
        [("cx", [1, 0]), ("x", [3]), ("h", [2]), ("measure", [3])],
        [("x", [2]), ("measure", [2]), ("measure", [0])],
        [("tdg", [1]), ("t", [1]), ("h", [1]), ("measure", [1])],
        [],
    ]
    result = projectq_parser2.break_into_sections()
    assert expected_gate_count == projectq_parser2.gate_count
    assert expected_width == projectq_parser2.max_width
    assert expected_result == result
    assert projectq_parser2.first_ancilla_idx == 2

    # Create an empty ProjectQ parser object
    projectq_parser3 = m.ParseProjectQ(test_file_short_with_rz)
    # call the break_into_sections() method
    # Note the addition of 1 gate compared to projectq_parser2
    expected_gate_count = 19
    expected_width = 4
    expected_result = [
        [
            ("h", [2]),
            ("cx", [0, 2]),
            ("t", [0]),
            ("tdg", [2]),
            ("cx", [1, 2]),
            ("t", [2]),
            ("measure", [2]),
        ],
        # There is an additional rz(pi/2) gate added in projectq_measure_anc_short_with_rz.txt
        # Note the addition of a single "s" gate compared to projectq_parser2
        [("cx", [1, 0]), ("x", [3]), ("s", [3]), ("h", [2]), ("measure", [3])],
        [("x", [2]), ("measure", [2]), ("measure", [0])],
        [("tdg", [1]), ("t", [1]), ("h", [1]), ("measure", [1])],
        [],
    ]
    result = projectq_parser3.break_into_sections()
    assert expected_gate_count == projectq_parser3.gate_count
    assert expected_width == projectq_parser3.max_width
    assert expected_result == result
    assert projectq_parser3.first_ancilla_idx == 2


# if __name__ == "__main__": test_projectq()
