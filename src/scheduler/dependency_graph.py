import time
from collections import defaultdict

import matplotlib as plt
import networkx as nx

from scheduler.circuit_and_rotation import circuit
from scheduler.circuit_and_rotation.circuit import MEASUREMENT, PI8


def update_blockers(
    blockers_dict: dict[int, int],
    blockers_reverse: dict[int, set[int]],
    assigned_rotations: set[int],
) -> set[int]:
    """
    Update dependency graph by removing assigned rotations from blockers and
    return new candidates
    """
    results = set()
    for rotation in assigned_rotations:
        blockers_dict.pop(rotation)
        if rotation not in blockers_reverse:
            continue
        blocked_rotations = blockers_reverse[rotation]

        for blocked_rotation in blocked_rotations:
            blockers_dict[blocked_rotation] -= 1
            if blockers_dict[blocked_rotation] == 0:
                results.add(blocked_rotation)
    return results


def is_commute(rotation_i: circuit.Rotation, rotation_j: circuit.Rotation) -> bool:
    if MEASUREMENT in {rotation_i.operation_type, rotation_j.operation_type}:
        return is_trivial_commute(rotation_i, rotation_j)

    if (len(rotation_i.x & rotation_j.z) + len(rotation_i.z & rotation_j.x)) % 2 == 0:
        return True
    return False


def is_trivial_commute(
    rotation_i: circuit.Rotation, rotation_j: circuit.Rotation
) -> bool:
    """Checks if two rotations act on distinct sets of qubits"""
    if rotation_i.active_qubit & rotation_j.active_qubit:
        return False
    return True


class DependencyGraph:
    """
    Base class for creating dependency graph
    """

    def __init__(self, circuit_):
        self.circuit_ = circuit_

    def get_dependency_graph(self):
        raise NotImplementedError

    def get_blocker_reverse_and_blocker_simple(self, blocker_dict):
        """blockers_dict = defaultdict(set) is {int rotation_id: set(rotation ids)}
        for each element of blocker_dict, the values are the rotations that are
        blocking the key

        blockers_simple's value is the number of relative blockers each rotation has
        e.g:
        Suppose we have 1 blocks 2, 2 blocks 3, and 3 blocks 4
        blocker_simple = {1: 0, 2: 1, 3: 1, 4: 1}

        reverse_blockers = {rotation_i: rotations that are blocked by rotation_i}

        """

        blockers_simple = defaultdict(int)
        for i in range(0, len(self.circuit_.rotations)):
            blockers_simple[i] = 0

        blockers_reverse = defaultdict(set)

        for key, blockers in blocker_dict.items():
            blockers_simple[key] = len(blockers)
            for blocker in blockers:
                if blocker in blockers_reverse:
                    blockers_reverse[blocker].add(key)
                else:
                    blockers_reverse[blocker] = {key}

        return blockers_simple, blockers_reverse


