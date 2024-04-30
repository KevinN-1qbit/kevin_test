
#include "../cpp_compiler/Measure.hpp"
#include "../cpp_compiler/Rotation.hpp"
#include <vector>
#include <iostream>

using namespace std;


int Test_isCommute()
{
    
    
    vector<char> x = {'x'};
    vector<int> zero = {0} ;
    Rotation X    = Rotation(0,x,zero);
    vector<char> y = {'y'};
    Rotation Y    = Rotation(0,y,zero);
    vector<char> z = {'z'};
    Rotation Z    = Rotation(0,z,zero);
    Rotation XY   = Rotation(0,vector<char> {'x','y'},{0,1}); 
    vector<int> one = {1};
    Rotation IZ   = Rotation(0,z,one);
    Rotation ZYZ  = Rotation(0,vector<char> {'z','y','z'},{0,1,2});
    Rotation XZY  = Rotation(0,vector<char> {'x','z','y'},{0,1,2});
 
    Measure MX   = Measure(0,x,zero);
    Measure MY   = Measure(0,y,zero);
    Measure MZ   = Measure(0,z,zero);
    Measure MXY  = Measure(0,vector<char> {'x','y'},{0,1});
    Measure MXZY = Measure(0,vector<char> {'x','z','y'},{0,1,2});

    vector< vector<Operation> > cases = {{X,Y,Z,XY,X,Y,Z,XY,ZYZ,X,Y,Z,XY,X,Y,Z,XY,ZYZ},{MX,MY,MZ,MXY,MY,MZ,MX,IZ,MXZY,X,Y,Z,XY,Y,Z,X,IZ,XZY}};
    vector<bool> expected = {true,true,true,true,false,false,false,false,false,true,true,true,true,false,false,false,false,false};

    for(int idx = 0 ; idx < cases[0].size() ; ++idx){
        if (expected[idx] != cases[0][idx].isCommute(cases[1][idx])){
            cout << cases[0][idx].Print() ;
            cout << cases[1][idx].Print() ;
            cout << "case " << idx << "failed\n" ;
            return 1;
        }
    }
    
    cout << "isCommute passed\n" ;
    return 0;
}

int test_isIdentity(){
    vector<char> x = {'x'};
    vector<int> zero = {0};
    Rotation XIII = Rotation(0,x,zero);
    vector<char> emptyc = {};
    vector<int> emptyi = {};
    Rotation III  = Rotation(0,emptyc,emptyi);

    vector<Rotation> cases    = {XIII,III} ;
    vector<bool> expected = {false,true} ;

    for(int idx = 0 ; idx < expected.size() ; ++idx){
        if (expected[idx] != cases[idx].isIdentity()){
            cout << "case " << idx << "failed\n" ;
            return 1;
        }
    }
        
    cout << "isIdentity passed\n" ;
    return 0;

}

int test_isSingleQubit(){
    vector<char> x = {'x'};
    vector<char> z = {'z'};
    vector<char> y = {'y'};
    vector<int> zero = {0};
    vector<int> one = {1};
    vector<int> three = {3};
    Rotation XIII = Rotation(0,x,zero);
    Rotation IZII = Rotation(0,z,one);
    Rotation IIIY = Rotation(0,y,three);
    Rotation YXII = Rotation(0,vector<char> {'y','x'},{0,1});
    Rotation YXZI = Rotation(0,vector<char> {'y','x','z'},{0,1,2});

    vector<Rotation> cases    = {XIII,IZII,IIIY,YXII,YXZI} ;
    vector<bool> expected = {true,true,true,false,false} ; 

    for(int idx = 0 ; idx < expected.size() ; ++idx){
        if (expected[idx] != cases[idx].isSingleQubit()){
            cout << "case " << idx << "failed\n" ;
            return 1;
        }
    }
        
    cout << "isSingleQubit passed\n" ;
    return 0;
}


int main(){
    if (Rotation(0,"0","1").xBasis.size() < 3){
        cout << "Error: Test_Operation needs to be compile for at least 3 Qubits\n" ;
        return 1;
    }
    vector<int> results = {Test_isCommute(),test_isIdentity(), test_isSingleQubit()};
    int count = 0 ;
    int nTests = results.size();
    for (int idx = 0 ; idx < nTests ; ++idx) {
        count = count + results[idx];
    }
    cout << "------------------------------------------\n";
    cout << "Tests passed in test_Operation: " << nTests-count << "/" << nTests <<"\n";
    cout << "------------------------------------------\n";
    return 0;
}