from src.Pi8Compiler import Pi8Compiler
from src.Pi8Compiler_Multithreaded import Pi8Compiler_Multithreaded
from math import pi
from utils.ParserQasm import ParserQasm 

from projectq import MainEngine
from projectq.ops import H, Z, Y, X, CNOT, Swap, ControlledGate, Measure, All, QubitOperator, TimeEvolution, C, Command, T, Tdag
from projectq.meta import Loop, Compute, Uncompute, Control, Dagger
from projectq.backends import ResourceCounter, CommandPrinter, Simulator
from projectq.setups import default, decompositions, restrictedgateset
import sys, re, ray, random
from io import StringIO
from ray import logging


def parse(string_input):
    # filepath = "ksat.txt"
    # data = []
    # with open(filepath, 'r') as file:
    #     for line in file:
    #         if line[:2] == '<p': continue
    #         data.append(line.split('|'))
    data    = []
    raw     = string_input.split('\n')
    for line in raw:
        if line[:2] == '<p': continue
        data.append(line.split('|'))


    gate = []
    qs   = []
    for d in data:
        # print(d)
        if d != ['\n'] and d != ['']:
            gate.append(d[0].strip())
            qs.append(d[1].strip())

    paired = list(zip(gate,qs))
        
    qbase       = []
    allocate    = []  #allocate
    deallocate  = []  #deallocate
    for p in paired:
        g       = p[0].lower()
        qubits  = re.findall(r'\b\d+\b', p[1]) #get all numbers from a string
        q       = [int(e) for e in qubits]

        if p[0] == 'CX':
            n = 2
            # g = 'cx'
        elif p[0] == "Allocate":
            n = 1
            allocate.append((g,n,q))
            continue
        elif p[0] == "Deallocate":
            n = 1
            deallocate.append((g,n,q))
            continue
        elif p[0] == 'T^\\dagger':
            n = 1
            g = 'tdg'
        else:
            n = 1
        qbase.append((g,n,q))

    return qbase, allocate, deallocate

def compiler(data_in, compiler_version):
    data, allocate, deallocate = parse(data_in)
    num_qubits                 = len(allocate)

    if compiler_version == "serial":
        gates           = Pi8Compiler(data, num_qubits)   
    if compiler_version == 'multi':
        ray.init(logging_level=logging.ERROR)
        gates           = Pi8Compiler_Multithreaded(data, num_qubits) 

    final_FF        = gates.run_compiler()

    gates = [str(ele) for ele in final_FF]

    with open("compiler_out.txt", 'w+') as out:
        for each in gates:
            if each[:7] == 'Measure': continue
            out.write(each + '\n')

def translate_to_projectq():
    filepath    = 'compiler_out.txt'
    phase       = []
    qubits      = []
    with open(filepath,'r') as file:
        i = 0
        for each in file:
            if each == []: continue
            raw = each.split()
            phase.append(raw[1].strip(":"))
            qubits.append(raw[2])

    num             = len(qubits[0])
    compiler        = Pi8Compiler([],0)
    decoded_phase   = []
    for p in phase:
        decoded_phase.append(compiler.decode_angle(int(p)))

    qubitOP = []

    for q in qubits:
        r = ''
        i = 0
        for l in q:
            if l != 'I':
                op = l + str(i)
                r = r + ' ' + op
            i += 1
        qubitOP.append(r.strip())

    return decoded_phase, qubitOP, num

def ham(data):
    ops  = []
    for ele in data:
        op = QubitOperator(ele)
        ops.append(op)
    return ops

def rotate(eng, phase, hamiltonian, num):
    wavefunction  = eng.allocate_qureg(num)

    # Apply exp(-i * H * t) to the wavefunction:
    for pair in zip(phase, hamiltonian):
        TimeEvolution(time=(-1)*pair[0], hamiltonian=pair[1]) | wavefunction    # (-1) factor needed because input phase already accounts for the negative sign

    All(Measure) | wavefunction

    out = [int(e) for e in wavefunction]

    print('Pi8Compiler result: ', out)
    return out

def circuit_half_adder(eng, mode, num1, num2):
    qureg   = eng.allocate_qureg(4)

    if num1 == 1:
        X | qureg[0]
    if num2 == 1:
        X | qureg[1]

    CNOT | (qureg[0],qureg[2])
    CNOT | (qureg[1],qureg[2])
    C(X,2) | (qureg[0],qureg[1],qureg[3])

    if mode == "s":
        All(Measure) | qureg
        sol = [int(q) for q in qureg]
        print("ProjectQ result:    ", sol)
        return sol
    
    else:
        print(command_printer)
        return None

