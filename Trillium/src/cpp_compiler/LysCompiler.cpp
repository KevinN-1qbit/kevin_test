#include "LysCompiler.hpp"
#include <bitset>
#include <stdexcept>
#include <cmath>
using namespace std;

 LysCompiler::LysCompiler(vector<shared_ptr<Operation>> encoded_circuit){
     // Guard against empty input
     if (encoded_circuit.size() == 0) throw std::invalid_argument("Input circuit must have at least one element");

     this->circuit = encoded_circuit;
 };

 LysCompiler::LysCompiler(vector<shared_ptr<Operation>> encoded_circuit, int ancillaBegin){

     this->circuit = encoded_circuit;
     this->ancillaBegin = ancillaBegin;
 };


LysCompiler::LysCompiler(int numDefaultMeasurements, vector<shared_ptr<Operation>> encoded_circuit){
    // Guard against empty input
    if (encoded_circuit.size() == 0) throw std::invalid_argument("Input circuit must have at least one element");

    for(auto& rot : encoded_circuit) {
        this->circuit.push_back(std::move(rot));
    }
    vector<char> emptyc = {};
    Measure tempMeasure;
    vector<shared_ptr<Operation>> pMeasurement;
    for(int indexQubit = 0 ; indexQubit < numDefaultMeasurements ; ++indexQubit){
        tempMeasure = Measure(true, emptyc, {});
        tempMeasure.zBasis = pow(2,numQubits-1-indexQubit);
        pMeasurement.emplace_back(make_shared<Measure>(tempMeasure));
    }

    this->circuit.insert(this->circuit.end(),make_move_iterator(pMeasurement.begin()),make_move_iterator(pMeasurement.end())); // append default measurement at the end of the circuit

};


 pair<bool,vector<Rotation> > LysCompiler::combineRotation(Rotation R11, Rotation R22){

     //make a copy of the rotations
     Rotation R1 = Rotation(R11);
     Rotation R2 = Rotation(R22);

     //Check if they are identity
     vector<bool> identityCheck = {R1.isIdentity(), R2.isIdentity()};
     //case : both identity, remove both
     if(identityCheck[0] == true and identityCheck[1] == true){
         vector<Rotation> responseRotations = {};
         pair<bool,vector<Rotation> > combinationResponse = make_pair(true, responseRotations);
         return combinationResponse;
     }

     // case : R11 is Identity, remove it
     if(identityCheck[0] == true and identityCheck[1] == false){
         vector<Rotation> responseRotations = {R2};
         pair<bool,vector<Rotation> > combinationResponse = make_pair(true, responseRotations);
         return combinationResponse;
     }

     // case : R22 is Identity, remove it
     if(identityCheck[0] == false and identityCheck[1] == true){
         vector<Rotation> responseRotations = {R1};
         pair<bool,vector<Rotation> > combinationResponse = make_pair(true, responseRotations);
         return combinationResponse;
     }

     // case: they can't be combine because they have not the same basis
     if( !((R1.xBasis == R2.xBasis) and (R1.zBasis == R2.zBasis)) ){
         vector<Rotation> responseRotations = {R1, R2};
         pair<bool,vector<Rotation> > combinationResponse = make_pair(false, responseRotations);
         return combinationResponse;
     }

     int newAngle = R1.angle + R2.angle;

     // combine to identity
     if(newAngle == 0){
         vector<Rotation> responseRotations = {};
         pair<bool,vector<Rotation> > combinationResponse = make_pair(true, responseRotations);
         return combinationResponse;
     }

     //if one the the rotation is a Pauli (pi/2, angle = 0) allows combination
     // only with another pauli or a -pi/4 rotation (-2)
     pair<int,int> angles = make_pair(R1.angle, R2.angle);
     vector<pair<int,int> > allowsCombine = {make_pair(-2, 0), make_pair(0, -2)};
     if(angles.first == 0 || angles.second == 0){
         if ( find(allowsCombine.begin(), allowsCombine.end(), angles) == allowsCombine.end() ){
             vector<Rotation> responseRotations = {R1, R2};
             pair<bool,vector<Rotation> > combinationResponse = make_pair(false, responseRotations);
             return combinationResponse;
         }
         else{
             if (newAngle == -2)
                 newAngle = 2;
         }
     }

     // not allows case sum to +/-3 (5pi/8)
     if(abs(newAngle) == 3){
         vector<Rotation> responseRotations = {R1, R2};
         pair<bool,vector<Rotation> > combinationResponse = make_pair(false, responseRotations);
         return combinationResponse;
     }

     //combine to pi/2 (Pauli)
     if(abs(newAngle) == 4)
         newAngle = 0;

     // return the combined rotation
     Rotation newRotation = R1 ;
     newRotation.angle = newAngle ;
     vector<Rotation> responseRotations = {newRotation};
     pair<bool,vector<Rotation> > combinationResponse = make_pair(true, responseRotations);
     return combinationResponse;
 }



 pair<bool,vector<shared_ptr<Operation> > > LysCompiler::combineGate(shared_ptr<Operation> R11, shared_ptr<Operation> R22){
     pair<bool,vector<shared_ptr<Operation>>> result;
     if (R11->isRotation() && R22->isRotation()) {
         pair<bool,vector<Rotation>> res = combineRotation(*static_pointer_cast<Rotation>(R11),*static_pointer_cast<Rotation>(R22));
         result.first = res.first;
         for (int i=0; i < (int)res.second.size(); i++){
             result.second.emplace_back(make_shared<Rotation>(res.second[i]));
         }
     }
     else {
         vector<shared_ptr<Operation>> gates = {R11,R22};
         result = make_pair(false,gates);
     }
     return result;
 }



 bool LysCompiler::implementNoOrderingRotationCombination(vector<shared_ptr<Operation>> &listOfRotations){

     bool changed = false;

     //base case, one element
     if(listOfRotations.size() == 1){
         shared_ptr<Operation> op = listOfRotations[0];
         if(op->isIdentity()){
             //remove it if it is the identity
             listOfRotations.erase(listOfRotations.begin());
             return true;
         }
         else
             return false;
     }

     int index1 = 0;
     int index2 = 1;

     int sizeCondition = listOfRotations.size() - 1;
     while( sizeCondition > index1 ){
         shared_ptr<Operation> R1 = listOfRotations[index1];  //first rotation to compare
         shared_ptr<Operation> R2 = listOfRotations[index2];  //second rotation to compare
         pair<bool,vector<shared_ptr<Operation>> > combinationResponse = this->combineGate(R1, R2);
         bool isCombine = combinationResponse.first;
         vector<shared_ptr<Operation>> tempResponseList = combinationResponse.second;

         // if a combination happend, update the list
         if(isCombine){
             if(tempResponseList.size() == 0){
                 // case : combine to identity
                 // It is important to remove R2 before we remove R1 to prevent index issues.
                 listOfRotations.erase(listOfRotations.begin() + index2);    //remove R2
                 listOfRotations.erase(listOfRotations.begin() + index1);    //remove R1
             }
             else{
                 //case : combine to a new rotation
                 listOfRotations[index1] = tempResponseList[0];              //replace R1 by the combined rotation
                 listOfRotations.erase(listOfRotations.begin() + index2);    //remove R2
             }
             changed = true;
         }
         else{
             //can't be combined, check the next rotation
             ++index2;
         }
         if(index2 >= listOfRotations.size()){
             // if we are at the end of the list for R2, change R1 and reset R2
             ++index1;
             index2 = index1+1;
         }
         sizeCondition = listOfRotations.size() - 1;
     }

     return changed;
 }



 bool LysCompiler::noOrderingRotationCombination(vector<shared_ptr<Operation>> &listOfRotations){

     //base case : empty list
     if(listOfRotations.size() == 0)
         return false;

     //go through the list once
     bool changed = this->implementNoOrderingRotationCombination(listOfRotations);

     // go through the list until there is no more changes (recursive call)
     if(changed){
         this->noOrderingRotationCombination(listOfRotations);
     }

     return changed;
 }



