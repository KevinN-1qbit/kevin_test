#include "Measure.hpp"

using namespace std;

Measure::Measure(){}

Measure::Measure(bool phase, bitset<numQubits> xBasis, bitset<numQubits> zBasis){
    this->phase = phase;
    this->xBasis = xBasis;
    this->zBasis = zBasis;
}

Measure::Measure(bool phase, bitset<numQubits> xBasis, bitset<numQubits> zBasis, vector<Rotation> rotations){
    this->phase = phase;
    this->xBasis = xBasis;
    this->zBasis = zBasis;
    this->rotations = rotations;
}




Measure::Measure(bool phase, string xBasis, string zBasis, vector<Rotation> rotations){
    Operation newOp = Operation(xBasis,zBasis);
    this->phase = phase;
    this->xBasis = newOp.xBasis;
    this->zBasis = newOp.zBasis;
    this->rotations = rotations;
}
Measure::Measure(bool phase, string xBasis, string zBasis){
    Operation newOp = Operation(xBasis,zBasis);
    this->phase = phase;
    this->xBasis = newOp.xBasis;
    this->zBasis = newOp.zBasis;
}




Measure::Measure(bool phase, vector<char> basis, vector<int> qubits){
    Operation newOp = Operation(basis,qubits);
    this->phase = phase;
    this->xBasis = newOp.xBasis;
    this->zBasis = newOp.zBasis;
}
Measure::Measure(bool phase, vector<char> basis, vector<int> qubits, vector<Rotation> rotations){
    Operation newOp = Operation(basis,qubits);
    this->phase = phase;
    this->xBasis = newOp.xBasis;
    this->zBasis = newOp.zBasis;
    this->rotations = rotations;
}



bool Measure::operator==(Measure const& measure) const {
    return (this->xBasis == measure.xBasis && this->zBasis == measure.zBasis && this->phase == measure.phase && this->rotations == measure.rotations) || (this->isIdentity() && measure.isIdentity());
}

bool Measure::operator!=(Measure const& measure) const {
    return (this->xBasis != measure.xBasis || this->zBasis != measure.zBasis || this->phase != measure.phase || this->rotations != measure.rotations) && !(this->isIdentity() && measure.isIdentity());
}

bool Measure::isTgate(){
    return false;
}

bool Measure::isRotation(){
    return false;
}

bool Measure::isClassicalControlledRotation(){
    if (this->rotations == vector<Rotation>()){
        return false;
    }
    return true;
}


string Measure::toStr(){
    string phase;
    if (this->phase) phase = "+";
    else phase = "-";

    string rotation_str ;
    string x = this->xBasis.to_string();
    string z = this->zBasis.to_string();
    for (int i = 0 ; i < numQubits ; i++ ){
        if (x[i]=='1' & z[i]=='0'){
            rotation_str += 'X';
        }
        else if (x[i]=='0' & z[i]=='1'){
            rotation_str += 'Z';
        }
        else if (x[i]=='1' & z[i]=='1'){
            rotation_str += 'Y';
        }
        else if (x[i]=='0' & z[i]=='0'){
            rotation_str += 'I';
        }
        else {
            cout << "errror\n" ;
        }
    }

    if (this->isClassicalControlledRotation()){
        rotation_str += "\n Classically controlled Rotations \n" ;
        for(Rotation rot: this->rotations){
            rotation_str += rot.toStr();
        }
    }

    return "M" + phase + " " + rotation_str + "\n";
}
