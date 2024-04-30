#include "../cpp_compiler/Operation.hpp"
#include "../cpp_compiler/Measure.hpp"
#include "../cpp_compiler/Rotation.hpp"
#include <vector>
#include <iostream>

using namespace std;

int test_eq(){
    vector<char> emptyc = {};
    vector<char> x = {'x'};
    vector<char> z = {'z'};
    Measure Xpi8   = Measure(true,x,{0});
    Measure Xpi8n  = Measure(false,x,{0});
    Measure Zpi2   = Measure(true,z,{0});
    Measure Zpi2_2 = Measure(true,z,{0});
    Measure I1     = Measure(false,emptyc,{});
    Measure I2     = Measure(true,emptyc,{});
    Measure Zcontrolled     = Measure(true,z,{0},{Rotation(0,x,{1})});
    Measure Zcontrolled2    = Measure(true,z,{0},{Rotation(0,x,{1})});
    Measure Zcontrolledz    = Measure(true,z,{0},{Rotation(0,z,{1})});

    vector<Measure> cases    = {Xpi8, Xpi8n, Zpi2, Zpi2_2, I1, I2,Zcontrolled,Zcontrolled2,Zcontrolledz} ;
    vector<bool> expected = {false,false,true,false,true,false,true,false} ; 

    for(int idx = 1 ; idx <= expected.size() ; ++idx){
        bool result = (cases[idx-1]==cases[idx]);
        if (expected[idx-1] != result){
            cout << cases[idx-1].toStr();
            cout << cases[idx].toStr();
            cout << "case " << idx-1 << "-"<< idx << " failed\n" ;
            return 1;
        }
    }
        
    cout << "eq passed\n" ;
    return 0;
}

int test_isClassicalControlledRotation(){
    vector<char> emptyc = {};
    vector<char> x = {'x'};
    vector<char> z = {'z'};
    Measure Xpi8   = Measure(true,x,{0});
    Rotation rot   = Rotation(false,vector<char> {'x','x'},{0,1});
    Measure Xpi8cc = Measure(true,x,{0},{rot});
    Measure Xpi8id = Measure(true,"01","00",{rot});

    if (Xpi8.isClassicalControlledRotation()){
        cout << Xpi8.toStr();
        cout << "isClassicalControlledRotation failed, case 0\n";
        return 1;
    }

    if (!Xpi8cc.isClassicalControlledRotation()){
        cout << Xpi8cc.toStr();
        cout << "isClassicalControlledRotation failed, case 1\n";
        return 1;
    }

    if (!Xpi8id.isClassicalControlledRotation()){
        cout << Xpi8id.toStr();
        cout << "isClassicalControlledRotation failed, case 2\n";
        return 1;
    }
    

    cout << "isClassicalControlledRotation passed\n" ;
    return 0;
}

int main(){
    if (Measure(false,"0","1").xBasis.size() < 2){
        cout << "Error: Test_Measure needs to be compile for at least 2 Qubits\n" ;
        return 1;
    }

    vector<int> results = {
        test_eq(),
        test_isClassicalControlledRotation()
    };
    int count = 0 ;
    int nTests = results.size();
    for (int idx = 0 ; idx < nTests ; ++idx) {
        count = count + results[idx];
    }
    cout << "------------------------------------------\n";
    cout << "Tests passed in test_Measure: " << nTests-count << "/" << nTests <<"\n";
    cout << "------------------------------------------\n";
    return 0;
}