class DependencyGraphTrivialCommute(DependencyGraph):
    """
    O(nd) approach, which generate dependency graph based on "trivial commute
    rule".
    trivial commute rule:
    if two rotations do have share any common qubit, then there is no
    precedence constraint between these two rotations.

    return (blockers_reverse, blockers_simple)
    where blockers_reverse = {int rotation_id: set(rotation_ids that are
    blocked by rotation_id)}
    and blockers_simple = {int rotation_id: (int) number of
    rotations blocking rotation_id}
    """

    def __init__(self, circuit_):
        super().__init__(circuit_)

    def get_dependency_graph(self):
        width = self.circuit_.num_qubits
        length = len(self.circuit_.rotations)
        barR = [[-1 for _ in range(width)] for _ in range(length)]

        blockers_dict = defaultdict(set)
        blockers_dict[0] = set()
        blockers_reverse = defaultdict(set)

        # blockers_dict = defaultdict(set) is {int rotation_id: set(rotation ids)}
        # for each element of blocker_dict, the values are the rotations that are
        # blocking the key

        # NOTE:
        # Rotations which are not blocked by anything will not be included
        # blocker_dict nor blocker_reverse
        # This implies the very first rotation will not be in blocker_dict

        # NOTE:
        # blockers_simple's value is the number of relative blockers each rotation
        # has
        # e.g:
        # Suppose we have 1 blocks 2, 2 blocks 3, and 3 blocks 4
        # blocker_simple = {1: 0, 2: 1, 3: 1, 4: 1}
        # This works for the trivial commute case, where we can prune the redundant
        # "1 blocks 3" constraint
        for rotation_id in range(1, length):
            previous_rotation_qubits = self.circuit_[rotation_id - 1].active_qubit
            rotations_blocking_current_r = set()

            for qubit_id, patch_id in self.circuit_.assignments.items():
                if patch_id in previous_rotation_qubits:
                    barR[rotation_id][qubit_id] = rotation_id - 1
                else:
                    barR[rotation_id][qubit_id] = barR[rotation_id - 1][qubit_id]

                if (
                    patch_id in self.circuit_[rotation_id].active_qubit
                    and barR[rotation_id][qubit_id] != -1
                ):
                    rotations_blocking_current_r.add(barR[rotation_id][qubit_id])

            blockers_dict[rotation_id] = rotations_blocking_current_r

        blockers_simple, blockers_reverse = self.get_blocker_reverse_and_blocker_simple(
            blockers_dict
        )

        return blockers_reverse, blockers_simple, blockers_dict

    def get_dependency_graph_nx(self, blockers_dict):
        """Returns the dependency graph in a NetworkX format"""

        # derive the networkx form
        graph = nx.DiGraph()
        graph.add_node(-1)  # dummy rotation represents for the entry point
        graph.add_nodes_from(blockers_dict.keys())
        for node in blockers_dict.keys():
            graph.add_edge(-1, node, weight=1)

        # create edges for all the other rotations
        for blocked, blocker in blockers_dict.items():
            # v is the set of rotations blocking k
            for src in blocker:
                graph.add_edge(src, blocked, weight=1)

        return graph

    def plot_nodes_by_depth(self, circuit_name):
        """Plot a histogram for the number of nodes in each depth level of the dependency graph"""

        blockers_reverse, blockers_simple, _ = self.get_dependency_graph()

        count_levels = {}
        level = 1
        roots = []
        for r, n in blockers_simple.items():
            if n == 0:
                roots.append(r)

        while blockers_simple:
            count_levels[level] = len(roots)
            roots = update_blockers(blockers_simple, blockers_reverse, roots)
            level += 1

        # Draw a histogram from the elements of a dictionary
        values = list(count_levels.values())
        max_value = max(values)
        bins = list(range(max_value + 2))
        _, _, bars = plt.hist(values, bins=bins, align="left", color="darkblue")
        plt.bar_label(bars)
        plt.xticks(bins[:-1])
        plt.xlabel("Width")
        plt.ylabel("Frequency")
        plt.title(circuit_name[:-4])
        plt.savefig(circuit_name[:-4] + ".png")
        plt.clf()
        plt.show()


class DependencyGraphFull(DependencyGraph):
    """
    O(n^2) approach, generate dependency graph base on "commute rule".
    commute rule:
    if two rotations commute (even with common qubit), then there is no
    precedence constraint between these two rotations.


    return (reverse_blockers, blockers)
    where reverse_blockers = {rotation_i: rotations that are blocked by
                                rotation_i}
    and blockers = {rotation_i: number of rotations blocking rotation_i}
    """

    def __init__(self, circuit_):
        super().__init__(circuit_)

    def get_dependency_graph(self):
        length = len(self.circuit_.rotations)
        blocker_dict = defaultdict(set)
        is_commute_time = float()

        for i in range(0, length - 1):
            for j in range(i + 1, length):
                start = time.time()
                is_commute_ = is_commute(
                    self.circuit_.rotations[i], self.circuit_.rotations[j]
                )
                end = time.time()
                is_commute_time += end - start
                if not is_commute_:
                    blocker_dict[j].add(i)

        blockers_simple, blockers_reverse = self.get_blocker_reverse_and_blocker_simple(
            blocker_dict
        )

        return blockers_reverse, blockers_simple, blocker_dict


