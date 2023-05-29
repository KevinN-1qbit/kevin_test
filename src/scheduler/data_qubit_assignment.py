""" Solve the data qubit assignment problem, 
i.e., which qubits in the layout will be used by the circuit
"""

import random
from enum import Enum

import networkx as nx

from scheduler.circuit_and_rotation import circuit, circuit_stats
from layout_processor.adjacency_graph import (
    AdjacencyGraph,
    ComponentType,
)


# ! Move to graph library?
def get_corner_and_non_corner_data_patches(adj_graph: AdjacencyGraph):
    # get corner (XZ = Y) and non-corner data qubit patches
    corner = []
    non_corner = []
    for qubit, angle in adj_graph.qubit_angle.items():
        if angle == "B":
            corner.append(qubit[1:])
        else:
            non_corner.append(qubit[1:])
    return (corner, non_corner)


# ! Move to graph library?
def get_data_patches_in_same_crossings(
    graph: nx.Graph, corner_qubits: list
) -> list(list()):
    corners = []
    corner_found = set()
    for q1 in corner_qubits:
        # check if this qubit had its corner found
        if q1 in corner_found:
            continue

        # get qubit 1 neighbors
        this_corner = [q1]
        neighbors = set(graph.neighbors(("q" + str(q1), "X")))
        neighbors.update(set(graph.neighbors(("q" + str(q1), "Z"))))

        # search among the other corner qubits those that share the same neighbors
        for q2 in corner_qubits:
            if q1 == q2:
                continue

            # get qubit 2 neighbors
            neighbors2 = set(graph.neighbors(("q" + str(q2), "X")))
            neighbors2.update(set(graph.neighbors(("q" + str(q2), "Z"))))
            common = neighbors & neighbors2

            # if qubits 1 and 2 share a neighbor, they belong to the same corner
            if len(common) > 0:
                this_corner.append(q2)
                neighbors = neighbors | neighbors2
        corners.append(this_corner)
        corner_found.update(this_corner)
    return corners


class AssignPolicy(Enum):
    MANUAL = 1
    RANDOM = 2
    RANDOM_CORNER = 3
    CLUSTER_CROSSING = 4
    AFFINITY = 5


