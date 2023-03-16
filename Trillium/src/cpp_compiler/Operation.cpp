#include "Operation.hpp"

using namespace std;

Operation::Operation(){};

Operation::Operation(std::string xBasis, std::string zBasis){
    this->xBasis = bitset<numQubits>(xBasis);
    this->zBasis = bitset<numQubits>(zBasis);
}

Operation::Operation(vector<char> basis, vector<int> qubits){
        
    if(basis.size() != qubits.size())   /// Basis and Qubits vectors must be of the same size.
        throw invalid_argument( "Illegal declaration. Number of basis and number of qubits must be equal and the qubits must be unique." );
    /// In the following statements we create an encoding of the x and z basis as integers.
    /// The purpose of this is to increase the processing speed.

    long long unsigned xBasisInteger = 0;
    long long unsigned zBasisInteger = 0;
    
    if(basis.size() != 0){
        for(int index = 0; index < basis.size(); index++){
            char basisElem = basis[index];
            if(basisElem == 'x')
                xBasisInteger += (int)pow(2, numQubits - 1 - (qubits[index]));
            else if(basisElem == 'z')
                zBasisInteger += (int)pow(2, numQubits - 1 - (qubits[index]));
            else if(basisElem == 'y'){
                xBasisInteger += (int)pow(2, numQubits - 1 - (qubits[index]));
                zBasisInteger += (int)pow(2, numQubits - 1 - (qubits[index]));
            } else
                throw invalid_argument("Unknown basis");
        }
    }

    this->xBasis = bitset<numQubits>(xBasisInteger);
    this->zBasis = bitset<numQubits>(zBasisInteger);
}

bool Operation::isCommute(const Operation rhs) const{
    bitset<numQubits> xzDif = this->xBasis & rhs.zBasis;
    bitset<numQubits> zxDif = this->zBasis & rhs.xBasis;

    int num1sXZDiff = xzDif.count();
    int num1sZXDiff = zxDif.count();
    
    return ((num1sZXDiff + num1sXZDiff) % 2 == 0);
}

bool Operation::isIdentity() const{
    if(this->xBasis.count() == 0 && this->zBasis.count() == 0)
        return true;
    return false;
}

bool Operation::isSingleQubit() const{
    if((this->xBasis | this->zBasis).count() == 1)
        return true;
    return false;
}
bool Operation::isTgate(){
    return false;
}

bool Operation::isRotation(){
    return false;
}

std::string Operation::Print(){
    string numQubitsStr = "numQubits: " + to_string(numQubits) + "\n";
    string xBasisStr = "xBasis: " + this->xBasis.to_string() + " as binary." + "\n";
    string zBasisStr = "zBasis: " + this->zBasis.to_string() + " as binary." + "\n";
    return numQubitsStr + xBasisStr + zBasisStr;
}
