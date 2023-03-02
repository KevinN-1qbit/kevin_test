#ifndef LysCompiler_hpp
#define LysCompiler_hpp

#include <stdio.h>
#include <string>
#include <iostream>
#include <vector>
#include "Measure.hpp"
#include "Rotation.hpp"
#include "Operation.hpp"
#include <ctime>
#include <map>
#include <thread>
#include <math.h>
#include <algorithm>
#include <variant>

//typedef std::variant<Rotation,Measure> Gate; //Type-safe union of Rotation and Measure

/**
 * @brief A helper function to print out the gates in the format of R1 : XXIZZ
 */
//void toStrVariantVec(std::vector<Gate> &gateVec);

/**
 * @brief Lys compiler class transforms the input circuit in the set Clifford+T into a T+measurements.
 *
 * @note: The goal of the lys compiler is to push all T to the front of the circuit, and absorb
 *        as many Clifford gates into measurements (by way of change of basis) as possible.
 *        However, exceptions are made when ancilla qubits are involved. Since one cannot commute
 *        over an ancilla qubits, gates are left in place on the ancillas and/or between ancilla and data qubits
 */
class LysCompiler{

public:
   std::vector<std::shared_ptr<Operation>> circuit;       // The vector of Gate representing the circuit.
   int ancillaBegin = numQubits;    // The index at which the ancillas begin note
                                    // Encoding convention is: XZYY represents qubit index 0, 1, 2, 3. We count from left to right, begins at 0.
                                    // E.g: ancillaBegin = 3 means ancilla starts at index 3
                                    // Default to "numQubits" meaning that the default case has no ancilla. In this case ancillaBegin is an index that's out of bound

     /**
      * @brief Construct a new Lys Compiler object
      *
      * @param encoded_circuit Target encoded circuit as a vector of Gates (Rotations and Measures).
      */
     LysCompiler(std::vector<std::shared_ptr<Operation>> encoded_circuit);

     /**
      * @brief Construct a new Lys Compiler object
      *
      * @param encoded_circuit Target encoded circuit as a vector of Gates (Rotations and Measures).
      * @param ancillaBegin: index at which the ancillas start.
      */
     LysCompiler(std::vector<std::shared_ptr<Operation>> encoded_circuit, int ancillaBegin);

    // /**
    //  * @brief Construct a new Lys Compiler object with default measurements: {ZII...I, IZI...I, ..., I...IZI, I..IIZ}. Assuming the circuit doesn't have data qubit measures at the end
    //  *
    //  * @param numDefaultMeasurements Number of Z Measure to add to the circuit, these Z measurements will
    //  * be add to qubits corresponding to the numQubits most significant bits in int representations.
    //  * @param encoded_circuit Target encoded circuit as a vector of Rotations and Measure. Must not have data qubit measures at the end of the circuit.
    //  * @param ancillaBegin: index at which the ancillas start.
    //  */
    // LysCompiler(int numDefaultMeasurements, std::vector<Gate> encoded_circuit, int ancillaBegin);

    /**
     * @brief Construct a new Lys Compiler object with default measurements: {ZII...I, IZI...I, ..., I...IZI, I..IIZ}. Assuming the circuit doesn't have data qubit measures at the end
     *
     *
     * @param numDefaultMeasurements Number of Z Measure to add to the circuit, these Z measurements will
     * be add to qubits corresponding to the numQubits less significant bits in int representations.
     * @param encoded_circuit Target encoded circuit as a vector of Rotations. Must not have data qubit measures at the end of the circuit
     */
    LysCompiler(int numDefaultMeasurements, std::vector<std::shared_ptr<Operation>> encoded_circuit);