Rotation LysCompiler::applyCommutation(Rotation nonTgateRotation, Rotation tgateRotation){

    // initialization of the output
    bitset<numQubits> updatedXbasis;
    bitset<numQubits> updatedZbasis;
    int updatedAngle;

    // case angle of the nonT is pi/2 (Pauli)
    if(nonTgateRotation.angle == 0){
        // the basis is unchanged and the angle is flip
        updatedXbasis = tgateRotation.xBasis;
        updatedZbasis = tgateRotation.zBasis;
        updatedAngle = -1 * tgateRotation.angle;}
    // case angle is +/-pi/4 (Clifford)
    else{

        // the updated basis is nonT x T
        updatedXbasis = nonTgateRotation.xBasis ^ tgateRotation.xBasis;
        updatedZbasis = nonTgateRotation.zBasis ^ tgateRotation.zBasis;

        // exp(-i nonT)exp(-i T) = exp(-i (-i nonT x T))exp(-i nonT)
        updatedAngle  = tgateRotation.angle;
        if (nonTgateRotation.angle < 0)
            updatedAngle = -1 * updatedAngle ;

        // Number of Y in nonT and T
        bitset<numQubits> nonTY = nonTgateRotation.xBasis & nonTgateRotation.zBasis ;
        bitset<numQubits> TY = tgateRotation.xBasis & tgateRotation.zBasis;

        // Parity check for permutation associate with Y = iXZ = -iZX

        //ZX
        if ((~nonTgateRotation.xBasis & nonTgateRotation.zBasis & tgateRotation.xBasis & ~tgateRotation.zBasis).count() % 2 == 1)
            updatedAngle = -1 * updatedAngle ;
        //XZX
        if ((nonTY & tgateRotation.xBasis & ~tgateRotation.zBasis).count() % 2 == 1)
            updatedAngle = -1 * updatedAngle ;

        //ZXZ
        if ((~nonTgateRotation.xBasis & nonTgateRotation.zBasis & TY).count() % 2 == 1)
            updatedAngle = -1 * updatedAngle ;

        //count the number of complex i apply
        if ((( nonTY.count() + TY.count() - (updatedXbasis & updatedZbasis).count()  + 1) % 4) != 0)
            updatedAngle = -1 * updatedAngle ;

    }

    Rotation commutationResponsesRotation = Rotation(updatedAngle, updatedXbasis, updatedZbasis);
    return commutationResponsesRotation;
}



