from typing import Optional, TypedDict
from math import sqrt
import logging.config
import stim, sinter, json
import numpy as np
from scipy.optimize import curve_fit
from uncertainties import correlated_values, unumpy
import matplotlib.pyplot as plt
from noise import NoiseParams, NoiseModel, units
import src.input_parser as input
from src.logger.src_logger_config import LOGGING_CONFIG


# Setup Logger
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)


class Measure(TypedDict):
    value: float
    unit: str


def emulate_ftqc_json(
    code_dict,
    number_of_cores,
    protocol_dict,
    decoder_dict,
    qubit_technology_dict,
    output_dir,
    plot_filename,
):
    """Emulated ftqc based on given json input and generates visualization and report.

    Args:
        code_dict (dict): Code dictionary
        number_of_cores (int): Number of cores
        protocol_dict (dict): Protocol dictionary
        decoder_dict (dict): Decoder dictioanry
        qubit_technology_dict (dict): Qubit technology parameters
        output_dir (str): Directory to save outputs.
        plot_filename (str): Filename for the generated plot.
    Returns:
        ftqc_report (dict): FTQC report
    """
    logger.info(f"code_dict={code_dict}")
    logger.info(f"number_of_cores={number_of_cores}")
    logger.info(f"protocol_dict={protocol_dict}")
    logger.info(f"decoder_dict={decoder_dict}")
    logger.info(f"qubit_technology_dict={qubit_technology_dict}")
    logger.info(f"output_dir={output_dir}")
    logger.info(f"plot_filename={plot_filename}")

    # Set up parameters
    noise_params = NoiseParams.transmon(qubit_technology_dict["parameters"])
    noise_model = NoiseModel.transmon(noise_params.ps)
    protocol = input.get_protocol_specifier(
        code_dict["specifier"], protocol_dict["specifier"]
    )
    rounds = protocol_dict["number_of_rounds"]
    parity_check_time = calculate_parity_check_time(noise_params, rounds)
    decoder = input.get_decoder_specifier(decoder_dict["specifier"])

    # TODO (Issue #8) get code distance from input file
    code_distance = None

    # If min_ler_estimate is not None, then we will plot the fit function upto the
    # distance that gives this logical error rate
    d_max = None

    # TODO: Investigate and make this field configurable if desired (#18)
    min_ler_estimate = 1e-15

    # FTQC emulations
    task_stats = emulate_ftqc(
        noise_model, protocol, decoder, rounds, number_of_cores, code_distance
    )

    # TODO: Improve this logical flow (#19)
    if code_distance is None:
        mean, std, plot_params = fit(task_stats)

        # Find maximum distance to plot the fit function from minimum logical error rate
        if min_ler_estimate is not None:
            d_max = find_cutoff_d_from_ler(
                min_ler_estimate,
                *correlated_values(
                    plot_params["fit_params"][0], plot_params["fit_params"][1]
                ),
            )

        plot_path = plot_ler_with_fit(
            x_data=plot_params["xs"],
            y_data=plot_params["ys"],
            y_err=plot_params["es"],
            fit_params=plot_params["fit_params"],
            x_max=d_max,
            plot_dir=output_dir,
            plot_name=plot_filename,
        )

        ftqc_report = generate_output_data_fit(parity_check_time, mean, std, plot_path)
    else:
        logical_error_rate = task_stats[0].errors / task_stats[0].shots
        ftqc_report = generate_output_data_ler(parity_check_time, logical_error_rate)

    logger.info(f"ftqc_report={ftqc_report}")
    logger.info("- Return")
    return ftqc_report


def read_input_data(file_path: str) -> dict:
    """Read input data from file.

    Args:
        file_path (str): Path to input file.

    Returns:
        dict: A dictionary containing the input data.
    """
    logger.info(f"file_path={file_path}")

    with open(file_path, "r") as read_file:
        args = json.load(read_file)
    input.validate_input_data(args)

    logger.info(f"args={args}")
    logger.info("- Return")
    return args


