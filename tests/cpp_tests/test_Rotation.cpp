#include "../cpp_compiler/Operation.hpp"
#include "../cpp_compiler/Measure.hpp"
#include "../cpp_compiler/Rotation.hpp"
#include <vector>
#include <iostream>

using namespace std;


int Test_isTgate()
{
    vector<char> x = {'x'};
    vector<char> z = {'z'};
    Rotation Xpi8 = Rotation(1,x,{0});
    vector<char> emptyc = {};
    Rotation I    = Rotation(1,emptyc,{});
    Rotation Zpi2 = Rotation(0,z,{0});
    Rotation Zpi4 = Rotation(-2,z,{0}); 

    vector<Rotation> cases = {Xpi8, I, Zpi2, Zpi4};
    vector<bool> expected = {true,false,false,false};

    for(int idx = 0 ; idx < cases.size() ; ++idx){
        if (expected[idx] != cases[idx].isTgate()){
            cout << "case " << idx << " failed\n" ;
            return 1;
        }
    }
    
    cout << "isTgate passed\n" ;
    return 0;
}

int test_eq(){
    vector<char> x = {'x'};
    vector<char> z = {'z'};
    vector<char> emptyc = {};
    
    //TODO : Add test for bitset constructor (to help understand the indexing)
    Rotation Xpi8_2  = Rotation(1,"01","00");
    Rotation Xpi8   = Rotation(1,x,{Xpi8_2.xBasis.size()-1});
    Rotation Xpi8n  = Rotation(-1,"01","00");
    Rotation Zpi2_2 = Rotation(0,"00","01");
    Rotation Zpi2   = Rotation(0,z,{Xpi8_2.xBasis.size()-1});
    Rotation I1     = Rotation(0,emptyc,{});
    Rotation I2     = Rotation(0,"00","00");

    vector<Rotation> cases    = {Xpi8,Xpi8_2, Xpi8n, Zpi2, Zpi2_2, I1, I2} ;
    vector<bool> expected = {true,false,false,true,false,true} ; 

    for(int idx = 1 ; idx <= expected.size() ; ++idx){
        bool result = (cases[idx-1]==cases[idx]);
        if (expected[idx-1] != result){
            cout << cases[idx-1].toStr();
            cout << cases[idx].toStr();
            cout << "Equality case " << idx-1 << "-"<< idx << " failed\n" ;
            return 1;
        }
    }
        
    cout << "eq passed\n" ;
    return 0;
}

int test_blockAction() {
    // Define four rotations. The circuit has five qubits, the first three are data and last two ancilla
    vector<char> x1 = {'x','x','x'};
    vector<char> x2 = {'x'};
    vector<char> x3 = {'x', 'x','z','z','z'};
    Rotation R1 = Rotation(1, x1, {0, 1, 2});    // only act on data qubits
    Rotation R2 = Rotation(1, x2, {4});          // only act on ancilla
    Rotation R3 = Rotation(1, x3, {0,1,2,3,4});  // act on both data and ancilla
    Rotation I1 = Rotation(0, vector<char> {}, {});           // identity
    int ancBeginIdx = 3;                            // ancilla begins at index 3

    vector<Rotation> cases = {R1, R2, R3, I1};
    vector<char> expected  = {'d','a','b','a'};

    for (int i =0; i < cases.size(); i++) {
        if (cases[i].blockAction(ancBeginIdx) != expected[i]) {
            cout << "blokAction case " << i << " failed\n";
            return 1;
        }
    }

    cout << "blockAction passed\n";
    return 0;

}

int main(){
    if (Rotation(0,"0","1").xBasis.size() < 5){
        cout << "Error: Test_Rotation needs to be compile for at least 5 Qubits\n" ;
        return 1;
    }
    vector<int> results = {Test_isTgate(), test_eq(), test_blockAction()};
    int count  = 0 ;
    int nTests = results.size();
    for (int idx = 0 ; idx < nTests ; ++idx) {
        count = count + results[idx];
    }
    cout << "------------------------------------------\n";
    cout << "Tests passed in test_Rotation: " << nTests-count << "/" << nTests <<"\n";
    cout << "------------------------------------------\n";
    return 0;
}