Measure LysCompiler::applyCommutation(Rotation R1, Measure M1) {
    //Copy M1
    Measure new_measure_object   = Measure(M1.phase,M1.xBasis,M1.zBasis,M1.rotations);   //Output Measure
    new_measure_object.outputPosition = M1.outputPosition;

    //Rotation pi/2 change the phase
    if (R1.angle==0){
        new_measure_object.phase = !(new_measure_object.phase) ;
    }

    //Rotation pi/4, combine basis and change phase
    else if (abs(R1.angle)==2){
        new_measure_object.xBasis = R1.xBasis ^ M1.xBasis ;
        new_measure_object.zBasis = R1.zBasis ^ M1.zBasis ;


        // Number of Y in R and M
        bitset<numQubits> RY = R1.xBasis & R1.zBasis ;
        bitset<numQubits> MY = M1.xBasis & M1.zBasis;

        // Parity check for permutation associate with Y = iXZ = -iZX
        //ZX
        if ((~R1.xBasis & R1.zBasis & M1.xBasis & ~M1.zBasis).count() % 2 == 1){
            new_measure_object.phase = !(new_measure_object.phase);
        }
        //XZX
        if ((RY & M1.xBasis & ~M1.zBasis).count() % 2 == 1){
            new_measure_object.phase = !(new_measure_object.phase);
        }

        //ZXZ
        if ((~R1.xBasis & R1.zBasis & MY).count() % 2 == 1){
            new_measure_object.phase = !(new_measure_object.phase);
        }
        //count the number of complex i apply
        int numberOfComplexFromInitalGate = (RY.count() + MY.count() - (new_measure_object.xBasis & new_measure_object.zBasis).count());
        if (((numberOfComplexFromInitalGate % 2) == 1) & (numberOfComplexFromInitalGate > 0)){
            new_measure_object.phase = !(new_measure_object.phase);
        }

        if (R1.angle == -2){
            new_measure_object.phase = !(new_measure_object.phase);
        }

    }
    //make sure there is no other angle sent
    else {
        throw invalid_argument( "Rotation must be Clifford or Pauli" );
        return new_measure_object;
    }
    for(int idxCRot = 0 ; idxCRot < M1.rotations.size() ; idxCRot++){
        Rotation cRot = new_measure_object.rotations[idxCRot] ;
        if (!cRot.isCommute(R1)){
            new_measure_object.rotations[idxCRot] = applyCommutation(R1,cRot);
        }

    }

    return new_measure_object;
}