def emulate_ftqc(
    noise_model: NoiseModel,
    protocol: str = "surface_code:rotated_memory_z",
    decoder: list[str] = ["pymatching"],
    rounds: int = 1,
    number_of_cores: int = 8,
    code_distance: Optional[int] = None,
) -> list[sinter.TaskStats]:
    """Generate and run Monte Carlo sampling of quantum error correction circuits.

    Args:
        protocol (str, optional): protocol specifier. Defaults to
            "surface_code:rotated_memory_z".
        decoder (list[str], optional): decoder specifier. Defaults to ["pymatching"].
        rounds (int, optional): number of parity check rounds. Defaults to 1.
        number_of_cores (int, optional): number of cores. Defaults to 8.
        code_distance (Optional[int], optional): code distance. Defaults to None.
        noise_model (NoiseModel): noise model

    Returns:
        list[sinter.TaskStats]: Statistics for the emulation results for each code
            distance.
    """
    logger.info(f"noise_model={noise_model}")
    logger.info(f"protocol={protocol}")
    logger.info(f"decoder={decoder}")
    logger.info(f"rounds={rounds}")
    logger.info(f"number_of_cores={number_of_cores}")
    logger.info(f"code_distance={code_distance}")

    # Generate tasks for Monte Carlo sampling
    tasks = []
    if code_distance is None:
        max_code_distance = 9
        for d in range(3, max_code_distance + 2, 2):
            circuit = stim.Circuit.generated(protocol, rounds=rounds, distance=d)
            circuit = noise_model.noisy_circuit(circuit)
            tasks += [sinter.Task(circuit=circuit, json_metadata={"d": d})]
    else:
        circuit = stim.Circuit.generated(
            protocol, rounds=rounds, distance=code_distance
        )
        circuit = noise_model.noisy_circuit(circuit)
        tasks += [sinter.Task(circuit=circuit, json_metadata={"d": code_distance})]

    # Run Monte Carlo sampling of quantum error correction circuits
    task_stats = sinter.collect(
        num_workers=number_of_cores,
        tasks=tasks,
        decoders=decoder,
        max_shots=50_000_000,
        max_errors=10000,
        print_progress=False,
    )

    logger.info(f"task_stats={task_stats}")
    logger.info("- Return")
    return task_stats


def fit(task_stats: sinter.TaskStats) -> [list, list, dict]:
    """Fit the error rates and code distances to an exponential curve.

    Args:
        task_stats (sinter.TaskStats): Statistics for the emulation results for each
            code distance.

    Returns:
        [list, list, dict]: Mean and standard deviation of the fitting parameters and
            data used to plot.
    """
    logger.info(f"task_stats={task_stats}")

    # Get the error rate for each distance
    xs, ys, es = [], [], []
    for stats in task_stats:
        xs += [stats.json_metadata["d"]]
        ys += [stats.errors / stats.shots]
        es += [sqrt(ys[-1] * (1 - ys[-1]) / stats.shots)]

    # Remove points with very small error rates
    xs, ys, es = (np.array(_) for _ in [xs, ys, es])
    inds = np.where(es / ys > 0.0001)[0]
    xs, ys, es = (_[inds] for _ in [xs, ys, es])

    # Fit the error rate to an exponential curve
    p_opt, p_cov = curve_fit(
        lambda d, a, b: a - (d + 1) / 2 * b, xs, np.log(ys), sigma=es / ys
    )
    mean = np.array(p_opt)
    std = np.sqrt(np.diagonal(p_cov))

    params = (p_opt, p_cov)
    plottable = {"xs": xs, "ys": ys, "es": es, "fit_params": params}

    logger.info(f"mean={mean}")
    logger.info(f"std={std}")
    logger.info(f"plottable={plottable}")
    logger.info("- Return")
    return mean, std, plottable


def calculate_parity_check_time(
    noise_params: NoiseParams, num_parity_check_rounds: int
) -> Measure:
    """Calculate the parity check time.

    Args:
        noise_params (NoiseParams): Noise parameters.
        num_parity_check_rounds (int): Number of parity check rounds.

    Returns:
        Measure: Parity check time in microseconds.
    """
    logger.info(f"noise_params={noise_params}")
    logger.info(f"num_parity_check_rounds={num_parity_check_rounds}")

    t1, t2, tM, tR = (
        noise_params.t1,
        noise_params.t2,
        noise_params.tM,
        noise_params.tR,
    )

    logger.info("- Return")

    parity_check_time: Measure = {
        "value": round(
            (tM + num_parity_check_rounds * (4 * t2 + 2 * t1 + tM + tR)) / units["μs"],
            3,
        ),
        "unit": "μs",
    }

    return parity_check_time


def generate_output_data_fit(
    parity_check_time: Measure, mean, std, emulator_plot_path
) -> dict:
    """Generate output data for fitting results.

    Args:
        parity_check_time (Measure): Parity check time.
        mean (array): Mean of the fitting parameters.
        std (array): Standard deviation of the fitting parameters.
        emulator_plot_path (str): The file path of emulator visualization.

    Returns:
        dict: Output data for fitting results.
    """
    logger.info(f"parity_check_time={parity_check_time}")
    logger.info(f"mean={mean}")
    logger.info(f"std={std}")
    logger.info(f"emulator_plot_path={emulator_plot_path}")

    output = {
        "parity_check_time": parity_check_time,
        "fit": {
            # functional form of the fit in LaTeX format
            "functional_form": r"\exp\left(a - \dfrac{b(d+1)}{2}\right)",
            "fitting_parameters": {
                "a": {"value": round(mean[0], 3), "error": round(std[0], 3)},
                "b": {"value": round(mean[1], 3), "error": round(std[1], 3)},
            },
        },
        "emulator_plot_path": emulator_plot_path,
    }

    logger.info(f"output={output}")
    logger.info("- Return")
    return output


