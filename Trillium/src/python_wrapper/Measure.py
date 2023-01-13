from .Operation import Operation

class Measure(Operation):
    def __init__(self, num_qubits: int, phase: bool, basis: list=[], qubits: list=[]):
        """Constructor, makes the Measure object.

        Args:
            num_qubits (int): [description]
            phase (bool): True encodes Plus; False encodes Negative 
            basis (list, optional): Defaults to []. Defaults to [].
            qubits (list, optional): Defaults to []. Defaults to [].
        """
        super().__init__(num_qubits, basis, qubits)
        self.phase = phase

    def __repr__(self) -> str:
        """Returns printable representation.

        Returns:
            str -- Printable string to represent Rotation data.
        """
        x = self.x 
        z = self.z
        return  "Measure -> (X) " + bin(x)[2:] + "; (Z) " + bin(z)[2:]

    def __str__(self) -> str:
        """Returns String tranform for the Measure.

        Returns:
            str: String representation of the Measure.
        """
        measure_str = ''
        qubits = ''
        phase  = '-'
        if (self.phase == 1): phase = '+'
        x = bin(self.x)[2:].zfill(self.n)
        z = bin(self.z)[2:].zfill(self.n)
        for i in range(0,self.n):
            if (int(x[i])==1) & (int(z[i])==0):     measure_str += 'X'
            elif (int(x[i])==0) & (int(z[i])==1):   measure_str += 'Z'
            elif (int(x[i])==1) & (int(z[i])==1):   measure_str += 'Y'
            else:                         measure_str += 'I'

        return "Measure " + phase + ": " + measure_str

    def __eq__(self, other) -> bool:
        """Boolean comparator method for independant measure. 

        Arguments:
            other {Measure} -- Other Measure object used for comparison

        Returns:
            bool -- True/False. Return True if two Measure instances are exactly the same
        """
        if not isinstance(other, type(self)):
            return False
        if self.is_identity() and other.is_identity():
            return True
        conditions = [
            self.phase == other.phase,
            self.x     == other.x,
            self.z     == other.z,
            self.n     == other.n
        ]
        if all(conditions):
            return True
        else:
            return False

