import os
from os.path import isfile, join
from utils.ParserQasm import ParserQasm

if __name__ == '__main__':
	dir_path = os.path.dirname(os.path.realpath(__file__))
	qasm_dir_path = dir_path + "/data/qasm_files/"
	qasm_files = [f for f in os.listdir(qasm_dir_path) if isfile(join(qasm_dir_path, f))]
	param_gates = ['rx', 'ry', 'rz']
	for fname in qasm_files:
		if (".qasm" not in fname):
			continue
		ifname_path = qasm_dir_path + fname
		ofname_path = dir_path + "/data/qiskit_files/" + fname
		parse_command = ParserQasm(ifname_path)
		instructions_decoded = parse_command.instructions_decoded
		num_qubits = len(parse_command.encoded_names_dict)
		print("Translating "+fname+", Number of qubits "+str(num_qubits))
		qname = instructions_decoded[0][2][0].split("[")[0]

		with open(ofname_path, 'w+') as ofile:
			ofile.write(qname + " = QuantumRegister("+str(num_qubits)+")"+"\n")
			ofile.write("circuit = QuantumCircuit("+qname+")"+"\n\n")
			for line in instructions_decoded:
				gate = line[0]
				if any(p in gate for p in param_gates): 
					qubits = ",".join(str(q) for q in line[2])
					qiskit_cmd = "circuit."+gate.split(')')[0]+","+qubits+")"+"\n"
				else:
					qubits = ",".join(str(q) for q in line[2])
					qiskit_cmd = "circuit."+gate+"("+qubits+")"+"\n"
				ofile.write(qiskit_cmd)
