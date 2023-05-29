import configparser
import math
import os

from prettytable import PrettyTable

from hla_scheduler.hla_scheduler import Circuit, QuantumSystem


# Load configs
config = configparser.ConfigParser()
config.read_file(open("src/config/scheduler.conf"))


def expected_optimal_runtime(qc: QuantumSystem):
    # get time to distill the first magic states
    min_protocol = min(fac.protocol.t for fac in qc.distillation.factories)

    # this is an approximation for the optimal solution in a steady distillation flow (infinite factories)
    # given that each pi8 rotation takes [min_time,max_time] time steps to run
    # and the first batch of magic states takes protocol.t+2 time steps to be distilled
    return (
        qc.circuit.pi8 * (qc.data.pi8_max_time + qc.data.pi8_min_time) / 2
        + min_protocol
        + 2
        + qc.circuit.measurements
    )


def print_parameters(qc: QuantumSystem):
    # header
    parameters = [
        [
            "Nb. factories",
            "Dist. protocol",
            "Storage cap.",
            "Storage entries",
            "Storage exits",
            "Physical qubit error rate",
            "Nb. runs",
            "Simulation mode",
        ]
    ]

    # parameters
    parameters.append(
        [
            qc.distillation.nb_factories,
            qc.distillation.factories[0].protocol.protocol,
            qc.storage.capacity,
            qc.storage.nb_entry,
            qc.storage.nb_exit,
            qc.physical_error,
            qc.nb_runs,
            config["Experiments"]["simulation_mode"],
        ]
    )

    # print in a pretty table
    tab = PrettyTable(parameters[0])
    tab.add_rows(parameters[1:])
    tab.title = "Simulation parameters"
    print(tab, "\n")
    return tab


