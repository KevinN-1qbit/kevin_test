import csv
import itertools
import math
import os
import re
from typing import Literal

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.widgets import Slider

from scheduler import generate_rotation, layout_optimization
from model.scheduler_model import _RotationIndexToMSUsed
from triangle_layout import triangle_layouts
from helpers import paths

_LayoutType = Literal["linear", "spiral", "zigzag", "rectangular"]
_SchedulerType = Literal[
    "naive", "sequential", "linearbus", "mip", "multistep8", "cheat"
]
_FileExtension = Literal[".pkl", ".csv"]


def plot_schedule(
    num_qubits: int,
    num_magics: int,
    n_layers_commute_forward: int,
    layout_type: _LayoutType,
    scheduler_type: _SchedulerType,
    placement: dict[int, int],
    scheduler_result: dict[int, _RotationIndexToMSUsed],
    rotations: dict[int, tuple[int, list[int]]],
):
    """Generate a plot for the scheduling results.
    Use sliding bar/left & right arrow keys to adjust the tick number
    """

    # Get the layout and corresponding graph
    layout = layout_optimization.get_layout(layout_type, num_qubits, num_magics)
    graph = layout.extract_graphs()

    # create figure and plot scatter
    fig, ax = plt.subplots(nrows=1, ncols=1)

    ###########################################################################
    # This is where the tick is updated when we change the slider
    def update_plot(val):
        """Update plot according to slider bar value"""

        # This conditional statement is simply
        # used to handle the first tick (containing rotations) before
        # any key press or slider change is registered
        if val:
            idx = val
        else:
            idx = int(tickslider.val)
        ax.cla()

        rotation_and_magic_state = scheduler_result[idx]

        if rotation_and_magic_state:
            triangles_in_rotaions = {}

            for i, (rotation_id, magic_state_num) in enumerate(
                rotation_and_magic_state.items()
            ):
                # Rotation id contains qubit ids,
                # need to convert to data tile id using placement
                tiles_in_rotation = [placement[r] for r in rotations[rotation_id][1]]

                # Include magic state tile if one is used
                if magic_state_num:
                    tiles_in_rotation.append(magic_state_num)

                # Need to find bus tiles if we have
                # rotations/measurements with multi-qubits
                if len(tiles_in_rotation) > 1:
                    bus_tiles = find_bus_tiles_used(tiles_in_rotation, graph)
                    tiles_in_rotation.extend(bus_tiles)

                # Convert all tiles to Triangle objects for plotting
                triangles_used = [
                    layout.ints_to_triangles[t] for t in tiles_in_rotation
                ]

                # Include the type of rotation
                # (i.e. rotations[rotation_id][0])
                triangles_in_rotaions[i] = (rotations[rotation_id][0], triangles_used)

            layout.visualize_on_ax(
                ax=ax, placement=placement, rotation_used=triangles_in_rotaions
            )

            ax.set_title(
                "Scheduler: "
                + scheduler_type
                + "\n Lookahead: "
                + str(n_layers_commute_forward)
                + "\n Use left/right arrow keys to adjust tick"
            )

        fig.canvas.draw_idle()

    ###########################################################################
    # This is where the keyboard left & right
    # arrow inputs are handled
    def on_press(event):
        """Button press event. Use right arrow to increment tick and
        left arrow to decrement tick.
        """

        current_tick = tickslider.val
        idx = tickslider.valstep.index(current_tick)

        if event.key == "right" and current_tick != max(tickslider.valstep):
            tickslider.set_val(tickslider.valstep[idx + 1])

        elif event.key == "left" and current_tick != min(tickslider.valstep):
            tickslider.set_val(tickslider.valstep[idx - 1])

    fig.canvas.mpl_connect("key_press_event", on_press)

    # Only make slider available for the ticks that have rotations
    slider_linespace = [tick for tick, rots in scheduler_result.items() if rots]

    # The slider position
    # 4-tuple of floats rect = [left, bottom, width, height]
    axtickslider = plt.axes([0.25, 0.01, 0.5, 0.03])
    tickslider = Slider(
        axtickslider,
        "Tick",
        0,
        valstep=slider_linespace,
        valinit=slider_linespace[0],
        valmax=slider_linespace[-1],
        valfmt="%d",
    )
    tickslider.on_changed(update_plot)

    # Display the first tick containing rotations
    # before any button press or slider change
    update_plot(min(tickslider.valstep))

    plt.show()