void LysCompiler::pushTForwardThread(vector<shared_ptr<Operation>> & flattenGates, int beginIndex, int endIndex, vector<int> &threadSplitIndices, int threadOrderIndex){

    //base case the flattenGates is empty
    if((int)flattenGates.size() == 0){
        threadSplitIndices[threadOrderIndex] = 0;
        return;
    }

    //find the first nonT within the range
    int firstNontgateIndex = (int)flattenGates.size();
    for(int gateIndex = beginIndex; gateIndex < endIndex; ++gateIndex){
        //        shared_ptr<Operation> pGate = flattenGates[gateIndex];
        if (flattenGates[gateIndex]->isRotation()) {
            shared_ptr<Operation> pRot = static_pointer_cast<Rotation>(flattenGates[gateIndex]);
            if (!pRot->isTgate()){
                firstNontgateIndex = gateIndex;
                break;
            }
        }
        else {
            firstNontgateIndex = gateIndex;
            break;
        }
    }

    //only T gates in the range
    if(firstNontgateIndex > endIndex - 1){
        threadSplitIndices[threadOrderIndex] = endIndex ;
        return;
    }

    // loop from the gate after the first nonT through the end of the range
    int offset = firstNontgateIndex;
    shared_ptr<Rotation> pCurrent_r;
    Operation previous_g;
    shared_ptr<Rotation> pPrevious_g;

    for(int gateIndex = offset + 1; gateIndex < endIndex; ++gateIndex){
        if (flattenGates[gateIndex]->isRotation() && flattenGates[gateIndex]->isTgate()) {
            // if the current gate is a T gate
            pCurrent_r = static_pointer_cast<Rotation>(flattenGates[gateIndex]);
            int pivot = gateIndex;
            //commute it until it is before the first nonT gate
            while(pivot > firstNontgateIndex){

                pPrevious_g = static_pointer_cast<Rotation>(flattenGates[pivot - 1]);

                // look if the current gate commute with the gate before
                previous_g = *flattenGates[pivot - 1];

                if(!pCurrent_r->isCommute(previous_g)){
                    //if not, apply commutation
                    Rotation commutationResultsRotation = applyCommutation(*pPrevious_g, *pCurrent_r);
                    //update the T gate
                    pCurrent_r->xBasis = commutationResultsRotation.xBasis;
                    pCurrent_r->zBasis = commutationResultsRotation.zBasis;
                    pCurrent_r->angle = commutationResultsRotation.angle;
                }
                // commute the nonT and the T
                flattenGates[pivot] = move(flattenGates[pivot - 1]);
                flattenGates[pivot - 1] = pCurrent_r;
                // update the index of the Tgate
                pivot -= 1;
            }
            //update the index of the first nonT gate
            firstNontgateIndex = firstNontgateIndex + 1;

        }

    }

    //update the next threa so it start where the first nonT gate is
    threadSplitIndices[threadOrderIndex] = firstNontgateIndex;
    return;
}




vector<int> LysCompiler::implementationPushTForward(vector<shared_ptr<Operation>> & flattenGates, int numThreads, int begin, int subsetEnd){
    int end;
    vector<int> splitIndices(numThreads,0);
    int subVectorLength = (subsetEnd - begin) / numThreads;
    std::thread threadsVector[numThreads];

    //    start each thread
    for(int idxThread = 0 ; idxThread < numThreads - 1 ; ++idxThread) {
        end = begin + subVectorLength ;
        //        flattenGates[end]
        std::thread threadFlattenGate([&flattenGates, begin, end, &splitIndices, idxThread]() { return pushTForwardThread(flattenGates, begin, end, splitIndices, idxThread); });
        threadsVector[idxThread] = std::move(threadFlattenGate);
        begin = end;
    }
    end = subsetEnd ;
    std::thread threadFlattenGate([&flattenGates, begin, end, &splitIndices, numThreads]() { return pushTForwardThread(flattenGates, begin, end, splitIndices, numThreads-1) ; });
    threadsVector[numThreads - 1] = std::move(threadFlattenGate);

    //wait for all thread to finish
    for(int threadIndex = 0; threadIndex < numThreads; threadIndex++){
        threadsVector[threadIndex].join();
    }

    return {splitIndices[0], splitIndices[splitIndices.size() - 1]};
}




int LysCompiler::pushTForward(vector<shared_ptr<Operation>> &  flattenGates){

    //initial number of threads
    int numThreads = (int)flattenGates.size() / 100 ;
    numThreads = (50 < numThreads ) ? 50 : numThreads;          // take at most 50 threads, but insure that there is at least 100 gates in each thread

    pair<vector<shared_ptr<Operation>>, vector<shared_ptr<Operation>>> forwardedGates ;  //output

    //variable for the threads:
    //  -first element : index at which the threads start (inclusive)
    //  -second element : index at which the threads end (exclusive)
    vector<int> resultItr = {0,(int)flattenGates.size()};


    //each threads must have at least 100 elements, and the number of threads must be greater than one
    while( numThreads > 1){
        resultItr = this->implementationPushTForward(flattenGates,numThreads,resultItr[0],resultItr[1]);
        numThreads = numThreads - 1 ;
    }

    //final run
    resultItr = this->implementationPushTForward(flattenGates,1,resultItr[0],resultItr[1]);

    return resultItr[0];
}




