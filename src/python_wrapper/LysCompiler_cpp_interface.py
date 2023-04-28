from math import pi
import time
from .Rotation import Rotation
from .Measure import Measure
import os
import subprocess
from time import sleep

class LysCompiler():
    '''A class which compiles the input circuit into a circuit consists of pi/8 rotation gates and measurement
    '''
    # Gate Defintion convention is as the following: [rotation_basis, rotation_angle]
    # z4: pi/4 rotation in z basis; similar definition applies to x4, y4
    # z8: pi/8 roration in z basis; similar definition applies to x8, y8
    gate_def = {
        'h'     : [['z', pi/4],['x', pi/4],['z', pi/4]],
        's'     : ['z', pi/4],
        'sdg'   : ['z', -pi/4],
        't'     : ['z', pi/8],
        'tdg'   : ['z', -pi/8],   
        'cx'    : [['z', pi/2],[ 'x', pi/2]],
        'z4'    : ['z', pi/4],
        'z4-'   : ['z', -pi/4],
        'x4'    : ['x', pi/4],
        'x4-'   : ['x', -pi/4],
        'z8'    : ['z', pi/8],
        'z8-'   : ['z', -pi/8],
        'x'     : ['x', pi/2],
        'z'     : ['z', pi/2],
        'y'     : ['y', pi/2]
    }
    rotation_gates  = ['rz', 'ry', 'rx']    # We do not process rotation gates. Throw an exception if encounters one. 


    def __init__(self, circuit: list = [], num_qubits: int = 0, make_new_cpp = False, pytest_mode = False):
        """Constructor, takes the circuit list.
        
        This File also calls Makefile for the C++ functions in case they aren't present.

        Args:
            circuit (list, optional): A list[tuple(Str, int, list[int])] list represending the circuits
                in a [(gate_name, number_of_qubits_involved_in_gate, [qubit_IDs])]. Defaults to [].
            num_qubits (int, optional): Total number of qubits used for this circuit. Defaults to 0.
            make_new_cpp (bool, optional): Force the Makefile to run again to create .o and .so files 
                for cpp again. Defaults to False.
            python_test (bool, optional): Keyword used not to build c++ files in case intended to only 
                test python functions.
        """

        self.circuit    = circuit
        self.num_qubits = num_qubits

        if num_qubits <= 0 and len(circuit) != 0:
            raise TypeError("Non empty circuit must use at least one qubit. Please indicate the correct number of qubits for circuit.")
            
        # self.runLysCompiler = runLysCompiler
        self.runLysCompiler = None


        list_of_required_cpp_files = ['src/cpp_compiler/runLysCompiler.so']
        # list_of_required_cpp_files = ['src/cpp_compiler/runLysCompiler.o', 
        #                                 'src/cpp_compiler/runLysCompiler.so']

        if not pytest_mode:
            
            # Change the number of qubits in the cpp file
            if self.update_cpp_num_qubits() or make_new_cpp is True or not all([os.path.isfile(required_file_path) for required_file_path in list_of_required_cpp_files]):

                print("Cpp compiled for different number of qubits OR missing required files. Creating the .o and .so files now using the Makefile")

                # python_version = " PYTHON_VERSION=" + str(input("Please enter your Python3 version (Ex: 3.8, 3.6 ...):"))
                python_version = " PYTHON_VERSION=3.8"

                make_process = subprocess.Popen(["make", python_version], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd="src/cpp_compiler/")
                exit_code = make_process.returncode
                poll = make_process.poll()

                print("This process might take a while. Please wait.")
                while poll == None:
                    sleep(1)
                    poll = make_process.poll()
                
                exit_code = make_process.returncode
                if exit_code:
                    print("There is an issue with the make process. As a hint, please try to run the make file in the directory using shell commands.")
                else:
                    print("Make complete.")
            else:
                print("Cpp compiled for matches the current number of qubits.")

            # After the .o and .so files are confirmed, import them and add them as 
            # an object of this compiler wrapper.
            from ..cpp_compiler import runLysCompiler
            self.runLysCompiler = runLysCompiler
        else:
            print("In pytest mode, do not require to build the cpp functions.")
    



    def update_cpp_num_qubits(self):

        print("function 'update_cpp_num_qubits' is being called with num qubits of " + str(self.num_qubits))

        # Read in the cpp file
        with open('src/cpp_compiler/Operation.hpp', 'r') as f:
            filedata = f.readlines()
        for line_index in range(0, len(filedata)):
            if "numQubits" in filedata[line_index]:

                # Extract the current number of qubits in the file.
                current_num_qubits = int(filedata[line_index].split("numQubits")[1].strip())
                # Update is not required if the number of qubits are the same.
                if current_num_qubits == self.num_qubits:
                    # print("...... Same number of qubits. No need to update numQubits")
                    return False

                filedata[line_index] = "#define numQubits " + str(self.num_qubits)  + "\n"
                break
        # Write the cpp file out again
        with open('src/cpp_compiler/Operation.hpp', 'w') as f:
            f.writelines(filedata)
        
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
        translated     = []
        
        for each_gate in circuit:
            gate_name   = each_gate[0]
            if gate_name == 'measure':
                translated.append((each_gate[0], each_gate[1])) # if gate is measure, directly add to the translated list
            elif gate_name in self.gate_def.keys():
                # Apply the translation rules defined in gate_def and replace the original gates with the translation
                translated.append((self.gate_def[gate_name], each_gate[1]))
            elif gate_name in self.rotation_gates:  
                raise ValueError("Input list has rotation gates. Decompose the input before proceeding")
            else:
                raise ValueError("Add '" + str(gate_name) + "' gate to the definition")
        return translated
    

    def _decompose_cnot(self, circuit: list) -> list:
        """Decompose the cnot gate from (z,x) to tensor(z4,x4)*(Z4-)*(X4-).

        Raises:
            ValueError: CNOT gates are defined as (x,z).

        Returns:
            list: list[tuple(list[[Str, int]], [int])] representing the [[rotation_basis, angle], [qubitID(s)]] per gate
                  where the cnot gates are decomposed.
        """
        gates_to_decompose  = self._translate_to_rotation(circuit)
        cnot                = self.gate_def['cx']
        cnot_reverse_def    = [cnot[1],cnot[0]]
        decomposed_gates    = []
        for gate in gates_to_decompose:
            if gate[0] == cnot :
                tensor_zx       = ([self.gate_def['z4'], self.gate_def['x4']], gate[1])
                gate_on_1st_q   = (self.gate_def['z4-'], [gate[1][0]]) 
                gate_on_2nd_q   = (self.gate_def['x4-'], [gate[1][1]]) 
                decomposed_gates.extend([tensor_zx,gate_on_1st_q,gate_on_2nd_q])
            elif gate[0] == cnot_reverse_def: 
                raise ValueError("CNOT gate defined as (x,z). Unaccounted for definition. Exiting.")  
            else:
                decomposed_gates.append(gate)
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
        angle_decoding = {
            0 : pi/2 ,
            2 : pi/4 ,
            -2: -pi/4, 
            1 : pi/8 ,
            -1: -pi/8
        }

        if angle not in angle_decoding.keys():
            raise ValueError("Unknown encoded angle")
        else:
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
        angle_encoding = {
            round(-pi/2,8):  0,
            round(pi/2,8) :  0,
            round(pi/4,8) :  2,
            round(-pi/4,8): -2, 
            round(pi/8,8) :  1,
            round(-pi/8,8): -1
        }

        if round(angle,8) not in angle_encoding.keys():
            raise ValueError("Unknown angle")
        else:
            return angle_encoding[round(angle,8)]
             
    def _transform_to_operation_objects(self, num_qubits: int, decomposed_gates: list) -> list:
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
        # num_qubits      = num_qubits
        rotations    = []
        measurements = []
        gates = []
        for gate in decomposed_gates:
            if gate[0] == 'measure':
                gates.append(Measure(num_qubits, True, ['z'], gate[1]))  # Default to measure in Z

            else:
                if len(gate[1]) > 1:          # Case of ZX rotation (part of pre-decomposed CX)
                    basis = [gate[0][i][0] for i in range(len(gate[0]))]
                    qubit = gate[1]
                    angle = gate[0][0][1]
                    angled_encoded = self.encode_angle(angle)
                    gates.append(Rotation(num_qubits, angled_encoded, basis, qubit))

                elif len(gate[1]) == 1:     # Case of H, S
                    if (type(gate[0][0]) is list):
                        for value in gate[0]:
                            basis = [value[0]]
                            qubit = gate[1]
                            angle = value[1]
                            angled_encoded = self.encode_angle(angle)
                            gates.append(Rotation(num_qubits, angled_encoded, basis, qubit))
                        continue
                    else:                   # Other single qubit gate
                        basis = [gate[0][0]]
                        qubit = gate[1]
                        angled_encoded = self.encode_angle(gate[0][1])
                        gates.append(Rotation(num_qubits, angled_encoded, basis, qubit))

        # return rotations, measurements
        return gates

    def _encode(self, circuit: list) -> list:
        """Creates a rotation list version of the circuit.

        Returns:
            list: List object returned by the _transform_to_rotation_objects method.
        """
        decomposed_Gates    = self._decompose_cnot(circuit)
        # rotation, measure   = self._transform_to_operation_objects(self.num_qubits, decomposed_Gates)
        gates   = self._transform_to_operation_objects(self.num_qubits, decomposed_Gates)
        # return rotation, measure
        return gates   
    
    def transform_to_python_rotation(self, compiled_circuit):
        """Create a Pythonic copy of a Boost-C++ Rotation circuit.

        Args:
            encoded_gates (runLysCompiler.RotVec): C++ Rotation vector object create by Boost 
                in runLysCompiler.

        Returns:
            list: A list of Python-Rotation objects representing a circuit.
        """
        python_compiled_circuit = []
        for gate in compiled_circuit:
            python_gate = Rotation(0, 0, [], [])
            python_gate.n = self.num_qubits
            python_gate.angle = gate.angle

            gate_bitset_string_tuple = self.runLysCompiler.return_rotation_basis_string(gate)
            python_gate.x = int(gate_bitset_string_tuple[0], 2)
            python_gate.z = int(gate_bitset_string_tuple[1], 2)

            python_compiled_circuit.append(python_gate)
        return python_compiled_circuit
    
    def transform_to_python_measure(self, compiled_measure):
        """Create a Pythonic copy of a Boost-C++ Measure circuit.

        Args:
            compiled_measure (runLysCompiler.MeaVec): C++ Measure vector object create by Boost 
                in runLysCompiler.

        Returns:
            list: A list of Python-Measure objects representing a circuit.
        """
        python_compiled_circuit = []
        for gate in compiled_measure:
            python_gate = Measure(0, 0, [], [])
            python_gate.n = self.num_qubits
            python_gate.phase = gate.phase

            gate_bitset_string_tuple = self.runLysCompiler.return_measure_basis_string(gate)
            
            python_gate.x = int(gate_bitset_string_tuple[0], 2)
            python_gate.z = int(gate_bitset_string_tuple[1], 2)

            python_compiled_circuit.append(python_gate)
        return python_compiled_circuit

    # def _optimize_rotation_timed_cpp_compiler(self) -> list:
    #     overall_start_time = time.time()

    #     encode_start_time = time.time()
    #     encoded_gates = self._encode()
    #     encode_end_time = time.time()
    #     encode_time = encode_end_time - encode_start_time
        
    #     cpp_encoded_gates = self.transform_to_cpp_circuit(encoded_gates)
    #     encoded_num_gates = len(cpp_encoded_gates)

    #     compiler_results = self.runLysCompiler.run_single_circuit(self.num_qubits, cpp_encoded_gates)

    #     compiled_circuit = self.transform_to_python_rotation(compiler_results[0])
        
    #     runtime_dict = compiler_results[1]
    #     runtime_dict["encode"] = encode_time

    #     overall_end_time = time.time()
    #     runtime_dict["overall"] = overall_end_time - overall_start_time
        
    #     return compiled_circuit, runtime_dict, encoded_num_gates

    def convert_to_cpp(self, gate_list:list):
        rotation_cpp  = self.runLysCompiler.RotVec()
        measure_cpp   = self.runLysCompiler.MeaVec()
        rotaion_index = self.runLysCompiler.indexVec()
        measure_index = self.runLysCompiler.indexVec()
        rotaion_index_py = []
        measure_index_py = []

        for i, gate in enumerate(gate_list):          
            if isinstance(gate, Rotation):
                rotation_cpp.append(self.runLysCompiler.Rotation(gate.angle, bin(gate.x)[2:].zfill(self.num_qubits), bin(gate.z)[2:].zfill(self.num_qubits)))
                rotaion_index_py.append(i)

            elif isinstance(gate, Measure):
                measure_cpp.append(self.runLysCompiler.Measure(gate.phase, bin(gate.x)[2:].zfill(self.num_qubits), bin(gate.z)[2:].zfill(self.num_qubits)))
                measure_index_py.append(i)
   
        rotaion_index = self.runLysCompiler.toCppInt(rotaion_index_py)
        measure_index = self.runLysCompiler.toCppInt(measure_index_py)

        return rotation_cpp, rotaion_index, measure_cpp, measure_index


    def optimize_cpp(self, circuit: list, combine):
        '''Process the whole circuit'''
       
        gates = self._encode(circuit)
        rotation_cpp, rotaion_index, measure_cpp, measure_index = self.convert_to_cpp(gates)

        if (len(measure_cpp) == 0):
            # print("No meansurement in this circuit. Use default measurement")
            results = self.runLysCompiler.run_lys_default_mea(self.num_qubits, rotation_cpp, combine)

        else:
            # print("Use full circuit with measurement !!!!")
            results = self.runLysCompiler.run_lys_with_mea(rotation_cpp, rotaion_index, measure_cpp, measure_index, True)

        rotations, rot_index = results[0], results[1]
        measures,  mea_index = results[2], results[3]

        compiled_circuit = self.convert_to_python_obj(rotations, measures, rot_index, mea_index)

        return compiled_circuit


    def optimize_cpp_section(self, circuit:list, combine:bool, ancillaBegins:int):
        '''The circuit are entered as sections. Will process each section individually'''
        # pre-process to encode the circuit
        encoded_circuit = []
        for each in circuit:
            if each == []: continue
            encoded_circuit.append(self._encode(each))

        # go through each section to create equivalent c++ objects
        rot_vec_vec = self.runLysCompiler.RotVecVec()   # vector of vector of rotations
        rot_ind_vec = self.runLysCompiler.indexVecVec() # vector of indices for each section of rotatons
        mea_vec_vec = self.runLysCompiler.MeaVecVec()   # vector of vector of measures
        mea_ind_vec = self.runLysCompiler.indexVecVec() # vector of indices for each section of measures

        for section in encoded_circuit:
            rotation_cpp, rotaion_index, measure_cpp, measure_index = self.convert_to_cpp(section)
            rot_vec_vec.append(rotation_cpp)
            rot_ind_vec.append(rotaion_index)
            mea_vec_vec.append(measure_cpp)
            mea_ind_vec.append(measure_index)

        # pass over to the c++ compiler
        results = self.runLysCompiler.run_lys_section(rot_vec_vec, rot_ind_vec, mea_vec_vec, mea_ind_vec, [ancillaBegins], combine)

        # Get the compiled result from the c++ compiler
        rotations, rot_index = results[0], results[1]
        measures,  mea_index = results[2], results[3]

        # Convert the output from c++ objects into python objects
        compiled_circuit = self.convert_to_python_obj(rotations, measures, rot_index, mea_index)

        return compiled_circuit

    def convert_to_python_obj(self, rot_cpp, mea_cpp, rot_ind, mea_ind):
        total  = len(rot_ind) + len(mea_ind)
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
        return result

    def run_no_layer(self, language:str, combine:bool, ancillaBegins = 0):
        # the gates are not put into layers
        compiledGate = []

        if language == 'qasm':
            compiledGate = self.optimize_cpp(self.circuit, combine)
            
        elif language == 'projectq':
            compiledGate = self.optimize_cpp_section(self.circuit, combine, ancillaBegins)

        return compiledGate




