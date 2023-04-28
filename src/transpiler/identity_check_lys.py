from src.python_wrapper.LysCompiler_cpp_interface import LysCompiler
from src.python_wrapper.Measure     import Measure
from math import pi
from utils.parse import ParseQasm 

from copy import deepcopy
import sys, ray
from ray import logging

func            = sys.argv[1]   # which func to run
lines_of_code   = sys.argv[2]   # which func to run
measurement     = sys.argv[3]   # if 'Y', invoke the combine measurement methods

ifname_path     = "data/input/data_stats_test_folder/qasm_test_50_lines.qasm"
parse_command   = ParseQasm(ifname_path)
inst            = parse_command.instructions
num_qubits      = parse_command.num_qubits
data            = inst[:1000]

gates           = LysCompiler(data, num_qubits)
forward         = gates._encode()
inverse         = []
circuit         = deepcopy(forward)
for each in reversed(forward):
    if each.angle != 0:
        each.angle = -1 * each.angle
    inverse.append(each)
circuit         = circuit + inverse


if measurement != 'Y':
    optimized_rotation   = gates._optimize_rotation_identity_check(circuit)
    if len(optimized_rotation) == 0:
        print("..."+ func+ ' ' + "passed the identity check without combining measure"+ "........................................ [PASSED]")
    else:
        print("..."+ func+ ' ' + "failed the identity check without combining measure"+ "........................................ [FAILED]")
        
else:
    optimized_rotation   = gates.run_compiler(False,True)
    if len(optimized_rotation) == num_qubits:
        for each in optimized_rotation:
            if (each.is_identity()): continue
            else:
                print("   FAIL! -> "+ func+ ' ' + "failed the identity check with combining measure")
                break
        print("..."+ func+ ' ' + "passed the identity check with combining measure"+ "........................................ [PASSED]")
    else:
        print("..."+ func+ ' ' + "failed the identity check with combining measure"+ "........................................ [FAILED]")




