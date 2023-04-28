class Operation():
    def __init__(self, num_qubits: int, basis:list =[] , qubits:list =[]):
        """Constructor, makes the Operation object.

        Args:
            num_qubits (int): Number of qbits.
            basis (list, optional): Rotation or measurement basis. Defaults to [].
            qubits (list, optional): The qubit(s) which the rotation or the measurement is acting on. Defaults to [].

        Raises:
            ValueError: Number of qbits must be equal and each qbit must be unique
            ValueError: Uknown Basis
        """
        self.n      = num_qubits     #number of qubits in the circuit
        self.x      = 0
        self.z      = 0
        
        if len(basis) != len(set(qubits)):
            raise ValueError("Illegal declaration. Number of basis and number of qubits must be equal and the qubits must be unique")
        if basis != []:
            for index, val in enumerate(basis):
                if val == 'x':
                    self.x += 2**(num_qubits-1-int(qubits[index]))
                elif val == 'z':
                    self.z += 2**(num_qubits-1-int(qubits[index]))
                elif val == 'y':
                    self.x += 2**(num_qubits-1-int(qubits[index]))
                    self.z += 2**(num_qubits-1-int(qubits[index]))
                else:
                    raise ValueError("Unknown basis")

    def __repr__(self):
        """Returns printable representation.

        Returns:
            str: Printable string to represent Operation data.
        """
        raise NotImplementedError("Please Implement this method")

    
    def is_commute(self,other) -> bool:
        """This method takes to opetations and check if they commute.

        Returns:
            bool: True if they commute, False otherwise
        """
        return ((bin(self.x & other.z).count('1') + bin(self.z & other.x).count('1'))%2 == 0)

    def is_identity(self) -> bool:
        '''This method check if the operation is identity

        Returns:
            bool: True if the operation is identity, False otherwise
        '''
        if (self.x == 0 and self.z == 0) :
            return True
        return False
    
    def is_single_qubit(self) -> bool:
        '''This method check if the operation acts on exactly one qubit

        Returns:
            bool: True if the operation acts on one qubit, False otherwise
        '''
        xOrz = self.x | self.z
        if bin(xOrz).count('1')==1 :
            return True
        return False
    
    