def generate_output_data_ler(
    parity_check_time: Measure, logical_error_rate: float
) -> dict:
    """Generate output data for logical error rate.

    Args:
        parity_check_time (Measure): Parity check time.
        logical_error_rate (float): Logical error rate.

    Returns:
        dict: Output data for logical error rate.
    """
    logger.info(f"parity_check_time={parity_check_time}")
    logger.info(f"logical_error_rate={logical_error_rate}")

    output = {
        "parity_check_time": parity_check_time,
        "logical_error_rate": logical_error_rate,
    }

    logger.info(f"output={output}")
    logger.info("- Return")
    return output


def generate_output_data_plot(
    code_distance: list[int], logical_error_rate: list[float], uncertainity: list[float]
) -> dict:
    """Generate output data for logical error rate.

    Args:
        code_distance (list(int)): a list of integers
            corresponding to code distances simulated.
        logical_error_rate (list(float)): a list of floats
            for logical error rates from simulation results
        uncertainity (list(float)): a list of floats corresponding
            to uncertainites in the logical error rates.
    Returns:
        dict: Output data used for plotting.
    """
    logger.info(f"code_distance={code_distance}")
    logger.info(f"logical_error_rate={logical_error_rate}")
    logger.info(f"uncertainity={uncertainity}")

    output = {}
    for i in range(len(code_distance)):
        output[f"distance_{code_distance[i]}"] = {
            "distance": int(code_distance[i]),
            "logical_error_rate": logical_error_rate[i],
            "uncertainity": uncertainity[i],
        }

    logger.info(f"output={output}")
    logger.info("- Return")
    return output


def write_output_data(
    output: dict,
    output_file_dir: str = "data/output/",
    output_file_name: str = "output.json",
    format="json",
):
    """Write output data to external file.

    Args:
        output (dict): Output data.
        output_file_dir (str): The directory to output file. Defaults to "data/output/".
        output_file_name (str): The name to output file. Defaults to "output.json".
        format (str, optional): File format. Defaults to "json".
    """
    logger.info(f"output={output}")
    logger.info(f"output_file_dir={output_file_dir}")
    logger.info(f"output_file_name={output_file_name}")
    logger.info(f"format={format}")

    output_file_path = output_file_dir + output_file_name
    if format == "json":
        output_json = json.dumps(output, indent=4)

        with open(output_file_path, "w") as write_file:
            write_file.write(output_json)
            write_file.close()

        logger.info(f"Successfully save the output at {output_file_path}")


def fit_func(d: np.array, *params: tuple[float, float]) -> np.array:
    """
    Fit function for the log of logical error rate.

    Args:
        d (numpy array): Distance.
        params (tuple): Fit parameters a and b.

    Returns:
        Numpy array of log of logical error rates.
    """
    logger.info(f"d={d}")
    logger.info(f"params={params}")

    if len(params) == 2:
        a, b = params
    else:
        err_msg = f"Not implemented fit for #{len(params)} parameters"
        logger.error(err_msg)
        raise NotImplementedError(err_msg)

    logger.info("- Return")
    return a - (d + 1) / 2 * b


def find_cutoff_d_from_ler(logical_error_rate: float, *params) -> int:
    """
    For a given logical error rate, find the cutoff (minumum) code distance
        required to achieve it based on the fit parameters.

    Args:
        logical_error_rate (float): The minimum logical error rate needed to achie.
        params (tuple(float)): Fit parameters a and b.

    Returns:
        Cutoff code distance.
    """
    logger.info(f"logical_error_rate={logical_error_rate}")
    logger.info(f"params={params}")

    if len(params) == 2:
        a, b = params
    else:
        err_msg = f"Not implemented fit for #{len(params)} parameters"
        logger.error(err_msg)
        raise NotImplementedError(err_msg)
    d = unumpy.nominal_values((a - np.log(logical_error_rate)) * 2 / b - 1)
    if np.ceil(d) % 2 == 1:
        logger.info("- Return")
        return np.ceil(d)
    else:
        logger.info("- Return")
        return np.ceil(d) + 1


