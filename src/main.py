import argparse
import configparser
import json
import os
import os.path as osp
import sys
import time
from typing import Dict, Any
from layout_processor.magic_state_factory import MagicStateFactory
from layout_processor.tile_layout import (
    read_layout_from_pkl,
    get_memory_fabric_with_2x2_data_blocks_layout,
)
from layout_processor.adjacency_graph import AdjacencyGraph
from hla_scheduler.QRE_report import generate_report_and_save
from hla_scheduler.hla_scheduler import Circuit, QuantumSystem
from scheduler.steiner_tree_heuristic import solve_rotations_scheduling
from scheduler.circuit_and_rotation.generate_rotation import (
    parse_rotations,
    convert_Y_operators,
)
from scheduler.data_qubit_assignment import (
    AssignPolicy,
    solve_data_qubit_assignment,
)
from helpers import paths
from helpers.utils import update_dict_from_json

# Load configs
config = configparser.ConfigParser()
config.read_file(open("src/config/scheduler.conf"))

# Load default HLA scheduler parameters
with open("src/hla_scheduler/hla_scheduler_default_params.json") as f:
    input_hla_scheduler_params_dict = json.load(f)


def parse_args():
    parser = argparse.ArgumentParser(
        description="""Employs the SK algorithm, a transpiled circuit and a
        scheduler to produce an efficient schedule for executing a user-defined
        quantum circuit on the quantum chip architecture suggested by Hansa or
        defined by the user, while minimizing the resources required."""
    )
    parser.add_argument("--input_t_circuit", help="Path to transpiled input file")
    parser.add_argument("--output_dir", help="Directory to output report")
    parser.add_argument("--output_report_filename", help="Name of the output report")
    parser.add_argument("--input_layout", help="Path to input layout file")
    parser.add_argument(
        "--input_hla_scheduler_params", help="Path to input hla scheduler params file"
    )
    parser.add_argument(
        "--generate_hla_schedule",
        help="Choose to generate hla schedule when running HLAScheduler",
    )
    parser.add_argument(
        "--dual_mode",
        help="Choose whether to run both HLAScheduler and scheduler",
    )
    args = parser.parse_args(None if sys.argv[1:] else ["-h"])

    # Make sure that all required arguments are provided
    required_set = [args.input_t_circuit, args.output_dir]

    if args.input_t_circuit:
        if not osp.isfile(args.input_t_circuit) and not osp.exists(
            args.input_t_circuit
        ):
            parser.error(f"The input_t_circuit: {args.input_t_circuit} does not exist")
    if args.output_dir:
        if not osp.exists(args.output_dir):
            parser.error(f"The output_dir: {args.output_dir} does not exist")

    if None in required_set:
        if args.input_t_circuit is None:
            parser.error(
                "Missing file path to circuit. Please specify "
                "the path to input circuit by: "
                "--input_t_circuit path_to_input_circuit"
            )

        elif args.output_dir is None:
            parser.error(
                "Missing file directory to output. Please specify "
                "the directory to store the output report by: "
                "--output_dir directory_to_store_outputs"
            )
    return args


def parse_input_configs():
    """Parse the command arguments and update the input hla scheduler params
    dict.

    Returns:
        input_t_circuit (str): The path to the circuit file.
        output_dir (str): The path to the output directory.
        output_report_filename (str): The filename of the output report.
        layout_path (str): The path to the layout file.
        input_hla_scheduler_params_dict (dict): A dictionary containing
            parameters for the HLA scheduler. Default is False.
        generate_hla_schedule (bool): Whether to generate schedules for HLAScheduler.
        dual_mode (bool): Whether to run both HLAScheduler and scheduler.
            Default is False.
        depot_exit (int): The number of data-storage blocks connections (1 for
            serial scheduling).
    """
    # default value for generate_hla_schedule, dual_mode
    generate_hla_schedule, dual_mode = False, False

    try:
        args = parse_args()
        input_t_circuit = args.input_t_circuit
        output_dir = args.output_dir
        output_report_filename = args.output_report_filename
        layout_path = args.input_layout
        input_hla_scheduler_params = args.input_hla_scheduler_params

        if args.generate_hla_schedule:
            generate_hla_schedule = args.generate_hla_schedule
        if args.dual_mode:
            dual_mode = eval(args.dual_mode)
    except Exception as e:
        print(f"Failed to parse inputs: {e}")

    try:
        print("Reading the hla scheduler params.")
        if input_hla_scheduler_params:
            update_dict_from_json(
                input_hla_scheduler_params_dict, input_hla_scheduler_params
            )
        print(input_hla_scheduler_params_dict)
    except Exception as e:
        print(f"Failed to update the input_hla_scheduler_params_dict: {e}")

    depot_exit = input_hla_scheduler_params_dict["depot_exit"]

    return (
        input_t_circuit,
        output_dir,
        output_report_filename,
        layout_path,
        input_hla_scheduler_params_dict,
        generate_hla_schedule,
        dual_mode,
        depot_exit,
    )