void LysCompiler::reduceLayerGreedyAlgoThread(vector<vector<shared_ptr<Operation>>> &circuitLayers, bool &change){
    //initialization of the variable
    int currentLayerIndex     = 0;
    bool done                 = false;  // indicate the layering process is done or not
    bool beginOfMeasure       = false;  // set to true the moment when we encounter a Measure. The input data always has all Measures at the end of the circuit, with no Rotation mixed in between measures
    vector<shared_ptr<Operation>> currentLayer = {};
    vector<shared_ptr<Operation>> nextLayer    = {};

    //go through all layer until it converge
    while(!done){
        done = true;
        currentLayerIndex = 0;
        // loop over all layers in circuitLayers
        while(currentLayerIndex < (int)circuitLayers.size() - 1){
            currentLayer = circuitLayers[currentLayerIndex];        //first layer to process
            vector<int> indicesOfAddedToCurrentLayer ;              //Index of rotation in next layer to add to current layer ?
            vector<shared_ptr<Operation>> addToCurrentLayer ;                        //Rotation in next layer to add to current layer

            // if the currentLayer is empty, erase it and start the next iteration
            if((int)currentLayer.size() == 0){
                circuitLayers.erase(circuitLayers.begin() + currentLayerIndex);
                continue;
            }

            else{
                nextLayer    = circuitLayers[currentLayerIndex + 1];       //second, or next, layer to process
                bool commute = false; // indicate whether the item from the next layer commutes with the elements in the current layer

                //loop over all Rotation in next layer
                for(int nextLayerGateIndex = 0; nextLayerGateIndex < (int)nextLayer.size(); nextLayerGateIndex++){
                    shared_ptr<Rotation> nextLayerGate;
                    if (nextLayer[nextLayerGateIndex]->isRotation()) {
                        // if the next element is a Rotation, proceed normally
                        nextLayerGate = static_pointer_cast<Rotation>(nextLayer[nextLayerGateIndex]);
                    }
                    else{
                        // if the next element is a Measure, break. We do not layer the Measures and all measures should stay where they are in the circuit
                        beginOfMeasure = true;
                        commute        = false;
                        break;
                    }

                    // Go through the following is the next element is a Rotation
                    // check if the rotation in next layer commute with ALL rotation in current layer
                    for(int currentLayerGateIndex = 0; currentLayerGateIndex < (int)currentLayer.size(); currentLayerGateIndex++){
                        Operation currentLayerGate = *(currentLayer[currentLayerGateIndex]);
                        commute = nextLayerGate->isCommute(currentLayerGate);
                        if(commute == false){
                            break;
                        }
                    }

                    // if nextLayerGate commute with ALL rotation in current layer, we will add it to the current layer
                    if(commute){
                        addToCurrentLayer.emplace_back(nextLayer[nextLayerGateIndex]);
                        indicesOfAddedToCurrentLayer.emplace_back(nextLayerGateIndex);
                        done = false;           //A rotation have been remove from a layer to another, which may allows other change
                        change = true ;         //change happend
                    }
                }

                //Add rotations to the current layer
                circuitLayers[currentLayerIndex].insert(circuitLayers[currentLayerIndex].end(), addToCurrentLayer.begin(), addToCurrentLayer.end());

                if (nextLayer.size() != addToCurrentLayer.size()){
                    //case NOT ALL rotations in nextLayer were added
                    // Remove rotation added from the end since we are removing with indices.
                    for(int gateIndex = (int)addToCurrentLayer.size() - 1; gateIndex >= 0; --gateIndex){
                        int transferredGateIndexInNextLayer = indicesOfAddedToCurrentLayer[gateIndex];
                        circuitLayers[currentLayerIndex + 1].erase(circuitLayers[currentLayerIndex + 1].begin() + transferredGateIndexInNextLayer);
                    }
                    //current layer becomes next layer, ++nextLayer
                    ++currentLayerIndex;
                }
                else{
                    //case all gate in next layer were added to current layer, erase next layer
                    circuitLayers.erase(circuitLayers.begin()+currentLayerIndex+1);
                }
                // break from the while if sees a Measure
                if (beginOfMeasure){
                    break;
                }
            }
            // break from the while if sees a Measure
            if (beginOfMeasure){
                break;
            }
        }
        beginOfMeasure = false;
    }
    return;
}


