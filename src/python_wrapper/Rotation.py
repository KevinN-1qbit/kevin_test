from math import pi
from .Operation import Operation

class Rotation(Operation):
    '''A class presenting the rotations in a circuit
    Attributes:
        x       : the x part of the tableau representation of a Pauli string
        z       : the z part of the tableau representation of a Pauli string
        angle   : rotation angle and phase. 0 is pi/2; 1 is pi/8, 2 is pi/4
        n       : number of qubits
    Example:
        Rotation XYZI of -pi/8 is encoded as:
        x       : [True, True, False, False]
        z       : [False, True, True, False]
        angle   : -1
    To use:
        r1 = Rotation(3, 1, ['x'], [2])  # "I" is implied
        results: 
            r1.x     = [F, F, T]
            r1.z     = [F, F, F]
            r1.angle = 1

    Convention:
        Left most position is qubit 0; right most position is qubit n
    '''

    def __init__(self, num_qubits: int, angle: int, basis:list =[] , qubits:list =[]):
        """Constructor, makes the rotation object.

        Args:
            num_qubits (int): Number of qbits.
            angle (int): qbit angle.
            basis (list, optional): TODO: Please Add good desctriptions here.. Defaults to [].
            qubits (list, optional): TODO: Please Add good desctriptions here. Defaults to [].
        """
        super().__init__(num_qubits, basis, qubits)
        self.angle = angle

    def __repr__(self) -> str:
        """Returns printable representation.

        Returns:
            str: Printable string to represent Rotation data.
        """
        x = self.x 
        z = self.z
        return  "Rotation: " + " angle: " + str(self.angle) + "\n (X) " + bin(x)[2:].zfill(self.n) + "\n (Z) " + bin(z)[2:].zfill(self.n)
    
    def __str__(self) -> str:
        """Returns String tranform for the Rotation.

        Returns:
            str: String representation of the Rotation
        """
        rotation_str = ''
        qubits = ''
        angle  = str(self.angle)
        x = bin(self.x)[2:].zfill(self.n)
        z = bin(self.z)[2:].zfill(self.n)
        for i in range(0,self.n):
            if (int(x[i])==1) & (int(z[i])==0):     rotation_str += 'X'
            elif (int(x[i])==0) & (int(z[i])==1):   rotation_str += 'Z'
            elif (int(x[i])==1) & (int(z[i])==1):   rotation_str += 'Y'
            else:                         rotation_str += 'I'

        return "Rotate " + angle + ": " + rotation_str

    def __eq__(self, other) -> bool:
        """Boolean comparator method for independant rotations. 

        Args:
            other (Rotation): Other Rotation object used for comparison.

        Returns:
            bool: True/False.
        """
        # Built-in method to check if two rotations instances are exactly the same
        if not isinstance(other, type(self)):
            return False
        if self.is_identity() and other.is_identity():
            return True
        conditions = [
            self.angle == other.angle,
            self.x     == other.x,
            self.z     == other.z,
            self.n     == other.n
        ]
        if all(conditions):
            return True
        else:
            return False
      
    def is_tgate(self) -> bool:
        """Returns True if Rotation is T-gate.

        Args:
            err (float): Tolerance for tgate.

        Returns:
            bool: True/False.
        """
        if self.is_identity():
            return False
        
        return (abs(self.angle) == 1)
    






