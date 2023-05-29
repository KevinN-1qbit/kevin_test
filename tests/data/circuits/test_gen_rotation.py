import pytest

from scheduler.circuit_and_rotation import circuit, generate_rotation as m
from scheduler.circuit_and_rotation.circuit import (
    PI8,
    PI4,
    MEASUREMENT,
)  # pylint: disable=unused-import

rotations = [
    circuit.Rotation(0, PI4, True, {0, 2}, {2}),
    circuit.Rotation(1, PI8, True, {4}, {4, 5}),
    circuit.Rotation(2, MEASUREMENT, True, {3}, {3}),
]

small_rotation_tests = [
    (circuit.Circuit(rotations, 6), [{0, 1, 2}, {2}, {0}, {0, 2}, {1}]),
]


@pytest.mark.parametrize("circuit_, " "expected_inds", small_rotation_tests)
def test_circuit(
    circuit_: circuit.Circuit,
    expected_inds: list[set[int]],
) -> None:
    assert set(circuit_.inds_all) == expected_inds[0]
    assert circuit_.inds_meas == expected_inds[1]
    assert circuit_.inds_pi4_rots == expected_inds[2]
    assert circuit_.inds_pi4_rots_and_meas == expected_inds[3]
    assert circuit_.inds_pi8_rots == expected_inds[4]


lys_circuit_test = [
    (
        "testSingleSection.txt",
        [{0, 1, 2, 3, 4, 5, 6, 7, 8}, {7, 8}, {2, 4, 6}, {2, 4, 6, 7, 8}, {0, 1, 3, 5}],
    ),
]
