def translate_to_QBASE(instructions):
	translated_instructions = []
	for command in instructions:
		gate_name = command[0]
		if gate_name == 'I' or gate_name == 'id': #identity gate
			translated_instructions.append(('id', command[1], command[2]))
		elif gate_name == 'T' or gate_name == 't': # T gate
			translated_instructions.append(('t', command[1], command[2]))
		elif gate_name == 'H' or gate_name == 'h': # H gate
			translated_instructions.append(('h', command[1], command[2]))
		elif gate_name == 's' or gate_name == 'Ph': # phase gate
			translated_instructions.append(('s', command[1], command[2]))
		elif gate_name == 'CX' or gate_name == 'cx' or gate_name == 'CNOT': # controlled not gate
			translated_instructions.append(('cx', command[1], command[2]))
		elif 'Ry' in gate_name or 'ry' in gate_name:
			translated_instructions.append(('ry'+gate_name[len('ry'):], command[1], command[2]))
		elif 'Rz' in gate_name or 'rz' in gate_name:
			translated_instructions.append(('rz'+gate_name[len('rz'):], command[1], command[2]))
		elif 'Rx' in gate_name or 'rx' in gate_name:
			translated_instructions.append(('rx'+gate_name[len('rx'):], command[1], command[2]))
		elif gate_name.lower() == 'entangle':
			translated_instructions.append(('entangle', command[1], command[2]))
		elif gate_name == "T^\dagger" or gate_name == 'tdg':
			translated_instructions.append(('tdg', command[1], command[2]))
		elif gate_name == 'sdg' or gate_name == "S^\dagger":
			translated_instructions.append(('sdg', command[1], command[2]))
		elif gate_name.lower() == 'swap':
			translated_instructions.append(('swap', command[1], command[2]))
		elif gate_name == 'X' or gate_name == 'x':
			translated_instructions.append(('x', command[1], command[2]))
		elif gate_name == 'Y' or gate_name == 'y':
			translated_instructions.append(('y', command[1], command[2]))
		elif gate_name == 'Z' or gate_name == 'z':
			translated_instructions.append(('z', command[1], command[2]))
		elif gate_name.lower() == 'measure':
			translated_instructions.append(('measure', command[1], command[2]))
		elif gate_name.lower() == 'allocate':
			translated_instructions.append(('allocate', command[1], command[2]))
		elif gate_name.lower() == 'deallocate':
			translated_instructions.append(('deallocate', command[1], command[2]))
		elif 'u0' in gate_name or 'U0' in gate_name:
			translated_instructions.append(('u0'+gate_name[2:], command[1], command[2]))
		elif 'u1' in gate_name or 'U1' in gate_name:
			translated_instructions.append(('u1'+gate_name[2:], command[1], command[2]))
		elif 'u2' in gate_name or 'U2' in gate_name:
			translated_instructions.append(('u2'+gate_name[2:], command[1], command[2]))
		elif 'u3' in gate_name or 'U3' in gate_name:
			translated_instructions.append(('u3'+gate_name[2:], command[1], command[2]))
		elif 'cy' == gate_name or 'CRy' == gate_name:
			translated_instructions.append(('cy', command[1], command[2]))
		elif 'cz' == gate_name or 'CZ' == gate_name:
			translated_instructions.append(('cz', command[1], command[2]))
		elif 'ch' == gate_name or 'CH' == gate_name:
			translated_instructions.append(('ch', command[1], command[2]))
		elif 'ccx' == gate_name:
			translated_instructions.append(('ccx', command[1], command[2]))
		elif 'crz' in gate_name or 'CRz' in gate_name:
			translated_instructions.append(('crz'+gate_name[3:], command[1], command[2]))
		elif 'cu1' in gate_name:
			translated_instructions.append(('cu1'+gate_name[3:], command[1], command[2]))
		elif 'cu3' in gate_name:
			translated_instructions.append(('cu3'+gate_name[3:], command[1], command[2]))
		elif 'rzz' in gate_name:
			translated_instructions.append(('rzz'+gate_name[3:], command[1], command[2]))
		elif 'cswap' in gate_name:
			translated_instructions.append(('cswap', command[1], command[2]))
		else:
			qbase_gate = gate_name.lower()
			translated_instructions.append((qbase_gate, command[1], command[2]))
	return translated_instructions

def translate_to_ProjectQ(instructions):
	single_qubit_gateset = ['Measure','Allocate','Deallocate','H','X','Y','Z','S','T',"T^\dagger",'SqrtX','Ph','Ry','Rx','Rz','R']
	two_qubit_gateset = ['CR','CX','SWAP','Entangle','CZ', 'CRy', 'Measure']
	instructions_ProjectQ = []
	for cmd in instructions:
		gate = cmd[0]
		if gate.upper() in single_qubit_gateset or gate.upper() in two_qubit_gateset: # for gates like H,X,Y,Z,S,T,SWAP etc
			instructions_ProjectQ.append((gate.upper(), cmd[1], cmd[2]))
		elif gate[0].upper() + gate[1:] in single_qubit_gateset or gate[0].upper() + gate[1:] in two_qubit_gateset: # for gates like Measure, Allocate, Deallocate,T^\dagger,Ph,Ry,Rz,Rx,Entangle, Measure
			instructions_ProjectQ.append((gate[0].upper() + gate[1:], cmd[1], cmd[2]))
		elif '(' in gate and ')' in gate: # for gates like Ry,Rx,Rz,CR,ETC
			gate_no_param = gate.split('(')[0]
			if gate_no_param.upper() in single_qubit_gateset or gate_no_param.upper() in two_qubit_gateset: #for gates like R,CR,
				instructions_ProjectQ.append((gate_no_param.upper()+gate[len(gate_no_param):], cmd[1], cmd[2]))
			elif gate_no_param[0].upper() + gate_no_param[1:] in single_qubit_gateset or gate_no_param[0].upper() + gate_no_param[1:] in two_qubit_gateset: #for gates like Ph,Ry,Rx,Rz
				instructions_ProjectQ.append((gate_no_param[0].upper() + gate_no_param[1:] + gate[len(gate_no_param):], cmd[1],cmd[2]))
		elif gate == 'id':
			instructions_ProjectQ.append(('I',cmd[1],cmd[2]))
		elif gate == 'sqrtx':
			instructions_ProjectQ.append(('SqrtX',cmd[1],cmd[2]))
		elif gate == 'cy':
			instructions_ProjectQ.append(('CRy',cmd[1],cmd[2]))

	return instructions_ProjectQ

def translate_to_Qiskit(instructions):
	'''
	Qiskit uses the same naming convention as QBase so no need to translate
	'''
	return instructions

def translate_to_Qasm(instructions, parser):
	#need the parser to get the gate names
	gates_dict = parser.gate_info_dict
	instructions_Qasm = []
	for cmd in instructions:
		gate = cmd[0]
		gate_name = gate.split('(')[0]
		if gate_name == 'swap':
			instructions_Qasm.append((gate,cmd[1],cmd[2]))
			continue
		for saved_gate in gates_dict:
			if gate_name == saved_gate.lower():
				if '(' in gate and ')' in gate: # if the gate has parameters
					instructions_Qasm.append((saved_gate+gate[len(saved_gate):],cmd[1],cmd[2]))
				else:
					instructions_Qasm.append((saved_gate,cmd[1],cmd[2]))
	return instructions_Qasm
