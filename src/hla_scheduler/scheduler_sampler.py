import configparser
import copy
import random
from collections import defaultdict

import networkx as nx
import simpy
from scheduler.circuit_and_rotation import circuit
from layout_processor.adjacency_graph import AdjacencyGraph
from scheduler.caching import shortest_path_caching, steiner_tree_caching
from layout_processor import magic_state_factory as msf
from layout_processor.adjacency_graph import (
    AdjacencyGraph,
    ComponentType,
    MagicStateStatus,
)
from scheduler.steiner_tree_heuristic import solve_rotations_packing

# Load configs
config = configparser.ConfigParser()
config.read_file(open("src/config/scheduler.conf"))
simulation_mode = config["Experiments"]["simulation_mode"]


class ScheduleSampler:
    """A class used to sample schedule randomly upto the distribution
    specified by the user
    """

    def __init__(
        self,
        dep_graph: nx.DiGraph,
        trans_cir: circuit.Circuit,
        adj_graph: AdjacencyGraph,
        ms_fact: msf.MagicStateFactory,
    ):
        """The contructor
        Args:
            circuit_file:the name of the circuit file
        """
        self._dp_graph = copy.deepcopy(dep_graph)
        self._preprocess_graph()
        self._trans_cir = trans_cir
        self._adj_graph = adj_graph
        self._ms_fact = ms_fact
        self.strees_cached = {}
        self.shortest_path_cache = shortest_path_caching.SPCaching()
        self.result_cached = {}
        self.random_generator = random.Random(1)
        self.fails_count = {
            "Qubit cant rotate": 0,
            "Qubit is disconnected from graph": 0,
            "Steiner tree not found": 0,
            "No magic/zero state in subgraph": 0,
            "No path to a magic state": 0,
            "No path to a zero state": 0,
        }
        # the steiner tree caching used whole way through one run of the simulator

    def sample(
        self, depot: simpy.Container, output_depot: simpy.Resource
    ) -> list[list[int]]:
        """
        Args:
            depot: the simpy container to describe the storage zone
            output_depot: the simpy resource to describe the depot exit
        Return: a list of lists of rotations
        """
        # get the list of nodes that are executable
        candidate_rots = self.get_schedulable_rotations()
        # sample from the list
        # with pi4/measurement rotations, the procedure become a bit more compilcated
        # Pseudo-code:
        # The Exact mode:
        # case 1: there is no pi4/measurement rotations
        #         the current procedure
        # case 2: there are pi4/measurement rotations:
        #         if depot.level >0 # at least we can pack one pi4/meas and one pi8 rotation
        #            (pi4/measurement + pi8 rotations) -> rotation packer
        #         elif there is one (pi4/measurement) -> no need to call
        #         else pi4/measurement -> rotation packer
        # The Approximate mode:
        # case 1: there is no pi4/measurement rotations
        #         the current procedure
        # case 2: there are pi4/measurement rotations:
        #         nb_pi4_mea <- nb pi4/measurment rotations
        #         nb_rot <- sample from UNIFORM[1,nb_pi4_mea]
        #         randomly get nb_rot from the list of pi4/measurment rotations
        pi4_meas_rots = list(
            filter(
                lambda x: self._trans_cir.rotations[x].operation_type != 1,
                candidate_rots,
            )
        )
        pi8_rots = list(
            filter(
                lambda x: self._trans_cir.rotations[x].operation_type == 1,
                candidate_rots,
            )
        )
        scheduled_rots = []
        if simulation_mode == "Exact":
            if (
                len(pi4_meas_rots)
                + min(len(pi8_rots), depot.level, output_depot.capacity)
                > 1
            ):
                scheduled_rots = self.get_rots_scheduled(
                    pi4_meas_rots + pi8_rots, min(depot.level, output_depot.capacity)
                )
            else:
                scheduled_rots = candidate_rots[:1]
        elif simulation_mode == "Approximate":
            if len(pi4_meas_rots) == 0:
                num_rots = min(len(candidate_rots), depot.level, output_depot.capacity)
                scheduled_rots = random.sample(candidate_rots, num_rots)
            elif len(pi4_meas_rots) == 1:
                scheduled_rots = pi4_meas_rots
            else:
                sample_size = random.randint(1, len(pi4_meas_rots))
                scheduled_rots = random.sample(pi4_meas_rots, sample_size)
        else:
            raise ValueError(
                f"The simulation mode is not valid please check simu_mode!"
            )
        # remove the sampled nodes from g
        self.update_graph(scheduled_rots)
        return scheduled_rots

    def get_rots_scheduled(
        self, candidate_rotations: list[int], nb_ms_avail: int
    ) -> list[int]:
        """A function used to select rotations from the candidate set according to the given
        number of rotations.
        Args:
            candidate_rotations: a list of rotation indices from which the scheduled rotations are selected;
            nb_ms_avail: the number of available magic states
        Return:
            a list of rotation indices that are selected
        """
        rotations = [self._trans_cir.rotations[i] for i in candidate_rotations]
        available_magic_states = set()
        magic_nodes = self._adj_graph.get_nodes_of_type(ComponentType.MAGIC)
        nb_ms_turn_off = len(magic_nodes) - nb_ms_avail
        self._adj_graph.set_nodes_ticks(magic_nodes[:nb_ms_turn_off], -1)
        for _, magic_state in self._adj_graph.components_by_type[
            ComponentType.MAGIC
        ].items():
            if magic_state.status == MagicStateStatus.READY:
                available_magic_states.add(magic_state.node)
        key = steiner_tree_caching.compute_subproblem_key(
            available_magic_states, rotations
        )
        rot_assigned_this_tick = []
        if key in self.result_cached:
            cached_result = self.result_cached[key]
            rot_assigned_this_tick = steiner_tree_caching.get_result_from_cache(
                cached_result, rotations, self._adj_graph.unavailable_nodes
            )

        if len(rot_assigned_this_tick) == 0:
            rot_assigned_this_tick = solve_rotations_packing(
                commutable_rotations=rotations,
                adj_graph_full=self._adj_graph,
                shortest_path_cache=self.shortest_path_cache,
                steiner_trees_cached=self.strees_cached,
                random_generator=self.random_generator,
                fails_count=self.fails_count,
                magic_state_factory=self._ms_fact,
                hla_flag=True,
            )

            # cache set of rotations packed
            rot_assigned_this_tick = [
                r for r in rot_assigned_this_tick if not r[1] is None
            ]
            cached_result = {}
            for pack in rot_assigned_this_tick:
                cached_result[steiner_tree_caching.get_rotation_key(pack[0])] = pack
            if cached_result:
                self.result_cached[key] = cached_result
        res = [rot[0].ind for _, rot in enumerate(rot_assigned_this_tick)]
        return res

    def _preprocess_graph(self, root: int = -1):
        """A function used to proprocess the dependency graph.
        Essentially, it makes the dummy start vertex in the graph only connect to
        the vertices of which the depth is 1. The function has to be invoked right in the beginning
        of the sample function.
        Args:
           root: the index of the dummy start vertex;
        """
        rots = []
        dist = compute_longest_path(self._dp_graph, -1)
        for k, v in dist.items():
            if v == 1:
                rots.append(k)
            if v > 1:
                continue
        ngh = copy.deepcopy(self._dp_graph.neighbors(root))
        for v in ngh:
            if v not in rots:
                self._dp_graph.remove_edge(-1, v)

    def get_schedulable_rotations(self, root=-1) -> list[int]:
        """Based on the dependency graph, the function returns a list of
        rotations that can be scheduled at the current tick
        Args:
            root: the index of the start dummy vertex
        Return:
            A list of rotations
        """
        rots = []
        for node in self._dp_graph.neighbors(root):
            if self._dp_graph.in_degree(node) == 1:
                rots.append(node)  # the index of a node is equal to the rotation ind
        return rots

    def update_graph(self, removed_rots: list[int], root=-1):
        """After scheduling some rotations, the dependency graph is updated
        by removing the scheduled rotations and building connections as well.
        For instance, the dummy vertex -1 connects to vertex 0 which has a depth of 1.
        vertex 0 is followed by vertex 1. In tick 1, vertex 0 is scheduled.
        Then the update_graph functionremoves vertex 0 and draw a direct connection
        from the dummy vertex to vertex 1.
        Args:
            removed_rots: the list of scheduled rotations
            root: the index of the dummy start vertex
        """
        for rot in removed_rots:
            # for any rotation to be removed
            # check its neighbors
            for v in self._dp_graph.neighbors(rot):
                self._dp_graph.add_edge(root, v)
            self._dp_graph.remove_node(rot)

    def get_dp_graph(self) -> nx.DiGraph:
        """A getter function to return the dependency graph"""
        return self._dp_graph

    def any_rotation_left(self) -> bool:
        return self._dp_graph.number_of_nodes() > 1


