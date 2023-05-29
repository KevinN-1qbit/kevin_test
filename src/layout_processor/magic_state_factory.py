from __future__ import annotations

import dataclasses
import configparser
from typing import Union

import networkx as nx

from scheduler.circuit_and_rotation.circuit import PI8
from layout_processor.adjacency_graph import (
    AdjacencyGraph,
    ComponentType,
    MagicStateStatus,
)

config = configparser.ConfigParser()
config.read_file(open("src/config/scheduler.conf"))


@dataclasses.dataclass
class Factory:
    """Contains information of each individual magic state factory."""

    ms: list = dataclasses.field(default_factory=list)

    def get_num_ms_available(self, magic_states) -> int:
        num_ms_available_in_this_factory = 0
        for ms in self.ms:
            if magic_states[ms].available:
                num_ms_available_in_this_factory += 1
        return num_ms_available_in_this_factory


@dataclasses.dataclass
class MagicState:
    node: tuple
    factory: int
    available: bool

    def consume(self):
        self.available = False

    def replenish(self):
        self.available = True


class MagicStateFactory:
    """Contains information for all magic states distilled by a
    magic state factory. Handles magic state update & availability
    """

    def __init__(
        self,
        tick_replenish,
        graph,
        store_policy="match",
        reset_policy="match",
        place_store="",  #'before',
        place_reset="",  #'after'
    ):
        self.TICK_REPLENISH = tick_replenish
        self.magic_states = {}
        self.tick = 1
        self.count = 0
        self.factories: list[Factory] = []
        self.after_init(graph)
        self.storage_store_policy = store_policy
        self.storage_reset_policy = reset_policy

        # if there is no storage in the layout, then set these policies to null
        if len(graph.components_by_type[ComponentType.STORAGE]) == 0:
            self.place_store = ""
            self.place_reset = ""
        else:
            self.place_store = place_store
            self.place_reset = place_reset

    def after_init(self, graph: AdjacencyGraph) -> None:
        magic_states = graph.get_nodes_of_type(ComponentType.MAGIC)

        #! verify: if magic states is replenished every time step, then self.TICK_REPLENSIH = 1, not 0
        if self.TICK_REPLENISH == 0:
            graph.set_nodes_ticks(magic_states, 0)
        else:
            graph.set_nodes_ticks(magic_states, self.TICK_REPLENISH - 1)

        # set one magic state per factory
        # TODO this is enough to the HLAScheduler. However, custom layouts may require multiple
        # TODO magic states per factory. We should find a way to get this info from an user input.
        for factory_idx, ms in enumerate(magic_states):
            self.factories.append(Factory())
            self.factories[factory_idx].ms.append(ms)
            self.magic_states[ms] = MagicState(ms, factory_idx, False)

    def available_magic_state_for_current_tick(
        self, graph: AdjacencyGraph, tick_elapsed: int
    ):
        available_ms = set()
        for _, ms in graph.components_by_type[ComponentType.MAGIC].items():
            if graph.nx_graph.nodes[ms.node]["ticks"] - tick_elapsed == 0:
                available_ms.add(ms.node)
                self.magic_states[ms.node].replenish()
        return available_ms

    @staticmethod
    def check_if_only_magic_state_required(current_candidates):
        return all(op.operation_type == PI8 for op in current_candidates)

    def increment_tick(
        self,
        assigned_rotations,
        graph_full: AdjacencyGraph,
        rotation_assignment,
        ticks_elapsed,
    ):
        """
        if all magic states of a factory are used, then all m.s. of the factory
        becomes available again after self.TICK_REPLENISH ticks
        if not all magic states of a factory are used, the consumed magic states
        are set to unavailable but won't be replenished until all m.s. are used
        """

        graph_full.decrease_nodes_ticks(ticks_elapsed)

        # check if all magic states in a factory are depleted
        for fac in self.factories:
            if all(
                graph_full.components_by_type[ComponentType.MAGIC][ms[0]].status
                == MagicStateStatus.DEPLETED
                for ms in fac.ms
            ):
                # trigger magic state factory replenishment
                #! verify: if magic states is replenished every time step, then self.TICK_REPLENSIH = 1, not 0
                if self.TICK_REPLENISH == 0:
                    graph_full.set_nodes_ticks(fac.ms, self.TICK_REPLENISH)
                else:
                    graph_full.set_nodes_ticks(fac.ms, self.TICK_REPLENISH + 1)

                for ms in fac.ms:
                    self.magic_states[ms].replenish()

        self.tick += ticks_elapsed

        # insert the rotations packed into the container with the scheduling
        if len(assigned_rotations) > 0:
            rotation_assignment[self.tick - 1] = assigned_rotations.copy()

    def choose_best_magic_state(
        self, graph: nx.Graph, ms_candidates: list, target
    ) -> tuple[
        Union[tuple[str, str], None], list[Union[tuple[str, str], int, nx.Graph]]
    ]:
        """Choose the magic state with the lowest(best) score, where score is calculated as:
        S = w * c_1 + c_2
        - c_1: number of ms available in factory
        - c_2: shortest path length to connect to the target
        - w: weight factor
        """

        # define the decision criteria:
        #   1: number of ms available in factory;
        #   2: shortest path length
        decision_criteria = {}
        for ms in ms_candidates:
            ms_ava = None
            if ms[0][0] == "m":
                # if candidate is a magic state
                ms_fac = self.magic_states[ms].factory
                ms_ava = self.factories[ms_fac].get_num_ms_available(self.magic_states)
            elif ms[0][0] == "s":
                # if candidate is a storage, ms_available is set to a higher score
                ms_ava = len(self.graph.components_by_type[ComponentType.MAGIC]) + 1
            decision_criteria[ms] = {
                "ms available in factory": ms_ava,
                "path length": 0,
            }

        # weight parameter
        criteria_weight = 100  # ms consumed/tiles used

        # find the shortest paths between source and target nodes
        ms_chosen = -1
        best_score = -1
        best_path = []
        for ms, criteria in decision_criteria.items():
            # initialize objective score with criteria 1
            score = criteria_weight * criteria["ms available in factory"]
            if ms_chosen == -1 or score < best_score:
                try:
                    # solve the shortest path problem
                    (length, path) = nx.single_source_dijkstra(
                        graph, ms, target=target, weight="weight"
                    )

                    # (OPTIONAL) store all paths generated to verify solution
                    criteria["path length"] = length

                    # calculate objective score from the criteria considered
                    score += length

                    # update ms chosen if best found
                    if ms_chosen == -1 or score < best_score:
                        ms_chosen = ms
                        best_score = score
                        best_path = path
                except nx.NetworkXNoPath:
                    # if no path exists, ignore
                    criteria["path length"] = 99999
                    continue
            else:
                continue

        if ms_chosen == -1:
            return None, []
        return ms_chosen, best_path