def find_bus_tiles_used(data_and_magic_tiles_for_one_rotation, graph):
    """Given data tiles (possibly w/ a magic state tile), find the bus tiles
    that are connected to the given tiles, then return all bus tiles in between
    """
    # Find all bus tiles connected to given data
    # and/or magic state tiles
    # E.g. neighbour_bus_tile = [[10, 6], [6], [7]]
    # indicates that there is one tile that is
    # connected to 2 bus tile, 10 & 6
    neighbour_bus_tile = []
    for tile in data_and_magic_tiles_for_one_rotation:
        neighbour_bus_tile_for_each_given_tile = []
        for neighbour in graph.connections[tile]:
            if neighbour in graph.bus_tiles:
                neighbour_bus_tile_for_each_given_tile.append(neighbour)
        neighbour_bus_tile.append(neighbour_bus_tile_for_each_given_tile)

    # Find all combinations of nested list
    # E.g. when neighbour_bus_tile = [[10, 6], [6], [7]]
    # all_bus_tiles_combinations = [(10, 5, 7), (6, 5, 7)]
    all_bus_tiles_combinations = list(itertools.product(*neighbour_bus_tile))

    # Find the shortest distance bus tiles
    shortest_bus_len = math.inf
    shortest_bus = list()
    for bus_combo in all_bus_tiles_combinations:
        min_bus_id, max_bus_id = min(bus_combo), max(bus_combo)
        if max_bus_id - min_bus_id < shortest_bus_len:
            shortest_bus_len = max_bus_id - min_bus_id
            shortest_bus = list(range(min_bus_id, max_bus_id + 1))
    return shortest_bus


def plot_score_with_layout(
    num_qubits_all: list[int],
    num_magics_all: list[int],
    num_ticks_all: list[int],
    lookahead_all: list[int],
    placements_all: list[dict[int, int]],
    layout_type_all: list[_LayoutType],
    scheduler_type_all: list[_SchedulerType],
):
    """Generate a plot w/ 2 panels. On the left is a
    scatter plot showing the number of ticks for each result.
    Clicking on a point on the scatter plot will then make the
    right panel shows the correponding layout and placement.
    """

    # create figure and plot scatter
    fig, [ax1, ax2] = plt.subplots(nrows=1, ncols=2)
    (line,) = ax1.plot(num_ticks_all, ls="", marker="o")

    ax1.set_title("Placement Scores")
    ax1.set_xlabel("Placement")
    ax1.set_ylabel("Scores")

    ax1.xaxis.set_ticks(np.arange(0, len(num_qubits_all), 1))

    def click(event):
        # if the mouse is over the scatter points
        if line.contains(event)[0] and not ax2.lines:
            # find out the index within the array from the event
            # i.e. the indice of the point clicked
            ind: int
            (ind,) = line.contains(event)[1]["ind"]

            # Get the layout
            layout = layout_optimization.get_layout(
                layout_type_all[ind], num_qubits_all[ind], num_magics_all[ind]
            )

            # Visualize
            layout.visualize_on_ax(ax=ax2, placement=placements_all[ind])

            ax2.set_title(
                "Placement"
                + str(ind)
                + ", lookahead="
                + str(lookahead_all[ind])
                + ", scheduler="
                + str(scheduler_type_all[ind])
            )

        else:
            # if not click a point
            ax2.clear()
        fig.canvas.draw_idle()

    # add callback for mouse moves
    fig.canvas.mpl_connect("button_press_event", click)
    plt.show()