def compute_longest_path(
    dep_graph: nx.Graph, source: int, depth: int = None
) -> defaultdict[int, int]:
    """Find the longest path from source to target over a directed acylic graph (DAG)
    Args:
        dep_graph: the graph over which we compute the longest path
        source: the source vertex
        depth: only compute for nodes that have the longest distance from the source shorter or equal to depth
    Logic:
        Computing the longest path on a DAG is fortunately trivial which takes O(E+V) as the
        time complexity. The general idea of the algorithm is based on the following observation.
        Let's say we have a vertex j which is one of the neighbors of i. How to determine l[j]?
        We need to know the longest path for all the vertices that pointing to j.
        Denote the set of vertices as S(j). Then l(j) = max_i\in S(j) {l(i)} + 1.
        The order of updating l(i) really matters. What is usually done is to
        sort vertices in topological order and update l accordingly.
        We get the topological order by depth first search by which one can easily find that j is
        visited later than whatever vertices in S(j). The only difference is we need a stack to
        store the visited vertices.
    Returns:
        a dictionary of which the key stands for the target node and the value is the longest distance
    """
    weights = nx.get_edge_attributes(dep_graph, "weight")
    stack = list(reversed(list(nx.topological_sort(dep_graph))))
    dist = defaultdict(lambda: -(10**9))
    dist[source] = 0
    while len(stack) > 0:
        u = stack[-1]
        del stack[-1]  # deleting the last element should just take O(1)
        assert dist[u] != -(10**9)
        for i in dep_graph.neighbors(u):
            if dist[i] < dist[u] + weights[u, i]:
                dist[i] = dist[u] + weights[u, i]
    return dist