def circuit_4bitAdder(eng,mode,num1,num2):
    # Reference of circuit: https://arxiv.org/pdf/quant-ph/0206028.pdf

    numA   = eng.allocate_qureg(4)
    numB   = eng.allocate_qureg(4)
    carry  = eng.allocate_qureg(5)

    # Configuring the input 
    num1_bin = bin(num1)[2:]
    num2_bin = bin(num2)[2:]
    for i, value in enumerate(reversed(num1_bin)):
        if value == '1':
            X | numA[i]
    for i, value in enumerate(reversed(num2_bin)):
        if value == '1':
            X | numB[i]

    # Constructing the full adder circuit
    C(X,2) | (numA[0],numB[0],carry[1])
    CNOT | (numA[0], numB[0]) 
    C(X,2) | (carry[0],numB[0],carry[1])

    C(X,2) | (numA[1],numB[1],carry[2])
    CNOT | (numA[1],numB[1])
    C(X,2) | (carry[1],numB[1],carry[2])

    C(X,2) | (numA[2],numB[2],carry[3])
    CNOT | (numA[2],numB[2])
    C(X,2) | (carry[2],numB[2],carry[3])

    C(X,2) | (numA[3],numB[3],carry[4])
    CNOT | (numA[3],numB[3])
    C(X,2) | (carry[3],numB[3],carry[4])

    CNOT | (carry[3], numB[3])
    CNOT | (carry[2], numB[2])
    CNOT | (carry[1], numB[1])
    CNOT | (carry[0], numB[0])

    if mode == "s":
        All(Measure) | numA
        All(Measure) | numB
        All(Measure) | carry

        inputa     = [int(a) for a in numA]
        sol        = [int(q) for q in numB]
        carry_bits = [int(c) for c in carry]
        print("ProjectQ input A:   ", inputa)
        print("ProjectQ result:    ", sol)
        print("ProjectQ carry:     ", carry_bits)
        return inputa + sol + carry_bits
    
    else:
        print(command_printer)
        return None

def oracle_kSAT_satisfy(eng, input_x, anc_out, kSAT_instance):
    '''
    Marks the strings x = (x_1,...,x_n) that satisfy the Boolean formula given by 'kSAT_instance'
    by flipping the 'anc_out' qubit.
    Args:
        eng (MainEngine): Main compiler engine the algorithm is being run on.
        input_x (Qureg) : n-qubit quantum register holding the values of the n Boolean variables x_1,...,x_n \in {0,1}, where 0=FALSE and 1=TRUE
        anc_out (Qubit) : Output qubit to flip in order to mark the solution.
        kSAT_instance : A classical list of m clauses specifying the given kSAT problem instance
    '''
    #infer num_clas, num_lit, and reg_size from clauses_registers
    num_clauses = len(kSAT_instance) # number of clauses
    num_lit     = len(kSAT_instance[0]) # number of literals per clause
    num_variables = len(input_x) # number of different variables in the Boolean formula

    # Now we're ready to compute the oracle output for a given input value 'input_x'
    with Compute(eng):

        anc_clauses = eng.allocate_qureg(num_clauses)
        anc_lit  =  eng.allocate_qureg(num_lit)

        for i in range(num_clauses):
            # For each clause 'i' in the range of the number of all clauses,
            # we check if that clause is satisfied or not satisfied.
            # Checking if a clause is satisfied is achieved by checking if AT LEAST ONE
            # of the involved variables yields the value 'TRUE'; this in turn is the case
            # if the variable has the value '1' while it is not negated or it has the
            # value '0' but the negation of it is to be taken.
            # For each clause 'i', we record the result by writing a '1' into
            # the ancilla qubit 'anc_clauses[i] if that clause is NOT satisfied.
            # Finally, the complete k-SAT instance will be satisfied if and only if
            # anc_clauses[i]=0 for all i. That is how this oracle is constructed.

            for j in range(num_lit):
                if kSAT_instance[i][j] % 2 == 0: # this corresponds to the case of 'no negation'
                    CNOT | (input_x[int(kSAT_instance[i][j]/2)],anc_lit[j])
                else:  # this corresponds to the case of 'negation' of the variable is to be taken
                    X | input_x[int(kSAT_instance[i][j]/2)]
                    CNOT | (input_x[int(kSAT_instance[i][j]/2)],anc_lit[j])
                    X | input_x[int(kSAT_instance[i][j]/2)]


            # The clause 'i' is not satisfied iff all qubits in the list 'anc_lit' have value '0';
            # Conditioned on all the qubits in the list 'anc_lit' being '0' we flip the qubit anc_clauses[i];
            # Thus, the result "anc_clauses[i] = 1" means that the corresponding clause 'i' is NOT satisfied.
            All(X) | anc_lit
            with Control(eng, anc_lit):
                X | anc_clauses[i]
            All(X) | anc_lit

            # Now we reverse the computation of the result of checking the clause 'i':
            for j in range(num_lit):
                if kSAT_instance[i][j] % 2 == 0: # this corresponds to the case of 'no negation'
                    CNOT | (input_x[int(kSAT_instance[i][j]/2)],anc_lit[j])
                else:  # this corresponds to the case of 'negation' of the variable is to be taken
                    X | input_x[int(kSAT_instance[i][j]/2)]
                    CNOT | (input_x[int(kSAT_instance[i][j]/2)],anc_lit[j])
                    X | input_x[int(kSAT_instance[i][j]/2)]

    # Finally, the k-SAT instance is satisfied if and only if anc_reg_Ac[i]=0 for all i; since all clauses must be satisfied.
    # Hence, conditioned on all qubits in the register 'anc_clauses' having value '0', we flip the 'anc_out' qubit.
    All(X) | anc_clauses
    with Control(eng, anc_clauses):
        X | anc_out
    All(X) | anc_clauses
    Uncompute(eng)

