""" Parsers of programs for quantum computers """

import re
import os.path as osp
import itertools as it

from utils import decompose


class Parse:
    """Base class for parsers of programs for quantum computers

    BASE CLASS should NOT be Instantiated alone!"""

    # This variable holds gates names that are different but are the same gate.
    # Example. CX = CNOT; I = Identity; S = Ph = P
    # pylint: disable=bad-whitespace
    translate_dict = {
        "cnot": "cx",
        "i": "identity",
        "p": "s",
        "ph": "s",
        "t^\\dagger": "tdg",
        "s^\\dagger": "sdg",
    }

    def __init__(self, filepath, epsilon):
        self.filepath = filepath
        self.epsilon = epsilon

    @staticmethod
    def read_in_file(file_path):
        raw = []
        with open(file_path) as f:
            for line in f:
                word = line.strip()
                if word.split() != []:
                    raw.append(word.split())
        return raw

    @staticmethod
    def _get_gate_list_after_approx(gate_list, rz_approx, gate_index_lookup):
        """Modify the original list to add in the decomposed gates...

        ...using the decomposition dictionary rz_approx

        Args:
            gate_list (list): the original list of gates with rz gates
            rz_approx (dict):
                a dictionary containing the rz approximation of the rz gates
                with the original rz gate as keys, the approximated sequence
                as values
            gate_index_lookup (dict):
                a dictionary storing the indices of the rz gates in original
                gate_list using indices as keys, gate as values

        Returns:
            gate_list (list): The same gate_list but with rz gates decomposed
        """

        # Inserting the rz approximations from highest indices to lowest,
        # that way, the subsequence indices won't be affected
        for gate_index in sorted(gate_index_lookup.keys(), reverse=True):
            # Remove original entry
            gate_list.pop(gate_index)

            # This will store the gate approximation
            gate_approx_created = []

            # rz_approx is a dictionary containing the rz approximation of
            # the rz gates
            # Operators are shown in matrix order, not circuit order.
            # This means they are meant to be applied from right to left
            # (hence the [::-1])
            for g in rz_approx[gate_index_lookup[gate_index][0]][::-1]:
                g = g.lower()

                # Ignore new line character and omega scaler
                if "\n" in g or "w" in g:
                    continue

                gate_approx_created.append((g, gate_index_lookup[gate_index][1]))

            # Add new entry
            gate_list[gate_index:gate_index] = gate_approx_created

        return gate_list

    @staticmethod
    def _rz_gates_index_in_original_list(gate_list):
        """Save the indices of rz gates in gate_list and get the unique rz gates
        Args:
            gate_list (list): the original list of gates with rz gates
        Returns:
            gate_index_lookup (dict):
                a dictionary storing the indices of the rz gates in original
                gate_list using indices as keys, gate as values
            unique_rz_gates (list):
                a list containing unique rz gates in gate_list
        """

        # The indices of the rz gates will be the keys for this dictionary
        gate_index_lookup = {}

        # This list will store the unique rz gates
        unique_rz_gates = []

        for gate_index, gate in enumerate(gate_list):
            if "rz" in gate[0]:
                # When we encounter a rz gate,
                #      we use its position in original gate_list as key
                # The gate itself is the value
                gate_index_lookup[gate_index] = gate

                if gate[0] not in unique_rz_gates:
                    unique_rz_gates.append(gate[0])

        return gate_index_lookup, unique_rz_gates

    def perform_rz_decomposition(self, gate_list):
        """Decompose the rz gates
        Args:
            gate_list (list): the original list of gates with rz gates
        Returns:
            gate_list (list): The same gate_list but with rz gates decomposed
        """

        # Pre process the gates
        # i.e. save the indices of rz gates in gate_list and
        #      get the unique rz gates
        gate_index_lookup, unique_rz_gates = self._rz_gates_index_in_original_list(
            gate_list
        )

        if unique_rz_gates:
            # Dictionary will contain the decomposed rz gates
            # i.e. rz(0.1452345):HTHTHTHTHTHT
            #       (just an example, not actual decomposition)
            rz_approx = {}

            for rz_gate in unique_rz_gates:
                # Do the decomposition
                decom = decompose.Decompose(rz_gate, self.epsilon)

                # Save the decomposition in dictionary
                rz_approx[rz_gate] = decom.operators

            # Using the decomposition dictionary rz_approx,
            # modify the original list to add in the decomposed gates
            gate_list = self._get_gate_list_after_approx(
                gate_list, rz_approx, gate_index_lookup
            )

        return gate_list


