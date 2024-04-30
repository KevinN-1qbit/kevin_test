"""A command line interface for the lys package"""

import argparse
import sys
import os
import os.path as osp
import time
import pathlib
import multiprocessing
import logging.config
import os.path as osp
import subprocess

from logger.logger_config import get_logging_config
from utils import parse

# Setup Logger
logging.config.dictConfig(get_logging_config())
logger = logging.getLogger(__name__)


def is_bool(value: str) -> bool:
    """Checks if the input is a string representing a boolean value"""
    logger.info(f"value={value}")

    value = value.lower()
    if value not in ["true", "false"]:
        message = "Argument entered is invalid. " "Please enter either True or False."
        logger.error(message)
        raise argparse.ArgumentTypeError(message)

    logger.info(f"value={value == 'true'}")
    logger.info("- Return")
    return value == "true"


# noinspection PyMissingTypeHints
def parse_args():
    """TODO: docstrings"""
    logger.info("()")
    cmd_parser = argparse.ArgumentParser(
        prog="lys",
        usage="Typical case: %(prog)s  -input path_to_input_file " "-language qasm",
        description="Convert a circuit into rotations and reduce the T-count "
        "and depth by performing optimization. Optionally, can "
        "combine non-T rotations with measurements.",
        fromfile_prefix_chars="@",
    )

    cmd_parser.version = "Lys CLI Version 1."

    cmd_parser.add_argument(
        "-input",
        action="store",
        type=str,
        metavar="",
        help="Path to the input circuit file",
    )

    cmd_parser.add_argument(
        "-output_path",
        action="store",
        type=str,
        metavar="",
        help="Path for output transpiled circuit",
        default="",
    )

    cmd_parser.add_argument(
        "-time_out",
        type=int,
        help="Set the time limit in sec for the tranpilation process. "
        "Default is 2_147_483_647, which is the INT_MAX value in C++.",
        default=2_147_483_647,
    )

    cmd_parser.add_argument(
        "-remove_non_t",
        action="store",
        type=is_bool,
        metavar="",
        help="Choose whether to transform the circuit to remove the non-T"
        "rotations. Default is True",
        default=True,
    )

    cmd_parser.add_argument(
        "-recompile",
        action="store",
        type=is_bool,
        metavar="",
        help="Choose whether to recompile the cpp source " "code. Default is False",
        default=False,
    )

    cmd_parser.add_argument(
        "-language",
        action="store",
        type=str,
        metavar="",
        help="Choose the language of the circuit file. "
        "No default value provided. Please make sure "
        "you choose the correct language option as "
        "the current version of transpiler cannot "
        "detect the wrong language being used",
        choices=["qasm", "projectq"],
    )

    cmd_parser.add_argument(
        "-epsilon",
        action="store",
        type=float,
        metavar="",
        help="Set the value of decomposition precision. "
        "Positive values only. "
        "Smaller values give higher precision",
        default=1e-10,
    )

    cmd_parser.add_argument(
        "-bypass_optimization",
        action="store",
        type=is_bool,
        metavar="",
        help="Determine whether or not to bypass optimization and calculate basis conversion only",
        default=False,
    )

    cmd_parser.add_argument(
        "-optimizer_executable",
        action="store",
        type=str,
        metavar="",
        help="File path to optimizer executable",
        default="",
    )

    cmd_parser.add_argument(
        "-version",
        action="store",
        type=str,
        metavar="",
        help="Print the version of the tool",
    )

    # Execute the parse_args() method
    args = cmd_parser.parse_args(None if sys.argv[1:] else ["-h"])

    # Make sure that all required arguments are provided
    required_set = [args.input, args.language]

    if args.input:
        if not osp.isfile(args.input) and not osp.exists(args.input):
            error_msg = f"The input: {args.input} does not exist"
            logger.error(error_msg)
            cmd_parser.error(error_msg)

    if None in required_set:
        if (args.language is None) and (args.input is not None):
            error_msg = """
                Missing language choice. Please specify the
                input language by: -language choice_of_language"""
            logger.error(error_msg)
            cmd_parser.error(error_msg)

        elif args.language is not None and args.input is None:
            error_msg = """
                Missing file path to circuit. Please specify
                the path to input circuit by:
                -input path_to_input_circuit"""
            logger.error(error_msg)
            cmd_parser.error(error_msg)

    logger.info(f"args={args}")
    logger.info("- Return")
    return args


# Construct the functions to set the parameters
def get_transpiled_circuit(parser: type(parse.Parse), file: str, cfg: dict) -> None:
    """TODO: docstrings

    Args:
        parser (type): _description_
        file (str): _description_
        cfg (dict): _description_
    """
    logger.info(f"parser={parser}")
    logger.info(f"file={file}")
    logger.info(f"cfg={cfg}")

    optimizer_executable = cfg["optimizer_executable"]

    input_file = file
    output_file = cfg["output_path"] + "_transpile.txt"
    arguments = ['--input', input_file, '--output', output_file, "--big-file"]

    # Call the Rust optimizer executable
    try:
        output = subprocess.check_output([optimizer_executable] + arguments, stderr=subprocess.STDOUT)
        logger.info(output.decode('utf-8'))  # Decode output bytes to string and print
        logger.info(f"Successfully wrote to {output_file}")
    except subprocess.CalledProcessError as e:
        logger.error("Error:", e.output.decode('utf-8'))  # Decode error output bytes to string and print

    logger.info("- Return")