def solve_data_qubit_assignment(
    _circuit_: circuit.Circuit,
    _adj_graph_: AdjacencyGraph,
    policy: AssignPolicy,
    seed=1,
    threshold_affinity=0.4,
    threshold_repulse=0.1,
):
    """Solve the data qubit assignment problem, i.e., given a set of qubits requested
    in the circuit assign them to data qubits in the device layout. The assignments
    are stored in the _circuit_.assignments container.

    Args:
        _circuit_: circuit
        _adj_graph_: adjacency graph dervied from the layout
        policy: {MANUAL, RANDOM, RANDOM_CORNER, CLUSTER_CROSSING}
            Assignment policy.
            - MANUAL, manually assignment qubits to patches;
            - RANDOM, randomly assign qubits to components;
            - RANDOM_CORNER, randomly assign most requested qubits to patchs in corners,
                and randomly assign the remaining to non-corners;
            - CLUSTER_CROSSING, seed qubits randomly weighted by their nb of requests
                assign the seed to a random crossing then, leech others qubits using a
                decision criteria based on the affinity metrics.
        seed: RNG seed
        threshold_affinity, threshold_repulse: parameters for the CLUSTER_CORNER policy

    Return:
        assignments: qubits to patches assignments
        non_corner_patches: set of patches with a qubits assigned that is not a corner
    """

    # fixed seed to always generate the same assignments
    random.seed(seed)

    # current qubit assignments
    assignments = {n: n for n in range(_circuit_.num_qubits)}

    # get circuit stats
    qubits_info = circuit_stats.get_stats(_circuit_, assignments)

    if policy == AssignPolicy.MANUAL:
        # manual assignment
        choice = [0, 3, 12, 15]
        assignments = {qubit: patch for qubit, patch in enumerate(choice)}

    elif policy == AssignPolicy.RANDOM:
        # random assignment
        all_qubits = [qubit[1:] for qubit in _adj_graph_.qubit_angle.keys()]
        assert _circuit_.num_qubits <= len(all_qubits), "Not enough qubits to assign"

        for qubit in qubits_info.values():
            choice = random.choice(all_qubits)
            assignments[qubit.id] = int(choice)
            all_qubits.remove(choice)

    elif policy == AssignPolicy.RANDOM_CORNER:
        # random corner assignment (best for time saving):
        #   randomly assign to qubits in corners first, avoiding turn operations
        #   then, randomly assign the remaining to other qubits

        # get corner (XZ = Y) and non-corner data qubit patches
        patch_Y, non_patch_Y = get_corner_and_non_corner_data_patches(_adj_graph_)
        assert _circuit_.num_qubits <= len(patch_Y) + len(
            non_patch_Y
        ), "Not enough qubits to assign"

        # sort by number of times the angle required by each qubit is flipped in the circuit
        qubits_by_flips = list(qubits_info.values())
        qubits_by_flips.sort(key=lambda x: x.flips, reverse=True)

        for idx, qubit in enumerate(qubits_by_flips):
            if len(patch_Y) > 0:
                # assign qubits with most flips to corners
                choice = random.choice(patch_Y)
                assignments[qubit.id] = int(choice)
                patch_Y.remove(choice)
            else:
                # assign remaining qubits to non-corners
                choice = random.choice(non_patch_Y)
                assignments[qubit.id] = int(choice)
                non_patch_Y.remove(choice)

    elif policy == AssignPolicy.CLUSTER_CROSSING:
        # 'seed corner' assignment:
        #      seed qubits randomly weighted by their nb of requests
        #      assign the seed to a random corner
        #      then, leech others qubits using a decision criteria based on the affinity metrics

        assignments = {n: None for n in range(_circuit_.num_qubits)}

        # get corner and non-corner qubits
        patch_Y, non_patch_Y = get_corner_and_non_corner_data_patches(_adj_graph_)
        assert _circuit_.num_qubits <= len(patch_Y) + len(
            non_patch_Y
        ), "Not enough qubits to assign"

        # get qubits belonging to the same corners
        crossings = get_data_patches_in_same_crossings(_adj_graph_.nx_graph, patch_Y)

        # sort qubits by flips
        qubits_by_flips = list(qubits_info.values())
        qubits_by_flips.sort(key=lambda x: x.flips, reverse=True)

        # generate list of possible seeds
        seed_pos, seed_probs = [], []
        for idx, qubit in enumerate(qubits_by_flips):
            seed_pos.append(idx)
            seed_probs.append(qubit.flips)

        while len(crossings) > 0 and len(seed_pos) > 0:
            # choose seed
            this_seed = random.choices(seed_pos, weights=seed_probs, k=1)
            qubit_seed = qubits_info[this_seed[0]]
            seed_pos.remove(this_seed[0])

            # choose crossing
            this_crossing = random.choice(crossings)
            crossings.remove(this_crossing)

            # assign seed to a random position in this corner
            choice = random.choice(this_crossing)
            assignments[qubit_seed.id] = int(choice)
            patch_Y.remove(choice)
            this_crossing.remove(choice)

            # leech other qubits to the remaining corners
            for idx, qubit_leech in enumerate(qubits_by_flips):
                # if self or qubit already assigned, skip
                if (
                    not assignments[qubit_leech.id] is None
                    or qubit_leech.affinity[qubit_seed.id] is None
                ):
                    continue

                # get metrics
                attractive_metric = (
                    qubit_leech.affinity[qubit_seed.id] / qubit_leech.requests
                )
                repulsive_metric = (
                    qubit_leech.requests - qubit_leech.affinity[qubit_seed.id]
                ) / qubit_seed.requests

                # if selection criteria met
                if (
                    attractive_metric >= threshold_affinity
                    and repulsive_metric <= threshold_repulse
                ):
                    choice = random.choice(this_crossing)
                    assignments[qubit_leech.id] = int(choice)
                    patch_Y.remove(choice)
                    this_crossing.remove(choice)
                    seed_pos.remove(idx)

                    if len(this_crossing) == 0:
                        break

            seed_probs = []
            for id in seed_pos:
                seed_probs.append(qubits_info[id].flips)

        # assign remaining qubits to non-corners
        for qubit, patch in assignments.items():
            if patch == None:
                if len(patch_Y) > 0:
                    choice = random.choice(patch_Y)
                    assignments[qubit] = int(choice)
                    patch_Y.remove(choice)
                else:
                    choice = random.choice(non_patch_Y)
                    assignments[qubit] = int(choice)
                    non_patch_Y.remove(choice)

    elif policy == AssignPolicy.AFFINITY:
        # affinity-based assignment:
        #   use an affinity-based metric to determine the qubits assignments
        #   ex: affinity = nb of times pairs of qubits are requested together
        #   place affine qubits closer to each other (quadratic semi-assignment problem?)
        #   affinity metrics are stored in _circuit_.qubits_info
        pass

    # update the qubits assignments in the circuit
    circuit_stats.update_qubits_assignments(qubits_info, assignments, _adj_graph_)

    # update circuit to account for the new assignments
    _circuit_.update_patches_in_rotations(assignments)

    # update and print qubit assignments
    print("Qubit assignments:", assignments)

    # remove qubits not assigned from the adj_graph
    for qubit in _adj_graph_.get_nodes_of_type(ComponentType.QUBIT):
        if not int(qubit[0][1:]) in set(assignments.values()):
            _adj_graph_.nx_graph.remove_node(qubit)

    # get non-corner patches with qubits assigned to them
    non_corner_patches = set()
    for q in qubits_info.values():
        if q.corner == False:
            non_corner_patches.add(q)

    return (assignments, non_corner_patches)
