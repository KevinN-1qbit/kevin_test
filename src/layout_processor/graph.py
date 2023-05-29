""" Functions and a class that relate the layout graph and qubit allocation
to data tiles.

The layout graph has nodes for all the data, bus and magic state tiles
and edges to indicate adjacency in the original layout.
"""

from __future__ import annotations

import dataclasses
from typing import (
    Literal,
    Mapping,
    Union,
    Iterable,
    ChainMap,
    NamedTuple,
    cast,
)
import collections

from layout_processor import patches
from scheduler.surface_code_layout import tiles
from scheduler.circuit_and_rotation.circuit import (
    PI8,
    PI4,
)


@dataclasses.dataclass(frozen=True)  # Makes immutable by standard means
class Graph:
    """A graph for the MIP scheduler to use.  Also can be plotted on a layout."""

    # Key is index in the graph, value is the tile.Tile from the TileLayout
    # Assuming this Graph is created from the TileLayout.get_graph_for_MIP
    # These start from 0 and increase consecutively (going up until you finish
    # a column of bus tiles, then continuing from the bottom next column of
    # bus tiles)
    inds_to_bus_tiles: dict[int, tiles.Tile]

    # Key is index in the graph, value is the edges.Edge from the TileLayout
    # The edges.Edge has information about the qubit number (or MS number or
    # resource number) if needed.
    inds_to_qubit_edges: dict[int, patches.Edge] = dataclasses.field(
        default_factory=dict
    )
    inds_to_resource_edges: dict[int, patches.Edge] = dataclasses.field(
        default_factory=dict
    )
    inds_to_ms_edges: dict[int, patches.Edge] = dataclasses.field(default_factory=dict)
    inds_to_storage_edges: dict[int, patches.Edge] = dataclasses.field(
        default_factory=dict
    )

    # This is "the graph", where key and values all represent nodes in the graph
    # This adj_matrix is bi-directional, but the get_directional_adj_matrix
    # method can be called to get directional connections for the MIP.
    adj_matrix: dict[int, set[int]] = dataclasses.field(
        default_factory=lambda: collections.defaultdict(set)
    )  # pylint: disable=line-too-long

    # These are intended to help the user to get the index in the graph
    # that they want.
    # For instance:
    # To get the index corresponding to the "X" edge of qubit number 5:
    #       self.qubit_edges_to_inds[(5, "X")]
    # To get the index corresponding to the "Z" edge of magic state number 2:
    #       self.ms_edges_to_inds[(2, "Z")]
    qubit_edges_to_inds: dict[
        tuple[int, Literal["X", "Z"], tuple[int, int]], int
    ] = dataclasses.field(default_factory=dict)
    resource_edges_to_inds: dict[
        tuple[int, Literal["X", "Z"], tuple[int, int]], int
    ] = dataclasses.field(default_factory=dict)
    ms_edges_to_inds: dict[
        tuple[int, Literal["X", "Z"], tuple[int, int]], int
    ] = dataclasses.field(default_factory=dict)
    storage_edges_to_inds: dict[
        tuple[int, Literal["X", "Z"], tuple[int, int]], int
    ] = dataclasses.field(default_factory=dict)

    @property
    def bus_tiles_to_inds(self) -> dict[tiles.Tile, int]:
        bus_tiles_to_inds_ = {val: key for key, val in self.inds_to_bus_tiles.items()}
        assert len(bus_tiles_to_inds_) == len(self.inds_to_bus_tiles)
        return bus_tiles_to_inds_

    @property
    def inds_to_all(self) -> Mapping[int, Union[tiles.Tile, patches.Edge]]:
        """All the inds mapped to their respective tiles and edges.

        I.e. all these dicts combined:
            inds_to_bus_tiles, inds_to_qubit_edges,
            inds_to_resource_edges, inds_to_ms_edges,
            and inds_to_storage_edges
        """

        # this cast normally wouldn't be valid (since type parameters of mutable containers need to be invariant)
        # but since we make sure all uses of the map are immutable I think it's ok
        return collections.ChainMap(
            cast(dict[int, tiles.Tile | patches.Edge], self.inds_to_bus_tiles),
            cast(dict[int, tiles.Tile | patches.Edge], self.inds_to_qubit_edges),
            cast(dict[int, tiles.Tile | patches.Edge], self.inds_to_resource_edges),
            cast(dict[int, tiles.Tile | patches.Edge], self.inds_to_ms_edges),
            cast(dict[int, tiles.Tile | patches.Edge], self.inds_to_storage_edges),
        )

    def __post_init__(self) -> None:
        # Check no duplicate bus_tiles
        bus_tiles = set(self.inds_to_bus_tiles.values())
        assert len(bus_tiles) == len(self.inds_to_bus_tiles)

        if self.adj_matrix == {}:
            # Wire up the adj_matrix if it was not initialized
            bus_tiles_to_inds = self.bus_tiles_to_inds
            for ind, tile in self.inds_to_bus_tiles.items():
                for n in tile.neighbors & bus_tiles:
                    ind_n = bus_tiles_to_inds[n]
                    self.adj_matrix[ind].add(ind_n)

        self.validate()

    def validate(self) -> None:
        assert len(self.inds_to_bus_tiles) > 0
        assert (
            len(self.inds_to_bus_tiles)
            + len(self.inds_to_qubit_edges)
            + len(self.inds_to_resource_edges)
            + len(self.inds_to_ms_edges)
            + len(self.inds_to_storage_edges)
            == len(self.inds_to_all)
            == len(self.adj_matrix)
        )
        assert (
            self.inds_to_bus_tiles.keys()
            | self.inds_to_qubit_edges.keys()
            | self.inds_to_resource_edges.keys()
            | self.inds_to_ms_edges.keys()
            | self.inds_to_storage_edges.keys()
            == self.inds_to_all.keys()
            == self.adj_matrix.keys()
        )

        assert self.inds_to_bus_tiles.keys() == set(self.bus_tiles_to_inds.values())
        assert self.inds_to_qubit_edges.keys() == set(self.qubit_edges_to_inds.values())
        assert self.inds_to_resource_edges.keys() == set(
            self.resource_edges_to_inds.values()
        )
        assert self.inds_to_ms_edges.keys() == set(self.ms_edges_to_inds.values())
        assert self.inds_to_storage_edges.keys() == set(
            self.storage_edges_to_inds.values()
        )

    def _add_patch(self, patch: patches.Patch) -> None:
        """Adds to the Graph all edges in patch that connect to the bus. Indices
        for these edges are automatically generated"""

        bus_tiles_to_inds = self.bus_tiles_to_inds
        for edge in sorted(patch.edges, key=patches.edge_key):
            if edge.neighbor_tile in bus_tiles_to_inds:
                if edge.content_type == "magic" and edge.xz_type == "X":
                    assert False, "This is not expected to happen!"
                if edge.xz_type in ["XX", "ZZ"]:
                    # Not going to add these for now, as expect to be
                    # rarely useful
                    continue
                assert edge.content_type == patch.content_type
                ind = len(self.inds_to_all)
                assert (
                    ind not in self.inds_to_all
                ), "This code has assumed the inds start at 0 and are consecutive"

                self._add_edge(ind, edge)

    def _add_edge(self, ind: int, edge: patches.Edge) -> None:
        """Adds "edge" to the graph with the index "ind" """
        assert isinstance(edge, patches.Edge)

        if edge.ind is None:
            raise ValueError("Edge Index cannot be None")

        xz = edge.xz_type
        assert xz == "X" or xz == "Z"

        eti_key = (edge.ind, xz, (edge.neighbor_tile.x, edge.neighbor_tile.y))

        inds_to_edge_dict: dict[int, patches.Edge] = dict(
            qubit=self.inds_to_qubit_edges,
            resource=self.inds_to_resource_edges,
            magic=self.inds_to_ms_edges,
            storage=self.inds_to_storage_edges,
        )[edge.content_type]
        match edge.content_type:
            case "qubit":
                edge_to_inds_dict = self.qubit_edges_to_inds
            case "resource":
                edge_to_inds_dict = self.resource_edges_to_inds
            case "magic":
                edge_to_inds_dict = self.ms_edges_to_inds
            case "storage":
                edge_to_inds_dict = self.storage_edges_to_inds

        assert ind not in self.inds_to_all, "ind already in use"
        assert ind not in inds_to_edge_dict
        assert ind not in self.adj_matrix

        edge_to_inds_dict[eti_key] = ind
        inds_to_edge_dict[ind] = edge
        ind_bus_neighbor = self.bus_tiles_to_inds[edge.neighbor_tile]
        self.adj_matrix[ind] = {ind_bus_neighbor}
        self.adj_matrix[ind_bus_neighbor].add(ind)

    def __str__(self) -> str:
        s = ""
        s += f"\ninds_to_bus_tiles={self.inds_to_bus_tiles}"
        s += f"\ninds_to_qubit_edges={self.inds_to_qubit_edges}"
        s += f"\ninds_to_resource_edges={self.inds_to_resource_edges}"
        s += f"\ninds_to_ms_edges={self.inds_to_ms_edges}"
        s += f"\ninds_to_storage_edges={self.inds_to_storage_edges}"

        s += f"\n\ninds_to_bus_tiles={self.inds_to_bus_tiles.keys()}"
        s += f"\ninds_to_qubit_edges={self.inds_to_qubit_edges.keys()}"
        s += f"\ninds_to_resource_edges={self.inds_to_resource_edges.keys()}"
        s += f"\ninds_to_ms_edges={self.inds_to_ms_edges.keys()}"
        s += f"\ninds_to_storage_edges={self.inds_to_storage_edges.keys()}"

        s += f"\n\nadj_matrix={self.adj_matrix}"

        return s

    def get_all_connections(self) -> set[tuple[int, int]]:
        return {
            tuple(sorted([ind1, ind2]))  # type: ignore
            for ind1, inds in self.adj_matrix.items()
            for ind2 in inds
        }

    def plot_on_ax(self, alpha: float, ax, color) -> None:
        """Plots the graph for the MIP (on top of the layout)

        Plots lines of color "color" showing the connections of
            bus tiles to each other and to edges
        Prints the index numbers of graph nodes in color "color":
            In the middle of bus tiles in medium text
            On the out side of edges in small text
        """

        class Point(NamedTuple):
            x: float
            y: float

        def center(val_: Union[tiles.Tile, patches.Edge]) -> Point:
            if isinstance(val_, tiles.Tile):
                return Point(val_.x, val_.y)
            else:
                assert isinstance(val_, patches.Edge)
                return Point(
                    (val_.patch_tile.x + val_.neighbor_tile.x) / 2,
                    (val_.patch_tile.y + val_.neighbor_tile.y) / 2,
                )

        for ind1, ind2 in self.get_all_connections():
            center1 = center(self.inds_to_all[ind1])
            center2 = center(self.inds_to_all[ind2])
            # Plot line showing connection between nodes in graph
            ax.plot(
                [center1.x, center2.x], [center1.y, center2.y], color=color, alpha=alpha
            )

        for ind, val in self.inds_to_all.items():
            if isinstance(val, tiles.Tile):
                ax.text(
                    val.x,
                    val.y,
                    f"{ind}",
                    fontsize=12,
                    color=color,
                    verticalalignment="center",
                    horizontalalignment="center",
                )
            else:
                assert isinstance(val, patches.Edge)
                ax.text(
                    val.patch_tile.x * 0.35 + val.neighbor_tile.x * 0.65,
                    val.patch_tile.y * 0.35 + val.neighbor_tile.y * 0.65,
                    f"{ind}",
                    fontsize=9,
                    color=color,
                    verticalalignment="center",
                    horizontalalignment="center",
                )

    @staticmethod
    def build_from(
        inds_to_bus_tiles: dict[int, tiles.Tile], patches_: Iterable[patches.Patch]
    ) -> Graph:
        g = Graph(inds_to_bus_tiles)

        for patch in sorted(patches_, key=patches.patch_key):
            g._add_patch(patch)  # pylint: disable=protected-access

        return g
