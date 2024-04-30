#include <stdio.h>
#include <vector>
#include <string>
#include <vector>
#include <stdexcept>
#include <math.h>
#include <bitset>
#include "Operation.hpp"
#include "Rotation.hpp"

#ifndef MEASURE_H
#define MEASURE_H

/**
 * @brief Measure object including integer encodings of xBasis, zBasis, number of Qubits and phase.
 *
 * @note A child of Operation struct.
 */
class Measure: public Operation {
public:

    bool phase;  ///< Phase angel. true means plus angle, false means negative angle
    std::vector<Rotation> rotations={}; // Rotation controlled on the measure outcome
    int outputPosition = -1;

    /**
     * @brief Empty Measure constructor, used only for the purpose of C++ Boost functionality.
     *
     * @return Measure
     */
    Measure();

    /**
     * @brief Measure constructor, create the encoded version of the measure data.
     *
     * @param phase Encoded phase for the Measure operation. true means plus angle, false means negative angle
     * @param xBasis Encoded string as a binary represention of the x axis.
     * @param zBasis Encoded string as a binary represention of the z axis.
     *
     * @return Measure
     */
    Measure(bool phase, std::string xBasis, std::string zBasis);

    /**
     * @brief Measure constructor with classically controlled rotation following measurement.
     *
     * @param phase Encoded phase for the Measure operation. true means plus angle, false means negative angle
     * @param xBasis Encoded string as a binary represention of the x axis.
     * @param zBasis Encoded string as a binary represention of the z axis.
     * @param rotations Vector of Rotation obj classically controlled on the outcome of measurement
     *
     * @return Measure
     */
    Measure(bool phase, std::string xBasis, std::string zBasis, std::vector<Rotation> rotations);

    /**
     * @brief Measure constructor, create the encoded version of the measure data.
     *
     * @param phase Encoded phase for the Measure operation. true means plus angle, false means negative angle
     * @param xBasis Encoded bitset as a binary represention of the x axis.
     * @param zBasis Encoded bitset as a binary represention of the z axis.
     *
     * @return Measure
     */
    Measure(bool phase, std::bitset<numQubits> xBasis, std::bitset<numQubits>  zBasis);

    /**
     * @brief Measure constructor with classically controlled rotation following measurement.
     *
     * @param phase Encoded phase for the Measure operation. true means plus angle, false means negative angle
     * @param xBasis Encoded string as a binary represention of the x axis.
     * @param zBasis Encoded string as a binary represention of the z axis.
     * @param rotations Vector of Rotation obj classically controlled on the outcome of measurement
     *
     * @return Measure
     */
    Measure(bool phase, std::bitset<numQubits> xBasis, std::bitset<numQubits>  zBasis, std::vector<Rotation> rotations);


    /**
     * @brief Measure constructor, create the encoded version of the rotation data.
     *
     * @param phase Phase for the Measure operation. true means plus angle, false means negative angle
     * @param basis A vector of 'x','y','z' characters representing the rotation on each qubit.
     * @param qubits A vector of integers indicating which qubits are operated on.
     *
     * @return Measure
     */
    Measure(bool phase, std::vector<char> basis, std::vector<int> qubits);

    Measure(bool phase, std::vector<char> basis, std::vector<int> qubits, std::vector<Rotation> rotations);


    /**
     * @brief Equality operator for Measure objects.
     *
     * @param measure Other Measure.
     * @return true if Equal.
     * @return false if Inequal.
     */
    bool operator==(Measure const& measure) const;

    /**
     * @brief Inequality operator for Measure objects.
     *
     * @param measure Other Rotation
     * @return true if Equal.
     * @return false if Inequal.
     */
    bool operator!=(Measure const& measure) const;

    /**
     * @brief Check to see if this measure is a tgate Rotation (pi/8).
     *
     * @note We expect this to be always false for a measure object since a measure object is by definition not a T gate
     *
     * @return true if the object is a T-gate rotation
     * @return false if the object is not a T-gate rotation
     */
    bool isTgate();

    /**
     * @brief Look if there is rotations controlled on the measure outcome
     *
     * @return true if there is.
     * @return false if there is none.
     */
    bool isClassicalControlledRotation();


    /**
     * @brief Create a string which includes information from the Measurement.
     *
     * @return std::string A print statement which includes a summary
     * of information about the Measurement: the angle, and the basis
     * (format {I,X,Z,Y}, e.g. IXIZY)
     */
    std::string toStr();

    bool isRotation();
};


#endif /* MEASURE */