vector<vector<shared_ptr<Operation>>> LysCompiler::reduceLayerGreedyAlgo(vector<shared_ptr<Operation>> &circuitVec){

    int numLayers = circuitVec.size();

    // layers of gates. Within each layer, all gates mutually commute
    vector<vector<shared_ptr<Operation>>> circuitLayers(numLayers);
    //initialization: one gate per layer
    for(int layerIndex = 0; layerIndex < numLayers; ++layerIndex){
        circuitLayers[layerIndex] = {circuitVec[layerIndex]};
    }

    int numThreads = 50 ;
    bool change = true;
    vector< vector< vector<shared_ptr<Operation> > > > slicedVect(numThreads);
    vector<std::thread> threadsVector(numThreads);
    while(numLayers > 100 && change){

        // deep copy the layers into a slicedVect in order to pass it to the threads
        int numGatesInThread = (numLayers / numThreads);

        int endIndex = 0;
        int beginIndex = 0;
        for(int index = 0; index < numThreads; ++index){
            beginIndex = index * numGatesInThread;
            if(index == numThreads - 1 )
                endIndex = numLayers;
            else
                endIndex = (index + 1) * numGatesInThread;
            auto beginIdx = circuitLayers.begin() + beginIndex ;
            auto endIdx = circuitLayers.begin() +endIndex ;
            vector< vector<shared_ptr<Operation>> > subVector(endIndex-beginIndex);
            copy(beginIdx,endIdx,subVector.begin());
            slicedVect[index] = subVector;
        }

        //start the threads
        bool changeHappened[50] = {false};

        for(int layerIdx = 0 ; layerIdx < numThreads ; ++layerIdx){
            std::thread threadFlattenGate([&slicedVect, &changeHappened, layerIdx, this]() { return reduceLayerGreedyAlgoThread(slicedVect[layerIdx], changeHappened[layerIdx]); });
            threadsVector[layerIdx]=std::move(threadFlattenGate);
        }

        //wait for all threads to be done
        for(int threadIndex = 0; threadIndex < numThreads; threadIndex++)
            threadsVector[threadIndex].join();

        //update the output and see if any change ocurred
        circuitLayers.clear();
        change = false;
        for(int sliceIndex = 0; sliceIndex < numThreads; ++sliceIndex ){
            circuitLayers.insert(circuitLayers.end(), slicedVect[sliceIndex].begin(), slicedVect[sliceIndex].end());
            change = change || changeHappened[sliceIndex];
        }

        //update the first condition
        numLayers = circuitLayers.size();

    }

    //final run
    change = true;
    while(change){
        change = false;
        reduceLayerGreedyAlgoThread(circuitLayers, change);
    }

    return circuitLayers;
}


int LysCompiler::optimizeRotation(){
    bool changedFlag = true;
    int numOfTgates = 0;
    vector<shared_ptr<Operation>> pushedBackNonT;

    while(changedFlag){
        changedFlag = false;

        //step 1. Push all T gates in the circuit to the beginning of the circuit
        numOfTgates = this->pushTForward(this->circuit);

        // all nonT are in pushedBackNonT (no T gates). Each round, the new nonTgates comes from the previous section of T+nonT mixsure and therefore, we must insert at the beginning of pushedBackNonT
        vector<shared_ptr<Operation>> tgates (this->circuit.begin(), this->circuit.begin() + numOfTgates);
        pushedBackNonT.insert(pushedBackNonT.begin(), this->circuit.begin() + numOfTgates, this->circuit.end());

        //step 2. Reduce the T gates layers by partitioning them into layers where all T gates mutually commute within the same layer
        vector<vector<shared_ptr<Operation>> > reduced_T_Layers = this->reduceLayerGreedyAlgo(tgates);

        //step 3. For each T layer, comebine them into pi/4 or pi/2 rotations when possible. Set changeFlag if such a combination occurs
        for(int layerIndex = 0; layerIndex < (int)reduced_T_Layers.size(); ++layerIndex){
            changedFlag = this->noOrderingRotationCombination(reduced_T_Layers[layerIndex]) || changedFlag;
        }

        // update the circuit, with the T gates that have been through the reduction step (T and nonT)
        this->circuit = {};
        // Here we are essentially flattening the layered gates into a vector.
        // Notice that the nonT gates from step 1 are not included. This is done to save processing time since we do not need to process pushed back nonT gates in subsequent rounds
        for(vector<shared_ptr<Operation>> layer : reduced_T_Layers)
            this->circuit.insert(this->circuit.end(), layer.begin(), layer.end());
    }

    //step 5

    // put nonT into layer
    vector<vector<shared_ptr<Operation>> > reduced_NonT_layers = this->reduceLayerGreedyAlgo(pushedBackNonT);

    // combine nonT within layer and flatten out the nonT layers into a vector
    pushedBackNonT = {};
    for(int layerIndex = 0; layerIndex < (int)reduced_NonT_layers.size(); ++layerIndex){
        this->noOrderingRotationCombination(reduced_NonT_layers[layerIndex]);
        pushedBackNonT.insert(pushedBackNonT.end(), reduced_NonT_layers[layerIndex].begin(), reduced_NonT_layers[layerIndex].end());
    }

    // At this point, this->circuit holds all the pushed forward T gates and the remaining nonT gates are stored in pushedBackNonT
    numOfTgates = this->circuit.size();

    // //return t and nont separately.

    // Insert the pushed back nonT gates at the end of the circuit
    this->circuit.insert(this->circuit.end(), pushedBackNonT.begin(), pushedBackNonT.end());

    // return t_nonT_pair;
    return numOfTgates;
}