def preprocess_circuit_and_layout(input_t_circuit, layout_path, depot_exit):
    """Preprocess the circuit and read in the layout from a .pkl file.

    Args:
        input_t_circuit (str): The path to the circuit file.
        layout_path (str): The path to the input layout .pkl file.

    Returns:
        circuit_(Circuit): The quantum circuit object.
        layout (TileLayout): The layout of a surface code error-corrected
            quantum computer.
    """
    print("Start preprocessing circuit and layout")
    try:
        circuit_ = Circuit()
        circuit_.read_circuit(input_t_circuit)

        if not layout_path:
            # generate memory fabric in the HLA layout from the number of qubits extracted from the circuit
            layout = get_memory_fabric_with_2x2_data_blocks_layout(
                circuit_.trans_cir.num_qubits,
                depot_exit,
            )
        else:
            # if a custom layout is input, read it from its pickle file
            layout = read_layout_from_pkl(layout_path)

        # Plot layout read
        # layout.plot()
    except Exception as e:
        raise Exception(f"Failed to preprocess circuit and layout: {e}")

    print("Done preprocessing circuit and layout")
    return circuit_, layout


def build_graphs_and_initialize_magic_state_factory(
    circuit: Circuit,
    layout,
):
    """Build an adjacency graph to represent the quantum hardware's physical
        constraints, a dependency graph for the quantum circuit's logical
        constraints and initalize a magic state factory to handle magic
        state update & availability.

    Args:
        circuit (Circuit:): The quantum circuit object.
        layout (TileLayout): The layout of a surface code error-corrected
            quantum computer.
        depot_exit (int): number of data-storage blocks connections (1 for
            serial scheduling)

    Returns:
        adj_graph (AdjacencyGraph): A networkx graph representing the circuit's
            connectivity.
        ms_factory (MagicStateFactory): A factory handles magic state
            update & availability.
    """
    print("Start building graphs and initalizing magic state factory")
    try:
        # build adjacency graph
        adj_graph = AdjacencyGraph(layout)
        adj_graph.process_graph()

        # build dependency graph
        circuit.process_circuit(adj_graph)
    except Exception as e:
        raise Exception(f"Failed to build graphs: {e}")
    try:
        # initialize magic state factory
        ms_factory = MagicStateFactory(
            tick_replenish=0,
            graph=adj_graph,
        )
    except Exception as e:
        raise Exception(f"Failed to initialize magic state factory: {e}")

    print("Done building graphs and initalizing magic state factory")
    return adj_graph, ms_factory


def run_HLAScheduler(
    config,
    input_t_circuit,
    circuit_,
    adj_graph,
    ms_factory,
    depot_exit,
    input_hla_scheduler_params_dict,
    output_dir,
    output_report_filename,
) -> None:
    """
    Runs the quantum HLAScheduler on the given circuit.

    Args:
        config(Dict[str, Any]): A dictionary containing configuration parameters.
        input_t_circuit (str): The path to the circuit file.
        circuit_(Circuit): The quantum circuit object.
        adj_graph (AdjacencyGraph): The graph representing the qubit
            adjacencies in the layout.
        ms_factory (MatchStrategyFactory): The factory object that handles
            magic state update & availability.
        depot_exit (int): number of data-storage blocks connections (1 for
            serial scheduling).
        input_hla_scheduler_params_dict (Dict[str, Any]): A dictionary
            containing layout parameters.
        output_dir(str): The directory where the output report will be saved.
        output_report_filename(str): The filename of the output report.
    Returns:
        None.

    Raises:
        FileNotFoundError: If the circuit file does not exist.
        Exception: If build the quantum system and run the simulation.
        Exception: If failed to generate and save the QRE report.

    """
    print("start running HLAScheduler")
    start = time.time()

    # Load the circuit file
    if not os.path.exists(input_t_circuit):
        raise FileNotFoundError(f"The circuit file {input_t_circuit} does not exist.")

    try:
        # Build the quantum system
        qc = QuantumSystem(
            circuit=circuit_,
            adj_graph=adj_graph,
            ms_fact=ms_factory,
            distillation_protocol=input_hla_scheduler_params_dict[
                "distillation_protocol"
            ],
            physical_qubit_error_rate=input_hla_scheduler_params_dict[
                "physical_qubit_error_rate"
            ],
            depot_capacity=input_hla_scheduler_params_dict["depot_capacity"],
            nb_factories=input_hla_scheduler_params_dict["nb_fac"],
            depot_entries=input_hla_scheduler_params_dict["depot_entry"],
            depot_exits=depot_exit,
        )

        # Run the simulation
        expected_runtime = qc.simulate(
            nb_runs=int(config["Experiments"]["nb_run"]),
            print_simulation=config["Experiments"]["print_out"],
        )

        end = time.time()
        total_compilation_time = end - start
        print(f"\nTotal QRE time : {total_compilation_time:.3f}")
    except Exception as e:
        raise (f"Failed to build the quantum system and run the simulation: {e}")

    try:
        # Generate and save the QRE report
        circuit_filename = os.path.basename(input_t_circuit)
        if not output_report_filename:
            output_report_filename = (
                os.path.splitext(circuit_filename)[0] + "_QREreport.txt"
            )
        generate_report_and_save(
            circuit_,
            qc,
            expected_runtime,
            print_details=config["Report"]["print_details"],
            save_report=config["Report"]["save_report"],
            output_dir=output_dir,
            output_report_name=output_report_filename,
            compilation_time=total_compilation_time,
        )
    except Exception as e:
        raise (f"Failed to generate and save the QRE report: {e}")

    print("Done running HLAScheduler")


