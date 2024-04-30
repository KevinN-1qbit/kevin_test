import pytest
from unittest.mock import patch, Mock
from worker.transpiler_node import transpiler_function

# TODO: Fix this code as it's not runnable

# @pytest.fixture
# def mock_message():
#     return {
#         "file_path": "input.qasm",
#         "language": "qasm",
#         "timeout": 10,
#         "epsilon": 0.01,
#         "request_id": "test_request",
#     }


# @patch("worker.transpiler_function.subprocess.run")
# @patch("worker.transpiler_function.Circuit")
# def test_transpiler_function_success(mock_circuit, mock_subprocess, mock_message):
#     # Mock subprocess.run to simulate a successful transpiler execution
#     mock_subprocess.return_value.returncode = 0

#     # Mock the Circuit object
#     mock_transpiled_circuit = Mock()
#     mock_transpiled_circuit.name = "test_circuit"
#     mock_transpiled_circuit.num_qubits = 5
#     mock_transpiled_circuit.total_operations = 20
#     mock_transpiled_circuit.pi8 = 8
#     mock_transpiled_circuit.pi4 = 12
#     mock_transpiled_circuit.measurements = 2
#     mock_circuit.return_value = mock_transpiled_circuit

#     # Mock Redis interactions
#     mock_redis = Mock()
#     with patch("worker.transpiler_function.redis", mock_redis):
#         transpiler_function(mock_message)

#         # Verify the pushed message
#         report_topic = mock_message["request_id"]
#         expected_report = {
#             "circuit_name": "test_circuit" + "_transpile.txt",
#             "instruction_set": "pauli_rotations",
#             "num_data_qubits_required": 5,
#             "total_num_operations": 20,
#             "num_non_clifford_operations": 8,
#             "num_clifford_operations": 12,
#             "num_logical_measurements": 2,
#             "transpiled_circuit_path": "test_circuit" + "_transpile.txt",
#         }

#         # Check if rpush was called with the expected arguments
#         mock_redis.rpush.assert_called_once_with(report_topic, expected_report)


# @patch("worker.subprocess.transpiler_function.run")
# @patch("worker.transpiler.transpiler_function.Circuit")
# def test_transpiler_function_failure(mock_circuit, mock_subprocess, mock_message):
#     # Mock subprocess.run to simulate a failure in transpiler execution
#     mock_subprocess.side_effect = Exception("Transpiler error")

#     # Mock the Circuit object
#     mock_circuit.return_value = Mock()

#     # Mock Redis interactions
#     mock_redis = Mock()
#     with patch(
#         "worker.transpiler.transpiler_function.redis", mock_redis
#     ):
#         transpiler_function(mock_message)

#         # Verify the pushed message
#         report_topic = mock_message["request_id"]
#         expected_report = {
#             "status": "failed",
#             "message": "Transpiler error",
#         }

#         # Check if rpush was called with the expected arguments
#         mock_redis.rpush.assert_called_once_with(report_topic, expected_report)
