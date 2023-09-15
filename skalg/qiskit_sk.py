
# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2020.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
import math
from qiskit.circuit import QuantumCircuit
from qiskit.synthesis.discrete_basis.generate_basis_approximations import (
    generate_basic_approximations,
)
from qiskit.transpiler.passes.synthesis import SolovayKitaev


# c_approx is a constant that arises from the paper.  This is only a bound, and might be larger in practice
c_approx = 4 * math.sqrt(2)

# the depth for each approximation gate for the approximation gate library.  Note that this value is not actually what's needed for 
# a real computation
library_depth = 16

# epsilon_0 is how good we approximate things in the basic library.  Note that it must be below 1/c_approx^2
# The value below needs to be determined from the library depth
epsilon_0 = 1/64

# A function for converting a given error tolerance into the requisite depth of recurance.  It depends on 
#   the values of epsilon_0 and c_approx
def find_recursion_depth(epsilon):
    # if we have ridiculous error bounds, might mess with logarithms
    if (epsilon > epsilon_0):
        return 0
    
    val_1 = math.log(1 / (epsilon * c_approx * c_approx))
    val_2 = math.log(1 / (epsilon_0 * c_approx * c_approx))
    return math.ceil(math.log(val_1 / val_2)/ math.log(3/2))

# A simple function for loading the qasm file into memory
def load_qasm_file(qasm_filename):
    # Load QASM file
    circuit = QuantumCircuit.from_qasm_file(qasm_filename)
    return circuit

# A placeholder function for actually running the SK algorithm.
def run_sk_on_circuit(circuit, epsilon, basis_gates = None):
    # Create the library for the base case of recursion
    # Note that we should input the basis_gates ourselves here, but for now we're just using a fixed gate set
    # Additionally, we should somehow determine the library depth based on the gate-set, but for now we're just using a magic number
    gate_approx_library = generate_basic_approximations(
        basis_gates=["h", "t", "tdg"], depth=library_depth
    )

    # Instantiate the SK class
    rec_depth = find_recursion_depth(epsilon / circuit.size())

    skd = SolovayKitaev(
        recursion_degree=rec_depth, basic_approximations=gate_approx_library
    )

    # actually run the SK algorithm
    compiled_circuit = skd(circuit)

    # return circuit after running SK
    return compiled_circuit

# Simple function to write output to file
def write_qasm_to_file(circuit, output_filename):
    QuantumCircuit.qasm(circuit, False, filename=output_filename)



def run_sk_pipeline(qasm_input_filename: str, qasm_output_filename: str, error_budget: float, basis_gates=None):
    """Function to run the Solovay-Kitaev algorithm in Qiskit on an input qasm file.  The function opens the
    filename at qasm_input_filename, parses it as a qasm file, then runs the Solovay Kitaev algorithm on the
    parsed file with a total error in approximating the entire circuit bounded by error_budget.  

    Args:
        qasm_input_filename: a string of the name of the input qasm file to run the SK algorithm on
        qasm_output_filename: a string of the name of the file we want to save the output qasm file to
        error_budget: a float larger than 0.0 (and for practical purposes it should also be less than 1.0)
        basis_gates: an optional list of tuples of (name, 2x2 matrix) of universal 2x2 matrices that we want
            to decompose the circuit into


    """
    circuit = load_qasm_file(qasm_input_filename)
    compiled_circuit = run_sk_on_circuit(circuit, error_budget, basis_gates)
    write_qasm_to_file(compiled_circuit, qasm_output_filename)


# usecase
#run_sk_pipeline("test.qasm", "test_post.qasm",.1)
