""" Get statistics about the quantum circuit """

import dataclasses
from scheduler.circuit_and_rotation import circuit
from layout_processor.adjacency_graph import AdjacencyGraph


# class to store the stats of each qubit used in the circuit
@dataclasses.dataclass
class Qubit_Stats:
    id: int  # qubit ID
    assignment: int | None = 0  # data qubit patch to which this qubit is assigned
    X: int = 0  # nb X rotations requested for this qubit
    Y: int = 0  # nb Y rotations requested for this qubit
    Z: int = 0  # nb Z rotations requested for this qubit
    requests: int = 0  # total nb requestes for this qubit
    flips: int = (
        0  # nb of times a N request is followed by a M request, for N,M in {X,Y,Z}
    )
    affinity: dict = dataclasses.field(
        default_factory=dict
    )  # nb ot times this qubit is requested with another
    perc_affinity: dict = dataclasses.field(
        default_factory=dict
    )  # percentage of affinity
    not_together: dict = dataclasses.field(
        default_factory=dict
    )  # nb of times this qubit is not requested with another
    corner: bool = None  # if this qubit is assigned to a corner data qubit patch

    @property
    def XZ(self) -> int:
        return self.X + self.Z


def get_stats(_circuit_: circuit, qubit_tile_assignments: dict):
    qubits_info = dict()

    # initialize Qubit_Stats
    for tile in qubit_tile_assignments:
        qubits_info[tile] = Qubit_Stats(tile, tile)

    # get qubit requests
    qubits_info = get_qubit_requests_stats(qubits_info, _circuit_)

    # get qubit affinity matrix
    qubits_info = get_qubit_affinity_stats(qubits_info, _circuit_)

    # get qubit turns
    qubits_info = get_qubit_turn_stats(qubits_info, _circuit_)

    return qubits_info


def get_qubit_requests_stats(qubits_info: dict, _circuit_: circuit):
    """Number of times a qubit is requested
    requests_i = X_i + Y_i + Z_i, for all i in qubits
    """
    for rot in _circuit_.rotations:
        for q in rot.x:
            qubits_info[q].X += 1
        for q in rot.y:
            qubits_info[q].Y += 1
        for q in rot.z:
            qubits_info[q].Z += 1

    for q in qubits_info.values():
        q.requests = q.X + q.Y + q.Z
        assert q.requests > 0, "Qubit %d in the circuit is never requested" % q.id

    return qubits_info


def get_qubit_affinity_stats(qubits_info: dict, _circuit_: circuit):
    """Number of times a pair of qubits are requested together
    affinity_ij = i | j, for all i,j in qubit in rotation
    """
    for q1 in qubits_info.values():
        for q2 in qubits_info.values():
            if q1.id == q2.id:
                q1.affinity[q2.id] = None
            else:
                q1.affinity[q2.id] = 0

    for rot in _circuit_.rotations:
        active_qubit = list(rot.active_qubit)
        for i in range(0, len(active_qubit)):
            for j in range(i + 1, len(active_qubit)):
                qubits_info[active_qubit[i]].affinity[active_qubit[j]] += 1
                qubits_info[active_qubit[j]].affinity[active_qubit[i]] += 1

    for q1 in qubits_info.values():
        for q2, affinity in q1.affinity.items():
            if affinity is None:
                q1.perc_affinity[q2] = None
                q1.not_together[q2] = None
            else:
                q1.perc_affinity[q2] = affinity / q1.requests
                q1.not_together[q2] = q1.requests - affinity
    return qubits_info


def get_qubit_turn_stats(qubits_info: dict, _circuit_: circuit):
    """Number of times a qubit theoretically needs to be turned
    turn_i = (X->Z)_i + (Z->X)_i + 3 (X->Y)_i + 2 (Z->Y)_i, for all i in qubits
    (X->Z)_i: request X followed by request Z for qubit i
    """
    current_angle = ["X" for q in range(0, _circuit_.num_qubits)]

    for rot in _circuit_.rotations:
        for qubit in rot.x:
            if current_angle[qubit] == "Z":
                qubits_info[qubit].flips += 1
                current_angle[qubit] = "X"

        for qubit in rot.z:
            if current_angle[qubit] == "X":
                qubits_info[qubit].flips += 1
                current_angle[qubit] = "Z"

        for qubit in rot.y:
            # Y transforms to a Z-X-Z
            if current_angle[qubit] == "X":
                qubits_info[qubit].flips += 3
                current_angle[qubit] = "Z"
            elif current_angle[qubit] == "Z":
                qubits_info[qubit].flips += 2
        for qubit in rot.rotation_active_edges:
            if qubit[1] == "X" and current_angle[int(qubit[0][1:])] == "Z":
                current_angle[int(qubit[0][1:])] = "X"
                qubits_info[int(qubit[0][1:])].flips += 1
            elif qubit[1] == "Z" and current_angle[int(qubit[0][1:])] == "X":
                current_angle[int(qubit[0][1:])] = "Z"
                qubits_info[int(qubit[0][1:])].flips += 1
    return qubits_info


def update_qubits_assignments(
    qubits_info: dict, assignments: dict, adj_graph: AdjacencyGraph
):
    for qubit, patch in assignments.items():
        qubits_info[qubit].assignment = patch

        if adj_graph.qubit_angle["q" + str(patch)] == "B":
            qubits_info[qubit].corner = True
        else:
            qubits_info[qubit].corner = False