# noinspection PyPep8Naming
class ParseQasm(Parse):
    """A parser for quantum programs in .qasm format"""

    def __init__(self, filepath, epsilon=1e-10) -> None:
        super().__init__(filepath, epsilon)

        # number of gates in the qasm file, including three qubit gates
        self.gate_count = 0

        # number of gates with all three-qubit gates decomposed into
        # 1 or 2 qubit gates
        self.gate_count_decomp = 0
        self.instructions, self.num_qubits = self.get_gate_list()

    def entire_list(self) -> list:
        """Combine all code, including imported libraries, into one list

        Args:
            None

        Returns:
            whole_name:
                a list containing the contents of all the header files and
                the file given to the Parser
        """

        # turns every line in the file into a list
        qasm_list = self.read_in_file(self.filepath)

        library = []
        unpack_lib = []
        for line in qasm_list:
            # iterate through qasm list and find all header files

            if line[0] == "include":  # if line is a header
                name = line[1].strip(";")
                lib_name = name.replace('"', "", 2)
                path_to_root_dir = osp.dirname(osp.dirname(osp.realpath(__file__)))
                lib_path = f"{path_to_root_dir}/src/transpiler/{lib_name}"

                # gets into the header file and turns it into a list
                lib_list = self.read_in_file(lib_path)

                library.append(lib_list)

        # To unpack the list of library.
        # Only useful when there are multiple "include"s
        for lib in library:
            unpack_lib = unpack_lib + lib

        # returns a list with the contents of the header files and the qasm_list
        whole_file = unpack_lib + qasm_list
        return whole_file

    @staticmethod
    def get_gate(data: list) -> dict:
        """Returns a dict. Key is gate name and Value is a 4-tuple where

        the first element is a list of all the gate parameter,
        the second element is how many qubits are needed in that gate,
        the third element is a list of the qubit names, and
        the last element is a list of the broken down gates used in this gate
        (empty if this gate is a base gate)

        Args:
            data (list):
                a list consists of the strings parsed from
                one line of the input file

        Returns:
            A dict with one key (the gate name (str)) and
            one value (3-tuple described above)

        Examples:
            >>>output = get_gate_name(list)
            >>>print(output)
            {"cx": [[], 2, [], []}
            {"cu1": [[lambda], 2, [a,b], ['u1(lambda/2)', 'a;', 'cx' , 'a,b;',
            'u1(-lambda/2)', 'b;', 'cx', 'a,b;',  'u1(lambda/2)', 'b;']}
        """

        gate = {}

        gate_name = (data[1].split("("))[0]  # gets the name of the gate
        try:  # check if there are any gate parameters
            args = (data[1][data[1].index("(") + 1 : data[1].index(")")]).split(",")
        except ValueError:  # todo Catch the intended exception type here, only
            args = []
        # gets the number of qubits used in the gate
        num_qbit = len(data[2].split(","))
        qubit_names = data[2].split(",")
        try:  # check if theres a decomposed version of the gate
            breakdown = data[data.index("{") + 1 : data.index("}")]
        except BaseException as e:
            # todo Catch the intended exception type here, only
            breakdown = []
        gate[gate_name] = [args, num_qbit, qubit_names, breakdown]
        return gate

    @staticmethod
    def store_gate_info(data, gate_info_dict):
        """Gets the gate and saves parameter values given by the input code

         (used when we have to break down a gate into its simpler form)

        Args:
            data:
                line read in from the input code
                (ex. ['cu1(0.54)', 'q[30],q[29];'])
            gate_info_dict:
                todo Fill this out

        Returns:
            saved_values:
                dict that stores all the parameter values and qubits to their
                assigned values (the qubits are saved as their original names)

                ex. gate is: crz(lambda) a,b
                    user input is: crz(0.91) q[23],q[39];
                    returns: ['crz', {lambda: 0.91}, {a: q[23], b: q[30]}]
        """

        gate_name = data[0]
        gate_description = gate_info_dict.get(gate_name)
        parameter_lst = gate_description[0]
        qubit_lst = gate_description[2]
        parameter_values = {}
        qubit_values = {}

        try:
            assigned_parameters = (
                data[0][data[0].index("(") + 1 : data[0].index(")")]
            ).split(",")
        except BaseException as e:
            # todo Catch the intended exception type here, only
            assigned_parameters = []

        assigned_qubits = data[1:]
        for ind, value in enumerate(assigned_parameters):
            param_name = parameter_lst[ind]
            parameter_values[param_name] = value
        for ind, value in enumerate(assigned_qubits):
            qubit_name = qubit_lst[ind]
            qubit_values[qubit_name] = value
        saved_values = [gate_name, parameter_values, qubit_values]

        return saved_values

    def breakdown_3qubit_gate(
        self,
        gate_info_dict,
        gate,
        saved_values,
        gate_name,
        num_qubits_per_gate,
        qubit_name,
    ) -> None:
        """Looks into the 3-qubit gate definition and breaks it down...

        into a simpler definition. If there is another 3-qubit gate inside that
        definition, it will break that down as well.

        Args:
        gate:
            name of the gate that we need to break down
        saved_values:
            list of containing the gate name, a dict with the saved parameter
            values, a dict with the saved qubit values
        gate_name:
            a list of the names of the gates used in the file
            (ex. ['cu1', 'h', ...])
        num_qubits_per_gate:
            a list of the number of qubits used in the gates
            (ex. [1, 1, 2, ...])
        qubit_name:
            list of the qubits used in the gates in their original names
            (ex. [[q[0]], [q[1]], [q[0], q[1]], ... ]

        Returns:
            N/A
            Modifies gate_name, num_qubits_per_gate and qubit_name
        """

        assigned_parameters = saved_values[1]
        assigned_qubits = saved_values[2]
        gate_info = gate_info_dict.get(gate)
        definition = gate_info[3]  # gets definition of 3-qubit gate
        if definition == []:
            raise Exception(
                "3-qubit gate must be decomposed " "into 1 or 2 qubit gates"
            )

        # the gate name and parameters are in the even indices and
        # the qubits it's acting on are one index after
        is_gate_3qubit = False
        for counter, elem in enumerate(definition):
            cur_gate = elem.split("(")[0]  # gets the name of the current gate
            if counter % 2 == 0:
                # if the current index is the name of the gate with parameters

                gate_info = gate_info_dict.get(cur_gate)
                if gate_info[1] == 3:
                    # if the gate in the definition is also a 3-qubit gate

                    is_gate_3qubit = True
                    self.breakdown_3qubit_gate(
                        gate_info_dict,
                        cur_gate,
                        saved_values,
                        gate_name,
                        num_qubits_per_gate,
                        qubit_name,
                    )

                else:
                    # if its not a 3-qubit gate, then
                    # just append the information normally

                    # if its a normal gate, then increase decomposed gate count
                    self.gate_count_decomp += 1
                    inst_name = elem
                    param_lst = []  # list of all parameters used in this gate
                    for param in assigned_parameters:
                        if param in inst_name:
                            param_lst.append(param)

                    for param in param_lst:
                        # replace all gate parameters with their assigned values

                        while param in inst_name:
                            ind = inst_name.index(param)
                            inst_name = inst_name.replace(param, "", 1)
                            inst_name = (
                                inst_name[0:ind]
                                + str(assigned_parameters.get(param))
                                + inst_name[ind:]
                            )

                    try:
                        # append the gate name with their
                        # parameter values substituted in
                        expression_list = (
                            inst_name[inst_name.index("(") + 1 : inst_name.rindex(")")]
                        ).split(",")
                        simplified_expression_list = []
                        for exp in expression_list:
                            simplified_exp = eval(exp)
                            simplified_expression_list.append(simplified_exp)

                        final_name = cur_gate + "("
                        for count, param in enumerate(simplified_expression_list):
                            if count == len(simplified_expression_list) - 1:
                                final_name += str(param)
                            else:
                                final_name += str(param) + ","
                        final_name += ")"
                        gate_name.append(final_name)
                    except BaseException as e:
                        # todo Catch the intended exception type here, only
                        # append the gate name that has no parameters
                        gate_name.append(inst_name)

                    num_qubit = (gate_info_dict.get(cur_gate))[1]

                    # append the number of qubits used in the gate
                    # to the num_of_qubits list
                    num_qubits_per_gate.append(num_qubit)

            else:  # elem are the qubits used in the gate
                if is_gate_3qubit is True:
                    # if elem is the 3 qubits used in the 3-qubit gate

                    # just set to false since it will be taken care of
                    # when you recursively call the function
                    is_gate_3qubit = False
                    continue
                else:
                    qubits = (elem.replace(";", "")).split(",")
                    qubits_used = []
                    for i in qubits:
                        qubits_used.append(assigned_qubits.get(i))
                    # append which qubits were used in the gate (original name)
                    # to the list
                    qubit_name.append(qubits_used)

    def _process_the_input(self):
        """Processes the given file or instruction list and returns 3 lists

        Args:
        none

        Returns:
        gate_name:
            a list of the names of the gates used in the file
             (ex. ['cu1', 'h', ...])
        num_qubits_per_gate:
            a list of the number of qubits used in the gates
             (ex. [1, 1, 2, ...])
        qubit_name:
            a list of the qubits used in the gates by their
             original names (ex. [[q[0]], [q[1]], [q[0], q[1]], ... ]
        """

        raw_data = self.entire_list()
        gate_name, num_qubits_per_gate, qubit_name = [], [], []
        inside_gate_bracket_flag = 0
        entire_gate_def = []
        gate_info_dict = {}

        for line in raw_data:
            if line[0] == "//":  # if the line is a comment, then disregard it
                continue

            char = line[0].split("(")
            gate = char[0]

            # The inside_gate_bracket_flag is to indicate whether the current
            # line is part of a gate definition. This is to avoid adding the
            # gates used in a gate definition to the gate_set.

            if (line[0] == "gate") or (inside_gate_bracket_flag == 1):
                # if we are still reading in gate definitions
                if line[-1] == "}":
                    # either the gate definition was all in one line or
                    # it's the end of the multi-line gate definition
                    entire_gate_def.extend(line)
                    new_gate = self.get_gate(entire_gate_def)
                    gate_info_dict.update(new_gate)
                    entire_gate_def = []
                    inside_gate_bracket_flag = 0
                    continue

                if line[0] == "gate" or line[-1] == "{":
                    # if the gate definition is a multi-line definition
                    entire_gate_def.extend(line)
                    inside_gate_bracket_flag = 1

                elif inside_gate_bracket_flag == 1:
                    # inside of the multi-line gate definition
                    entire_gate_def.extend(line)
                    inside_gate_bracket_flag = 1
            # If we are not inside the gate definition, we check to see if
            # the current line is a gate operation
            # elif gate in self.gate_info_dict
            # and (inside_gate_bracket_flag == 0):
            elif gate in gate_info_dict and (inside_gate_bracket_flag == 0):
                # split the line into a list of strings with the gate name and qubits
                line = [
                    element.replace(";", "").strip()
                    for item in line
                    for element in item.split(",")
                    if element
                ]

                gate_description = gate_info_dict.get(gate)
                if gate_description[1] == 3:
                    # if the gate is a 3-qubit gate, then
                    # break it down into simpler definition

                    # saves the values of the parameters and qubit names
                    saved_values = self.store_gate_info(line, gate_info_dict)

                    self.breakdown_3qubit_gate(
                        gate_info_dict,
                        gate,
                        saved_values,
                        gate_name,
                        num_qubits_per_gate,
                        qubit_name,
                    )
                    self.gate_count += 1
                    continue

                # this is the gate name with the parameters beside it
                # if it has parameters
                gate_with_params = line[0]
                gate_name.append(gate_with_params)

                num_qubits_per_gate.append(gate_description[1])

                qubit_names_list = line[1:]
                qubit_name.append(tuple(qubit_names_list))
                self.gate_count += 1  # increase gate count
                self.gate_count_decomp += 1  # increase gate count
            # Can do other things here. Such as handling "measure","barrier" etc
            else:
                pass

        return gate_name, num_qubits_per_gate, qubit_name

    @staticmethod
    def encode_qubit_name(qubit_names):
        """Turn str qubit names into integers

        i.e. Change ['q[0]', 'q[2]'] to [0,2]
        """

        # Extract (into a list of lists) the numbers from strings like 'q[3]'
        # pylint: disable=invalid-name
        qubit_IDs = [
            [int(re.findall(r"\d+", q)[0]) for q in name] for name in qubit_names
        ]

        # Determine how to re-number qubits so they are consecutive,
        # starting from 0
        unique_qubits = sorted(set(it.chain.from_iterable(qubit_IDs)))
        map_to_fix_qubit_numbering = dict((v, i) for i, v in enumerate(unique_qubits))

        # renumber the qubits
        encoded = [
            [map_to_fix_qubit_numbering[id_] for id_ in ids] for ids in qubit_IDs
        ]

        return encoded, unique_qubits

    def get_gate_list(self):
        gate_name, _, qubit_name = self._process_the_input()
        # pylint: disable=invalid-name
        qubit_IDs, unique_q = self.encode_qubit_name(qubit_name)
        num_qubits = len(unique_q)
        instructions = list(zip(gate_name, qubit_IDs))

        # Check if any rz gates,
        # if yes decompose the rz gates and
        #        return a gates_list with decomposed gates
        # if no return the original gates_list
        instructions = self.perform_rz_decomposition(instructions)

        return instructions, num_qubits