     /**
      * @brief Check if two rotations can be combined, if so, combine them.
      *
      * @note A set of Conditions must be met.
      * Conditions:
      *      - Two rotations must be of the same basis to combine
      *      - Does not allow angle sum to +/- 3 when combining angles
      *      - Does not allow angle 0 to combine with either angle 1 or 2
      *      - For angle, allowing 1+1 = 2; 2+2 = 4; 1-1 = deletion; 2-2 = deletion;
      *      0+0 = deletion; 2-1 = 1; -2+1 = -1; 0-2=+2
      *
      * @param R11 First rotation to combine.
      * @param R22 Second rotation to combine.
      *
      * @return pair<bool,vector<Rotation>> The Boolean is true if R11 and R22 can be combine, false otherwise.
      * Result of the combination of R11 and R22, return R11 and R22 if they can't be combine. Could consist of 0, 1 or 2 Rotations.
      */
     std::pair<bool,std::vector<Rotation> > combineRotation(Rotation R11, Rotation R22);

     /**
      * @brief Check if two Gates can be combined, if so, combine them.
      *
      * @note Only Rotations can be combine, if both of Gates are Rotations,
      * it call combineRotation
      *
      * @param R11 First Gate to combine.
      * @param R22 Second Gate to combine.
      *
      * @return pair<bool,vector<Rotation>> The Boolean is true if R11 and R22 can be combine, false otherwise.
      * Result of the combination of R11 and R22, return R11 and R22 if they can't be combine. Could consist of 0, 1 or 2 Gates.
      */
     std::pair<bool,std::vector<std::shared_ptr<Operation>> > combineGate(std::shared_ptr<Operation> R11, std::shared_ptr<Operation> R22);

     /**
      * @brief Combine Gates when order does not matter (e.g. when they all commute, in a Layer).
      *
      * @note The function goes through the list one time.
      *
      * @param listOfRotations Vector of Gate objects. In other words, a Layer.
      *
      * @return pair<bool, vector<Gate>> Returns True if at least one combination happend, returns False otherwise.
      *
      */
     bool implementNoOrderingRotationCombination(std::vector<std::shared_ptr<Operation>> &listOfRotations);

     /**
      * @brief Combine rotations when order does not matter (e.g. when they all commute, in a Layer).
      *
      * @note The vector is changed in place.
      *
      * @param listOfRotations Vector of Gates objects representing a single layer.
      *
      * @return pair<bool, vector<Gate>> True if any inplace change was applied; False otherwise.
      *
      */
     bool noOrderingRotationCombination(std::vector<std::shared_ptr<Operation>> &listOfRotations);

    /**
     * @brief Apply the commutation rules for a nonT gate and a T gate that DON'T commute (PP'=-P'P)
     * The nonT gate is unchanged, but the T gate must be updated after the commutation
     *
     * @note This function only transforms the tgateRotation, nonTgateRotation must be
     * a Clifford or a Pauli Type (+/-Pi/4 or Pi/2 corresponding angle +/-2 or 0). The only
     * condtition is that nonTgateRotation and tgateRotation MUST NOT COMMUTE. There is no
     * restriction on tgateRotation beside that (could be pi/8,pi/4,pi/2 corresponding
     * angle 1,2,0).
     *
     * @param nonTgateRotation A nonT gate rotation (angle must be 0 or +/- 2)
     * @param tgateRotation A T gate rotation that DON'T commute with nonTgateRotation
     *
     * @return Rotation  after updated Rotation corresponding to tgateRotation after the Commutations.
     */
    static Rotation applyCommutation(Rotation nonTgateRotation, Rotation tgateRotation);

    /**
     * @brief Permute a Rotation with a Measure that DON'T commute (PP'=-P'P)
     *
     * @param R1 NonT gate Rotation object (angle must be 0 or +/-2).
     * @param M1 Measure object that DON'T COMMUTE with R1.
     *
     * @return Measure return the resulting Measure of the permutation of R1 and M1
     */
    static Measure applyCommutation(Rotation R1, Measure M1);

//     /**
//     * @brief Permute a Measure with a Rotation that DON'T commute (PP'=-P'P)
//     * Rotation must be a tgate (pi/8, i.e. angle equivalent to +/-1)
//     *
//     * @param Meas Measure object
//     * @param tGate Rotation object (angle must be +/-1).
//      that DON'T COMMUTE with Meas.
//     *
//     * @return Measure return the resulting Rotation of the permutation of Meas and tgate
//     */
//    static Rotation applyCommutation(Measure Meas, Rotation tGate);

//    /**
//     * @brief Permute a Gate with a Rotation that DON'T commute (PP'=-P'P)
//     * Rotation must be a tgate (pi/8, i.e. angle equivalent to +/-1)
//     *
//     * @param gate Gate object (Rotation or Measure)
//     * @param tGate Rotation object (angle must be +/-1).
//      that DON'T COMMUTE with gate.
//     *
//     * @return Rotation return the resulting Rotation of the permutation of gate and tGate
//     */
//    static Rotation applyCommutation(Operation gate, Rotation tGate);

