import itertools as it
import pickle

import matplotlib
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.widgets import Slider

from layout_processor import tile_layout

prev_tick = 0


def create_histogram(tree_nodes_all_assignment):
    histogram = {}
    for rotation_assigned_per_tick in tree_nodes_all_assignment:
        for tree in rotation_assigned_per_tick:
            for node in tree:
                if isinstance(node, int):
                    node_key = node
                else:
                    node_key = node[0]
                if node_key in histogram:
                    histogram[node_key] += 1
                else:
                    histogram[node_key] = 1

    return histogram


def plot_heatmap(layout, tree_nodes_all_assignment):
    hist = create_histogram(tree_nodes_all_assignment)
    node_to_coord = get_node_to_tile_coordinate_dict(layout)
    hist_max = max(hist.values())
    hist_min = min(hist.values())
    hist_range = hist_max - hist_min
    normalized_interval = 20

    cmap = plt.get_cmap("jet", normalized_interval)
    cmaplist = [cmap(i) for i in range(cmap.N)]

    fig, ax = plt.subplots(nrows=1, ncols=1)
    layout.plot_on_ax(alpha=0.3, ax=ax)

    bounds = np.linspace(hist_min, hist_max, normalized_interval)
    norm = matplotlib.colors.BoundaryNorm(bounds, cmap.N)
    ax2 = fig.add_axes([0.91, 0.1, 0.03, 0.8])
    matplotlib.colorbar.ColorbarBase(
        ax2,
        cmap=cmap,
        norm=norm,
        spacing="proportional",
        ticks=bounds,
        boundaries=bounds,
    )

    for node, tile in node_to_coord.items():
        if node in hist:
            c = int((hist[node] - hist_min) / hist_range * (normalized_interval - 1))
            if isinstance(node, str) and "r" in node:
                for t in tile:
                    t.plot_on_ax(ax, alpha=1, colour="white")
                    t.plot_on_ax(ax, alpha=1, colour=cmaplist[c])
            else:
                tile.plot_on_ax(ax, alpha=1, colour="white")
                tile.plot_on_ax(ax, alpha=1, colour=cmaplist[c])

        else:
            if isinstance(node, str) and "r" in node:
                for t in tile:
                    t.plot_on_ax(ax, alpha=1, colour="grey")
            else:
                tile.plot_on_ax(ax, alpha=1, colour="grey")

    plt.show()
    print()


def get_node_to_tile_coordinate_dict(layout):
    graph_for_index_ref = layout.get_graph_for_mip()
    node_to_tile_coord = (graph_for_index_ref.inds_to_bus_tiles,)
    node_to_tile_coord = node_to_tile_coord[0]
    for tile in graph_for_index_ref.inds_to_qubit_edges.values():
        key_tile = "q" + str(tile.ind)
        if key_tile not in node_to_tile_coord:
            node_to_tile_coord[key_tile] = tile.patch_tile
    for tile in graph_for_index_ref.inds_to_ms_edges.values():
        key_tile = "m" + str(tile.ind)
        if key_tile not in node_to_tile_coord:
            node_to_tile_coord[key_tile] = tile.patch_tile
    for tile in graph_for_index_ref.inds_to_resource_edges.values():
        key_tile = "r" + str(tile.ind)
        if key_tile not in node_to_tile_coord:
            node_to_tile_coord[key_tile] = {tile.patch_tile}
        else:
            node_to_tile_coord[key_tile].add(tile.patch_tile)

    return node_to_tile_coord