def plot_ler_with_fit(
    x_data: list[int],
    y_data: list[float],
    y_err: list[float],
    fit_params: tuple[float, float],
    x_max: int = None,
    plot_dir="data/output/",
    plot_name="plot",
):
    """
    Plot logical error rate including the best fit line, and save the generated figure
    in the provided directory and with the specified name.

    Args:
        x_data (list[int]): x-axis values for plot corresponding to code distance.
        y_data (list[float]): y-axis values for plot corresponding to the
                logical error rates of each code distance.
        y_err (list[float]): uncertainity of the logical error rates (y_data)
        fit_params (tuple[float, float]): parameters for the best fit line.
        x_max (int, optional): Maximum code distance to plot the fit function.
        plot_dir (str, optional): Directory where the plot will be saved. Defaults to
            "data/output/".
        plot_name (str, optional): Name of the generated plot image. Defaults to
            "plot".

    Returns:
        str: The path where the plot is saved.
    """
    logger.info(f"x_data={x_data}")
    logger.info(f"y_data={y_data}")
    logger.info(f"y_err={y_err}")
    logger.info(f"fit_params={fit_params}")
    logger.info(f"x_max={x_max}")
    logger.info(f"plot_dir={plot_dir}")
    logger.info(f"plot_name={plot_name}")

    # fit parameters
    params = correlated_values(fit_params[0], fit_params[1])

    # generate the x values for fit boundaries
    if x_max is None:
        ds = np.array(sorted(x_data))
    elif x_max is not None and x_max <= max(x_data):
        ds = np.array(sorted([d for d in x_data if d <= x_max]))
    else:
        ds = np.arange(3, x_max + 1, 2)

    # find the estimated y values from the fit
    _ys = fit_func(ds, *params)
    n, s = (unumpy.nominal_values(_ys), unumpy.std_devs(_ys))

    fig, ax1 = plt.subplots(ncols=1, figsize=(15, 15))
    ax1.tick_params(axis="both", which="major", labelsize=22)

    # plot the data points from simulation with error bars
    ax1.errorbar(
        x_data,
        y_data,
        y_err,
        ls="",
        marker="o",
        mfc="white",
        color="r",
        capsize=4,
        lw=2,
    )

    # plot the fit function with region of uncertainty
    ax1.fill_between(ds, np.exp(n - s), np.exp(n + s), alpha=0.5, ls="-")

    # Plot paramters
    ax1.grid(which="both")
    ax1.set_ylabel("Logical error rate", fontsize=34)
    ax1.set_xlabel("Code distance (d)", fontsize=34)
    ax1.set_yscale("log", base=10)

    # save plot to an image file
    plot_path = plot_dir + plot_name + ".png"
    plt.savefig(plot_path)
    plt.close()

    logger.info(f"Successfully save plot in {plot_path}")
    logger.info(f"plot_path={plot_path}")
    logger.info("- Return")
    return plot_path


if __name__ == "__main__":
    # Read input file
    input_file_name = "default_input.json"
    input_file_path = "data/input/" + input_file_name
    args = read_input_data(input_file_path)

    # Set up parameters
    noise_params = NoiseParams.transmon(args["qubit_technology"]["parameters"])
    noise_model = NoiseModel.transmon(noise_params.ps)
    protocol = input.get_protocol_specifier(
        args["code"]["specifier"], args["protocol"]["specifier"]
    )
    rounds = args["protocol"]["number_of_rounds"]
    parity_check_time = calculate_parity_check_time(noise_params, rounds)
    decoder = input.get_decoder_specifier(args["decoder"]["specifier"])
    number_of_cores = args["number_of_cores"]

    # TODO (Issue #8) get code distance from input file
    code_distance = None

    # If min_ler_estimate is not None, then we will plot the fit function upto the
    # distance that gives this logical error rate
    d_max = None

    # TODO: Investigate and make this field configurable if desired (#18)
    min_ler_estimate = 1e-15

    # FTQC emulations
    task_stats = emulate_ftqc(
        noise_model, protocol, decoder, rounds, number_of_cores, code_distance
    )

    # TODO: Improve this logical flow (#19)
    if code_distance is None:
        mean, std, plot_params = fit(task_stats)

        # Find maximum distance to plot the fit function from minimum logical error rate
        if min_ler_estimate is not None:
            d_max = find_cutoff_d_from_ler(
                min_ler_estimate,
                *correlated_values(
                    plot_params["fit_params"][0], plot_params["fit_params"][1]
                ),
            )

        # Generate and save plot
        plot_path = plot_ler_with_fit(
            x_data=plot_params["xs"],
            y_data=plot_params["ys"],
            y_err=plot_params["es"],
            fit_params=plot_params["fit_params"],
            x_max=d_max,
            plot_dir="data/output/",
            plot_name="plot",
        )

        output = generate_output_data_fit(parity_check_time, mean, std, plot_path)

        plottable_output = generate_output_data_plot(
            plot_params["xs"], plot_params["ys"], plot_params["es"]
        )

        # save plot data to json file
        write_output_data(plottable_output, output_file_name="plottable.json")

    else:
        logical_error_rate = task_stats[0].errors / task_stats[0].shots
        output = generate_output_data_ler(parity_check_time, logical_error_rate)

    # Write output data to file
    write_output_data(output, output_file_name="output.json")