int LysCompiler::RearrangeCliffordGates(int idxOfTGates,int idxLastRotation){
    // Change is made in-place to lst_clifford

    int start_idx_single_qubit = idxLastRotation+1;
    //     Operation op;
    shared_ptr<Operation> pOper;
    // look how many 1Qubit rotations are already at the end
    for (int idx = idxLastRotation; idx > idxOfTGates ; idx = idx - 1){
        pOper = this->circuit[idx];
        if (pOper->isSingleQubit()){
            start_idx_single_qubit = start_idx_single_qubit - 1;
        }
        else {
            break ;
        }
    }

    // Push the 1qubit rotations to the end of the circuit if they commute
    // or stop when the do not commute anymore
    for (int current_clifford_idx = start_idx_single_qubit-2 ; current_clifford_idx > idxOfTGates ; current_clifford_idx = current_clifford_idx - 1 ){
        shared_ptr<Operation> pCurrent_cliff = this->circuit[current_clifford_idx] ;   //First rotation to check
        bool commuteToTheEnd = true ;                               //Did it commute all the way?
        //Is the first rotation a 1 qubit rotation ?
        if(pCurrent_cliff->isSingleQubit()){
            int current_clifford_idx_dynamic = current_clifford_idx ;
            while(current_clifford_idx_dynamic < start_idx_single_qubit - 1){   //permute it with the next one if they commute
                shared_ptr<Operation> pNext_cliff = this->circuit[current_clifford_idx_dynamic + 1];
                if (pCurrent_cliff->isCommute(*pNext_cliff)){
                    this->circuit[current_clifford_idx_dynamic] = pNext_cliff ;
                    current_clifford_idx_dynamic = current_clifford_idx_dynamic + 1;
                    this->circuit[current_clifford_idx_dynamic] = pCurrent_cliff ;
                }
                else {
                    commuteToTheEnd = false ;   //current_clifford_gate did not commute to the end
                    break;
                }
            }
            //if current_clifford_gate did commute to the end, update the tracker
            if (commuteToTheEnd){
                start_idx_single_qubit = start_idx_single_qubit - 1 ;
            }
        }
    }

    return start_idx_single_qubit;
}


