""" 
InnerCaching is the class that specifies functions and data to cache shortest paths between data qubits
"""
from __future__ import annotations

import bisect
from collections import defaultdict

import networkx as nx


class SPCaching:
    """A class for functions and data to cache the shortest paths between data qubits"""

    def __init__(self):
        self._spp_caching = defaultdict(lambda: [])

    def spp_caching(self):
        return self._spp_caching

    def reset_spp_caching(self):
        self._spp_caching = defaultdict(lambda: [])

    def query_spp_cache(
        self,
        source: tuple[str, str],
        target: tuple[str, str],
        nx_graph: nx.Graph,
    ) -> tuple[tuple[str, str], tuple[float, list[int | tuple[str, str]]]] | None:
        """This function is used to retrieve a feasible path between a pair of terminals from the cache;
        Args:
            source: the source terminal;
            target: the other terminal;
            nx_graph: the nx graph on which the stree is generated
        Returns:
            Either the path or None; None stands for no feasible path retrieved.
        """
        if not self._check_data_qbit(source, target):
            return None
        terminal_pair = self._get_key_from_terminals(source, target)
        path_list = self._spp_caching[terminal_pair]
        if path_list:
            for p in path_list:
                new_path = p[1] if source == p[1][0] else list(reversed(p[1]))
                if self.spp_fc(new_path, nx_graph):
                    # return the key and the data of the path if found
                    return terminal_pair, (p[0], new_path)
        return None

    @staticmethod
    def spp_fc(
        path: list,
        nx_graph: nx.Graph,
    ):
        """The feasibility checker to judge if a path is feasible for the graph
        on which a stree is generated
        Args:
            path: list of terminals
            nx_graph: the nx graph on which the stree is generated
        """
        for i in range(len(path) - 1):
            e = (path[i], path[i + 1])
            if not nx_graph.has_edge(*e):
                return False
        return True

    def add_spp_cache(
        self,
        source: tuple[str, str],
        target: tuple[str, str],
        value: tuple[float, list],
    ) -> None:
        """A function to add a path as an entry of the cache.
        Args:
            source: the source terminal;
            target: the target terminal;
            value: the shortest path from source to target. It is a tuple, of which the
                   first element is the distance while the seond is the trajectory.
        Return:
            None
        """
        # filter out non-data-qubits
        if self._check_data_qbit(source, target):
            path_list = self._spp_caching[self._get_key_from_terminals(source, target)]
            pos = bisect.bisect_left(path_list, value)
            path_list.insert(pos, value)

    @staticmethod
    def _get_key_from_terminals(
        source: tuple[str, str], target: tuple[str, str]
    ) -> tuple[str, str]:
        """A function to return the correct key according to terminals
        Args:
            source: the source terminal;
            target: the target terminal;
        Returns:
            A tuple represents the key associated with the pair of "source" and "target".
        """
        tmp_list = [source, target]

        # sort by node type (given by the first letter)
        # 'q': data qubit
        # 'm': magic state qubit
        # 's': storage qubit
        # 'r': zero state qubit
        tmp_list.sort(key=lambda x: x[0][0])

        if source[0][0] == target[0][0]:
            # sort by the index if they have the same type
            tmp_list.sort(key=lambda x: x[0].split(x[0])[1])
        return tmp_list[0], tmp_list[1]

    @staticmethod
    def _check_data_qbit(source: tuple[str, str], target: tuple[str, str]) -> bool:
        """A function to check if the terminals are both data qubits.
        If not, we just skip dealing with the cache. Because, we just cache the results associated with
        data qubits for now.
        """
        try:
            return source[0][0] == "q" and target[0][0] == "q"
        except KeyError:
            """Very rarely, source and target don't match the patter of tuple[str, str].
            It needs to be further investigated.
            """
            return False
