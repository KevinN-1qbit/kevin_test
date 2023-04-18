"""A command line interface for the lys package"""

import argparse
import sys
import os
import os.path as osp
import time
import pathlib
import multiprocessing

from Trillium.utils import parse


def is_bool(value: str) -> bool:
    """ Checks if the input is a string representing a boolean value """
    value = value.lower()
    if value not in ["true", "false"]:
        message = "Argument entered is invalid. " \
                  "Please enter either True or False."
        raise argparse.ArgumentTypeError(message)
    return value == "true"


# noinspection PyMissingTypeHints
def parse_args():
    cmd_parser = argparse.ArgumentParser(
        prog="lys",
        usage="Typical case: %(prog)s  -input path_to_input_file "
              "-language qasm",
        description="Convert a circuit into rotations and reduce the T-count "
                    "and depth by performing optimization. Optionally, can "
                    "combine non-T rotations with measurements.",
        fromfile_prefix_chars="@")

    cmd_parser.version = "Lys CLI Version 1."

    cmd_parser.add_argument("-input", action="store", type=str, metavar="",
                            help="Path to the input circuit file")

    cmd_parser.add_argument("-output_filename", action="store", type=str, metavar="",
                            help="Filename for output transpiled circuit",
                            default="")

    cmd_parser.add_argument("-combine", action="store",
                            type=is_bool, metavar="",
                            help="Choose whether to combine the non-T "
                                 "rotations with measurement. Default is True",
                            default=True)

    cmd_parser.add_argument("-recompile", action="store",
                            type=is_bool, metavar="",
                            help="Choose whether to recompile the cpp source "
                                 "code. Default is False",
                            default=False)

    cmd_parser.add_argument("-language", action="store", type=str, metavar="",
                            help="Choose the language of the circuit file. "
                                 "No default value provided. Please make sure "
                                 "you choose the correct language option as "
                                 "the current version of compiler cannot "
                                 "detect the wrong language being used",
                            choices=["qasm", "projectq"])

    cmd_parser.add_argument("-epsilon", action="store", type=float, metavar="",
                            help="Set the value of decomposition precision. "
                                 "Positive values only. "
                                 "Smaller values give higher precision",
                            default=1e-10)

    cmd_parser.add_argument("-version", action="store", type=str, metavar="",
                            help="Print the version of the tool")

    # Execute the parse_args() method
    args = cmd_parser.parse_args(None if sys.argv[1:] else ["-h"])

    # Make sure that all required arguments are provided
    required_set = [args.input, args.language]

    if args.input:
        if not osp.isfile(args.input) and not osp.exists(args.input):
            cmd_parser.error("The file/directory specified does not exist")
        # elif not args.input.lower().endswith(("."+ args.language)):
        #     cmd_parser.error("Input is not of the correct file type. "
        #                      "Please provide a "." + args.language + " file.")

    if None in required_set:
        if (args.language is None) and (args.input is not None):
            cmd_parser.error("Missing language choice. Please specify the "
                             "input language by: -language choice_of_language")

        elif args.language is not None and args.input is None:
            cmd_parser.error("Missing file path to circuit. Please specify "
                             "the path to input circuit by: "
                             "-input path_to_input_circuit")

    return args


# Construct the functions to set the parameters
def get_compiled_circuit(
        parser: type(parse.Parse), file: str, cfg: dict) -> None:
    parse_command = parser(file, cfg["epsilon"])
    instructions = parse_command.instructions
    num_qubits = parse_command.num_qubits
    combine = cfg["combine"]
    recompile = cfg["recompile_cpp"]

    # We reimport the entire python wrapper class so that effectively
    # we are reimporting the c++ functions so that
    # we don't use the one's with the old number of qubits.
    # pylint: disable=import-outside-toplevel
    from Trillium.src.python_wrapper.LysCompiler_cpp_interface import LysCompiler

    compiled_circuit = []  # variable to hold the compiled circuit
    compiler = LysCompiler(instructions, num_qubits, recompile)
    if cfg["language"] == "projectq":
        compiled_circuit = \
            compiler.run_no_layer(
                cfg["language"], combine, parse_command.first_ancilla_idx)
    elif cfg["language"] == "qasm":
        compiled_circuit = compiler.run_no_layer(cfg["language"], combine)

    # Write output to a file
    output_path = "data/output/"
    pathlib.Path(output_path).mkdir(parents=True, exist_ok=True)

    # pylint: disable=unused-variable
    input_path, input_extension = osp.splitext(file)
    input_name = input_path.split("/")[-1]

    if cfg["output_filename"]:
        output_name = output_path + cfg["output_filename"]
    else:
        output_name = output_path + "Compiled_" + input_name + "_" \
            + time.strftime("%Y%m%d-%H-%M", time.localtime()) + ".txt"

    with open(output_name, "w+") as output_file:
        for line in compiled_circuit:
            output_file.writelines(str(line) + "\n")


def main(cfg: dict) -> None:
    chosen_parser, circuit_input = get_parser_and_circuit_input(cfg)

    if osp.isfile(circuit_input):
        p = multiprocessing.Process(target=get_compiled_circuit,
                                    args=(chosen_parser, circuit_input, cfg))
        p.start()
        p.join()
    elif osp.isdir(circuit_input):
        # ignore nested directories inside the folder
        directory = [circuit_input + "/" + file
                     for file in os.listdir(circuit_input)
                     if osp.isfile(osp.join(circuit_input, file))]
        for each_file in directory:
            p = multiprocessing.Process(target=get_compiled_circuit,
                                        args=(chosen_parser, each_file, cfg))
            p.start()
            p.join()

    print("Compilation completed. "
          "Result has been written to directory: data/output")


def get_parser_and_circuit_input(cfg: dict):
    parser_dict = {"qasm": parse.ParseQasm, "projectq": parse.ParseProjectQ}
    chosen_parser = parser_dict[cfg["language"]]
    circuit_input: str = cfg["input"]
    return chosen_parser, circuit_input


def get_cfg() -> dict:
    args = parse_args()
    config = {
                "input": args.input,
                "output_filename": args.output_filename,
                "language": args.language,
                "combine": args.combine,
                "recompile_cpp": args.recompile,
                "epsilon": args.epsilon
            }
    return config


if __name__ == "__main__":
    main(get_cfg())
