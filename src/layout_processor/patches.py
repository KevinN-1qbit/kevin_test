""" Contains a class for surface code patches, which usually occupy 1 or 2 tiles

Also contains a class for the edge of a patch,
which are usually of type "X" or "Z"
"""

from __future__ import annotations

from typing import Iterable, Literal, Union, Collection, Optional
import dataclasses

from layout_processor import tile_layout
from scheduler.surface_code_layout import tiles

EdgeType = Literal["X", "Z", "XX", "ZZ"]


def edge_key(edge: Edge) -> tuple:
    """To be used as a sort key for edges"""
    return tiles.key(edge.patch_tile), tiles.key(edge.neighbor_tile)


@dataclasses.dataclass(frozen=True)  # Makes immutable by standard means
class Edge:
    """Represents a single edge of a surface code patch.

    Usually this edge is of type "X" or "Z",
    although it is sometimes of type "XX" or "ZZ" for 2-qubit fast-patches
        1 or 2 qubits,
        1 or 2 adjacent tiles, and
        edges all around
    """

    patch_tile: tiles.Tile
    neighbor_tile: tiles.Tile
    xz_type: EdgeType
    content_type: Literal["qubit", "magic", "resource"]
    # The index of the qubit, MS, or resource state that the edge "exposes".
    ind: Optional[int]

    # type: ignore
    def __post_init__(self) -> None:
        assert self.neighbor_tile in self.patch_tile.neighbors
        assert self.xz_type in ["X", "Z", "XX", "ZZ"]
        assert self.content_type in ["qubit", "magic", "resource", "storage"]

    def plot_on_ax(self, ax) -> None:
        """Plot the solid or dotted lines representing this edge."""
        # We want a horizontal line if the tiles align vertically and vice versa
        dy = abs(self.patch_tile.x - self.neighbor_tile.x) / 2.2
        dx = abs(self.patch_tile.y - self.neighbor_tile.y) / 2.2

        # Move the lines a little toward the patch tile
        x = (self.patch_tile.x * 1.2 + self.neighbor_tile.x) / 2.2
        y = (self.patch_tile.y * 1.2 + self.neighbor_tile.y) / 2.2

        linestyle = dict(X=":", Z="-", XX=":", ZZ="-")[self.xz_type]
        x_range = [x - dx, x + dx]
        y_range = [y - dy, y + dy]

        ax.plot(x_range, y_range, linestyle=linestyle, linewidth=4, color="black")

    def plot_description_on_ax(self, ax) -> None:
        """Write the qubit number next to the edge just inside the patch

        This is intended to be used for fast block patches only, since
        they have 2 qubits so one cannot write a single qubit number
        in the middle of the patch"""
        x = 0.7 * self.patch_tile.x + (1 - 0.7) * self.neighbor_tile.x
        y = 0.7 * self.patch_tile.y + (1 - 0.7) * self.neighbor_tile.y
        qb = self.ind if self.ind is not None else self.content_type[0]
        ax.text(
            x,
            y,
            qb,
            fontsize=10,
            horizontalalignment="center",
            verticalalignment="center",
        )


def patch_key(patch: Patch) -> tuple:
    tile_key = min(tiles.key(t) for t in patch.tiles)
    return patch.content_type, tile_key


