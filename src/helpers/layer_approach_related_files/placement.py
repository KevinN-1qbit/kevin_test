# from scheduler.solve_model_pulp import solve_model_pulp
import heapq
import itertools as it
import math
import random
from collections import defaultdict
from typing import Type

import ray

from scheduler.circuit_and_rotation import generate_rotation
from triangle_layout import triangle_layouts
from helpers import paths


class Placement:
    def __init__(
        self,
        # TODO circuit should take an unified circuit object
        # regardless of input is TCC or SC
        # TODO: layout_graph should also take both TCC and SC
        circuit: generate_rotation.Rotation_Generator_Real_Circuit = None,
        layout_graph: triangle_layouts.GraphForOptimizingQubitPlacement = None,
    ):
        self.circuit = circuit
        self.layout_graph = layout_graph

    def get_connected_components(
        self, graph: dict[int, dict[int, float]]
    ) -> tuple[dict[int, dict[int, float]], list[set]]:
        """Find all disjoint components within the input graph,
        return the disjoint graphs and their nodes

        Arguments:
            graph: {
                0: {1: 3},
                1: {0: 3, 2: 1},
                2: {1: 1},
                3: {4: 1},
                4: {3: 1}
            }

        Returns:
            weighted_subgraphs = [
                {
                    0: {1: 3},
                    1: {0: 3, 2: 1},
                    2: {1: 1},
                },
                {
                    3: {4: 1},
                    4: {3: 1}
                }
            ]
            components = [{0, 1, 2}, {3, 4})]
        """

        components = []
        nodes_visited_accumulate = set()

        for starting_node in graph.keys():
            nodes_visited_each_starting_node = set()
            if starting_node in nodes_visited_accumulate:
                continue
            self._dfs_recursion(
                nodes_visited_accumulate,
                nodes_visited_each_starting_node,
                starting_node,
                graph,
            )

            components.append(nodes_visited_each_starting_node)

        if len(components) > 1:
            weighted_subgraphs = [
                {key: graph[key] for key in comp} for comp in components
            ]
        else:
            weighted_subgraphs = [graph]

        return weighted_subgraphs, components

    def _dfs_recursion(
        self,
        nodes_visited_accumulate: set[int],
        nodes_visited_each_starting_node: set[int],
        current_node: int,
        graph: dict[int, dict[int, float]],
    ):
        nodes_visited_accumulate.add(current_node)
        nodes_visited_each_starting_node.add(current_node)

        for neighbour in graph[current_node].keys():
            if neighbour not in nodes_visited_accumulate:
                self._dfs_recursion(
                    nodes_visited_accumulate,
                    nodes_visited_each_starting_node,
                    neighbour,
                    graph,
                )

    def get_edge_to_cut_from_weighted_graph(
        self, subgraph: dict[int, dict[int, float]]
    ) -> tuple[float, int, int]:
        """Return the edge to cut in the format of (weight, node1, node2) from
        the input weighted subgraph
        Edge_to_cut is the edge with the largest weight (because in get_weighted_graph(),
        the weights are inverted, i.e. largest weigths ==> least connected and vise versa)
        in the graph. If there are equal weights in the graph,
        the first encountered edge is chosen

        """
        edge_to_cut = None
        largest_weight = 0
        for node, connection_dict in subgraph.items():
            for other_node, weight in connection_dict.items():
                if weight > largest_weight:
                    largest_weight = weight
                    edge_to_cut = (weight, node, other_node)

        return edge_to_cut

    @staticmethod
    def get_maxLen_idx(array: list[dict[int, dict[int, float]]]) -> int:
        maxLen = -float("inf")
        idx = -1
        for i, val in enumerate(array):
            if len(val) > maxLen:
                maxLen = len(val)
                idx = i
        return idx

    def get_qubit_clusters(self) -> list[set[int]]:
        """Given a weighted graph representing the connectivity of the input circuit,
        where weights are the number of edges between two nodes,
        divide the graph into clusters.
        Each clusters consists of closely connected qubits.
        """

        weighted_graph = self.circuit.get_weighted_graph()
        subgraphs_all, components = self.get_connected_components(weighted_graph)
        subgraphs_all.sort(key=len)

        # Construct k-spanning tree of the first weighted subgraph and
        # cut k - 1 edges from the graph to form clusters
        # k is defined as the difference between the number of magic states factories in the layout
        # and the number of disjoint components in the input circuit

        # Since the purpose of cutting the graph k times is to obtain k + 1 clusters in order to
        # place the closely connected qubits near each of the magic states,
        # the number of clusters must be smaller and equal to the number of magic states, therefore
        # bounding k to be smaller than the number of magic states
        k = len(self.layout_graph.magic_state_tiles) - len(subgraphs_all)

        # k must also be greater than 1 since we will be cutting k - 1 edge
        # k cannot be greater than or equal to the number of qubits since we can have at most
        # number_of_qubits clusters, with each qubit in its own cluster
        if 2 <= k < self.circuit.num_qubits:
            cache = [{}]
            for _ in range(k):
                subgraphs_to_cut_candidate_from_components = (
                    subgraphs_all[-1] if subgraphs_all != [] else {}
                )

                cache_candidate_idx = self.get_maxLen_idx(cache)

                subgraphs_to_cut_candidate_from_cache = (
                    cache[cache_candidate_idx] if cache_candidate_idx != -1 else {}
                )

                if len(subgraphs_to_cut_candidate_from_components) > len(
                    subgraphs_to_cut_candidate_from_cache
                ):
                    subgraphs_all.pop()
                    mst_edges, mst_adj_list = get_min_spanning_tree(
                        subgraphs_to_cut_candidate_from_components
                    )
                    weight_and_edge = heapq.nlargest(1, mst_edges, key=lambda x: x[0])[
                        0
                    ]

                else:
                    mst_adj_list = subgraphs_to_cut_candidate_from_cache
                    cache[cache_candidate_idx] = {}
                    weight_and_edge = self.get_edge_to_cut_from_weighted_graph(
                        mst_adj_list
                    )

                # weight_and_edge[0] is the weight and we discard it
                # weight_and_edge[1] and weight_and_edge[2] represent an edge
                # between two nodes
                # We want to delete the connections here

                mst_adj_list[weight_and_edge[1]].pop(weight_and_edge[2])
                mst_adj_list[weight_and_edge[2]].pop(weight_and_edge[1])

                weighted_subgraphs, components = self.get_connected_components(
                    graph=mst_adj_list
                )
                cache.extend(weighted_subgraphs)

            cluster = [set(c.keys()) for c in cache if c != {}]
            nodes_in_subgraph_all = [set(s.keys()) for s in subgraphs_all if s != {}]
            cluster.extend(nodes_in_subgraph_all)
            cluster.sort(key=len, reverse=True)
            return cluster

        else:
            components.sort(key=len, reverse=True)
            return components

    def check_num_qubit_greater_than_num_data_tiles(self):
        if self.circuit.num_qubits > len(self.layout_graph.data_tiles):
            raise ValueError("There are more qubits than data tiles.")

    def get_placement_using_cluster(
        self, num_placement=1, seed=0
    ) -> list[dict[int, int]]:
        # TODO: 1. Number of qubit clusters not equal to num magic state
        # TODO: 2. some qubit clusters very large
        # TODO: 3. Visualize placement
        """Given qubit_clusters_all, which is already
        ranked in decending order according to the size of the cluster,

        1. Get all the magic state tiles in the layout
        2. Get the nearest data tiles near each magic state.
            The number of nearest data tiles is determined
            according to the number of qubits inside each cluster
        3. Place the qubits

        """

        self.check_num_qubit_greater_than_num_data_tiles()

        qubit_placement = defaultdict(int)
        magic_tiles_all = self.layout_graph.magic_state_tiles
        already_mapped_data_tiles = set()
        qubit_not_yet_placed = []
        data_tiles_cluster_all = []
        qubit_placement_multiple = []

        random_generator = random.Random(seed)
        qubit_clusters_all = self.get_qubit_clusters()

        # For each cluster, get the data tiles
        # near a magic state tile (shortest distance traveled via bus)
        for cluster, magic_tile in zip(qubit_clusters_all, magic_tiles_all):
            data_tiles_cluster = self._search_data_tile_via_bus(
                magic_tile, len(cluster), already_mapped_data_tiles
            )

            # Update already_mapped_data_tiles & corresponding ids
            # to make sure we don't revisit the same tiles
            already_mapped_data_tiles.update(data_tiles_cluster)

            data_tiles_cluster_all.append(data_tiles_cluster)

        # Flatten the qubit_clusters_all list
        qubit_clusters_all_flatten = set(it.chain(*qubit_clusters_all))

        qubit_not_used_in_rotation = list(
            set(range(self.circuit.num_qubits)) - qubit_clusters_all_flatten
        )

        free_date_tiles = list(self.layout_graph.data_tiles - already_mapped_data_tiles)

        # Check how many possible placements given all cluster sizes
        possible_num_placements = 0
        for qubit_cluster in qubit_clusters_all:
            cluster_size = len(qubit_cluster)
            if cluster_size > 1:
                possible_num_placements += math.factorial(cluster_size)

        if possible_num_placements < num_placement:
            print("Can only generate", possible_num_placements, "distinct placements.")
            num_placement = possible_num_placements

        while len(qubit_placement_multiple) < num_placement:
            qubit_not_yet_placed = qubit_not_used_in_rotation

            # For each cluster, get the corresponding data tiles
            # near a magic state tile (distance travelling via bus)
            for qubit_cluster, data_tiles_cluster in zip(
                qubit_clusters_all, data_tiles_cluster_all
            ):
                qubit_cluster_list = list(qubit_cluster)
                data_tiles_cluster_list = list(data_tiles_cluster)
                random_generator.shuffle(qubit_cluster_list)

                # Place the qubits, make sure there are more elements
                # in qubit_cluster than data_tiles_cluster
                # The remaining qubits in qubit_cluster that
                # are not yet placed will be randomly placed later
                i = 0
                while i < len(data_tiles_cluster):
                    qubit_placement[qubit_cluster_list[i]] = data_tiles_cluster_list[i]
                    i += 1
                # If any remaning not yet placed qubits
                if data_tiles_cluster_list[i:]:
                    qubit_not_yet_placed.extend(data_tiles_cluster_list[i:])

            # Place the remaining not yet placed qubits
            if qubit_not_yet_placed:
                random_generator.shuffle(qubit_not_yet_placed)

                for qubit, data in zip(qubit_not_yet_placed, free_date_tiles):
                    qubit_placement[qubit] = data

            if qubit_placement not in qubit_placement_multiple:
                qubit_placement_multiple.append(dict(qubit_placement))

        return qubit_placement_multiple

    def get_placement_random(self, num_placement=1, seed=0) -> list[dict[int, int]]:
        """Generate completely random placement"""

        self.check_num_qubit_greater_than_num_data_tiles()

        random_generator = random.Random(seed)

        qubit_placement_multiple = []
        while len(qubit_placement_multiple) < num_placement:
            qubit_placement = defaultdict(int)
            qubits = list(range(self.circuit.num_qubits))
            data_tiles = self.layout_graph.data_tiles

            random_generator.shuffle(qubits)
            for data_tile, qubit in zip(data_tiles, qubits):
                qubit_placement[qubit] = data_tile

            if qubit_placement not in qubit_placement_multiple:
                qubit_placement_multiple.append(dict(qubit_placement))

        return qubit_placement_multiple

    def _search_data_tile_via_bus(
        self, starting_magic_state: int, n_neighbors: int, to_avoid: set[int]
    ) -> set[int]:
        """Given a magic state tile, search for n nearest data tiles connected via bus tiles"""
        # Find the bus tile that's connected to starting_magic_state
        for neigbor in self.layout_graph.connections[starting_magic_state]:
            if neigbor in self.layout_graph.bus_tiles:
                starting_bus_tile = neigbor
                break

        # Do a breadth first search
        data_tiles_found = set()
        to_explore = [starting_bus_tile]
        already_visited = set()

        while len(data_tiles_found) < n_neighbors and to_explore:
            next_triangle = to_explore.pop(0)
            already_visited.add(next_triangle)

            for neighbor in self.layout_graph.connections[next_triangle]:
                if neighbor not in already_visited and neighbor not in to_avoid:
                    if (
                        neighbor in self.layout_graph.data_tiles
                        and len(data_tiles_found) < n_neighbors
                    ):
                        data_tiles_found.add(neighbor)
                    elif neighbor in self.layout_graph.bus_tiles:
                        to_explore.append(neighbor)

        return data_tiles_found

    def optimize_placement(self):
        # placeholder for the algorithm to optimize placement

        pass


def get_min_spanning_tree(
    graph: dict[int, dict[int, float]]
) -> tuple[list[float, int, int], dict[int, dict[int, float]]]:
    # mst_edges is a list of edges of the min spanning tree
    # mst_adj_list is in the adj list of the weight min spanning tree
    # the lower the weight is, the less connected the two nodes(qubits) are
    # To construct k-spanning tree, we will cut k - 1 edges
    # with the lowest weights from mst_for_cutting

    mst_edges = []
    mst_adj_list = defaultdict(dict)
    starting_qubit = list(graph.keys())[0]
    edges = [
        (cost, starting_qubit, end_qubit)
        for end_qubit, cost in graph[starting_qubit].items()
    ]
    visited = set([starting_qubit])

    heapq.heapify(edges)

    while edges != []:
        cost, begin, end = heapq.heappop(edges)
        if end not in visited:
            visited.add(end)

            heapq.heappush(mst_edges, (cost, begin, end))
            mst_adj_list[begin][end] = cost
            mst_adj_list[end][begin] = cost

            for next_end, cost in graph[end].items():
                if next_end not in visited:
                    heapq.heappush(edges, (cost, end, next_end))

    return mst_edges, dict(mst_adj_list)