# noinspection PyPep8Naming
class ParseProjectQ(Parse):
    """Class to parse through the ProjectQ returned gate list"""

    def __init__(self, filepath, epsilon=1e-10) -> None:
        super().__init__(filepath, epsilon)
        # number of gates in the qasm file, including three qubit gates
        self.gate_count = 0

        # max number of qubits active at the same time
        self.max_width = 0

        # index of the first occurring ancilla.
        # Set to be the width of the circuit if no ancilla is used
        self.first_ancilla_idx = 0

    @property
    def num_qubits(self):
        # could include all qubits used if not recycling ancilla
        return self.max_width

    @property
    def instructions(self):
        # a list of list of list
        return self.break_into_sections()

    def process_input(self, file_path):
        """Reads in raw file in str format, returns a list of [gate, qubits]

        All str names are changed to lower case, all qubit names are replaced
        with the integer that used to identify them.
        Gate names such as CNOT or "Tdagger" are replaced with the convention
        defined in the base class variable "translate_dict"
        This method will update the attribute "self.max_width" and return the
        list of data qubits

        Example input from a '.txt' file:
            Allocate | Qureg[5]
            H | Qureg[5]
            Allocate | Qureg[0]
            CX | ( Qureg[0], Qureg[5] )
            T^\\dagger | Qureg[5]
            Deallocate | Qureg[5]

        Returned output:
            gate_list =
                [
                    ('allocate', [5]),
                    ('h', [5]),
                    ('allocate', [0]),
                    ('cx', [0, 5]),
                    ('tdg', [5]),
                    ('deallocate', [5])
                ]

            data_qubits = [0,5]
        """

        num_active_qubits = 0  # number of active qbits in a given time slot
        data_qubits = []  # all data qbits in the circuit, except ancilla qbits
        gate_list = []
        # format of one gate_list element is: [gate_name, qubits_involved]
        # gate_name: e.g, X or H
        # qubit_involved: qubits the gate is acting on. e.g, [1]

        with open(file_path, "r") as f:
            for line in f:
                if line[:2] == "<p":
                    continue

                raw = line.split("|")
                if raw != ["\n"]:
                    gate_name = raw[0].strip().lower()
                    qubit_str = raw[1].strip()  # qubit numbers in str format

                    # convert qubit numbers to int
                    qubit_int = [int(ele) for ele in re.findall(r"\b\d+\b", qubit_str)]

                    if gate_name in super().translate_dict.keys():
                        # translate into the standard internal convention
                        gate_name = super().translate_dict[gate_name]
                    elif gate_name == "allocate":
                        num_active_qubits += 1
                    elif gate_name == "deallocate":
                        num_active_qubits -= 1
                    elif gate_name == "measure":
                        data_qubits.extend(qubit_int)
                    elif gate_name[:5] == "input":
                        # take care of the special case of "input measure ...".
                        # ProjectQ appends a gate after this line
                        gate_name = gate_name.split(":")[-1].strip()
                        if gate_name in super().translate_dict.keys():
                            gate_name = super().translate_dict[gate_name]
                        elif gate_name == "measure":
                            data_qubits.extend(qubit_int)
                        elif gate_name == "allocate":
                            num_active_qubits += 1
                        elif gate_name == "deallocate":
                            num_active_qubits -= 1

                    self.max_width = max(num_active_qubits, self.max_width)
                    gate_list.append((gate_name, qubit_int))

        self.first_ancilla_idx = len(data_qubits)

        return gate_list, data_qubits

    def break_into_sections(self) -> list:
        """Takes the pre-processed gate list, returns a list of list,
        with each sub-list containing a section of the gate list.
        Each sub-list is separated from the previous sub-list whenever
        the parser sees "allocate", "deallocate" and "measure".
        The ancilla qubits are recognized by them not being measured out
        at the end of the circuit. The ProjectQ convention is such
        that each time an ancilla is re-used, it is assigned a new number.
        This function will replace the subsequent numbers with a fixed ID.
        This step is needed for the data to be processed by Lys.

        For example, the following circuit has a max_width of 3, data qubits
        of [0,1]. This means qubit 2 and qubit 3 are ancillas
        and they are essential the same physical qubit. We replace 3 with 2.

        Example input:
            [
                ('allocate', [0]),
                ('x', [0]),
                ('allocate', [1]),
                ('h', [1]),
                ('cx', [0, 1]),
                ('allocate', [2]),
                ('tdg', [1]),
                ('h', [2]),
                ('deallocate', [2]),
                ('allocate', [3]),
                ('cx', [0, 3]),
                ('deallocate', [3]),
                ('measure', [0]),
                ('measure', [1])
            ]

        Returned data:
            [
                [('x', [0])],
                [('h', [1]), ('cx', [0, 1])],
                [('tdg', [1]), ('h', [2]), ('measure', [2])],
                [('cx', [0,2]), ('measure', [2])],  # We replaced No. 3 with 2
                [('measure', [0])],
                [('measure', [1])]
            ]
        """
        gate_list, data_qubits = self.process_input(self.filepath)

        # Check if any rz gates,
        # if yes decompose the rz gates and
        #        return a gates_list with decomposed gates
        # if no return the original gates_list
        gate_list = self.perform_rz_decomposition(gate_list)

        # ancilla_reg holds whether the ancilla is being used or not.
        # A list of booleans.
        # in the format of [True, False]; which means ancilla index 0
        # is being used, the second one is free to be allocated again
        # ancilla IDs are calculated to be
        #   = max_of_data_ID + ancilla_reg_index + 1
        # e.g., if there are 3 data qubits named [0,1,2], and two ancillas;
        # ancillas will always use either 3 or 4 as qubit_ID
        ancilla_reg = [False] * (self.max_width - len(data_qubits))

        # name_change is a dictionary to keep track of ancilla qubits whose ID
        # has been reassigned using ancilla_reg index
        # e.g., using the previous example, if ancillas are re-used and
        # named as 5; all gates occurring on qubit 5 will be replaced with
        # gate occurring on qubit 3
        # name_change is updated to be {5: 3},
        # meaning 5 is replaced with 3; ['h', [5]] becomes ['h',[3]]
        # ancilla_reg is updated to be [True, False]
        name_change = {}

        # measured_qubit keeps track of which qubits have been measured
        measured_qubit = []

        # the max numerical ID of the data qubits.
        # e.g., data_qubits is [0, 1, 2] and the max_dataID will be 2
        # this value is used to calculate the ancilla IDs
        # pylint: disable=invalid-name
        max_dataID = max(data_qubits)

        # Go through the list of gates and
        # apply the modifications mentioned above
        result = [[]]
        index = 0
        for operation in gate_list:
            gate, qubit = operation[0], operation[1]

            if gate == "allocate":
                # Do not cut the list
                # # Cut the list here. Subsequent elements
                # will go into the next section
                # if result[-1] != []:
                #     result.append([])
                #     index += 1

                # Then process the qubit ID
                q = qubit[0]
                if q not in data_qubits:
                    # this is an ancilla
                    if q < self.max_width:
                        # first time using this ancilla
                        ancilla_reg[q - max_dataID - 1] = True
                    else:
                        # Need to find an available ancilla spot
                        # and change the qubit ID
                        for j, value in enumerate(ancilla_reg):
                            if value is False:
                                # this ancilla spot is free to be assigned
                                ancilla_reg[j] = True

                                # original qubit ID is replaced with
                                # the ancilla ID
                                name_change[q] = j + max_dataID + 1
                                break

            elif gate == "deallocate":
                q = qubit[0]

                # if the qubit has been measured out already,
                # do not deallocate again
                if q in measured_qubit:
                    continue

                # all de-allocation is done by measuring the qubit out
                gate = "measure"

                if q not in data_qubits:
                    if q in name_change.keys():
                        # change it to be the ancilla ID
                        qubit = [name_change[q]]
                        q = qubit[0]
                    # Release this ancilla so it can be re-allocated again later
                    ancilla_reg[q - max_dataID - 1] = False

                # keep track of measured out qubits in case there are
                # classically controlled gates occurring after the measurement
                measured_qubit.append(q)

                if result[index] == []:
                    try:
                        result[index - 1].append((gate, qubit))
                    except IndexError:
                        result[index].append((gate, qubit))
                else:
                    result[index].append((gate, qubit))
                    index += 1
                    result.append([])

                # result[index].append((gate, qubit))

                # Cut the list here. Subsequent elements will
                # go into the next section
                self.gate_count += 1
                # if result[-1] != []:
                #     result.append([])
                #     index += 1

            elif gate == "measure":
                measured_qubit.append(qubit[0])

                if qubit[0] in name_change:
                    qubit[0] = name_change[qubit[0]]

                # if the the only element of this section is a measure, it
                # means it's the case of consecutive measurements, append to
                # the last section;
                if result[index] == []:
                    try:
                        result[index - 1].append((gate, qubit))
                    except IndexError:
                        result[index].append((gate, qubit))
                else:
                    result[index].append((gate, qubit))
                    index += 1
                    result.append([])

                self.gate_count += 1

            else:
                # pylint: disable=invalid-name
                qubit_ID_updated = []
                for q in qubit:
                    if q in measured_qubit:
                        # This should not happen. A measured qubit cannot be
                        # used again, since projectq doesn't reassign used
                        # qubit IDs
                        raise ValueError(
                            "Measured qubit being used again. "
                            "The qubit in question is ",
                            q,
                        )
                    elif q in name_change:
                        # check qubit id, if belongs to name change,
                        # replace name and then append
                        q = name_change[q]
                        qubit_ID_updated.append(q)
                    else:
                        qubit_ID_updated.append(q)
                result[index].append((gate, qubit_ID_updated))
                self.gate_count += 1

        return result


# ''' Beginning of debug code '''
if __name__ == "__main__":
    # file = "../data/input/projectq_measure.txt"
    file = "../data/input/projectq_measure_anc.txt"
    projectq = ParseProjectQ(file)
    for each in projectq.instructions:
        print(each)
        print()
    # print(projectq.instructions)
    # print(projectq.max_width)
    # print(projectq.gate_count)


# ''' End of debug code '''
