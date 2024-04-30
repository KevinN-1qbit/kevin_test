export PYTHONPATH=$PWD:$PYTHONPATH

cd src/cpp_compiler
cmake .
make

cd ../../

for i in $(seq 1 1 5)
do
    python3 src/main.py -input data/input/test_circuits/qasm_test_10_lines.qasm -language qasm
    #python3 src/main.py -input data/input/molecule_circuits/sk_mol_HH_recdep_4_dep_4.qasm -language qasm
done

rm -r data/output/