class Patch:
    """Represents a surface code patch.

    Usually contains:
        1 or 2 qubits,
        1 or 2 adjacent tiles, and
        edges all around
    """

    def __init__(
        self,
        type_: Literal["qubit", "resource", "magic", "storage"],
        inds: Iterable[int],
        tiles_: Iterable[tiles.Tile],
        edges: Iterable[Edge],
        layout: tile_layout.TileLayout,
    ) -> None:
        # There can be 1 or two qubits in a patch
        self.content_type: Literal["qubit", "resource", "magic", "storage"] = type_
        self.inds: frozenset[int] = frozenset(inds)

        self.tiles: set[tiles.Tile] = set(tiles_)  # The tiles inside the patch
        self.edges: set[Edge] = set(edges)  # The type of edge with
        self.layout: tile_layout.TileLayout = layout

        self.validate()

    @property
    def ind(self):
        assert len(self.inds) == 1, (
            "This property should not be used on a " "2-qubit patch"
        )
        return next(iter(self.inds))

    def __repr__(self) -> str:
        s = (
            f"Patch - tiles={self.tiles},  type={self.content_type},  "
            f"inds={self.inds}"
        )
        s += f"\n\t edges={self.edges}"
        return s

    def validate(self) -> None:
        self.validate_edges()

        # Check types
        assert isinstance(self.inds, frozenset)
        assert self.content_type in ["qubit", "resource", "magic", "storage"]
        assert isinstance(self.tiles, set)
        assert isinstance(self.edges, set)
        assert isinstance(self.layout, tile_layout.TileLayout)

        # Check that allocated to correct kind of tile
        if len(self.inds) == 1:
            if self.content_type == "magic":
                assert len(self.tiles) == 1
                assert self.tiles.issubset(self.layout.tiles_ms)
            if self.content_type == "resource":
                assert len(self.tiles) == 2
                assert self.tiles.issubset(self.layout.tiles_resource)

    def validate_edges(self) -> None:
        # Check that all external edges exist
        edge_neighbors = [edge.neighbor_tile for edge in self.edges]
        assert len(edge_neighbors) == len(set(edge_neighbors))
        assert tiles.get_neighbors(self.tiles) == set(edge_neighbors)

        # todo Validate (for 1 qubit case) that two X sided
        # todo Validate (for 1 qubit case) that two Z sided

    def get_neighbors(
        self, edge_type: EdgeType, empty_ok=False
    ) -> frozenset[tiles.Tile]:
        neighbors = frozenset(
            edge.neighbor_tile for edge in self.edges if edge == edge_type
        )
        assert empty_ok or neighbors
        return neighbors

    def get_bus_neighbors(
        self, edge_type: Union[EdgeType, Literal["any"]] = "any"
    ) -> frozenset[tiles.Tile]:
        if edge_type == "any":
            neighbors = tiles.get_neighbors(self.tiles)
        else:
            neighbors = frozenset(
                edge.neighbor_tile for edge in self.edges if edge == edge_type
            )
        bus_neighbors = neighbors & self.layout.tiles_bus
        return bus_neighbors

    def plot_on_ax(self, ax) -> None:
        for edge in self.edges:
            edge.plot_on_ax(ax)

        assert len(self.tiles) <= 2, (
            "Below we plot a thin solid line around the patch, "
            "to make it clear that this is a single patch.  "
            "This code only works if len(self.tiles) <= 2.  "
            "At this point I (BK) don't see why we would have larger patches"
            "than this."
        )
        xs = [t.x for t in self.tiles]
        x_min = min(xs) - 0.45
        x_max = max(xs) + 0.45

        ys = [t.y for t in self.tiles]
        y_min = min(ys) - 0.45
        y_max = max(ys) + 0.45

        styling = dict(linestyle="-", linewidth=2, color="black", alpha=0.7)

        # Horizontal lines
        ax.plot([x_min, x_max], [y_min, y_min], **styling)
        ax.plot([x_min, x_max], [y_max, y_max], **styling)

        # Vertical lines
        ax.plot([x_min, x_min], [y_min, y_max], **styling)
        ax.plot([x_max, x_max], [y_min, y_max], **styling)

        if len(self.inds) == 1:
            x, y = tiles.get_center(self.tiles)
            ax.text(
                x,
                y,
                f"{self.content_type[0]}{self.ind}",
                fontsize=15,
                horizontalalignment="center",
                verticalalignment="center",
            )
        else:
            assert len(self.inds) == 2
            for edge in self.edges:
                edge.plot_description_on_ax(ax)

    @staticmethod
    def init_patch_z_top_bottom(
        ind: int,
        type_: Literal["qubit", "resource", "magic"],
        tile: tiles.Tile,
        layout: tile_layout.TileLayout,
    ) -> Patch:
        """Creates a 1-qubit, 1-tile compact patch.

        Such a patch is depicted here
         __
        :  :
         ¯¯

        The qubit's X edges are exposed on the left and right
        The qubit's Z edges are exposed on the top and bottom

        If the bus runs along only one side of the patch, this means the patch
        will have to be rotated to do both X and Z operations on the qubit.
        """
        edges = [
            Edge(tile, tile.up, "Z", type_, ind),
            Edge(tile, tile.down, "Z", type_, ind),
            Edge(tile, tile.left, "X", type_, ind),
            Edge(tile, tile.right, "X", type_, ind),
        ]
        return Patch(type_, [ind], {tile}, edges, layout)

    @staticmethod
    def init_patch_x_top_bottom(
        ind: int,
        type_: Literal["qubit", "resource", "magic", "storage"],
        tile: tiles.Tile,
        layout: tile_layout.TileLayout,
    ) -> Patch:
        """See init_patch_z_top_bottom doc string, but rotated 90 degrees"""
        edges = [
            Edge(tile, tile.up, "X", type_, ind),
            Edge(tile, tile.down, "X", type_, ind),
            Edge(tile, tile.left, "Z", type_, ind),
            Edge(tile, tile.right, "Z", type_, ind),
        ]
        return Patch(type_, {ind}, {tile}, edges, layout)

    @staticmethod
    def init_2_tile_patch(
        ind: int,
        type_: Literal["qubit", "resource", "magic"],
        tiles_: Collection[tiles.Tile],
        layout: tile_layout.TileLayout,
    ) -> Patch:
        """Creates a 1-qubit and 2-tile patch.

        Such a patch is depicted here (vertical orientation depicted.
        Horizontal orientation is also possible):
         ..
        :  |
        |__:

        The qubit's X and Z edges are both exposed on the left and right, making
            a Y measurement possible (if the bus runs along the left or right
            of the patch).
        The top is an X edge and the bottom is a Z edge
        """
        assert len(tiles_) == 2
        t1: tiles.Tile
        t2: tiles.Tile
        t1, t2 = sorted(tiles_, key=tiles.key)
        dir_t1_t2 = t1.direction_to_tile(t2)
        edges = [
            Edge(t2, t2.get_tile_in_dir(dir_t1_t2 - 1), "X", type_, ind),
            Edge(t1, t1.get_tile_in_dir(dir_t1_t2 - 1), "Z", type_, ind),
            Edge(t2, t2.get_tile_in_dir(dir_t1_t2 + 1), "Z", type_, ind),
            Edge(t1, t1.get_tile_in_dir(dir_t1_t2 + 1), "X", type_, ind),
            Edge(t2, t2.get_tile_in_dir(dir_t1_t2), "X", type_, ind),
            Edge(t1, t1.get_tile_in_dir(dir_t1_t2 + 2), "Z", type_, ind),
        ]
        return Patch(type_, {ind}, tiles_, edges, layout)

    @staticmethod
    def init_fast_patch(
        inds: list[int],
        type_: Literal["qubit", "resource", "magic"],
        tiles_: list[tiles.Tile],
        layout: tile_layout.TileLayout,
    ) -> Patch:
        """Creates a Fast Block layout, 2-qubit and 2-tile patch.

        Such a patch is depicted here (vertical orientation depicted.
        Horizontal orientation is also possible):
            __
        q1 :  : q2
        q1 |..| q2

        qubit 1's X and Z edges are on the left
        qubit 2's X and Z edges are on the right
        The top is the ZZ edge and the bottom is the XX edge.
        """
        assert len(inds) == 2
        assert len(tiles_) == 2
        assert type_ == "qubit"

        q1, q2 = inds
        t1, t2 = tiles_
        dir_t1_t2 = t1.direction_to_tile(t2)
        edges = [
            Edge(t2, t2.get_tile_in_dir(dir_t1_t2 - 1), "X", type_, q1),
            Edge(t1, t1.get_tile_in_dir(dir_t1_t2 - 1), "Z", type_, q1),
            Edge(t2, t2.get_tile_in_dir(dir_t1_t2 + 1), "X", type_, q2),
            Edge(t1, t1.get_tile_in_dir(dir_t1_t2 + 1), "Z", type_, q2),
            Edge(t2, t2.get_tile_in_dir(dir_t1_t2 + 0), "ZZ", type_, None),
            Edge(t1, t1.get_tile_in_dir(dir_t1_t2 + 2), "XX", type_, None),
        ]
        return Patch(type_, inds, set(tiles_), edges, layout)