    /**
     * @brief Commute all the T gates to the front of the circuit.
     *
     * @note Used as a thread function.
     * @note This function is very similar to a serial version except that it takes the start and end index
     * of the Rotation Vector circuit. After the forwarding is complete, this thread will return the split index
     * that splits the non T-gates and T-gates between beginIndex and endIndex. So we will have :
     * vector < ... ... , beginIndex T-gate, T-gate, T-gate ..., threadSplitIndices non T-gate, non T-gate, non T-gate, ...  endIndex non T-gate, ... ...>
     *
     * @param flattenGates A reference to the Vector of Gate (Rotation or Measure) gates.
     * @param beginIndex Beginning index for this thread to be processed from the Vector of Gates (inclusive).
     * @param endIndex End index for this thread to be processed from the Vector of Gates (exclusive).
     * @param threadSplitIndices A reference to an array of that will include the split indices for the commutation for the threads.
     * @param threadOrderIndex Index of the thread (index of threadSpliIndices). Use this number to dictate the index of the where to
     * place the split index in the threadSplitIndices .
     */
    static void pushTForwardThread(std::vector<std::shared_ptr<Operation>> & flattenGates, int beginIndex, int endIndex, std::vector<int> &threadSplitIndices, int threadOrderIndex);

    /**
     * @brief Bring all the T gates at the begining of the circuit.
     *
     * @note This function take care of the different threads.
     * @note It will split the T gates from the non-T gates
     *
     * @param flattenGates A Vector of gates comprising possibly both t and nonT. Flatten refers to the fact that layers have been flattened
     * @param beginIndex Beginning index for this thread to be processed from the Vector of Rotations (inclusive).
     *
     * @return vector<int>  return the Beginning index (inclusive) and end index (exclusive) for the next thread to be processed
     * from the Vector of Gates (inclusive).
     */

    std::vector<int> implementationPushTForward(std::vector<std::shared_ptr<Operation>> & flattenGates, int numThreads, int begin, int subsetEnd);


    /**
     * @brief Push all T-gates in the circuits to the beginning of the circuit using the commutation rules and transforms.
     *
     * @note The main Idea is that we will split the Vector of rotations into smaller sections to be processed by the multithreaded functions.
     * Everytime we take the beginning of the first subvector (which has only T-gates) and the last section of the last subvector (which has
     * only non T-gates), we remove them and we create new subvectors consisting of (non T-gates, T-gates) and give them to new threads for
     * processing. Keep in mind, at the moment, upon each iteration the number of threads decreases by one since we reduce one T-gates and one
     * non T-gates section.
     * @note If the number of gates are bigger than 100, it will runs un parallel, if not, it will run in serial
     * TODO: The reduction of the threads should be addressed at some point since it isn't using the full capabilities of
     * C++ multithreading
     *
     * @param flattenGates A Vector of gates comprising possibly both t and nonT. Flatten refers to the fact that layers have been flattened
     *
     * @return pair<vector<Gate>, vector<Gate> Return a pair of Vectors, the first Vector is a Vector of T-gates and
     * the second one is a Vector of the non T-gates.
     */
    int pushTForward(std::vector<std::shared_ptr<Operation>> & flattenGates);

     /**
      * @brief Reduce the number of T gate layers (gate-depth) of the circuit.
      *
      * @note This function is used in a thread
      * @note All gate in a layer commute with each other
      * @note All change are done in place
      *
      * @param circuitLayers A vector of vector of gates
      * @param change Indicate if any change occur during the process
      *
      */

     void reduceLayerGreedyAlgoThread(std::vector<std::vector<std::shared_ptr<Operation>>> &circuitLayers, bool &change);