int LysCompiler::basis_permutation(int numOfTGates) {
    int idxOfTGates = numOfTGates - 1;
    // list_of_gates is the list of clifford and measures
    // find the index of the last clifford gate before measure (from the beginning of the list)
    int idxGate = this->circuit.size()-1 ;
    // maksOverall shows which qubits are measured for all measures in this section
    // e.g., 1110 means measuring the 0th, 1st, and 2nd qubit, not measuring the 3rd. Convention is from left to right, LSB on the left
    bitset<numQubits> maskOverall ;
    // maksAncilla shows which qubits are ancillas in this section. 1 means this position is ancilla
    bitset<numQubits> maskAncilla ;

    //Note: re-verify mask ancilla operation
    while (idxGate>idxOfTGates){
        if (!this->circuit[idxGate]->isRotation()){
            shared_ptr<Measure> MeasureOnAllQubits = static_pointer_cast<Measure>(this->circuit[idxGate]);
            idxGate     = idxGate - 1;
            maskOverall = maskOverall | (MeasureOnAllQubits->xBasis | MeasureOnAllQubits->zBasis); // update the total measurement count
            maskAncilla.set();
            maskAncilla = maskAncilla >> ancillaBegin ;
        }
        else{
            break;
        }
    }

    this->RearrangeCliffordGates(idxOfTGates,idxGate);   // Move all 1-QuBit rotation that commute to the end

    // Combine Rotation from last to first
    int idxR = idxGate ;
    int numberOfCummutedGate = 0;   // the commuted gate should remain in the circuit and not be erased
    int idxLastM = this->circuit.size() - 1; // initial value

    while( idxR > idxOfTGates){
        //to Measure from first to last
        Rotation R;
        shared_ptr<Rotation> pR;
        if (this->circuit[idxR]->isRotation()){
            pR = static_pointer_cast<Rotation>(this->circuit[idxR]);
            R = *pR;
        }
        else{
            cout << "Fatal error. This should be a rotation but it is a Measure instead!!!" << endl;
        }

        // test to see if we "Do nothing"
        // Do thing if the following cases are both true:
        // if R is not Rd; if R belongs in M (Ra is included in M)
        // mask_anc | R | M == mask_anc | R
        bool doSomething  = true;
        char block_action = R.blockAction(this->ancillaBegin) ;      // decide the type of action required. See Rotation.hpp for definition
        //case: Rotation acts only on ancilla and they are not all deallocated afterward
        if (block_action == 'a') {
            if ((maskAncilla & (R.xBasis | R.zBasis) & maskOverall) != (maskAncilla & (R.xBasis | R.zBasis))) {
                // we do nothing
                doSomething = false;
                idxGate++;
            }
        }
        else{
            //case : Rotation acts on both data and ancilla and some ancilla are deallocated
            if (block_action == 'b'){
                if ((maskAncilla & (R.xBasis | R.zBasis) & maskOverall) != 0) {
                    // we do nothing
                    doSomething = false;
                    idxGate++;
                }
            }
        }

        // otherwise, we apply the commutation rules and absorb the rotations into measurements
        if (doSomething){
            for(int idxM = idxGate+1 ; idxM <= idxLastM ; idxM++ ){
                shared_ptr<Operation> pM = this->circuit[idxM];

                // variable mask only shows which qubits are measured for the current measure M at index idxM
                // e.g. 001 means measuring the 0th and 1st qubit, not measuring the 2nd qubit
                bitset<numQubits> mask_reverse = ~(pM->xBasis | pM->zBasis); // 0s shows the qubits which are measured

                // Can it be absorbed ? If it anticommutes with R, change list_of_measurements
                // otherwise the measurement commutes with the rotation; do nothing (ignore the rotation)
                if (!R.isCommute(*pM)){ // if M is a R, still holds
                    if(!this->circuit[idxM]->isRotation()) {
                        shared_ptr<Measure> pMea = static_pointer_cast<Measure>(this->circuit[idxM]);
                        this->circuit[idxM] = make_shared<Measure>(this->applyCommutation(R, *pMea)); // might not be a measure. tno try and catch.
                    }
                    else {
                        shared_ptr<Rotation> pRot = static_pointer_cast<Rotation>(this->circuit[idxM]);
                        this->circuit[idxM] = make_shared<Rotation>(this->applyCommutation(R, *pRot)); // might not be a measure. tno try and catch.
                    }
                }
                else{
                    // If they does commute but M is classically controlled, look if R commute with c-Rs
                    if (!this->circuit[idxM]->isRotation()){
                        shared_ptr<Measure> pMeas = static_pointer_cast<Measure>(this->circuit[idxM]);
                        Measure Meas = *pMeas;
                        for(int idxCRot = 0 ; idxCRot < Meas.rotations.size() ; idxCRot++){
                            Rotation cRot = Meas.rotations[idxCRot] ;
                            if (!cRot.isCommute(R)){
                                Meas.rotations[idxCRot] = applyCommutation(R,cRot);
                            }

                        }
                        this->circuit[idxM] = pMeas;
                    }

                }
            }

            // Decide if we erase the rotation or move it to be right after M
            // If R is Ra and all Ra is included in M > deallocate and erase the Ras
            bool moveAfterMeasure = true;
            if (R.blockAction(this->ancillaBegin) == 'a') {
                // cout << " Checking block == a" << endl;
                if ((maskAncilla & (R.xBasis | R.zBasis) & maskOverall) == (maskAncilla & (R.xBasis | R.zBasis))) {
                    // we erase the R
                    this->circuit.erase(this->circuit.begin() + idxR);
                    idxLastM--;
                    moveAfterMeasure = false;
                }
            }

            // Move the R to be right after the Ms. Preserve the order of Rs after moving to be after Ms
            if (moveAfterMeasure) {
                numberOfCummutedGate++;
                this->circuit.erase(this->circuit.begin() + idxR);
                this->circuit.insert(this->circuit.begin() + idxLastM, pR);
                idxLastM--;
            }
        }
        else{
            break;
        }

        idxR = idxR - 1;
        idxGate = idxGate - 1;
    }
    return numberOfCummutedGate;
}


pair<vector<vector<shared_ptr<Operation>>>,int> LysCompiler::runLysCompiler(bool combine, bool layer){
    //reduce gate count
    auto startTime1 = chrono::system_clock::now();
    int numOfTgates = this->optimizeRotation();

    int startingIdxToRemoveAfterMeasure;
    if (combine){
        int numOfCommutedCliffords = this->basis_permutation(numOfTgates);
        startingIdxToRemoveAfterMeasure = this->circuit.size() - numOfCommutedCliffords; // update the startingIdxToRemoveAfterMeasure to include the T gates inserted
    }

    vector<vector<shared_ptr<Operation>>> layerC ;

    auto endTime1 = chrono::system_clock::now();
    chrono::duration<double> elapsed_seconds1 = endTime1-startTime1;
    cout << "Done\n";
    cout << "elapsed time: " << elapsed_seconds1.count() << "s\n";

    cout << "Total gates: " << (int)size(this->circuit) << "\n";
    cout << "T gates: " << numOfTgates << "\n";
    cout << "Remove after measure: " << startingIdxToRemoveAfterMeasure << "\n";

    return make_pair(layerC, startingIdxToRemoveAfterMeasure);
}
