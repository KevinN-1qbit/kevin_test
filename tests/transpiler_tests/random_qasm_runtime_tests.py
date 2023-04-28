from src.python_wrapper.LysCompiler_cpp_interface import LysCompiler
from math import pi
from utils.parse import ParseQasm 
import matplotlib.pyplot as plt
from os import listdir
from os.path import isfile, join
import json
import matplotlib.style as style
import os
import glob
import random
import sys

style.use('seaborn-poster') #sets the size of the charts
style.use('ggplot')

def create_random_qasm_circuit(number_of_qubits, lines, file_name):
    '''
    A script to generate random qasm code to test Trillium with
    User inputs number of qubits and the number of lines of code they want to generate
    Writes out to data/input/commands_qasm.qasm
    '''
    #num = int(base*factor)
    #rnum = num+1
    qubit_nums=[x for x in range(number_of_qubits)]

    single_qubit_gateset = ['x', 'y', 'z', 'h', 's', 't', 'tdg']
    single_qubit_1param_gateset = ['u1', 'rx', 'ry', 'rz']
    single_qubit_2param_gateset = ['u2']
    single_qubit_3param_gateset = ['u3']
    two_qubit_gateset = ['cx', 'cz', 'cy', 'ch']
    two_qubit_1param_gateset = ['crz', 'cu1']
    two_qubit_3param_gateset = ['cu3']
    # all_single_qubit_gateset = single_qubit_gateset + single_qubit_1param_gateset + single_qubit_2param_gateset + single_qubit_3param_gateset
    all_single_qubit_gateset = single_qubit_gateset
    # all_two_qubit_gateset = two_qubit_gateset + two_qubit_1param_gateset + two_qubit_3param_gateset
    all_two_qubit_gateset = ['cx']

    qubits=['q['+str(i)+']' for i in qubit_nums]
    firstline='include "qelib1.inc";'
    code =[]
    code.append(firstline)


    for i in range(lines):
        get_rand_gate = random.randint(1,2) # either generates 1 or 2 (1 = single qubit gate, 2 = two qubit gate)
        if get_rand_gate == 1:
            gate = random.choice(all_single_qubit_gateset)
            ran = random.sample(qubits,1)
            if gate in single_qubit_gateset:
                code.append(gate + " " + ran[0] + ";")

            elif gate in single_qubit_1param_gateset:
                param = round(random.uniform(0,2), 2) #unsure what these values are supposed to be
                code.append(gate + "(" + str(param) + ") " + ran[0] + ";")

            elif gate in single_qubit_2param_gateset:
                param1 = round(random.uniform(0,2), 2) #unsure what these values are supposed to be
                param2 = round(random.uniform(0,2), 2) #unsure what these values are supposed to be
                code.append(gate + "(" + str(param1) + "," + str(param2) + ") " + ran[0] + ";")

            elif gate in single_qubit_3param_gateset:
                param1 = round(random.uniform(0,2), 2) #unsure what these values are supposed to be
                param2 = round(random.uniform(0,2), 2) #unsure what these values are supposed to be
                param3 = round(random.uniform(0,2), 2) #unsure what these values are supposed to be
                code.append(gate + "(" + str(param1) + "," + str(param2) + "," + str(param3) + ") " + ran[0] + ";")
        else:
            gate = random.choice(all_two_qubit_gateset)
            ran = random.sample(qubits,2)
            while (ran[0] == ran[1]):
                ran = random.sample(qubits,2)

            if gate in two_qubit_gateset:
                code.append(gate + " " + ran[0]+","+ran[1] + ";")
            
            elif gate in two_qubit_1param_gateset:
                param = round(random.uniform(0,2), 2) #unsure what these values are supposed to be
                code.append(gate + "(" + str(param) + ") " + ran[0]+ "," + ran[1] + ";")

            elif gate in two_qubit_3param_gateset:
                param1 = round(random.uniform(0,2), 2) #unsure what these values are supposed to be
                param2 = round(random.uniform(0,2), 2) #unsure what these values are supposed to be
                param3 = round(random.uniform(0,2), 2) #unsure what these values are supposed to be
                code.append(gate + "(" + str(param1) + "," + str(param2) + "," + str(param3) + ") " + ran[0]+ "," + ran[1] + ";")

    file_path = "data/input/random_qasm_runtime_circuits/" + file_name
    with open(file_path,'w+') as outfile:
        for i,j in enumerate(code):
            outfile.write("%s\n" % j)
    
    return file_path


