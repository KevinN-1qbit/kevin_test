""" module for decomposing rotations into Clifford + T """

import subprocess

from Trillium.utils import paths


class Decompose:
    """ Takes one unitary, and decomposes into Clifford + T

    currently limited to single qubit z-rotations
    """

    def __init__(self, unitary, epsilon=1e-10) -> None:
        # 1e-10 is the default value of gridsynth
        self.unitary = unitary
        self.epsilon = epsilon

    @property
    def operators(self):
        return self.decomposed()

    def decomposed(self):
        """ Calls the gridsynth binary to decompose the unitary

        Acts on one unitary at a time, returning the decomposed operators

        Assumes the input "unitary" is of the following format:
        [rz(0.134234), [2]]
            means apply Rz rotation for angle of 0.134234 (radians) to qubit 2
        """

        # todo: Make sure the output from ProjectQ is in radians and also,
        #  make it language dependent. Do not hardcode!
        gridsynth_loc = paths.rel_path_to_abs_path("utils/gridsynthEXE")
        angle = list(self.unitary.split("("))[1][:-1]
        cmds = [gridsynth_loc, angle, "-e", str(self.epsilon)]
        popen = subprocess.Popen(cmds, stdout=subprocess.PIPE)
        popen.wait()
        result = popen.stdout.read()

        return result.decode()