def generate_report_and_save(
    circuit_: Circuit,
    qc: QuantumSystem,
    expected_runtime: float,
    compilation_time: float,
    print_details=False,
    save_report=False,
    output_dir="src/data/outputs",
    output_report_name="report.txt",
):
    # print parameters
    parameters = print_parameters(qc)

    # header
    results = [["Circuit", "Runtime (sim.)", "Nb. logical qubits", "Compilation time"]]

    # results
    results.append(
        [
            circuit_.name[:-4],
            expected_runtime,
            # TODO print 'Runtime (serial opt.)' using expected_optimal_runtim(qc)
            qc.get_nb_logical_qubits(),
            compilation_time,
        ]
    )

    # print in a pretty table
    tab = PrettyTable(results[0])
    tab.add_rows(results[1:])
    tab.title = "Simulation results"
    print(tab, "\n")

    if save_report:
        # Initialize reprot content list
        report_content = [parameters, tab]

    if print_details:
        circuit_report = PrettyTable()
        circuit_report.header = False
        circuit_report.title = "CIRCUIT"
        circuit_report.add_row(["PI8", circuit_.pi8])
        circuit_report.add_row(["PI4", circuit_.pi4])
        circuit_report.add_row(["MEAS", circuit_.measurements])
        circuit_report.add_row(["QUBITS", circuit_.nb_qubits])
        print(circuit_report)

        total_distillation = circuit_.pi8 / (
            qc.distillation.factories[0].success_rate
            * qc.distillation.factories[0].protocol.k
        )
        total_distillation_per_factory = (
            total_distillation / qc.distillation.nb_factories
        )
        avg_distillation_time = qc.distillation.factories[0].protocol.t * (
            (
                qc.distillation.factories[0].pi8_min_time
                + qc.distillation.factories[0].pi8_max_time
            )
            / 2
        )
        total_runtime_distillation = (
            total_distillation_per_factory * avg_distillation_time
        )
        distillation_cycle_time = avg_distillation_time + math.ceil(
            qc.distillation.factories[0].protocol.k / qc.storage.nb_entry
        )

        distillation_block_report = PrettyTable()
        distillation_block_report.header = False
        distillation_block_report.title = "DISTILLATION BLOCK"
        distillation_block_report.add_row(
            ["Distillation protocol", qc.distillation.factories[0].protocol.protocol]
        )
        distillation_block_report.add_row(
            ["Nb. factories", qc.distillation.nb_factories]
        )
        distillation_block_report.add_row(
            [
                "Nb. logical qubits",
                qc.distillation.get_nb_logical_qubits(qc.storage.nb_entry),
            ]
        )
        distillation_block_report.add_row(
            ["Expected total nb. distillations", round(total_distillation, 1)]
        )
        distillation_block_report.add_row(
            [
                "Expected nb. distillations per factory",
                round(total_distillation_per_factory, 1),
            ]
        )
        distillation_block_report.add_row(
            [
                "Expected avg. distillation time in a factory",
                round(avg_distillation_time, 2),
            ]
        )
        # TODO distillation_block_report.add_row(['(*CHECK*) Expected quantum runtime of distillation cycles', total_runtime_distillation])
        distillation_block_report.add_row(
            [
                "Distillation success rate",
                round(qc.distillation.factories[0].success_rate, 3),
            ]
        )
        distillation_block_report.add_row(
            ["Distillation cycle time", distillation_cycle_time]
        )
        distillation_block_report.add_row(["...", "..."])
        print(distillation_block_report)

        storage_block_report = PrettyTable()
        storage_block_report.header = False
        storage_block_report.title = "STORAGE BLOCK"
        storage_block_report.add_row(
            ["Nb. of logical qubits", qc.storage.get_nb_logical_qubits()]
        )
        storage_block_report.add_row(["STORAGE", qc.storage.capacity])
        storage_block_report.add_row(
            ["BUS", qc.storage.get_nb_logical_qubits() - qc.storage.capacity]
        )
        storage_block_report.add_row(["...", "..."])
        print(storage_block_report)

        data_block_report = PrettyTable()
        data_block_report.header = False
        data_block_report.title = "DATA BLOCK"
        data_block_report.add_row(
            ["Nb. of logical qubits", qc.data.get_nb_logical_qubits()]
        )
        data_block_report.add_row(["DATA", circuit_.nb_qubits])
        data_block_report.add_row(
            ["BUS", qc.data.get_nb_logical_qubits() - circuit_.nb_qubits]
        )
        data_block_report.add_row(["...", "..."])
        print(data_block_report)

        ms_production_capacity = (
            qc.distillation.nb_factories
            * qc.distillation.factories[0].protocol.k
            / (avg_distillation_time / qc.distillation.factories[0].success_rate)
        )
        ms_storage_rate = (
            qc.distillation.nb_factories
            * qc.distillation.factories[0].protocol.k
            / (distillation_cycle_time / qc.distillation.factories[0].success_rate)
        )
        # TODO print 'ms_production_rate' using qc.distillation.nb_factories * qc.distillation.factories[0].protocol.k / (qc.distillation.factories[0].protocol.t + math.ceil(qc.distillation.factories[0].protocol.k / qc.storage.nb_entry)) * qc.distillation.factories[0].success_rate

        ms_consumption_capacity = 1 / (
            (qc.data.pi8_min_time + qc.data.pi8_max_time) / 2
        )  # TODO for a serial scheduling
        # TODO print 'ms_consumption_rate' using circuit_.pi8 / expected_runtime

        prod_cons_report = PrettyTable()
        prod_cons_report.header = False
        prod_cons_report.title = "PRODUCTION/CONSUMPTION"
        prod_cons_report.add_row(
            ["Magic state production rate capacity", round(ms_production_capacity, 3)]
        )
        prod_cons_report.add_row(
            ["Magic state storage rate", round(ms_storage_rate, 3)]
        )

        # TODO add row to 'prod_cons_report': (['Average magic state production
        # rate (ms/time step)', round(ms_production_rate,3)])

        prod_cons_report.add_row(
            ["Magic state consumption rate capacity", round(ms_consumption_capacity, 3)]
        )

        # TODO add row to 'prod_cons_report': (['Average magic state consumption rate (ms/time step)', round(ms_consumption_rate,3)])
        prod_cons_report.add_row(["...", "..."])
        print(prod_cons_report)

        # add each report to report_content for saving to file
        if save_report:
            report_content.append(circuit_report)
            report_content.append(distillation_block_report)
            report_content.append(storage_block_report)
            report_content.append(data_block_report)
            report_content.append(prod_cons_report)

        # TODO provide a report with the estimation for multiple scenarios? (e.g., 1 to F factories))

    # Save report to output_dir
    if save_report:
        save_report_to_file(
            report_content,
            output_dir,
            output_report_name,
        )


def save_report_to_file(
    report_content,
    output_dir="src/data/outputs",
    output_report_name="report.txt",
):
    """Save report content to file

    Args:
        report_content (list): a list of PrettyTable objects containing the
            report content
        output_dir (str, optional): the directory to save the output reports. Defaults to "src/data/outputs".
        output_report_name (str, optional): the output report file name. Defaults to "report.txt".
    """
    report_file_path = output_dir + "/" + output_report_name
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(report_file_path, "w") as f:
        for content in report_content:
            f.write(str(content) + "\n")
        f.close()

    print(f"Successfully save the report at directory: {report_file_path}")