class DependencyGraphFullTrimmed(DependencyGraph):
    """
    O(n^2) approach, generate dependency graph base on "commute rule" while
    pruning the dependency graph along the way through the "break" statement.

    commute rule:
    if two rotations commute (even with common qubit), then there is no
    precedence constraint between these two rotations.

    return (reverse_blockers, blockers)
    where reverse_blockers = {rotation_i: rotations that are blocked by
                                rotation_i}
    and blockers = {rotation_i: number of rotations blocking rotation_i}
    """

    def __init__(self, circuit_):
        super().__init__(circuit_)

    def get_dependency_graph(self):
        length = len(self.circuit_.rotations)
        blocker_dict = defaultdict(set)

        # blockers_dict = defaultdict(set) is {int rotation_id: set(rotation ids)}
        # for each element of blocker_dict, the values are the rotations that are
        # blocking the key
        all_keys = defaultdict(tuple)
        is_commute_time = float()

        # cache for checking if two rotations commute or not
        is_commute_dict = dict()

        # calculate key for each rotation.
        for i in range(0, length):
            all_keys[i] = calculate_key(self.circuit_[i])

        for i in range(0, length - 1):
            key_i = all_keys[i]

            for j in range(i + 1, length):
                key_j = all_keys[j]
                # if rotation_i == rotation_j, add i as j's blocker, then break the
                # inner loop.
                if key_i == key_j:
                    blocker_dict[j].add(i)
                    break

                start = time.time()

                # If we have computed the commutation relationship for this pair
                # before use cached result, do not recompute
                if (key_i, key_j) in is_commute_dict:
                    is_commute_ = is_commute_dict[(key_i, key_j)]
                elif (key_j, key_i) in is_commute_dict:
                    is_commute_ = is_commute_dict[(key_j, key_i)]
                else:
                    is_commute_ = is_commute(
                        self.circuit_.rotations[i], self.circuit_.rotations[j]
                    )

                    is_commute_dict[(key_i, key_j)] = is_commute_

                end = time.time()

                is_commute_time += end - start

                # if rotations i and j do not commute, add i as j's blocker
                if not is_commute_:
                    blocker_dict[j].add(i)

        blockers_simple, blockers_reverse = self.get_blocker_reverse_and_blocker_simple(
            blocker_dict
        )

        return blockers_reverse, blockers_simple, blocker_dict


class DependencyGraphPI8(DependencyGraph):
    """
    PI8 only
    """

    def __init__(self, circuit_):
        super().__init__(circuit_)

    def get_pi8_rotations(self):
        pi_8_rotations = [
            rotation
            for rotation in self.circuit_.rotations
            if rotation.operation_type == PI8
        ]

        return pi_8_rotations

    def get_dependency_graph(self):
        rotations = self.get_pi8_rotations()

        if not rotations:
            return dict(), dict()

        width = self.circuit_.num_qubits
        length = len(rotations)
        barR = [[-1 for x in range(width)] for y in range(length)]
        blockers_dict = defaultdict(set)

        for i, rotation in enumerate(rotations):
            if i == 0:
                blockers_dict[rotations[i].ind] = set()
                continue
            previous_rotation_qubits = rotations[i - 1].active_qubit
            for j in range(0, width):
                if j in previous_rotation_qubits:
                    barR[i][j] = i - 1
                else:
                    barR[i][j] = barR[i - 1][j]
            temp = set()
            for j in range(0, width):
                if j not in rotations[i].active_qubit:
                    continue
                if barR[i][j] == -1:
                    continue
                temp.add(rotations[barR[i][j]].ind)
            blockers_dict[rotations[i].ind] = temp

        _, blockers_reverse = self.get_blocker_reverse_and_blocker_simple(blockers_dict)

        return blockers_dict, blockers_reverse


def calculate_key(rotation: circuit.Rotation) -> tuple:
    op_type = rotation.operation_type
    x = tuple(sorted(rotation.x))
    z = tuple(sorted(rotation.z))
    return op_type, x, z
