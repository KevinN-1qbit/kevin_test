""" Defines class Tile and some helper functions to use with tiles """

from __future__ import annotations

import dataclasses
from typing import Iterable, Literal
import functools
import datetime

import matplotlib.pyplot as plt

# pylint: disable=consider-using-from-import  # get error if import as suggested
import matplotlib.patches as patches


# pylint: disable=multiple-statements
@dataclasses.dataclass(frozen=True)  # Makes immutable by standard means
class Tile:
    """Represents a single tile in the layout of a surface code error
    corrected quantum computer"""

    x: int
    y: int

    @functools.cached_property
    def neighbors(self) -> frozenset[Tile]:
        return frozenset(
            [
                Tile(self.x + 1, self.y),
                Tile(self.x, self.y + 1),
                Tile(self.x - 1, self.y),
                Tile(self.x, self.y - 1),
            ]
        )

    @property
    def up(self) -> Tile:
        return Tile(self.x, self.y + 1)

    @property
    def down(self) -> Tile:
        return Tile(self.x, self.y - 1)

    @property
    def left(self) -> Tile:
        return Tile(self.x - 1, self.y)

    @property
    def right(self) -> Tile:
        return Tile(self.x + 1, self.y)

    def get_tile_in_dir(self, dir_: int) -> Tile:
        dir_mod = dir_ % 4

        if dir_mod == 0:
            return self.up
        elif dir_mod == 1:
            return self.right
        elif dir_mod == 2:
            return self.down
        elif dir_mod == 3:
            return self.left
        else:
            assert False

    def direction_to_tile(self, tile2) -> Literal[0, 1, 2, 3]:
        assert tile2 in self.neighbors

        if tile2 == self.up:
            return 0
        elif tile2 == self.right:
            return 1
        elif tile2 == self.down:
            return 2
        elif tile2 == self.left:
            return 3
        else:
            assert False

    def plot(self, colour="red", alpha=0.3):
        # Use subplots to get "fig" and "axes", and set the figure size
        fig, axes = plt.subplots(1, 1, figsize=(12, 8))
        ax = axes  # It's not a list, b/c only 1 subplot

        self.plot_on_ax(ax, colour, alpha)

        title = f"Plot of Tile {self}"
        # 24hr time
        date_time_stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        ax.set_title(f"{date_time_stamp}\n{title}")

        ax.set_xlabel(f"x")
        ax.set_ylabel(f"y")

        ax.legend()
        fig.show()

    def plot_on_ax(self, ax, colour: str, alpha: float):
        # Creates a patch, but the plot's domain/range
        # don't automatically expand to include this patch
        rect = patches.Rectangle(
            (self.x - 0.4, self.y - 0.4), 0.8, 0.8, facecolor=colour, alpha=alpha
        )
        ax.add_patch(rect)


def get_neighbors(tiles: Iterable[Tile]) -> frozenset[Tile]:
    return frozenset.union(*[t.neighbors for t in tiles]) - frozenset(tiles)


def get_neighbors_single_deck(tiles: Iterable[Tile]) -> frozenset[Tile]:
    neighbors = set()
    for t in tiles:
        for n in t.neighbors:
            if n.y > t.y:
                neighbors.add(n)
    return frozenset(neighbors) - frozenset(tiles)


def get_center(tiles_: Iterable[Tile]) -> tuple[float, float]:
    """Returns: X and Y coordinates of center

    obtained by averaging X and Y of all tiles
    """
    xs = [tile.x for tile in tiles_]
    ys = [tile.y for tile in tiles_]
    ret = sum(xs) / len(xs), sum(ys) / len(ys)
    return ret


def key(tile: Tile) -> tuple[int, int]:
    """A key function, i.e. for sorting"""
    return tile.x, tile.y
