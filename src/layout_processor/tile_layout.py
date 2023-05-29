""" Contains class TileLayout and functions to build TileLayout instances """

from __future__ import annotations

import dataclasses
import functools
import itertools as it
import math
import json
import pickle
from typing import Literal, Union, Iterable
import datetime
import matplotlib.pyplot as plt
import os.path as osp
import sys
from layout_processor import patches, graph
from scheduler.surface_code_layout import tiles

FrozenDict = dict  # To indicate wish could make frozen (shouldn't be modified)!


class LayoutError(Exception):
    pass


@dataclasses.dataclass(frozen=True)  # Makes immutable by standard means
class TileLayout:
    """The layout of a surface code error-corrected quantum computer

    Contains bus, data, magic state and resource tile types.
    Optionally can include
        magic state factories
        patches with qubits assigned to them
    """

    tiles_bus: frozenset[tiles.Tile]
    tiles_data: frozenset[tiles.Tile]
    tiles_ms: frozenset[tiles.Tile]
    tiles_resource: frozenset[tiles.Tile]
    tiles_storage: frozenset[tiles.Tile]
    ms_factories: list[TileLayout] = dataclasses.field(default_factory=list)

    _patches: set[patches.Patch] = dataclasses.field(default_factory=set)
    _qubits_to_patches: dict[int, patches.Patch] = dataclasses.field(
        default_factory=dict
    )
    _resources_to_patches: dict[int, patches.Patch] = dataclasses.field(
        default_factory=dict
    )
    _mss_to_patches: dict[int, patches.Patch] = dataclasses.field(default_factory=dict)
    _storage_to_patches: dict[int, patches.Patch] = dataclasses.field(
        default_factory=dict
    )
    # All the tiles that are already contained in patches (for checking that
    # new patches do not overlap existing patches).
    _patch_tiles: set[tiles.Tile] = dataclasses.field(default_factory=set)

    # Set to true if user wants to plot the magic state factories along with the layout
    add_msfs: dataclasses.InitVar[bool] = False

    def __post_init__(self, add_msfs: bool) -> None:
        if add_msfs:
            self._add_msfs()

    @functools.cached_property
    def bus_tiles_to_inds(self) -> FrozenDict:
        btti = {t: i for i, t in enumerate(sorted(self.tiles_bus, key=tiles.key))}
        assert sorted(set(btti.values())) == list(range(len(btti)))
        assert btti.keys() == self.tiles_bus
        return btti

    @functools.cached_property
    def inds_to_bus_tiles(self) -> FrozenDict:
        ttn = self.bus_tiles_to_inds
        ntt = {val: key for key, val in ttn.items()}
        assert len(ttn) == len(ntt)
        return ntt

    @functools.cached_property
    def qubit_tiles_to_inds(self) -> FrozenDict:
        qtti = {t: i for i, t in enumerate(sorted(self.tiles_data, key=tiles.key))}
        assert sorted(set(qtti.values())) == list(range(len(qtti)))
        assert qtti.keys() == self.tiles_data
        return qtti

    @functools.cached_property
    def storage_tiles_to_inds(self) -> FrozenDict:
        qtti = {t: i for i, t in enumerate(sorted(self.tiles_storage, key=tiles.key))}
        assert sorted(set(qtti.values())) == list(range(len(qtti)))
        assert qtti.keys() == self.tiles_storage
        return qtti

    def tiles_all(self, include_msf_tiles=True) -> frozenset[tiles.Tile]:
        tiles_ = self.tiles_bus | self.tiles_data | self.tiles_ms | self.tiles_resource
        if include_msf_tiles:
            for msf in self.ms_factories:
                tiles_ |= msf.tiles_all()
        return tiles_

    def get_graph_for_mip(self) -> graph.Graph:
        return graph.Graph.build_from(self.inds_to_bus_tiles, self.get_patches())

    def plot(
        self,
        alpha=0.3,
        title="Plot of TileLayout",
        graphs: Iterable[graph.Graph] = frozenset([]),
        display_msfs=True,
    ) -> None:
        colours = it.cycle(["b", "g", "r", "c", "m", "y", "k", "w"])

        # Use subplots to get "fig" and "axes", and set the figure size
        fig, axes = plt.subplots(1, 1, figsize=(12, 8))
        ax = axes  # It's not a list, b/c only 1 subplot

        self.plot_on_ax(alpha, ax, display_msfs=display_msfs)
        g: graph.Graph
        for g, c in zip(graphs, colours):
            g.plot_on_ax(alpha, ax, c)

        ax.set_xlim(
            [
                min(t.x for t in self.tiles_all(display_msfs)) - 1,
                max(t.x for t in self.tiles_all(display_msfs)) + 1,
            ]
        )
        ax.set_ylim(
            [
                min(t.y for t in self.tiles_all(display_msfs)) - 1,
                max(t.y for t in self.tiles_all(display_msfs)) + 1,
            ]
        )

        # 24hr time
        date_time_stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        ax.set_title(f"{date_time_stamp}\n{title}")
        ax.set_xlabel(f"x")
        ax.set_ylabel(f"y")

        ax.legend()
        fig.show()
        print(f"plot done")

    def plot_on_ax(self, alpha: float, ax, display_msfs=True):
        for tile in self.tiles_bus:
            tile.plot_on_ax(ax, alpha=alpha, colour="green")
        for tile in self.tiles_data:
            tile.plot_on_ax(ax, alpha=alpha, colour="blue")
        for tile in self.tiles_ms:
            tile.plot_on_ax(ax, alpha=alpha, colour="red")
        for tile in self.tiles_resource:
            tile.plot_on_ax(ax, alpha=alpha, colour="purple")
        for tile in self.tiles_storage:
            tile.plot_on_ax(ax, alpha=alpha, colour="yellow")
        if display_msfs:
            for msf in self.ms_factories:
                msf.plot_on_ax(alpha / 3, ax)
        for patch in self._patches:
            patch.plot_on_ax(ax)

    def get_patches(self) -> set[patches.Patch]:
        """Use this getter to get self._patches such that can't modify it."""
        return set(self._patches)

    @property
    def n_patches(self) -> int:
        """The number of qubit, resource, and MS patches"""
        return len(self._patches)

    @property
    def n_qubits(self) -> int:
        """The number of qubits (encoded in patches)"""
        return len(self._qubits_to_patches)

    @property
    def n_bus(self) -> int:
        """The number of bus tiles"""
        return len(self.tiles_bus)

    def add_patch(self, patch_: patches.Patch) -> None:
        dict_to_add_to = dict(
            qubit=self._qubits_to_patches,
            resource=self._resources_to_patches,
            magic=self._mss_to_patches,
            storage=self._storage_to_patches,
        )[patch_.content_type]
        assert patch_.inds & dict_to_add_to.keys() == set()
        for ind in patch_.inds:
            assert isinstance(ind, int)
            assert ind not in dict_to_add_to
            dict_to_add_to[ind] = patch_

        assert patch_.tiles & self._patch_tiles == set()
        self._patches.add(patch_)
        self._patch_tiles.update(patch_.tiles)

    def add_patches_to_mss(self) -> None:
        """Add patches to the MS, numbered 1,2,3, and oriented with a z-edge
        towards a neighboring bus tile
        """
        for ind, tile in enumerate(sorted(self.tiles_ms, key=tiles.key)):
            bus_neighbors = tile.neighbors & self.tiles_bus
            assert len(bus_neighbors) == 1, (
                "While it is possible to have the X sides in contact "
                "with the bus as well, I didn't see why one would "
                "build a layout like that (wasteful of tiles), so I put "
                "this assert in. If >1 side is in contact with the bus "
                "I expect this is an error."
            )
            (bus_neighbor,) = bus_neighbors
            if tile.direction_to_tile(bus_neighbor) % 2 == 0:
                self.add_patch(
                    patches.Patch.init_patch_z_top_bottom(ind, "magic", tile, self)
                )
            else:
                self.add_patch(
                    patches.Patch.init_patch_x_top_bottom(ind, "magic", tile, self)
                )

    def add_patches_to_resource_tiles(self) -> None:
        resource_tiles_to_assign_patches_to = set(self.tiles_resource)
        ind = 0
        while resource_tiles_to_assign_patches_to:
            for t1 in sorted(resource_tiles_to_assign_patches_to, key=tiles.key):
                n = t1.neighbors & resource_tiles_to_assign_patches_to
                if len(n) == 0:
                    raise LayoutError(
                        "It appears that resource tiles are not" "laid out in pairs"
                    )
                if len(n) == 1:
                    (t2,) = n
                    resource_tiles_to_assign_patches_to.remove(t1)
                    resource_tiles_to_assign_patches_to.remove(t2)
                    self.add_patch(
                        patches.Patch.init_2_tile_patch(ind, "resource", [t1, t2], self)
                    )
                    ind += 1
                    break
            else:
                LayoutError(
                    "It appears that the resource tiles are laid out "
                    "such that they cannot be easily unambiguously "
                    "paired to create patches.  Please check "
                    "your layout and, if correct, "
                    "create and add patches manually "
                    "for the zero resource states."
                )

    def _add_msfs(self) -> None:
        """Automatically adds a MSF for each MS in the layout"""
        assert self.ms_factories == []
        for tile_ms in self.tiles_ms:
            bts = tile_ms.neighbors & self.tiles_bus
            assert len(bts) == 1
            (bt,) = bts
            msf = get_msf_15_to_1_protocol(tile_ms, bt.direction_to_tile(tile_ms))
            self.ms_factories.append(msf)

    def validate_patches(self, can_be_on_bus=False) -> None:
        p1: patches.Patch
        p2: patches.Patch
        for p1, p2 in it.combinations(self._patches, 2):
            assert p1.tiles & p2.tiles == set()

        if not can_be_on_bus:
            for p1 in self._patches:
                assert p1.tiles & self.tiles_bus == set()


