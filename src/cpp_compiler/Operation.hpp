#include <stdio.h>
#include <vector>
#include <string>
#include <stdexcept>
#include <math.h>
#include <bitset>
#include <iostream>

#ifndef OPERATION_H
#define OPERATION_H

#define numQubits 4
// this number will be overwritten when recompiling and if the new circuit has different number of qubits than the previous compiled version
// WARNING: Do not add anything after number "5" or change the the name "numQubits" or modify the above line in any way! Otherwise the python interface will not recognise it

/**
 * @brief Operation object including integer encodings of xBasis, zBasis and number of Qubits.
 *
 * @note Parent for Rotation and Measure.
 */
class Operation
{
public:
    virtual ~Operation() = default;
    //    int angle = -10;
    std::bitset<numQubits> xBasis = 0; ///< Encoded xBasis.
    std::bitset<numQubits> zBasis = 0; ///< Encoded zBasis.

    /**
     * @brief Empty Operation constructor, used only for the purpose of C++ Boost functionality.
     *
     * @return Operation
     */
    Operation();

    /**
     * @brief Operation constructor, create the encoded version of the operation data.
     *
     * @param xBasis Encoded integer as a binary represention of the x axis.
     * @param zBasis Encoded integer as a binary represention of the z axis.
     *
     * Note: Remember to take in as a string and transform it into bitset data for xBasis and zBasis.
     * Reason being that python integers can be larger than max available integer in C++.
     *
     * @return Operation
     */
    Operation(std::string xBasis, std::string zBasis);

    /**
     * @brief Operation constructor, create the encoded version of the operation data.
     *
     * @note TODO: initilization of the vector of one element or less
     *
     * @param basis A vector of 'x','y','z' characters representing the operation on each qubit.
     * @param qubits A vector of integers indicating which qubits are operated on.
     *
     * Note: This constructor is only used for tests written by us. Actual conversion is done on
     * the python side. Only supports up to 128 qubits.
     *
     * @return Operation
     */
    Operation(std::vector<char> basis, std::vector<int> qubits);

    /**
     * @brief Check if to Operations are Commutable.
     *
     * @note this function is the most important function regarding the
     * processing speed due to the frequency of getting called.
     * Out of different method this method has been the fastest, but other
     * developers are welcome to try.
     *
     * @param lhs Left hand side Operation.
     * @param rhs Right hand side Operation.
     *
     * @return true if the two operations are commutable.
     * @return false if the two operations are not commutable.
     */
    bool isCommute(const Operation rhs) const;

    /**
     * @brief Check if an Operation is Identity.
     *
     * @param operation Target operation.
     *
     * @return true if the Operation is an identity.
     * @return false if the Operation is not an identity.
     */
    bool isIdentity() const;

    /**
     * @brief Check if the Operation, operates on on a single qubit.
     *
     * @param operation Target operation.
     *
     * @return true if Operation works on a single qubit.
     * @return false if Operation does not work on only one qubit.
     */
    bool isSingleQubit() const;

    /**
     * @brief Check if the two operations share the same qubits.
     *
     * @param The other operation to check against.
     *
     * @return true if they share qubits.
     * @return false if they don't share qubits.
     */
    // bool hasOverlap(const Operation that) const

    /**
     * @brief Return a comprehensive string of the operation
     *
     *
     * @return std::string string containing the numQubit, X and Z basis
     *                     in unsigned long long and binary representation
     */
    std::string Print();

    virtual bool isTgate();

    virtual bool isRotation();

    virtual int getAngle();
};

///**
// * @brief Return a string of the X basis (binary rep)
// *
// *
// * @return std::string of the Xbasis in binary representation, e.g. 100101
//*/
// std::string Bitset2StringX(const Operation op);
//
///**
// * @brief Return a string of the Z basis (binary rep)
// *
// *
// * @return std::string of the Zbasis in binary representation, e.g. 100101
//*/
// std::string Bitset2StringZ(const Operation op);

#endif
