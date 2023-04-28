#!/bin/sh

echo "---------------------------- Testing projectq file: projectq_measure_anc_short.txt ----------------------------"
python lys.py -input data/input/test_circuits/projectq_measure_anc_short.txt -language projectq -recompile True
echo "\n"
echo "---------------------------- Testing projectq file: projectq_measure_anc.txt ----------------------------"
python lys.py -input data/input/test_circuits/projectq_measure_anc.txt -language projectq -recompile True
echo "\n"
echo "---------------------------- Testing qasm file: qasm_test_5_lines.qasm ----------------------------"
python lys.py -input data/input/test_circuits/qasm_test_5_lines.qasm -language qasm -recompile True
echo "\n"
echo "---------------------------- Testing qasm file: qasm_test_500_lines.qasm ----------------------------"
python lys.py -input data/input/test_circuits/qasm_test_500_lines.qasm -language qasm -recompile True
echo "\n"
