import os
import sys
import time
import matplotlib.pyplot as plt
from layout_processor.tile_layout import read_layout_from_pkl
from layout_processor.adjacency_graph import AdjacencyGraph
from layout_processor import magic_state_factory as msf
from hla_scheduler.QRE_report import generate_report_and_save
from hla_scheduler.hla_scheduler import Circuit, QuantumSystem
from helpers import paths


def plot_graph(title, data, rowX, rowY, rowC, opt):
    # create a dictionary to store data for each label
    data_dict = {}
    for row in data:
        x, y, label = row[rowX], row[rowY], row[rowC]
        if label not in data_dict:
            data_dict[label] = {"x": [], "y": []}
        data_dict[label]["x"].append(x)
        data_dict[label]["y"].append(y)

    # plot all data in the same plot
    fig, ax = plt.subplots(figsize=(6, 4))
    for label, data in data_dict.items():
        ax.scatter(data["x"], data["y"], label=f"Storage cap. = {label}")
    ax.set_xlabel(title[rowX])
    ax.set_ylabel(title[rowY])
    ax.legend()

    ax.axhline(opt, linestyle="dashed")

    plt.show()


def dump_expr_data(
    circuit_filename: str,
    expected_runtime: float,
    compilation_time: float,
    scheduling_rotations: dict,
    expr_folder: str = "./expr_res",
    prefix: str = "Simu",
):
    """A function invoked at the end of the HLAScheduler to dump some key data into a
    txt file. It's a complementary function to the simulation reports.
    Args:
        circuit_filename: the circuit name;
        expected_runtime: the expected quantum runtime
        simu_runtime: the simulation time
        scheduling_rotations: a dictionary stores the pairs of tick and rotation index.
        expr_folder: path to output files folder
        prefix: the prefix used for the exported files
    """
    if not os.path.exists(expr_folder):
        os.mkdir(expr_folder)
    if not os.path.exists(f"{expr_folder}/{prefix}_res.txt"):
        res_file = open(f"{expr_folder}/{prefix}_res.txt", "w")
        res_file.write(f"circuit_name,nb ticks,run time,nb parallelized rots\n")
    else:
        res_file = open(f"{expr_folder}/{prefix}_res.txt", "a")
    ticks = list(scheduling_rotations.keys())
    nb_rots = list(map(lambda x: len(x), scheduling_rotations.values()))
    nb_parallelized = len(list(filter(lambda x: x >= 2, nb_rots)))
    # print(qc.scheduling_rotations)
    fig, ax = plt.subplots()
    ax.set_title(f"{prefix} {circuit_filename}")
    ax.set_xlabel("ticks")
    ax.set_ylabel("nb rotations")
    ax.scatter(ticks, nb_rots)
    fig.savefig(f"{expr_folder}/{prefix} {circuit_filename}.png")
    res_file.write(
        f"{circuit_filename}, {expected_runtime}, {compilation_time}, {nb_parallelized}\n"
    )


# TODO create a separate main function to perform test
# if __name__ == "__main__":
# dump_expr_data(
#     circuit_filename=circuit_filename,
#     expected_runtime=expected_runtime,
#     compilation_time=total,
#     scheduling_rotations=qc.scheduling_rotations,
# )
