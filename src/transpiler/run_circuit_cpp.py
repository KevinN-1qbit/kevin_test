from src.python_wrapper.LysCompiler_cpp_interface import LysCompiler
from math import pi
from utils.parse import ParseQasm 
import matplotlib.pyplot as plt
from os import listdir
from os.path import isfile, join
import json
import matplotlib.style as style
import os

style.use('seaborn-poster') #sets the size of the charts
style.use('ggplot')

def run_optimizations_track_time(compiler, ifname_path):
    parse_command   = ParseQasm(ifname_path)
    instructions    = parse_command.instructions
    inst            = instructions    #input to the Tgate() class
    num_qubits      = parse_command.num_qubits
    
    data = inst
    compiler = LysCompiler(data, num_qubits)
    compiled_circuit, runtime_dict, encoded_num_gates = compiler._optimize_rotation_timed_cpp_compiler()
    print("Lenght of compiled circuit: ", len(compiled_circuit))
    return runtime_dict, encoded_num_gates

def create_runtime_plot_data(num_lines_runtime_dict):

    timed_functions = list(list(num_lines_runtime_dict.values())[0].keys())
    num_circuits_lines = list(num_lines_runtime_dict.keys())
    num_circuits_lines = [int(lines) for lines in num_circuits_lines]
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
    
    save_json_file = "data/output/py_cpp_runtimes/runtime_dict.json"
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
        ax.set_xlabel('Number of Gates', fontsize=20)
        ax.set_ylabel('Runtime (sec log-scale)', fontsize=20)
        ax.set_title(plot_title + str(" (Runtime vs Number of Gates)"))
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
        save_plot_file = "data/output/py_cpp_runtimes/" + plot_title + ".png"
        plt.savefig(save_plot_file)
        fig.clf()

if __name__== '__main__':
    runtime_test_qasm_files = [str("data/input/data_stats_test_folder/" + str(f)) for f in listdir("data/input/data_stats_test_folder/") if isfile(join("data/input/data_stats_test_folder/", f))]

    num_lines_runtime_dict = {}

    compiler = LysCompiler(make_new_cpp = False)

    for qasm_file in runtime_test_qasm_files:
        number_of_lines = int(qasm_file.split(".")[0].split("/")[-1].split("_")[2])

        if (1 < number_of_lines and number_of_lines <= 10):# or (5000 <= number_of_lines and number_of_lines <= 100000):
            print("Started processing file: ", qasm_file)
            runtime_dict, encoded_num_gates = run_optimizations_track_time(compiler, qasm_file)
            print("Done with file: ", qasm_file)
            num_lines_runtime_dict[encoded_num_gates] = runtime_dict
    
    print("Started processing the results ...")
    processed_results = create_runtime_plot_data(num_lines_runtime_dict)
    plot_runtimes(processed_results)
    print("Saving and ploting complete.")
    print("Compiler Run is complete.")




