from math import pi
import time
from .Rotation import Rotation
from .Measure import Measure
import os
import subprocess
from time import sleep

import logging.config

logger = logging.getLogger(__name__)


class LysCompiler:
    """A class which compiles the input circuit into a circuit consists of pi/8 rotation gates and measurement"""

    # Gate Defintion convention is as the following: [rotation_basis, rotation_angle]
    # z4: pi/4 rotation in z basis; similar definition applies to x4, y4
    # z8: pi/8 roration in z basis; similar definition applies to x8, y8
    gate_def = {
        "h": [["z", pi / 4], ["x", pi / 4], ["z", pi / 4]],
        "s": ["z", pi / 4],
        "sdg": ["z", -pi / 4],
        "t": ["z", pi / 8],
        "tdg": ["z", -pi / 8],
        "cx": [["z", pi / 2], ["x", pi / 2]],
        "z4": ["z", pi / 4],
        "z4-": ["z", -pi / 4],
        "x4": ["x", pi / 4],
        "x4-": ["x", -pi / 4],
        "z8": ["z", pi / 8],
        "z8-": ["z", -pi / 8],
        "x": ["x", pi / 2],
        "z": ["z", pi / 2],
        "y": ["y", pi / 2],
    }
    rotation_gates = [
        "rz",
        "ry",
        "rx",
    ]  # We do not process rotation gates. Throw an exception if encounters one.

    def __init__(
        self,
        circuit: list = [],
        num_qubits: int = 0,
        make_new_cpp=False,
        pytest_mode=False,
    ):
        """Constructor, takes the circuit list.

        This File also calls Makefile for the C++ functions in case they aren't present.

        Args:
            circuit (list, optional): A list[tuple(Str, int, list[int])] list representing the circuits
                in a [(gate_name, number_of_qubits_involved_in_gate, [qubit_IDs])]. Defaults to [].
            num_qubits (int, optional): Total number of qubits used for this circuit. Defaults to 0.
            make_new_cpp (bool, optional): Force the Makefile to run again to create .o and .so files
                for cpp again. Defaults to False.
            python_test (bool, optional): Keyword used not to build c++ files in case intended to only
                test python functions.
        """
        logger.info(f"num_qubits={num_qubits}")
        logger.info(f"make_new_cpp={make_new_cpp}")
        logger.info(f"pytest_mode={pytest_mode}")

        self.circuit = circuit
        self.num_qubits = num_qubits

        if num_qubits <= 0 and len(circuit) != 0:
            error_msg = "Non empty circuit must use at least one qubit. Please indicate \
                the correct number of qubits for circuit."
            logger.error(error_msg)
            raise TypeError(error_msg)

        self.runLysCompiler = None

        list_of_required_cpp_files = ["src/cpp_compiler/runLysCompiler.so"]

        if not pytest_mode:
            # Change the number of qubits in the cpp file
            if (
                self.update_cpp_num_qubits()
                or make_new_cpp is True
                or not all(
                    [
                        os.path.isfile(required_file_path)
                        for required_file_path in list_of_required_cpp_files
                    ]
                )
            ):
                logger.info(
                    "Cpp compiled for different number of qubits OR missing required files. Creating the .o and .so files now using the Makefile"
                )

                python_version = " PYTHON_VERSION=3.8"
                make_process = subprocess.Popen(
                    ["make", python_version],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd="src/cpp_compiler/",
                )
                exit_code = make_process.returncode
                poll = make_process.poll()

                logger.info("This process might take a while. Please wait.")
                while poll == None:
                    sleep(1)
                    poll = make_process.poll()

                exit_code = make_process.returncode
                if exit_code:
                    logger.error(
                        "There is an issue with the make process. As a hint, please try to run the make file in the directory using shell commands."
                    )
                else:
                    logger.info("Make complete.")
            else:
                logger.info("Cpp compiled for matches the current number of qubits.")

            # After the .o and .so files are confirmed, import them and add them as
            # an object of this compiler wrapper.
            from ..cpp_compiler import runLysCompiler

            self.runLysCompiler = runLysCompiler
        else:
            logger.info("In pytest mode, do not require to build the cpp functions.")

        logger.info("- Return")

    def update_cpp_num_qubits(self):
        """TODO: docstrings

        Returns:
            _type_: _description_
        """
        logger.info("()")
        logger.info(
            "function 'update_cpp_num_qubits' is being called with num qubits of "
            + str(self.num_qubits)
        )

        # Read in the cpp file
        with open("src/cpp_compiler/Operation.hpp", "r") as f:
            filedata = f.readlines()
        for line_index in range(0, len(filedata)):
            if "numQubits" in filedata[line_index]:
                # Extract the current number of qubits in the file.
                current_num_qubits = int(
                    filedata[line_index].split("numQubits")[1].strip()
                )
                # Update is not required if the number of qubits are the same.
                if current_num_qubits == self.num_qubits:
                    logger.info(f"num_qubits_updated={False}")
                    return False

                filedata[line_index] = (
                    "#define numQubits " + str(self.num_qubits) + "\n"
                )
                break
        # Write the cpp file out again
        with open("src/cpp_compiler/Operation.hpp", "w") as f:
            f.writelines(filedata)

        logger.info(f"num_qubits_updated={True}")
        logger.info("- Return")
        return True

    def _translate_to_rotation(self, circuit: list) -> list:
        """This method takes in a circuit composed of Clifford gates and translate the circuit
        into using only pi/8 and pi/4 rotation gates.

        Reference: arXiv:1808.02892

        Raises:
            ValueError: Non Decomposed rotation gates.
            ValueError: Undefined gate

        Returns:
            list: list[tuple(list[[Str, int]], [int])] representing the [[rotation_basis, angle], [qubitID(s)]] per gate
                    Example: [([['x', 0.7853981633974483], ['x', 0.7853981633974483]], [0]), ([['z', 3.141592653589793], ['x', 3.141592653589793]], [1, 0])]
        """
        logger.info("()")

        translated = []

        for each_gate in circuit:
            gate_name = each_gate[0]
            if gate_name == "measure":
                translated.append(
                    (each_gate[0], each_gate[1])
                )  # if gate is measure, directly add to the translated list
            elif gate_name in self.gate_def.keys():
                # Apply the translation rules defined in gate_def and replace the original gates with the translation
                translated.append((self.gate_def[gate_name], each_gate[1]))
            elif gate_name in self.rotation_gates:
                error_msg = "Input list has rotation gates. Decompose the input before proceeding"
                logger.error(error_msg)
                raise ValueError(error_msg)
            else:
                error_msg = "Add '" + str(gate_name) + "' gate to the definition"
                logger.error(error_msg)
                raise ValueError(error_msg)

        logger.info("- Return")
        return translated

    def _decompose_cnot(self, circuit: list) -> list:
        """Decompose the cnot gate from (z,x) to tensor(z4,x4)*(Z4-)*(X4-).

        Raises:
            ValueError: CNOT gates are defined as (x,z).

        Returns:
            list: list[tuple(list[[Str, int]], [int])] representing the [[rotation_basis, angle], [qubitID(s)]] per gate
                  where the cnot gates are decomposed.
        """
        logger.info("()")

        gates_to_decompose = self._translate_to_rotation(circuit)
        cnot = self.gate_def["cx"]
        cnot_reverse_def = [cnot[1], cnot[0]]
        decomposed_gates = []
        for gate in gates_to_decompose:
            if gate[0] == cnot:
                tensor_zx = ([self.gate_def["z4"], self.gate_def["x4"]], gate[1])
                gate_on_1st_q = (self.gate_def["z4-"], [gate[1][0]])
                gate_on_2nd_q = (self.gate_def["x4-"], [gate[1][1]])
                decomposed_gates.extend([tensor_zx, gate_on_1st_q, gate_on_2nd_q])
            elif gate[0] == cnot_reverse_def:
                error_msg = (
                    "CNOT gate defined as (x,z). Unaccounted for definition. Exiting."
                )
                logger.error(error_msg)
                raise ValueError(error_msg)
            else:
                decomposed_gates.append(gate)

        logger.info("- Return")
        return decomposed_gates

    @staticmethod
    def decode_angle(angle: int) -> float:
        """Turns the encoded signed int representing the angle with phase back into the actual multiples of pi

        Arguments:
            angle {int} -- Angle in encoded format.

        Raises:
            ValueError: Unknown encoded angle.

        Returns:
            float -- Angle mapped to this encoding format.
        """
        logger.trace(f"angle={angle}")

        angle_decoding = {0: pi / 2, 2: pi / 4, -2: -pi / 4, 1: pi / 8, -1: -pi / 8}

        if angle not in angle_decoding.keys():
            error_msg = "Unknown encoded angle"
            logger.error(error_msg)
            raise ValueError(error_msg)
        else:
            logger.trace(f"angle_decoding[angle]={angle_decoding[angle]}")
            logger.trace("- Return")
            return angle_decoding[angle]

    @staticmethod
    def encode_angle(angle: float) -> int:
        """Turns a float number representing the rotation angle with phase into a signed intger.

        Arguments:
            angle {float} -- Angle to be encoded.

        Raises:
            ValueError: Unknown Angle.

        Returns:
            int -- Angle in encoded format.
        """
        logger.trace(f"angle={angle}")

        angle_encoding = {
            round(-pi / 2, 8): 0,
            round(pi / 2, 8): 0,
            round(pi / 4, 8): 2,
            round(-pi / 4, 8): -2,
            round(pi / 8, 8): 1,
            round(-pi / 8, 8): -1,
        }

        if round(angle, 8) not in angle_encoding.keys():
            error_msg = "Unknown angle"
            logger.error(error_msg)
            raise ValueError(error_msg)
        else:
            logger.trace(
                f"angle_encoding[round(angle, 8)]={angle_encoding[round(angle, 8)]}"
            )
            logger.trace("- Return")
            return angle_encoding[round(angle, 8)]

    def _transform_to_operation_objects(
        self, num_qubits: int, decomposed_gates: list
    ) -> list:
        """Transforms the input data into a list.
        Args:
            decomposed_gates (list): List of gates where the input gates have been translated to pi/2, pi/4 or pi/8 rotations.
            num_qubits (int)       : Number of unique qubits in the entire circuit.
        Returns:
            list:  A list that represents the layers of the circuit.
                   Each element is one Rotation or Measure object.
                   Example:
                   [
                       Rotation(),
                       Rotation(),
                       ...
                   ]
        """
        logger.info(f"num_qubits={num_qubits}")

        gates = []
        for gate in decomposed_gates:
            if gate[0] == "measure":
                gates.append(
                    Measure(num_qubits, True, ["z"], gate[1])
                )  # Default to measure in Z

            else:
                if len(gate[1]) > 1:  # Case of ZX rotation (part of pre-decomposed CX)
                    basis = [gate[0][i][0] for i in range(len(gate[0]))]
                    qubit = gate[1]
                    angle = gate[0][0][1]
                    angled_encoded = self.encode_angle(angle)
                    gates.append(Rotation(num_qubits, angled_encoded, basis, qubit))

                elif len(gate[1]) == 1:  # Case of H, S
                    if type(gate[0][0]) is list:
                        for value in gate[0]:
                            basis = [value[0]]
                            qubit = gate[1]
                            angle = value[1]
                            angled_encoded = self.encode_angle(angle)
                            gates.append(
                                Rotation(num_qubits, angled_encoded, basis, qubit)
                            )
                        continue
                    else:  # Other single qubit gate
                        basis = [gate[0][0]]
                        qubit = gate[1]
                        angled_encoded = self.encode_angle(gate[0][1])
                        gates.append(Rotation(num_qubits, angled_encoded, basis, qubit))

        logger.info("- Return")
        return gates

    def __add_measure(self, num_qubits: int, pauli_operators: list) -> list:
        """Add final qubit measurements if they are missing in the circuit.

        Args:
            num_qubits (int): number of qubits in the circuit
            pauli_operators (list): circuit in rotation list format

        Returns:
            list: updated circuit in rotation list format
        """
        logger.info("_add_measure()")

        # Check if the last elements are measures
        for i in range(-num_qubits, 0):
            if not isinstance(pauli_operators[i], Measure):
                add_measures = True
                break

        if add_measures:
            for qubit in range(num_qubits):
                pauli_operators.append(
                    Measure(num_qubits, True, ["z"], [qubit])
                )  # Default to measure in Z

        logger.info("- Return")
        return pauli_operators

    def __basis_conversion_core(self, circuit: list) -> list:
        """TODO: docstrings

        Args:
            circuit (list): _description_

        Returns:
            list: _description_
        """
        logger.info("()")

        decomposed_Gates = self._decompose_cnot(circuit)
        pauli_operators = self._transform_to_operation_objects(
            self.num_qubits, decomposed_Gates
        )
        pauli_operators = self.__add_measure(self.num_qubits, pauli_operators)

        logger.info("- Return")
        return pauli_operators

    def basis_conversion(self, language: str) -> list:
        """Creates a rotation list version of the circuit.

        Returns:
            list: Returns a list of the converted Pauli Operators
        """
        logger.info(f"language={language}")

        if language == "qasm":
            return self.__basis_conversion_core(self.circuit)
        elif language == "projectq":
            pauli_operators_list = []
            for circuit_section in self.circuit:
                if len(circuit_section) == 0:
                    continue
                pauli_operators = self.__basis_conversion_core(circuit_section)
                pauli_operators_list.append(pauli_operators)

            logger.info("()")
            logger.info("- Return")
            return pauli_operators_list
        else:
            error_msg = f"{language} is not supported."
            logger.error(error_msg)
            raise Exception(error_msg)

    def transform_to_python_rotation(self, transpiled_circuit):
        """Create a Pythonic copy of a Boost-C++ Rotation circuit.

        Args:
            encoded_gates (runLysCompiler.RotVec): C++ Rotation vector object create by Boost
                in runLysCompiler.

        Returns:
            list: A list of Python-Rotation objects representing a circuit.
        """
        logger.trace("()")

        python_transpiled_circuit = []
        for gate in transpiled_circuit:
            python_gate = Rotation(0, 0, [], [])
            python_gate.n = self.num_qubits
            python_gate.angle = gate.angle

            gate_bitset_string_tuple = self.runLysCompiler.return_rotation_basis_string(
                gate
            )
            python_gate.x = int(gate_bitset_string_tuple[0], 2)
            python_gate.z = int(gate_bitset_string_tuple[1], 2)

            python_transpiled_circuit.append(python_gate)

        logger.trace("- Return")
        return python_transpiled_circuit

    def transform_to_python_measure(self, transpiled_measure):
        """Create a Pythonic copy of a Boost-C++ Measure circuit.

        Args:
            transpiled_measure (runLysCompiler.MeaVec): C++ Measure vector object create by Boost
                in runLysCompiler.

        Returns:
            list: A list of Python-Measure objects representing a circuit.
        """
        logger.trace("()")

        python_transpiled_circuit = []
        for gate in transpiled_measure:
            python_gate = Measure(0, 0, [], [])
            python_gate.n = self.num_qubits
            python_gate.phase = gate.phase

            gate_bitset_string_tuple = self.runLysCompiler.return_measure_basis_string(
                gate
            )

            python_gate.x = int(gate_bitset_string_tuple[0], 2)
            python_gate.z = int(gate_bitset_string_tuple[1], 2)

            python_transpiled_circuit.append(python_gate)

        logger.trace("- Return")
        return python_transpiled_circuit

    # def _optimize_rotation_timed_cpp_compiler(self) -> list:
    #     overall_start_time = time.time()

    #     encode_start_time = time.time()
    #     encoded_gates = self._encode()
    #     encode_end_time = time.time()
    #     encode_time = encode_end_time - encode_start_time

    #     cpp_encoded_gates = self.transform_to_cpp_circuit(encoded_gates)
    #     encoded_num_gates = len(cpp_encoded_gates)

    #     compiler_results = self.runLysCompiler.run_single_circuit(self.num_qubits, cpp_encoded_gates)

    #     transpiled_circuit = self.transform_to_python_rotation(compiler_results[0])

    #     runtime_dict = compiler_results[1]
    #     runtime_dict["encode"] = encode_time

    #     overall_end_time = time.time()
    #     runtime_dict["overall"] = overall_end_time - overall_start_time

    #     return transpiled_circuit, runtime_dict, encoded_num_gates

    def convert_to_cpp(self, gate_list: list):
        """TODO: docstrings

        Args:
            gate_list (list): _description_

        Returns:
            _type_: _description_
        """
        logger.info("()")

        rotation_cpp = self.runLysCompiler.RotVec()
        measure_cpp = self.runLysCompiler.MeaVec()
        rotation_index = self.runLysCompiler.indexVec()
        measure_index = self.runLysCompiler.indexVec()
        rotation_index_py = []
        measure_index_py = []

        for i, gate in enumerate(gate_list):
            if isinstance(gate, Rotation):
                rotation_cpp.append(
                    self.runLysCompiler.Rotation(
                        gate.angle,
                        bin(gate.x)[2:].zfill(self.num_qubits),
                        bin(gate.z)[2:].zfill(self.num_qubits),
                    )
                )
                rotation_index_py.append(i)

            elif isinstance(gate, Measure):
                measure_cpp.append(
                    self.runLysCompiler.Measure(
                        gate.phase,
                        bin(gate.x)[2:].zfill(self.num_qubits),
                        bin(gate.z)[2:].zfill(self.num_qubits),
                    )
                )
                measure_index_py.append(i)

        rotation_index = self.runLysCompiler.toCppInt(rotation_index_py)
        measure_index = self.runLysCompiler.toCppInt(measure_index_py)

        logger.info("- Return")
        return rotation_cpp, rotation_index, measure_cpp, measure_index

    def optimize_cpp(self, pauli_operators: list, removeNonT: bool, time_out: int):
        """Process the whole circuit

        TODO: docstrings
        """

        logger.info(f"removeNonT={removeNonT}")

        rotation_cpp, rotation_index, measure_cpp, measure_index = self.convert_to_cpp(
            pauli_operators
        )

        if len(measure_cpp) == 0:
            results = self.runLysCompiler.run_lys_default_mea(
                self.num_qubits, rotation_cpp, removeNonT, time_out
            )

        else:
            results = self.runLysCompiler.run_lys_with_mea(
                rotation_cpp, rotation_index, measure_cpp, measure_index, True, time_out
            )

        rotations, rot_index = results[0], results[1]
        measures, mea_index = results[2], results[3]

        transpiled_circuit = self.convert_to_python_obj(
            rotations, measures, rot_index, mea_index
        )

        logger.info("- Return")
        return transpiled_circuit

    def optimize_cpp_section(
        self,
        pauli_operator_list: list,
        removeNonT: bool,
        ancillaBegins: int,
        time_out: int,
    ):
        """The circuit are entered as sections. Will process each section individually

        TODO: docstrings
        """
        logger.info(f"removeNonT={removeNonT}")
        logger.info(f"ancillaBegins={ancillaBegins}")

        # go through each section to create equivalent c++ objects
        rot_vec_vec = self.runLysCompiler.RotVecVec()  # vector of vector of rotations
        rot_ind_vec = (
            self.runLysCompiler.indexVecVec()
        )  # vector of indices for each section of rotatons
        mea_vec_vec = self.runLysCompiler.MeaVecVec()  # vector of vector of measures
        mea_ind_vec = (
            self.runLysCompiler.indexVecVec()
        )  # vector of indices for each section of measures

        for section in pauli_operator_list:
            (
                rotation_cpp,
                rotation_index,
                measure_cpp,
                measure_index,
            ) = self.convert_to_cpp(section)
            rot_vec_vec.append(rotation_cpp)
            rot_ind_vec.append(rotation_index)
            mea_vec_vec.append(measure_cpp)
            mea_ind_vec.append(measure_index)

        # pass over to the c++ compiler
        results = self.runLysCompiler.run_lys_section(
            rot_vec_vec,
            rot_ind_vec,
            mea_vec_vec,
            mea_ind_vec,
            [ancillaBegins],
            removeNonT,
            time_out,
        )

        # Get the compiled result from the c++ compiler
        rotations, rot_index = results[0], results[1]
        measures, mea_index = results[2], results[3]

        # Convert the output from c++ objects into python objects
        transpiled_circuit = self.convert_to_python_obj(
            rotations, measures, rot_index, mea_index
        )

        logger.info("- Return")
        return transpiled_circuit

    def convert_to_python_obj(self, rot_cpp, mea_cpp, rot_ind, mea_ind):
        """TODO: docstrings

        Args:
            rot_cpp (_type_): _description_
            mea_cpp (_type_): _description_
            rot_ind (_type_): _description_
            mea_ind (_type_): _description_

        Returns:
            _type_: _description_
        """
        logger.info("()")

        total = len(rot_ind) + len(mea_ind)
        result = []
        for i in range(total):
            if i in rot_ind:
                j = rot_ind.index(i)
                rotation_py = self.transform_to_python_rotation([rot_cpp[j]])
                result.extend(rotation_py)
            else:
                # this item is a measure
                j = mea_ind.index(i)
                measure_py = self.transform_to_python_measure([mea_cpp[j]])
                result.extend(measure_py)

        logger.info("- Return")
        return result
