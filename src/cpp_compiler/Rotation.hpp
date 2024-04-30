#include <stdio.h>
#include <vector>
#include <string>
#include <vector>
#include <stdexcept>
#include <math.h>
#include <bitset>

#include "Operation.hpp"

#ifndef ROTATION_H
#define ROTATION_H

/**
 * @brief Rotation object including integer encodings of xBasis, zBasis, number of qubits and angle.
 * @note A child of Operation struct.
 */
class Rotation : public Operation
{
public:
    int angle = 0; ///< Encoded Rotation angle. Reference the python code for more information.
    /**
     * @brief Empty Rotation constructor, used only for the purpose of C++ Boost functionality.
     *
     * @return Rotation
     */
    Rotation();

    /**
     * @brief Rotation constructor, create the encoded version of the rotation data.
     *
     * @param angle Encoded angle for the Rotation operation.
     * @param xBasis Encoded string represention of the x axis.
     * @param zBasis Encoded string represention of the z axis.
     *
     * @return Rotation
     */
    Rotation(int angle, std::string xBasis, std::string zBasis);

    /**
     * @brief Rotation constructor, create the encoded version of the rotation data.
     *
     * @param angle Angle for the Rotation operation.
     * @param basis A vector of 'x','y','z' characters representing the rotation on each qubit.
     * @param qubits A vector of integers indicating which qubits are operated on.
     *
     * @return Rotation
     */
    Rotation(int angle, std::vector<char> basis, std::vector<int> qubits);

    /**
     * @brief Rotation constructor, create the encoded version of the rotation data.
     *
     * @param angle Encoded angle for the Rotation operation.
     * @param xBasis Encoded bitset represention of the x axis.
     * @param zBasis Encoded bitset represention of the z axis.
     *
     * @return Rotation
     */
    Rotation(int angle, std::bitset<numQubits> xBasis, std::bitset<numQubits> zBasis);

    /**
     * @brief Equality operator for Rotation objects.
     *
     * @param rotation Other Rotation.
     * @return true if Equal.
     * @return false if Inequal.
     */
    bool operator==(Rotation const &rotation) const;

    /**
     * @brief Inequality operator for Rotation objects.
     *
     * @param rotation Other Rotation
     * @return true if Equal.
     * @return false if Inequal.
     */
    bool operator!=(Rotation const &rotation) const;

    /**
     * @brief Check to see if a Rotation is a tgate Rotation (pi/8).
     *
     * @param rotation A Rotation object for the operation.
     *
     * @return true if the Rotation is a T-gate rotation
     * @return false if the Rotation is not a T-gate rotation
     */
    bool isTgate();

    /**
     * @brief Check if the rotation is acting on only the data qubits, only the ancilla or both
     *
     * @return char 'd' if only acts on data qubits;
     * char 'a' if only acts on ancilla;
     * char 'b' if acts on BOTH data and ancilla.
     */
    char blockAction(int ancillaBegin);

    /**
     *
     */
    int getAngle();

    /**
     * @brief Create a string which includes information from the Rotation.
     *
     * @return std::string A print statement which includes a summary
     * of information about the Rotation: the angle, and the basis
     * (format {I,X,Z,Y}, e.g. IXIZY)
     */
    std::string toStr();

    bool isRotation();
};

#endif /* ROTATION */