def get_msf_15_to_1_protocol(ms_tile: tiles.Tile, dir_to_expand_in: int) -> TileLayout:
    """Creates a MSF (Magic State Factory) for the 15:1 distillation protocol
    using a fixed layout as:
      d d r r
    m b b r r
      d d

    m: distillation port
    b: bus qubit
    d: data qubit
    r: distillary qubit

    This layout can be rotated along each of the 4 directions, and
    hence "dir_to_expand_in % 4" determines the direction in which
    the MSF expands out of the Magic State.
    """
    bus_tile1 = ms_tile.get_tile_in_dir(dir_to_expand_in)
    tiles_bus = [bus_tile1, bus_tile1.get_tile_in_dir(dir_to_expand_in)]

    tiles_data = set()
    for t in tiles_bus:
        tiles_data.add(t.get_tile_in_dir(dir_to_expand_in + 1))
        tiles_data.add(t.get_tile_in_dir(dir_to_expand_in - 1))

    tiles_resource = []
    tiles_resource.append(tiles_bus[-1].get_tile_in_dir(dir_to_expand_in))
    tiles_resource.append(tiles_resource[-1].get_tile_in_dir(dir_to_expand_in))
    tiles_resource.append(tiles_resource[0].get_tile_in_dir(dir_to_expand_in + 1))
    tiles_resource.append(tiles_resource[1].get_tile_in_dir(dir_to_expand_in + 1))

    return TileLayout(
        frozenset(tiles_bus),
        frozenset(tiles_data),
        frozenset([ms_tile]),
        frozenset(tiles_resource),
        frozenset(),
        add_msfs=False,
    )