def writeToFile(circuit: list, file: str, cfg: dict, step: str) -> None:
    """Takes a circuit and its configurations and writes them to given file path based on
       transpilation step

    Args:
        circuit (list): Circuit being written to file
        file (str): File path where circuit is being written to
        cfg (dict): Configurations for circuit
        step (str): Denotes step of transpiler (basis conversion vs transpile)
    Returns:
        output_name (str): Name and file path of the circuit
    """
    logger.info(f"file={file}")
    logger.info(f"cfg={cfg}")
    logger.info(f"step={step}")

    input_path, input_extension = osp.splitext(file)
    input_name = input_path.split("/")[-1]

    output_path = "data/output/"
    file_step_name = "Transpiled_" if step == "transpile" else "BasisConverted_"
    if cfg["output_path"]:
        output_name = cfg["output_path"] + "_" + step + ".txt"
    else:
        pathlib.Path(output_path).mkdir(parents=True, exist_ok=True)
        output_name = (
            output_path
            + file_step_name
            + input_name
            + "_"
            + time.strftime("%Y%m%d-%H-%M", time.localtime())
            + ".txt"
        )

    for i in range(5):
        try:
            with open(
                output_name, ("w" if cfg["language"] == "qasm" else "a")
            ) as output_file:
                for line in circuit:
                    output_file.writelines(str(line) + "\n")
            logger.info(f"Successfully wrote to {output_name} on attempt {i+1}")
            return output_name
        except (FileNotFoundError, PermissionError) as e:
            logger.debug(f"Attempt {i+1} failed: {e}")
            time.sleep(1)
    logger.error(f"All attempts to write to {output_name} have failed.")


def transpile(
    circuit_file_path,
    language,
    output_path,
    optimizer_executable,
    remove_non_t=True,
    time_out=0,
    recompile_cpp=False,
    epsilon=1e-10,
    bypass_optimization=False,
    redis_handler=None,
):
    """Transpile given circuit."""
    logger.info("()")
    logger.info(f"circuit_file_path={circuit_file_path}")
    logger.info(f"language={language}")
    logger.info(f"output_path={output_path}")
    logger.info(f"optimizer_executable={optimizer_executable}")
    logger.info(f"remove_non_t={remove_non_t}")
    logger.info(f"time_out={time_out}")
    logger.info(f"recompile_cpp={recompile_cpp}")
    logger.info(f"epsilon={epsilon}")
    logger.info(f"bypass_optimization={bypass_optimization}")
    logger.info(f"redis_handler={redis_handler}")

    try:
        # If redis_handler is provided, add it to the root logger
        root_logger = logging.getLogger()
        if redis_handler:
            root_logger.addHandler(redis_handler)
            root_logger.setLevel(logging.INFO)
            logger.info(
                f"sucessfully add redis handler to root handler and set level to info"
            )

        # Prepare config dictionary
        cfg = {
            "input": circuit_file_path,
            "language": language,
            "output_path": output_path,
            "remove_non_t": remove_non_t,
            "time_out": time_out,
            "recompile_cpp": recompile_cpp,
            "epsilon": epsilon,
            "bypass_optimization": bypass_optimization,
            "optimizer_executable": optimizer_executable
        }

        chosen_parser, circuit_input = get_parser_and_circuit_input(cfg)

        # Run transpilation process on circuit
        if osp.isfile(circuit_input):
            process = multiprocessing.Process(
                target=get_transpiled_circuit, args=(chosen_parser, circuit_input, cfg)
            )
            process.start()
            process.join()
        elif osp.isdir(circuit_input):
            # ignore nested directories inside the folder
            directory = [
                circuit_input + "/" + file
                for file in os.listdir(circuit_input)
                if osp.isfile(osp.join(circuit_input, file))
            ]
            for each_file in directory:
                process = multiprocessing.Process(
                    target=get_transpiled_circuit, args=(chosen_parser, each_file, cfg)
                )
                process.start()
                process.join()
    finally:
        # Remove redis handler
        if redis_handler:
            root_logger.removeHandler(redis_handler)
            logger.info("Removed redis handler from root logger.")

    logger.info("- Return")


def main(cfg: dict) -> None:
    """TODO: docstrings

    Args:
        cfg (dict): _description_
    """
    logger.info(f"cfg={cfg}")

    transpile(
        cfg["input"],
        cfg["language"],
        cfg["output_path"],
        cfg["optimizer_executable"],
        cfg["remove_non_t"],
        cfg["time_out"],
        cfg["recompile_cpp"],
        cfg["epsilon"],
        cfg["bypass_optimization"]
    )

    logger.info(
        "Transpilation completed. " "Result has been written to directory: data/output"
    )
    logger.info("- Return")


def get_parser_and_circuit_input(cfg: dict):
    """TODO: docstrings

    Args:
        cfg (dict): _description_

    Returns:
        _type_: _description_
    """
    logger.info(f"cfg={cfg}")

    parser_dict = {"qasm": parse.ParseQasm, "projectq": parse.ParseProjectQ}
    chosen_parser = parser_dict[cfg["language"]]
    circuit_input: str = cfg["input"]

    logger.info(f"chosen_parser={chosen_parser}")
    logger.info(f"circuit_input={circuit_input}")
    logger.info("- Return")
    return chosen_parser, circuit_input


def get_cfg() -> dict:
    """TODO: docstrings

    Returns:
        dict: _description_
    """
    logger.info("()")

    args = parse_args()
    config = {
        "input": args.input,
        "output_path": args.output_path,
        "language": args.language,
        "remove_non_t": args.remove_non_t,
        "time_out": args.time_out,
        "recompile_cpp": args.recompile,
        "epsilon": args.epsilon,
        "bypass_optimization": args.bypass_optimization,
        "optimizer_executable": args.optimizer_executable
    }

    logger.info(f"config={config}")
    logger.info("- Return")
    return config


if __name__ == "__main__":
    main(get_cfg())