def plot_schedule(layout, tree_nodes_all_assignment):
    """Generate a plot for the scheduling results.
    Use sliding bar/left & right arrow keys to adjust the tick number
    """

    # create figure and plot scatter
    node_to_tile_coord = get_node_to_tile_coordinate_dict(layout)
    fig, ax = plt.subplots(nrows=1, ncols=1)
    colours = it.cycle(
        [
            "peru",
            "darkred",
            "goldenrod",
            "chartreuse",
            "turquoise",
            "skyblue",
            "blueviolet",
            "hotpink",
        ]
    )
    layout.plot_on_ax(alpha=0.3, ax=ax)

    ###########################################################################
    # This is where the tick is updated when we change the slider
    def update_plot(val, tick_to_clear):
        """Update plot according to slider bar value"""
        if tick_to_clear is not None:
            clear_plot(tick_to_clear)

        # This conditional statement is simply
        # used to handle the first tick (containing rotations) before
        # any key press or slider change is registered
        if val:
            idx = val
        else:
            idx = int(tickslider.val)
        tree_nodes_current_tick = tree_nodes_all_assignment[idx]

        tiles_used = set()
        if tree_nodes_current_tick:
            for tree, c in zip(tree_nodes_current_tick, colours):
                for node in tree:
                    if isinstance(node, int):
                        tiles_used.add(node_to_tile_coord[node])
                        node_to_tile_coord[node].plot_on_ax(ax, alpha=0.8, colour=c)
                    else:
                        if "r" in node[0]:
                            tiles_used.update(node_to_tile_coord[node[0]])
                            for t in node_to_tile_coord[node[0]]:
                                t.plot_on_ax(ax, alpha=0.8, colour=c)
                        else:
                            tiles_used.add(node_to_tile_coord[node[0]])
                            node_to_tile_coord[node[0]].plot_on_ax(
                                ax, alpha=0.8, colour=c
                            )
        global prev_tick
        prev_tick = idx
        ax.set_title("Scheduler: " + "\n Use left/right arrow keys to adjust tick")

        fig.canvas.draw_idle()

    ###########################################################################
    def clear_plot(current_tick):
        """Clear the plot from previous tick"""
        tree_nodes_current_tick = tree_nodes_all_assignment[current_tick]

        if tree_nodes_current_tick:
            for tree in tree_nodes_current_tick:
                for node in tree:
                    if isinstance(node, int):
                        node_to_tile_coord[node].plot_on_ax(ax, alpha=1, colour="white")
                        node_to_tile_coord[node].plot_on_ax(
                            ax, alpha=0.3, colour="green"
                        )
                    elif "r" in node[0]:
                        for t in node_to_tile_coord[node[0]]:
                            t.plot_on_ax(ax, alpha=1, colour="white")
                            t.plot_on_ax(ax, alpha=0.3, colour="purple")
                    elif "m" in node[0]:
                        node_to_tile_coord[node[0]].plot_on_ax(
                            ax, alpha=1, colour="white"
                        )
                        node_to_tile_coord[node[0]].plot_on_ax(
                            ax, alpha=0.3, colour="red"
                        )
                    elif "q" in node[0]:
                        node_to_tile_coord[node[0]].plot_on_ax(
                            ax, alpha=1, colour="white"
                        )
                        node_to_tile_coord[node[0]].plot_on_ax(
                            ax, alpha=0.3, colour="blue"
                        )

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

    ###########################################################################

    fig.canvas.mpl_connect("key_press_event", on_press)

    # Only make slider available for the ticks that have rotations
    slider_linespace = [
        tick for tick, rots in enumerate(tree_nodes_all_assignment) if rots
    ]

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

    tickslider.on_changed(lambda new_val: update_plot(new_val, prev_tick))

    # Display the first tick containing rotations
    # before any button press or slider change
    update_plot(min(tickslider.valstep), None)

    plt.show()


if __name__ == "__main__":
    with open(
        "./src/helpers/Compiled_k_sat_QASM_single_iterate(6-num_clauses,4-num_variables)_20220304-11-34.txt",
        "rb",
    ) as p:
        tree_nodes_assignment = pickle.load(p)

    layout_ = tile_layout.read_layout_from_pkl(
        "./data/inputs/layout_files/sc_block_data_16_depot_4_corner.pkl"
    )
    plot_schedule(layout_, tree_nodes_assignment)
    # plot_heatmap(layout_, tree_nodes_assignment)