def read_performance_results_from_file(path):
    """Given a .csv file, read the corresponding variables"""

    with open(path, "r") as csv_file:
        num_qubits_all = []
        num_magics_all = []
        num_ticks_all = []
        lookahead_all = []
        placements_all = []
        layout_type_all = []
        scheduler_type_all = []

        # Split columns while reading
        for i, line in enumerate(csv.reader(csv_file, delimiter=",")):
            # Handle the header row
            if i == 0:
                for j, title in enumerate(line):
                    if title == "Num_data_qubits":
                        num_qubit_header_idx = j
                    elif title == "Num_magic_states":
                        num_magics_header_idx = j
                    elif title == "Num_ticks":
                        num_ticks_header_idx = j
                    elif title == "n_layers_commute_forward":
                        lookahead_header_idx = j
                    elif title == "layout_type":
                        layout_type_header_idx = j
                    elif title == "scheduler_str":
                        scheduler_type_header_idx = j
                    elif title == "Placement  Qubit(data_tile)":
                        placement_idx = j

                # Done w/ the header row
                continue

            num_qubits_all.append(int(line[num_qubit_header_idx]))
            num_magics_all.append(int(line[num_magics_header_idx]))
            num_ticks_all.append(int(line[num_ticks_header_idx]))
            lookahead_all.append(int(line[lookahead_header_idx]))
            layout_type_all.append(line[layout_type_header_idx])
            scheduler_type_all.append(line[scheduler_type_header_idx])
            placements = {}
            for placement_each_qubit in line[
                placement_idx : placement_idx + int(line[num_qubit_header_idx])
            ]:
                # E.g. convert 5(13) into [5, 13]
                qubit_tile = [
                    int(s) for s in re.findall(r"\b\d+\b", placement_each_qubit)
                ]
                placements[qubit_tile[0]] = qubit_tile[1]
            placements_all.append(placements)

    return (
        num_qubits_all,
        num_magics_all,
        num_ticks_all,
        lookahead_all,
        placements_all,
        layout_type_all,
        scheduler_type_all,
    )


def find_relevant_files_in_output(file_extension: _FileExtension):
    """Find either all .csv files or .pkl files in the output folder.
    Returns a list of paths with the selected file extension type.
    """
    experiment_files = []
    path_output = paths.get_output_dir()

    for path, subdirs, files in os.walk(path_output):
        for name in files:
            if name.endswith(file_extension):
                experiment_files.append(os.path.join(path, name))

    return experiment_files


if __name__ == "__main__":
    performance_results_path = find_relevant_files_in_output(".csv")
    scheduling_results_path = find_relevant_files_in_output(".pkl")

    # Make sure we have equal number of performance result files and
    # scheduling result files
    # assert len(performance_results_path) == len(scheduling_results_path)

    # We need to have the performance resuls in order to
    # know the placement & placement method, layout type, scheduler type,
    # num. of magic states
    if performance_results_path and scheduling_results_path:
        for performance_result_path, scheduling_result_path in zip(
            performance_results_path, scheduling_results_path
        ):
            (
                num_qubits_all,
                num_magics_all,
                num_ticks_all,
                lookahead_all,
                placements_all,
                layout_type_all,
                scheduler_type_all,
            ) = read_performance_results_from_file(performance_result_path)

            scheduling_results_all = generate_rotation.load_var(scheduling_result_path)

            plot_score_with_layout(
                num_qubits_all,
                num_magics_all,
                num_ticks_all,
                lookahead_all,
                placements_all,
                layout_type_all,
                scheduler_type_all,
            )

            for (
                num_qubits,
                num_magics,
                lookahead,
                layout_type,
                scheduler_type,
                placement,
                scheduling_result,
            ) in zip(
                num_qubits_all,
                num_magics_all,
                lookahead_all,
                layout_type_all,
                scheduler_type_all,
                placements_all,
                scheduling_results_all,
            ):
                plot_schedule(
                    num_qubits,
                    num_magics,
                    lookahead,
                    layout_type,
                    scheduler_type,
                    placement,
                    scheduling_result["rotation_schedule"],
                    scheduling_result["rotation_IDs"],
                )
    else:
        print(
            "No experiment files found in the directory "
            "Trillium/output. Please run experiments first."
        )