def oracle_kSAT_nonsatisfy(eng, input_x, anc_out, kSAT_instance):
    '''
    Marks the strings x = (x_1,...,x_n) that satisfy the Boolean formula given by 'instance_3SAT'
    by flipping the 'anc_out' qubit,
    Args:
        eng (MainEngine): Main compiler engine the algorithm is being run on.
        input_x (Qureg) : n-qubit quantum register holding the values of the n Boolean variables x_1,...,x_n \in {0,1}, where 0=FALSE and 1=TRUE
        anc_out (Qubit) : Output qubit to flip in order to mark the solution.
        kSAT_instance : A classical list of m clauses specifying the given kSAT problem instance
    '''

    #infer num_clas, num_lit, and reg_size from clauses_registers
    num_clauses = len(kSAT_instance) # number of clauses
    num_lit     = len(kSAT_instance[0]) # number of literals per clause
    num_variables = len(input_x) # number of different variables in the Boolean formula

    # Now we're ready to compute the oracle output for a given input value 'input_x'
    with Compute(eng):
        log_num_clauses = 1 if (num_clauses==1) else int(math.ceil(math.log(float(num_clauses),2)))
        anc_log_clauses = eng.allocate_qureg(log_num_clauses)


        for i in range(num_clauses):

            # The following 'for loop' takes account whether the variables involved should be negated or not;
            # an even number in the given list of clauses represents a variable without negation, whereas an odd
            # number represents a variable whose negated value needs to be evaluated. If the latter is the case,
            # we apply a NOT gate to the qubit that represent that variable.
            for j in range(num_lit):
                if kSAT_instance[i][j] % 2 == 0: # this corresponds to the case of 'no negation'
                    pass
                else:
                    X | input_x[int(kSAT_instance[i][j]/2)]

            # The following is a multi-fold controlled increment operation;
            # the incerement operation is applied iff all control qubits are '0'
            All(X) |  [input_x[int(kSAT_instance[i][j]/2)] for j in range(num_lit)]
            with Control(eng, [input_x[int(kSAT_instance[i][j]/2)] for j in range(num_lit)]):
                increment(eng, anc_log_clauses)
            All(X) |  [input_x[int(kSAT_instance[i][j]/2)] for j in range(num_lit)]

            # Reversing the application of NOT gates that account for negation of variables (see above)
            for j in range(num_lit):
                if kSAT_instance[i][j] % 2 == 0: # this corresponds to the case of 'no negation'
                    pass
                else:
                    X | input_x[int(kSAT_instance[i][j]/2)]

    # The given k-SAT instance will be satisfied by the input_x if and only if anc_log_clauses holds
    # the binary representation of the value '0', i.e. all the wires of 'anc_log_clauses' carry the value '0'.
    All(X) | anc_log_clauses
    with Control(eng, anc_log_clauses):
        X | anc_out
    All(X) | anc_log_clauses

    Uncompute(eng)

