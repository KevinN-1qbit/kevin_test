from typing import Union

import networkx as nx

from scheduler.circuit_and_rotation import circuit
from scheduler.circuit_and_rotation.circuit import TURN
from layout_processor.adjacency_graph import AdjGraphNode, TileName


def search_rotation_cached(
    key: tuple[TileName],
    nodes_available: set[AdjGraphNode],
    cache: dict[tuple[AdjGraphNode]],
) -> Union[nx.Graph, None]:
    """Search if a feasible Steiner tree is cached for a list of terminals

    Args:
        key: current terminal nodes
        nodes_available: nodes available in the adjacency graph
        cache: Steiner trees cached

    Returns:
        nx.Graph: Steiner tree cached if found, None if not
    """

    # ! possible bug for corner qubits:
    # ! if a qubit has turned, the stree stored may be infeasible for the new graph
    # ! verify if this can happen

    # TODO improv: if we save only the qubit id, not its X or Z state,
    # TODO maybe we could cache even more solutions

    # for each tree cached for this list of terminal nodes
    if key in cache:
        for stree in cache[key]:
            # if all terminal nodes are in the current adjacency graph
            tree_nodes = set(stree.nodes())
            if tree_nodes.issubset(nodes_available):
                return stree
    return None


def compute_subproblem_key(
    available_magic_state: set[AdjGraphNode],
    candidate_rotations: list[circuit.Rotation],
) -> tuple[tuple[AdjGraphNode], tuple[tuple[circuit.RotationType, tuple[int]]]]:
    """Maps the subproblem of this layer to a hash key

    Hash key depends on:
    1. available magic states;
    2. for each rotation of this layer:
        2.1 rotation type (pi 4 or pi 8)
        2.2 rotation active qubits
    """
    magic_state = sorted(available_magic_state)
    rotation_list = list()
    for rotation in candidate_rotations:
        rotation_list.append((rotation.operation_type, tuple(rotation.active_qubit)))
    rotation_list_sorted = sorted(rotation_list)

    return tuple(magic_state), tuple(rotation_list_sorted)


def get_result_from_cache(
    cached_result: dict[
        tuple[int, tuple[int]], tuple[circuit.Rotation, nx.Graph, AdjGraphNode]
    ],
    candidate_rotations: list[circuit.Rotation],
    unavailable_nodes: set[AdjGraphNode],
) -> list[tuple[circuit.Rotation, nx.Graph, AdjGraphNode]]:
    """Translate cached results to rotation assignment.

    Cached result takes the form:
        {rotation_hash_key
            : (magic_state_assigned_to_this_rotation, bus_used_for_this_rotation}

    returns:
        {rotation_id: magic_state_assigned_to_this_rotation}
        This is a translated version of cached_result
    """

    assignment_result = []

    for rot in candidate_rotations:
        rotation_key = get_rotation_key(rot)
        if rotation_key in cached_result:
            tree = cached_result[rotation_key]
            new_tree = tree[1]
            turn_mapping = {}
            overlap = False
            for node in unavailable_nodes:
                if isinstance(node, tuple) and node[0][0] == "q":
                    node = node[0]
                for t in new_tree.nodes:
                    if isinstance(t, tuple) and t[0][0] == "q":
                        t = t[0]
                    if node == t:
                        overlap = True

            if rot.operation_type is TURN and not overlap:
                q_new = list(rot.rotation_active_edges)[0]
                angle_old = list({"X", "Z"} - set(q_new[1]))[0]
                q_old = (q_new[0], angle_old)
                turn_mapping[q_new] = q_old
                new_tree = nx.relabel_nodes(tree[1], turn_mapping)
                assignment_result.append((rot, new_tree, tree[2]))
                continue
            elif not set(new_tree.nodes) & set(unavailable_nodes) and not overlap:
                # if rot.operation_type is not TURN:
                mapping = {}
                for q_new in list(rot.rotation_active_edges):
                    if q_new not in new_tree.nodes:
                        angle_old = list({"X", "Z"} - set(q_new[1]))[0]
                        q_old = (q_new[0], angle_old)
                        mapping[q_old] = q_new
                if mapping:
                    new_tree = nx.relabel_nodes(tree[1], mapping)
                assignment_result.append((rot, new_tree, tree[2]))
    return assignment_result


def get_rotation_key(
    rotation: circuit.Rotation,
) -> tuple[circuit.RotationType, tuple[int]]:
    """Helper function whichs generate hashkey for each rotation"""
    return rotation.operation_type, tuple(rotation.active_qubit)