def get_compact_linear_tile_layout(
    n_data: int, n_magic: Literal[1, 2], n_resource_states: Literal[1, 2] = 2
) -> TileLayout:
    """Creates a compact linear layout (per Litinsky's paper, A Game of
    Surface Codes, Figure 11c)

    The magic states are place at one or both ends of the horizontal linear bus

    Resource state(s) and data qubits (using compact 1-tile patches) are place
    top and bottom of the linear bus
    """
    bus_len = (n_data + n_resource_states * 2 + n_magic - 1) // 2

    tiles_bus = {tiles.Tile(x, 0) for x in range(bus_len)}

    if n_magic == 1:
        tiles_ms = {tiles.Tile(-1, 0)}
    else:
        assert n_magic == 2
        tiles_ms = {tiles.Tile(-1, 0), tiles.Tile(bus_len, 0)}

    if n_resource_states == 1:
        tiles_resource = {tiles.Tile(0, -1), tiles.Tile(1, -1)}
    elif n_resource_states == 2:
        tiles_resource = {
            tiles.Tile(0, -1),
            tiles.Tile(1, -1),
            tiles.Tile(bus_len - 2, -1),
            tiles.Tile(bus_len - 1, -1),
        }
    else:
        raise Exception("Haven't implemented for other values")

    tiles_data = tiles.get_neighbors(tiles_bus) - tiles_ms - tiles_resource

    assert len(tiles_data) in [n_data, n_data + 1]

    layout = TileLayout(
        frozenset(tiles_bus),
        frozenset(tiles_data),
        frozenset(tiles_ms),
        frozenset(tiles_resource),
    )

    for ind, tile in zip(range(n_data), tiles_data):
        layout.add_patch(
            patches.Patch.init_patch_x_top_bottom(ind, "qubit", tile, layout)
        )
    layout.add_patches_to_resource_tiles()
    layout.add_patches_to_mss()

    return layout


def get_linear_intermediate_block(
    n_data: int, n_magic: Literal[1, 2], n_resource_states: Literal[1, 2] = 2
) -> TileLayout:
    """Creates a intermediate linear layout (per Litinsky's paper, A Game of
    Surface Codes, Figure 13a)

    The magic states are place at one or both ends of the horizontal linear bus

    Resource state(s) and data qubits (using compact 1-tile patches) are place
    top and bottom of the linear bus
    """
    bus_len = n_data + n_resource_states * 2

    tiles_bus = {tiles.Tile(x, 0) for x in range(bus_len)}

    if n_magic == 1:
        tiles_ms = {tiles.Tile(-1, 0)}
    else:
        assert n_magic == 2
        tiles_ms = {tiles.Tile(-1, 0), tiles.Tile(bus_len, 0)}

    if n_resource_states == 1:
        tiles_resource = {tiles.Tile(0, 1), tiles.Tile(1, 1)}
    elif n_resource_states == 2:
        tiles_resource = {
            tiles.Tile(0, 1),
            tiles.Tile(1, 1),
            tiles.Tile(bus_len - 2, 1),
            tiles.Tile(bus_len - 1, 1),
        }
    else:
        raise Exception("Haven't implemented for other values")

    tiles_data = tiles.get_neighbors_single_deck(tiles_bus) - tiles_ms - tiles_resource

    layout = TileLayout(
        frozenset(tiles_bus),
        frozenset(tiles_data),
        frozenset(tiles_ms),
        frozenset(tiles_resource),
    )

    for ind, tile in zip(range(n_data), tiles_data):
        layout.add_patch(
            patches.Patch.init_patch_x_top_bottom(ind, "qubit", tile, layout)
        )
    layout.add_patches_to_resource_tiles()
    layout.add_patches_to_mss()

    return layout