def circuit_ksat_oracle(eng,mode,oracle,case):
    if case == '00':
        instance_kSAT = [[0,3],[1,3],[1,2]] # [0,0] solution
    if case == '11':
        instance_kSAT = [[0,3],[0,2],[1,2]] # [1,1] solution

    num           = len(instance_kSAT[0])
    input_reg     = eng.allocate_qureg(num)
    anc           = eng.allocate_qubit()

    if case == '11':
        X | input_reg[0]
        X | input_reg[1]

    if oracle == 'ksat-sat':
        oracle_kSAT_satisfy(eng,input_reg,anc,instance_kSAT)
    if oracle == 'ksat-non':
        oracle_kSAT_nonsatisfy(eng,input_reg,anc,instance_kSAT)

    if mode == "s":
        All(Measure) | input_reg
        Measure | anc
        inreg = [int(i) for i in input_reg]
        sol = [int(anc)]
        print("ProjectQ input_reg: ", inreg)
        print("ProjectQ ancilla:   ", sol)
        return inreg + sol
    else:
        print(command_printer)
        return None


if __name__== '__main__':
    mode   = sys.argv[1]   # which mode to run. 'full' means run through pi8compiler. any other input will only runs the simulation on the original projectq circuit
    compl  = sys.argv[2]   # which compiler to run
    circ   = sys.argv[3]   # which quantum circuit to run. Convention is MSB is on the right

    compiler_engines = restrictedgateset.get_engine_list(one_qubit_gates='any',
                                                         two_qubit_gates=(CNOT,),
                                                         other_gates=())
    resource_counter = ResourceCounter()
    command_printer  = CommandPrinter()
    simulate         = Simulator()

    # First, simulate the original projectq circuit, and print the outcome
    eng_sim      = MainEngine(backend=simulate)
    num1         = 0
    num2         = 0
    case         = '00'
    if circ == 'half':  # use the half adder circuit
        num1 = random.randint(0,1)
        num2 = random.randint(0,1)
        expected_sol = circuit_half_adder(eng_sim,'s', num1, num2)

    if circ == 'full':  # use the full adder circuit
        num1 = random.randint(0,7)
        num2 = random.randint(0,7)
        expected_sol = circuit_4bitAdder(eng_sim,'s', num1, num2)

    if circ == 'ksat-sat':  # use the ksat satisfy oracle 
        case = random.choice(['00','11'])
        expected_sol = circuit_ksat_oracle(eng_sim,'s', circ, case)

    if circ == 'ksat-non':  # use the ksat nonsatisfy oracle
        case = random.choice(['00','11'])
        expected_sol = circuit_ksat_oracle(eng_sim,'s', circ, case)

    # eng_sim.flush()

    if mode == 'all':  # only run the adder simulation if mode is not set to 'all' simulation 
        # Then, get the commands from the above simulation
        eng_cmd         = MainEngine(backend=command_printer, engine_list=compiler_engines)
        # Redirect the stdout to a variable such that we can use the printed commands for further processing
        stdout_ref      = sys.stdout    # store the reference for the stdout, optional. Needed only if we want to direct the stdout back to screen again
        output          = StringIO()    # redirect the stdout to the variable 'output'
        sys.stdout      = output        # redirect the stdout to the variable 'output'

        # Call the function that generates the stdout
        if circ == 'half':
            circuit_half_adder(eng_cmd, 'c', num1, num2)      
        if circ == 'full':
            circuit_4bitAdder(eng_cmd, 'c', num1, num2)
        if circ == 'ksat-sat':
            circuit_ksat_oracle(eng_cmd, 'c', circ, case)
        if circ == 'ksat-non':
            circuit_ksat_oracle(eng_cmd, 'c', circ, case)

        output_string   = output.getvalue() # the stdout is now stored as string in the "output_string" variable, which can be further processed
        sys.stdout      = stdout_ref    # redirect the stdout back to the screen if needed


        # Now, run the saved commands through the pi8compiler
        compiler(output_string, compl)
        # print("---> Done pi8 compilation")
        phase, qubitop, num = translate_to_projectq()
        # print("---> Done translating into ProjectQ")
        ops = ham(qubitop)
        # print("---> Done preparing hamiltonians")
        eng_sim = MainEngine(backend=simulate)
        compiled_sol = rotate(eng_sim, phase, ops, num)

        if expected_sol == compiled_sol:
            print('...'+ compl + ' ' + "passed the simulation check on circuit " + 'Adder'+ "........................................ [PASSED]")
        else:
            print("..."+ compl + ' ' + "failed the simulation check on circuit " + 'Adder'+ "........................................ [FAILED]")