def run_scheduler(input_t_circuit, adj_graph, ms_factory):
    """Runs the scheduler algorithm to schedule quantum rotations on qubits.

    Args:
        input_t_circuit (str): The path to the circuit file.
        adj_graph (AdjacencyGraph): The graph representing the qubit adjacencies
            in the layout.
        ms_factory (MatchStrategyFactory): The factory object that handles
            magic state update & availability.

    Returns:
        Tuple: A tuple of three values:
            - rotations_scheduling (List[RotationData]): A list of rotations,
                each represented as a RotationData object.
            - expected_quantum_computation_time (float): The expected quantum
                computation time in seconds.
            - compilation_time (float): The total time taken by the scheduler
                to compile the rotations, in seconds.

    Raises:
        FileNotFoundError: If the circuit file at `input_t_circuit` is not found.
        ValueError: If `adj_graph` is not an instance of `AdjacencyGraph`.
        TypeError: If `ms_factory` is not an instance of `MatchStrategyFactory`.
    """
    print("Start running scheduler")
    try:
        circuit_ = parse_rotations(input_t_circuit, split_y=False)

        # solve qubit assignment
        assignments, non_corner_patches = solve_data_qubit_assignment(
            circuit_, adj_graph, policy=AssignPolicy.RANDOM
        )

        #! (must be done after the qubit_assignments)
        circuit_ = convert_Y_operators(circuit_, non_corner_patches)

        # add turns
        circuit_.add_turn_qubits(adj_graph.qubit_angle)

        # Run scheduler
        (
            rotations_scheduling,
            expected_quantum_computation_time,
            compilation_time,
        ) = solve_rotations_scheduling(circuit_, adj_graph, ms_factory)
    except FileNotFoundError as e:
        raise Exception(f"File not found at path: {input_t_circuit}: {e}")
    except ValueError as e:
        raise Exception(
            f"AdjacencyGraph argument must be an instance of AdjacencyGraph: {e}"
        )
    except TypeError as e:
        raise Exception(
            f"MatchStrategyFactory argument must be an instance of MatchStrategyFactory: {e}"
        )

    print("Done running scheduler")
    return rotations_scheduling, expected_quantum_computation_time, compilation_time


# main function
if __name__ == "__main__":
    """
    Compilation flow:
    1) Parse input configs
    2) Preprocess circuit and layout
    3) Build graphs and initialize magic state factory
    4) Run scheduler AND/OR HLAScheduler
    5) Generate QRE report
    """

    # STEP 1: parse command line inputs and update configs
    (
        input_t_circuit,
        output_dir,
        output_report_filename,
        layout_path,
        input_hla_scheduler_params_dict,
        generate_hla_schedule,
        dual_mode,
        depot_exit,
    ) = parse_input_configs()

    # STEP 2: preprocess circuit and layout
    circuit, layout = preprocess_circuit_and_layout(
        input_t_circuit, layout_path, depot_exit
    )

    # STEP 3: build adjacency, dependency graphs and initialize magic state factory
    adj_graph, ms_factory = build_graphs_and_initialize_magic_state_factory(
        circuit, layout
    )

    # STEP 4: run HLAScheduler AND/OR scheduler
    if layout_path:
        run_scheduler(input_t_circuit, adj_graph, ms_factory)
        if dual_mode:
            run_HLAScheduler(
                config,
                input_t_circuit,
                circuit,
                adj_graph,
                ms_factory,
                depot_exit,
                input_hla_scheduler_params_dict,
                output_dir,
                output_report_filename,
            )
    else:
        run_HLAScheduler(
            config,
            input_t_circuit,
            circuit,
            adj_graph,
            ms_factory,
            depot_exit,
            input_hla_scheduler_params_dict,
            output_dir,
            output_report_filename,
        )

    # TODO STEP 5: generate and save QRE report
    # (currently only works on HLAScheduler)