def get_fast_linear_tile_layout(
    n_data: int, n_magic: Literal[1, 2], n_resource_states: Literal[1, 2] = 1
) -> TileLayout:
    """Creates a linear layout with 2-tile blocks for each qubit (per
    Litinsky's paper, A Game of Surface Codes, Figure 8)

    The magic states are place at one or both ends of the horizontal linear bus

    Resource state(s) and data qubits are place along the top and bottom of
    the linear bus

    Since each qubit occupies a 2-tile block, both its X and Z edges are
    exposed, allowing Y operations to be performed as well.
    """
    bus_len = (n_data * 2 + n_resource_states * 2 + 3) // 4 * 2

    tiles_bus = {tiles.Tile(x, 0) for x in range(bus_len)}

    if n_magic == 1:
        mst = tiles.Tile(-1, 0)
        tiles_ms = {mst}
        msfs = [get_msf_15_to_1_protocol(mst, 3)]
    else:
        assert n_magic == 2
        mst1 = tiles.Tile(-1, 0)
        mst2 = tiles.Tile(bus_len, 0)
        tiles_ms = {mst1, mst2}

        msfs = [get_msf_15_to_1_protocol(mst1, 3), get_msf_15_to_1_protocol(mst2, 1)]

    assert n_resource_states in [1, 2]
    tiles_resource = set(
        [
            tiles.Tile(0, -1),
            tiles.Tile(1, -1),
            tiles.Tile(bus_len - 2, -1),
            tiles.Tile(bus_len - 1, -1),
        ][: 2 * n_resource_states]
    )

    tiles_data = tiles.get_neighbors(tiles_bus) - tiles_ms - tiles_resource

    layout = TileLayout(
        frozenset(tiles_bus),
        frozenset(tiles_data),
        frozenset(tiles_ms),
        frozenset(tiles_resource),
        msfs,
    )

    for i in range(bus_len // 2):
        # Add patches to data qubits above the bus
        ts = {tiles.Tile(i * 2, 1), tiles.Tile(i * 2 + 1, 1)}
        assert ts.issubset(tiles_data)
        layout.add_patch(patches.Patch.init_2_tile_patch(i, "qubit", ts, layout))
    for i in range(n_data - bus_len // 2):
        # Add patches to data qubits below the bus
        ts = {tiles.Tile(i * 2 + 2, -1), tiles.Tile(i * 2 + 3, -1)}
        assert ts.issubset(tiles_data)
        layout.add_patch(
            patches.Patch.init_2_tile_patch(i + bus_len // 2, "qubit", ts, layout)
        )
    layout.add_patches_to_mss()
    layout.add_patches_to_resource_tiles()

    assert layout.n_patches == n_data + n_resource_states + n_magic
    layout.validate_patches()

    return layout


def get_fast_block_layout(
    n_data: int,
    n_magic: int,
    *,
    n_resource=1,
    n_cols: Union[int, Literal["auto"]] = "auto",
    add_msfs=True,
    add_bus_tiles_to_top=False,
) -> TileLayout:
    """Creates a fast-block layout (per Litinsky's paper, A Game of Surface
    Codes, Figure 13)

    If n_cols == "auto", the layout will be roughly a square, and otherwise
    a rectangle.  Inside the rectangle are columns of 2-qubit, 2-tile
    fast patches.  The bus wraps around both sides of each column of
    data qubits, and along the bottom.

    The magic states and resource state(s) are place on the right and left
    sides of the rectangle, towards the bottom.
    """
    if n_cols == "auto":
        n_cols = math.ceil(n_data**0.5)
    n_patches_per_col = math.ceil(n_data / n_cols / 2)
    print(f" n_cols is [[{n_cols}]]")
    print(f" n_patches_per_col is [[{n_patches_per_col}]]")

    bus_width = n_cols * 2 + 1
    bus_height = n_patches_per_col * 2 + 1

    # tiles_bus
    tiles_bus = {tiles.Tile(x, 0) for x in range(bus_width)}
    if add_bus_tiles_to_top:
        tiles_bus.update({tiles.Tile(x, bus_height) for x in range(bus_width)})
    for x in range(0, 2 * n_cols + 1, 2):
        for y in range(bus_height):
            tiles_bus.add(tiles.Tile(x, y))

    # tiles_data
    tiles_data = set()
    for x in range(1, 2 * n_cols, 2):
        for y in range(1, bus_height):
            tiles_data.add(tiles.Tile(x, y))

    # Initializing MSs and MSFs
    tiles_ms: set[tiles.Tile] = set(
        [tiles.Tile(-1, 2), tiles.Tile(bus_width, 2)][:n_magic]
    )
    if n_magic > 2:
        raise NotImplementedError

    # Initializing resource_patches
    tiles_resource: set[tiles.Tile] = set()
    if n_resource >= 1:
        tiles_resource.update([tiles.Tile(-1, 0), tiles.Tile(-1, 1)])
    if n_resource >= 2:
        tiles_resource.update([tiles.Tile(bus_width, 0), tiles.Tile(bus_width, 1)])
    if n_resource >= 3:
        raise NotImplementedError

    layout = TileLayout(
        frozenset(tiles_bus),
        frozenset(tiles_data),
        frozenset(tiles_ms),
        frozenset(tiles_resource),
        frozenset(),
        add_msfs=add_msfs,
    )

    # fast_patches
    qubits = iter(range(n_data + 1))
    yx = it.product(range(1, bus_height, 2), range(1, 2 * n_cols, 2))
    for y, x in yx:
        try:
            layout.add_patch(
                patches.Patch.init_fast_patch(
                    [next(qubits), next(qubits)],
                    "qubit",
                    [tiles.Tile(x, y), tiles.Tile(x, y + 1)],
                    layout,
                )
            )
        except StopIteration:
            # The "qubits" iterator has run out, so we are all done!
            break
    layout.add_patches_to_mss()
    layout.add_patches_to_resource_tiles()

    assert layout.n_patches == math.ceil(n_data / 2) + n_resource + n_magic
    layout.validate_patches()

    return layout


def get_bus_wrap_around_tile_layout(
    n_data: int, n_magic: Literal[1, 2], n_resource_states: Literal[1, 2] = 2
) -> TileLayout:
    """Creates a compact linear layout (per Litinsky's paper, A Game of
    Surface Codes, Figure 11c)

    The magic states are place at one or both ends of the horizontal linear bus

    Resource state(s) and data qubits (using compact 1-tile patches) are place
    top and bottom of the linear bus
    """
    bus_len = (n_data + n_resource_states * 2 + n_magic - 1) // 2

    tiles_bus_original = {tiles.Tile(x, 0) for x in range(bus_len)}
    tiles_bus_left = {tiles.Tile(-1, y) for y in range(-2, 3)}
    tiles_bus_right = {tiles.Tile(bus_len, y) for y in range(-2, 3)}
    tiles_bus_top = {tiles.Tile(x, 2) for x in range(bus_len)}
    tiles_bus_bottom = {tiles.Tile(x, -2) for x in range(bus_len)}

    tiles_bus = {
        *tiles_bus_original,
        *tiles_bus_top,
        *tiles_bus_bottom,
        *tiles_bus_left,
        *tiles_bus_right,
    }

    if n_magic == 1:
        tiles_ms = {tiles.Tile(-1, 0)}
    else:
        assert n_magic == 2
        tiles_ms = {tiles.Tile(-2, 0), tiles.Tile(bus_len + 1, 0)}

    if n_resource_states == 1:
        tiles_resource = {tiles.Tile(0, -1), tiles.Tile(1, -1)}
    elif n_resource_states == 2:
        tiles_resource = {
            tiles.Tile(0, -1),
            tiles.Tile(1, -1),
            tiles.Tile(bus_len - 2, -1),
            tiles.Tile(bus_len - 1, -1),
        }
    else:
        raise Exception("Haven't implemented for other values")

    tiles_data = (
        tiles.get_neighbors(tiles_bus_original)
        - tiles_ms
        - tiles_resource
        - tiles_bus_left
        - tiles_bus_right
    )

    layout = TileLayout(
        frozenset(tiles_bus),
        frozenset(tiles_data),
        frozenset(tiles_ms),
        frozenset(tiles_resource),
        frozenset(),
    )

    for ind, tile in zip(range(n_data), tiles_data):
        layout.add_patch(
            patches.Patch.init_patch_x_top_bottom(ind, "qubit", tile, layout)
        )
    layout.add_patches_to_resource_tiles()
    layout.add_patches_to_mss()

    return layout


def get_experimental_grid_layout(num_grid_x, num_grid_y, grid_length_x, grid_length_y):
    assert grid_length_x >= 4, "Min grid length x is 4"
    assert grid_length_y >= 4, "Min grid length y is 4"

    num_overlapping_x = num_grid_x - 1
    num_overlapping_y = num_grid_y - 1

    tile_bus_horizontal = set()
    for i in range(num_grid_y + 1):
        tile_bus_horizontal.update(
            {
                tiles.Tile(x, i * (grid_length_y - 1))
                for x in range(num_grid_x * grid_length_x - num_overlapping_x)
            }
        )

    tile_bus_vertical = set()
    for i in range(num_grid_x + 1):
        tile_bus_vertical.update(
            {
                tiles.Tile(i * (grid_length_x - 1), y)
                for y in range(num_grid_y * grid_length_y - num_overlapping_y)
            }
        )

    tiles_bus = {*tile_bus_horizontal, *tile_bus_vertical}
    tiles_data = tiles.get_neighbors(tiles_bus)

    layout = TileLayout(
        frozenset(tiles_bus), frozenset(tiles_data), frozenset(), frozenset()
    )

    for ind, tile in enumerate(tiles_data):
        layout.add_patch(
            patches.Patch.init_patch_x_top_bottom(ind, "qubit", tile, layout)
        )

    return layout


def get_memory_fabric_square_layout(len: int) -> tuple(set, set):
    """Generate a square memory fabric (dedicated block with the data qubits) where
     ata qubits (*) are grouped in blocks of 2x2 tiles wrapped by bus tiles (b).

    Example for len = 2:
        b b b b b b b
        b * * b * * b
        b * * b * * b
        b b b b b b b
        b * * b * * b
        b * * b * * b
        b b b b b b b

    Args:
        len (int): number of data qubit blocks in each side of the fabric

    Returns:
        (set, set): set of bus and data qubit tiles
    """
    tiles_bus = set()
    tiles_data = set()

    # generate blocks
    # b * *
    # b * *
    # b b b
    for x in range(0, 3 * len, 3):
        for y in range(0, 3 * len, 3):
            tiles_bus.update(tiles.Tile(x + i, y) for i in [0, 1, 2])
            tiles_bus.update(tiles.Tile(x, y + j) for j in [1, 2])
            tiles_data.update(tiles.Tile(x + i, y + j) for i in [1, 2] for j in [1, 2])

    # fabric top row
    tiles_bus.update({tiles.Tile(x, 3 * len) for x in range(3 * len)})

    # fabric right column
    tiles_bus.update({tiles.Tile(3 * len, y) for y in range(3 * len + 1)})

    return (tiles_bus, tiles_data)


def get_memory_fabric_with_2x2_data_blocks_layout(
    n_data: int, n_buffer: int = 1
) -> TileLayout:
    """Generate a memory fabric (dedicated block with the data qubits) where data
    qubits (*) are grouped in blocks of 2x2 tiles wrapped by bus tiles (b).

    Example with 13 data qubits:
        1) generate a square block (4 qubits)
        2) generate remaining data blocks on right (8 qubits), then on top (12 qubits)
        3) generate remaining data tiles (13 qubits)

                                         b b b               b b b b
                                         b * *               b * * b b b
                                         b * *               b * * b * b
        b b b b   |   b b b b        |   b b b b b b b   |   b b b b b b b
        b * * b   |   b * * b * * b  |   b * * b * * b   |   b * * b * * b
        b * * b   |   b * * b * * b  |   b * * b * * b   |   b * * b * * b
        b b b b   |   b b b b b b b  |   b b b b b b b   |   b b b b b b b
        4 qubits      8 qubits           12 qubits           13 qubits

    Args:
        n_data (int): minimum number of data qubits in the block
        n_buffer (int): number of buffers connected to the memory fabric

    Returns:
        TileLayout: container with all the tiles generated
    """

    assert n_data > 0, f"{n_data} is an invalid number of data qubits"
    assert n_buffer > 0, f"{n_data} is an invalid number of buffers"

    nb_data_blocks: float = n_data / 4
    fabric_size: int = math.floor(math.sqrt(nb_data_blocks))
    remaining_data_blocks: int = math.ceil(nb_data_blocks) - fabric_size * fabric_size
    remaining_data_tiles: int = n_data % 4

    tiles_bus = set()
    tiles_data = set()
    tiles_magic = set()

    # generate square fabric
    tiles_bus, tiles_data = get_memory_fabric_square_layout(fabric_size)

    # generate remaining data blocks
    blocks_generated: int = 0

    if remaining_data_blocks > 0:
        # get coordinates of remaining blocks
        block_coordinates: list() = []
        for i in range(fabric_size):
            block_coordinates.append({"x": 3 * fabric_size, "y": 3 * i})
        for i in range(fabric_size):
            block_coordinates.append({"x": 3 * i, "y": 3 * fabric_size})
        block_coordinates.append({"x": 3 * fabric_size, "y": 3 * fabric_size})

        for count, block in enumerate(block_coordinates):
            # special case for n_data in [1,2,3]
            if n_data in [1, 2, 3]:
                tiles_bus.update(
                    {tiles.Tile(block["x"] + i, block["y"]) for i in [1, 2]}
                )
                if remaining_data_tiles == 3:
                    tiles_bus.add(tiles.Tile(block["x"] + 3, block["y"]))

            # add bus tiles
            if count < fabric_size:
                # - - b
                # - - b
                # b b b
                tiles_bus.update(
                    {tiles.Tile(block["x"] + i, block["y"]) for i in [1, 2, 3]}
                )
                tiles_bus.update(
                    {tiles.Tile(block["x"] + 3, block["y"] + i) for i in [1, 2]}
                )
            else:
                # b b b
                # b - -
                # b - -
                tiles_bus.update(
                    {tiles.Tile(block["x"], block["y"] + i) for i in [1, 2, 3]}
                )
                tiles_bus.update(
                    {tiles.Tile(block["x"] + i, block["y"] + 3) for i in [1, 2]}
                )

            # add data tiles
            if count < fabric_size:
                data_coordinates = [
                    (block["x"] + i, block["y"] + j) for j in [1, 2] for i in [1, 2]
                ]
            else:
                data_coordinates = [
                    (block["x"] + i, block["y"] + j) for i in [1, 2] for j in [1, 2]
                ]

            if (
                blocks_generated + 1 != remaining_data_blocks
                or remaining_data_tiles == 0
            ):
                tiles_data.update(tiles.Tile(l[0], l[1]) for l in data_coordinates)
            else:
                # add remaining data tiles
                tiles_data.update(
                    tiles.Tile(l[0], l[1])
                    for l in data_coordinates[:remaining_data_tiles]
                )
                # complete with bus tiles
                tiles_bus.update(
                    tiles.Tile(l[0], l[1])
                    for l in data_coordinates[remaining_data_tiles:]
                )

            blocks_generated += 1

            # add buses on top of the top-left most block
            if (
                blocks_generated == fabric_size
                and blocks_generated != remaining_data_blocks
            ):
                tiles_bus.add(tiles.Tile(block["x"] + 1, block["y"] + 3))
                tiles_bus.add(tiles.Tile(block["x"] + 2, block["y"] + 3))
                tiles_bus.add(tiles.Tile(block["x"] + 3, block["y"] + 3))

            # stop when all remaining blocks are generated
            if blocks_generated == remaining_data_blocks:
                last_block = {"x": block["x"], "y": block["y"]}
                stopped = {
                    "count": count,
                    "dir": "v" if count < fabric_size else "h",
                }

                # adjust buses
                if count < fabric_size:
                    if remaining_data_tiles == 1:
                        tiles_bus.remove(tiles.Tile(block["x"] + 3, block["y"] + 2))
                        tiles_bus.remove(tiles.Tile(block["x"] + 3, block["y"] + 1))
                        if count == 0:
                            tiles_bus.remove(tiles.Tile(block["x"] + 3, block["y"]))
                    elif remaining_data_tiles in [0, 3]:
                        tiles_bus.add(tiles.Tile(block["x"] + 1, block["y"] + 3))
                        tiles_bus.add(tiles.Tile(block["x"] + 2, block["y"] + 3))
                        if remaining_data_tiles == 0:
                            tiles_bus.add(tiles.Tile(block["x"] + 3, block["y"] + 3))
                else:
                    if remaining_data_tiles == 1:
                        tiles_bus.remove(tiles.Tile(block["x"] + 2, block["y"] + 3))
                        tiles_bus.remove(tiles.Tile(block["x"] + 1, block["y"] + 3))
                        if count == fabric_size:
                            tiles_bus.remove(tiles.Tile(block["x"], block["y"] + 3))
                    elif remaining_data_tiles in [0, 3]:
                        tiles_bus.add(tiles.Tile(block["x"] + 3, block["y"] + 1))
                        tiles_bus.add(tiles.Tile(block["x"] + 3, block["y"] + 2))
                        if remaining_data_tiles == 0:
                            tiles_bus.add(tiles.Tile(block["x"] + 3, block["y"] + 3))

                break

    # default locations for the buffer connections
    max_x = max(tiles_bus, key=lambda tile: tile.x).x
    default_buffer_loc = [(i, -1) for i in range(0, max_x + 1, 5)]

    # add buffer connections
    if n_buffer > len(default_buffer_loc):
        raise Exception(
            f"This layout cannot support more than {len(default_buffer_loc)} buffer(s) connected to the memory fabric"
        )

    for buffer in range(n_buffer):
        tiles_magic.update(
            {tiles.Tile(default_buffer_loc[buffer][0], default_buffer_loc[buffer][1])}
        )

    layout = TileLayout(
        frozenset(tiles_bus),
        frozenset(tiles_data),
        frozenset(tiles_magic),
        frozenset(),
        frozenset(),
    )

    for tile in tiles_data:
        layout.add_patch(
            patches.Patch.init_patch_x_top_bottom(
                layout.qubit_tiles_to_inds[tile], "qubit", tile, layout
            )
        )
    layout.add_patches_to_resource_tiles()
    layout.add_patches_to_mss()

    return layout


def extend_modular_layout(tiles_in_module, factories_num: dict) -> list:
    """Expand a modular layout in a grid definied by factories_num

    Args:
        tiles_in_module: list of tiles in a module
        factories_num: number of factories

    Returns:
        layout_list_extended: extended list of tiles in all factories
    """

    # verify conditions whether this is a modular layout
    all_bus_tiles = []
    all_bus_tiles.extend(tiles_in_module[0])

    min_x_bus = min(all_bus_tiles, key=lambda x: x.x).x
    max_x_bus = max(all_bus_tiles, key=lambda x: x.x).x
    min_y_bus = min(all_bus_tiles, key=lambda x: x.y).y
    max_y_bus = max(all_bus_tiles, key=lambda x: x.y).y

    all_other_tiles = []
    for tiles_type in range(1, len(tiles_in_module)):
        all_other_tiles.extend(tiles_in_module[tiles_type])

    min_x_other = min(all_other_tiles, key=lambda x: x.x).x
    max_x_other = max(all_other_tiles, key=lambda x: x.x).x
    min_y_other = min(all_other_tiles, key=lambda x: x.y).y
    max_y_other = max(all_other_tiles, key=lambda x: x.y).y

    try:
        assert min_x_bus <= min_x_other
        assert max_x_bus >= max_x_other
        assert min_y_bus <= min_y_other
        assert max_y_bus >= max_y_other
    except AssertionError:
        raise Exception(
            "The layout given is not a valid modular layout and cannot be expanded."
        )

    # get module dimensions
    module_dim = {"x": max_x_bus - min_x_bus + 1, "y": max_y_bus - min_y_bus + 1}

    # create extended layout
    layout_extended = []
    for tile_type in tiles_in_module:
        tile_type_extended = set()
        for tile in tile_type:
            for num_h in range(factories_num["x"]):
                for num_v in range(factories_num["y"]):
                    tile_type_extended.add(
                        tiles.Tile(
                            tile.x + num_h * module_dim["x"],
                            tile.y - num_v * module_dim["y"],
                        )
                    )
        layout_extended.append(tile_type_extended)
    return layout_extended


def save_expanded_modular_layout_to_pkl(
    file_path: str,
    factories_num={"x": 1, "y": 1},
) -> str:
    """Create side-by-side copies of a custom modular layout and save it into a pickle file.

    Args:
        file_path: file path
        factories_num: number of horizontal (x) and vertical (y) factories
        factories_dim: number of horizontal (x) and vertical (y) tiles in each factory

    Returns:
        str: new layout file name
    """

    # read modular layout from .pkl file and get tiles coordinates
    layout_original = read_layout_from_pkl(file_path)
    tiles_coordinates = [
        layout_original.tiles_bus,
        layout_original.tiles_data,
        layout_original.tiles_resource,
        layout_original.tiles_ms,
        frozenset(),
        layout_original.tiles_storage,
    ]

    # create modular layout copied
    layout_extended = extend_modular_layout(
        tiles_coordinates,
        factories_num,
    )

    # Open a file and use dump()
    file_dir = osp.dirname(file_path)
    file_name = osp.basename(file_path)
    file_name_without_extension = file_name[: file_name.rindex(".")]

    new_file_name = (
        file_name_without_extension
        + "_"
        + str(factories_num["x"])
        + "x"
        + str(factories_num["y"])
        + ".pkl"
    )
    new_file_path = file_dir + "/" + new_file_name
    with open(new_file_path, "wb") as file:
        # A new file will be created
        pickle.dump(layout_extended, file)

    return new_file_path


def hansa_decode_hooks(obj):
    if "!type" in obj:
        if obj["!type"] == "Tile":
            return tiles.Tile(int(obj["x"]), int(obj["y"]))
        elif obj["!type"] == "frozenset":
            return frozenset(obj["values"])
        else:
            raise ValueError(f"Unknown type key {obj['!type']}")
    return obj


def read_layout_from_pkl(file_path: str) -> TileLayout:
    """Read a layout from a .pkl file

    Args:
        file_path: file path

    Returns:
        layout: layout
    """

    if file_path[-4:] == "json":
        with open(file_path, "r") as j:
            layout_list = json.load(j, object_hook=hansa_decode_hooks)
    else:
        with open(file_path, "rb") as p:
            layout_list = pickle.load(p)

    layout = TileLayout(
        frozenset(layout_list[0]),
        frozenset(layout_list[1]),
        frozenset(layout_list[3]),
        frozenset(layout_list[2]),
        frozenset(layout_list[5]),
    )

    for tile in layout_list[1]:
        layout.add_patch(
            patches.Patch.init_patch_x_top_bottom(
                layout.qubit_tiles_to_inds[tile], "qubit", tile, layout
            )
        )
    for tile in layout_list[5]:
        layout.add_patch(
            patches.Patch.init_patch_x_top_bottom(
                layout.storage_tiles_to_inds[tile], "storage", tile, layout
            )
        )
    layout.add_patches_to_resource_tiles()
    layout.add_patches_to_mss()
    return layout
