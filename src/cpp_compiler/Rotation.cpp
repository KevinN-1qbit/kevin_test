#include "Rotation.hpp"

using namespace std;

Rotation::Rotation() {}

Rotation::Rotation(int angle, bitset<numQubits> xBasis, bitset<numQubits> zBasis)
{
    this->angle = angle;
    this->xBasis = xBasis;
    this->zBasis = zBasis;
}

Rotation::Rotation(int angle, vector<char> basis, vector<int> qubits)
{
    //    Operation newOp = Operation(basis,qubits);
    this->angle = angle;
    if (basis.size() != qubits.size()) /// Basis and Qubits vectors must be of the same size.
        throw invalid_argument("Illegal declaration. Number of basis and number of qubits must be equal and the qubits must be unique.");
    /// In the following statements we create an encoding of the x and z basis as integers.
    /// The purpose of this is to increase the processing speed.

    long long unsigned xBasisInteger = 0;
    long long unsigned zBasisInteger = 0;

    if (basis.size() != 0)
    {
        for (int index = 0; index < basis.size(); index++)
        {
            char basisElem = basis[index];
            if (basisElem == 'x')
                xBasisInteger += (int)pow(2, numQubits - 1 - (qubits[index]));
            else if (basisElem == 'z')
                zBasisInteger += (int)pow(2, numQubits - 1 - (qubits[index]));
            else if (basisElem == 'y')
            {
                xBasisInteger += (int)pow(2, numQubits - 1 - (qubits[index]));
                zBasisInteger += (int)pow(2, numQubits - 1 - (qubits[index]));
            }
            else
                throw invalid_argument("Unknown basis");
        }
    }

    this->xBasis = bitset<numQubits>(xBasisInteger);
    this->zBasis = bitset<numQubits>(zBasisInteger);
}

Rotation::Rotation(int angle, string xBasis, string zBasis)
{
    this->angle = angle;
    this->xBasis = bitset<numQubits>(xBasis);
    this->zBasis = bitset<numQubits>(zBasis);
}

bool Rotation::operator==(Rotation const &rotation) const
{
    return (this->xBasis == rotation.xBasis && this->zBasis == rotation.zBasis && this->angle == rotation.angle) || (this->isIdentity() && rotation.isIdentity());
}

bool Rotation::operator!=(Rotation const &rotation) const
{
    return (this->xBasis != rotation.xBasis || this->zBasis != rotation.zBasis || this->angle != rotation.angle) && !(this->isIdentity() && rotation.isIdentity());
}

bool Rotation::isTgate()
{
    if (this->isIdentity())
        return false;
    else
        return abs(this->angle) == 1;
}

bool Rotation::isRotation()
{
    return true;
}

char Rotation::blockAction(int ancillaBegin)
{
    bitset<numQubits> xOrz = this->xBasis | this->zBasis;

    // Note: Optimize more if required
    bitset<numQubits> maskData; // = pow(2, this->numQubits - ancillaBegin) - 1;
    maskData.set();
    maskData = maskData << (numQubits - ancillaBegin);
    bitset<numQubits> maskAncilla = ~maskData;

    if ((maskData & xOrz) == 0)
    {
        return 'a';
    }
    if ((maskAncilla & xOrz) == 0)
    {
        return 'd';
    }
    return 'b';
}

int Rotation::getAngle()
{
    return angle;
}

string Rotation::toStr()
{

    string rotation_str;
    string angle = to_string(this->angle);
    string x = this->xBasis.to_string();
    string z = this->zBasis.to_string();
    for (int i = 0; i < numQubits; i++)
    {
        if (x[i] == '1' & z[i] == '0')
        {
            rotation_str += 'X';
        }
        else if (x[i] == '0' & z[i] == '1')
        {
            rotation_str += 'Z';
        }
        else if (x[i] == '1' & z[i] == '1')
        {
            rotation_str += 'Y';
        }
        else if (x[i] == '0' & z[i] == '0')
        {
            rotation_str += 'I';
        }
        else
        {
            cout << "errror\n";
        }
    }

    return "R" + angle + " " + rotation_str + "\n";
}