     /**
      * @brief Reduces the number of T gate layers using a greedy algorithm suggested by Litinski's paper.
      *
      * @note This fonction take care of the different threads.
      * @note All gates in a layer commute with each other
      *
      * @param circuitVec A Vector of the flatten gates used for gates reduction.
      * @return vector<vector<Gate>> A Vector of Vectors of Gatess which includes the layered circuits.
      */
    std::vector<std::vector<std::shared_ptr<Operation>>> reduceLayerGreedyAlgo(std::vector<std::shared_ptr<Operation>> &circuitVec);

    // /**
    //  *@brief This method is applied to the circuit of the object.  Run a timed version of the optimized Rotation.
    //  * It will :
    //  *      1. Push T forward
    //  *      2. Create layers for the T gates
    //  *      3. Try to combine gates into each layer
    //  *      4. Do 1-3 until there is no more change
    //  *      5. Reduce the number of non-T gates (step 2 and 3 for nonT)
    //  *
    //  * @note Change list_of_clifford_gates in place.
    //  * @note TODO : don't return the circuit, the change are already done inplace
    //  *
    //  *
    //  * @return pair<vector<Gate>, map<string, double>> Return a Vector of the flatten Gate circuit.
    //  * Also send back a map involving the runtime information.
    //  */
    // std::pair<std::vector<Gate>, std::map<std::string, double> > optimizeRotationTimed();

    /**
     *@brief This method is apply to the circuit of the object. It reduce the gate count.
     * It will :
     *      1. Push T forward
     *      2. Create layers for the T gates
     *      3. Try to combine gates into each layer
     *      4. Do 1-3 until there is no more change
     *      5. Reduce the number of non-T gates (step 2 and 3 for nonT)
     *
     * @note Change list_of_clifford_gates in place.
     *
     * @return std::pair<std::vector<Gate>,std::vector<Gate>> first vector are the t gates, second the nonT gates
     *
     */
    // std::pair<std::vector<Gate>,std::vector<Gate>>  optimizeRotation();
    int optimizeRotation();


     /**
      * @brief Put all the 1-Qubit Rotation as close as they can (commute) to the end of the
      * circuit (before final Measurements > idxLasRotation).
      *
      * @note Change list_of_clifford_gates in place.
      *
      * @param idxOfTGates index of the last T gates in this->circuit.
      * @param idxLastRotation index of the last rotation (before final Measures)
      *
      * @return int The index at which the number of 1-Qubit gate rotations start.
      */
     int RearrangeCliffordGates(int idxOfTGates,int idxLastRotation);

     /**
      * @brief Commute all the Clifford and Pauli rotations with measurement iteratively while attempting
      * to optimize the number of measurements layer.
      *
      * @note All the changes are applied in place (The vector should be only measure at the end).
      *
      * @param idxOfTGates index of the last T gates in this->circuit.
      *
      * @return int number of gate to pass to the next section (number of rotations after the Measures)
      */
     int basis_permutation(int idxOfTGates);


    /**
     * @brief Compile a circuit with Litinski's method: all T gates at the begining of the circuit,
     * fallow by clifford+pauli+measure if not combine. Will reduce the number of gates.
     *
     * @note All the changes to the circuit are applied in place except layering.
     *
     * @param combine   bool : Combine Clifford+Pauli to Measure.
     * @param layer     bool : Output optimized layer
     *
     * @return std::vector<std::vector<Gate>>
     *                          if layer = False return empty pair of the forme {{}}
     *                          if layer = True return vector of layer (layer = vector Gate )
     *         int index at which the Cliffords (after the measures) start
     *
     */
    std::pair<std::vector<std::vector<std::shared_ptr<Operation>>>,int> runLysCompiler(bool combine,bool layer);

};

/**
    * @brief Take an element from the variant Gate and return an Operation obj that's either Rotation or Measure obj
    *
    * @note Helper function to access the content of the union of variant since one cannot directly access what's inside the variant
    *
    * @param gate a Gates object that can either be a Rotation or a Measure
    *
    * @return Operation object, either a Rotation or a Measure
    */
//Operation gateToOp(Gate gate);

#endif /* LysCompiler_hpp */