def run_optimizations_track_time(compiler, ifname_path):
    parse_command   = ParseQasm(ifname_path)
    instructions    = parse_command.instructions
    num_qubits      = parse_command.num_qubits
    
    data     = instructions
    compiler = LysCompiler(data, num_qubits)
    compiled_circuit, runtime_dict, encoded_num_gates = compiler._optimize_rotation_timed_cpp_compiler()
    print("Lenght of compiled circuit: ", len(compiled_circuit))
    return runtime_dict, encoded_num_gates

def create_runtime_plot_data(num_lines_runtime_dict):

    timed_functions = list(list(num_lines_runtime_dict.values())[0].keys())
    circuit_info = list(num_lines_runtime_dict.keys())
    num_circuits_lines = [str(info) for info in circuit_info]
    num_circuits_lines.sort()

    processed_results = {}
    for function_name in timed_functions:
        x_list = []
        y_list = []

        for num_lines in num_circuits_lines:
            x_list.append(num_lines)
            y_list.append(num_lines_runtime_dict[num_lines][function_name])
        
        xy_list_pair = [x_list, y_list]
        processed_results[function_name] = xy_list_pair
    
    save_json_file = "data/output/random_qasm_runtimes/runtime_dict.json"
    with open(save_json_file, 'w') as out_file:
        json.dump(processed_results, out_file)
        
    return processed_results

def plot_runtimes(processed_results):

    for plot_title, xy_list_pair in processed_results.items():
        x_list = xy_list_pair[0]
        x_list = [str(x) for x in x_list]
        y_list = xy_list_pair[1]

        bar_locations = list( [num for num in range(0, len(x_list))] )

        width = 0.3
        fig, ax = plt.subplots()
        bars = ax.bar(x_list, y_list, width, color='b')
        ax.set_xlabel('Circuit Info', fontsize=20)
        ax.set_ylabel('Runtime (sec log-scale)', fontsize=20)
        ax.set_title(plot_title)
        ax.set_xticks(bar_locations)
        plt.xticks(rotation=45)
        ax.set_xticklabels(x_list)
        ax.set_yscale('log')
        ax.set_ylim([10**(-5),10**5])

        def autolabel(bars, y_list):
            """
            Attach a text label above each bar displaying its height
            """
            for bar_index in range(0,len(list(bars))):
                bar = list(bars)[bar_index]
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., 1.05 * height,
                        str(y_list[bar_index])[0:5],
                        ha='center', va='bottom', rotation = 75, fontsize = 20)

        autolabel(bars, y_list)
        plt.tight_layout()
        plt.draw()
        save_plot_file = "data/output/random_qasm_runtimes/" + plot_title + ".png"
        plt.savefig(save_plot_file)
        fig.clf()

if __name__== '__main__':
    runtime_test_qasm_files = [str("data/input/data_stats_test_folder/" + str(f)) for f in listdir("data/input/data_stats_test_folder/") if isfile(join("data/input/data_stats_test_folder/", f))]

    num_lines_runtime_dict = {}

    compiler = LysCompiler(make_new_cpp = False)

    list_of_circuit_info = [(5, 50000),(10, 50000),(15, 50000), (20, 50000), (25, 50000)]

    # First we remove the files from the last run
    files = glob.glob('data/input/random_qasm_runtime_circuits/*')
    for f in files:
        os.remove(f)

    for qasm_circuit in list_of_circuit_info:
        
        num_qubits = qasm_circuit[0]
        num_lines = qasm_circuit[1]
        file_name = str(num_qubits) + " qubits " + str(num_lines) + "lines"

        circuit_file_path = create_random_qasm_circuit(num_qubits, num_lines, file_name)

        print("Started processing file: ", file_name)
        runtime_dict, encoded_num_gates = run_optimizations_track_time(compiler, circuit_file_path)
        print("Done with file: ", file_name)
        num_lines_runtime_dict[str(encoded_num_gates) + " " + str(num_qubits)] = runtime_dict
    
    print("Started processing the results ...")
    processed_results = create_runtime_plot_data(num_lines_runtime_dict)
    plot_runtimes(processed_results)
    print("Saving and ploting complete.")
    print("Compiler Run is complete.")




