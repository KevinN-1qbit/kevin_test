import pytest
from utils import parse
from src.python_wrapper.Measure import Measure
from src.python_wrapper.LysCompiler_cpp_interface import LysCompiler


@pytest.mark.parametrize(
    "circuit_input",
    [
        "data/input/molecule_circuits/sk_mol_HH_recdep_4_dep_4.qasm",
        "data/input/test_circuits/qasm_test_50_lines.qasm",
    ],
)
def test_basis_conversion(circuit_input: str) -> None:
    circuit_input: str = circuit_input
    chosen_parser = parse.ParseQasm
    parse_command: type(parse.Parse) = chosen_parser(circuit_input, None)

    instructions = parse_command.instructions
    num_qubits = parse_command.num_qubits

    compiler = LysCompiler(instructions, num_qubits, pytest_mode=True)
    pauli_operators = compiler.basis_conversion("qasm")

    # Assert the last num_qubits operations in pauli_operators are of type Measure
    for i in range(num_qubits):
        operation = pauli_operators[-num_qubits + i]

        assert isinstance(
            operation, Measure
        ), "Last nb qubits operation in circuit is not of type Measure"

        assert operation.z == pow(
            2, num_qubits - i - 1
        ), "Measure operation is not on the correct qubit"
