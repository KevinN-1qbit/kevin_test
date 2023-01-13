#include "../cpp_compiler/LysCompiler.hpp"
#include <vector>
#include <iostream>

using namespace std;

int Test_defaultInitiatization()
{
    vector<char> x = {'x'};
    vector<char> z = {'z'};

    Rotation XIII = Rotation(1,x,{0});
    
    vector<Gate> flatten_gate(5,XIII);
    LysCompiler gatelist = LysCompiler(3,flatten_gate);
    vector<Gate> expected_measure = {Measure(true,z,{0}),Measure(true,z,{1}),Measure(true,z,{2})};
    if(expected_measure!=vector<Gate>(gatelist.circuit.begin()+5,gatelist.circuit.end())){
        toStrVariantVec(gatelist.circuit) ;
        toStrVariantVec(expected_measure) ;
        cout << "defaultInitialization failed\n";
        
        return 1;
    }

    cout << "defaultInitialization passed\n";
    return 0;
}


int Test_combineRotation(LysCompiler gatelist)
{
    vector<char> y = {'y'};
    vector<char> x = {'x'};
    vector<char> emptyc = {};
    Rotation III1        = Rotation(0,emptyc,{});
    Rotation III2        = Rotation(0,emptyc,{});
    Rotation XYZpi2      = Rotation(0,vector<char>{'x','y','z'},{0,1,2});
    Rotation XYZpi4      = Rotation(2,vector<char>{'x','y','z'},{0,1,2});
    Rotation XYZpi8      = Rotation(1,vector<char>{'x','y','z'},{0,1,2});
    Rotation XYZmpi4     = Rotation(-2,vector<char>{'x','y','z'},{0,1,2});
    Rotation XYZmpi8     = Rotation(-1,vector<char>{'x','y','z'},{0,1,2});
    Rotation XZZmpi8     = Rotation(-1,vector<char>{'x','z','z'},{0,1,2});
    Rotation IYIpi2      = Rotation(0,y,{1});
    Rotation XII         = Rotation(1,x,{0});
    Rotation XII2        = Rotation(2,x,{0});

    vector< vector<Rotation>> cases = {
        {XYZpi4,XYZpi4},
        {III1,III2},
        {XYZpi2,III2},
        {III1,XYZpi8},
        {IYIpi2,XYZpi8},
        {XZZmpi8,XYZpi8},
        {XYZmpi4,XYZmpi8},
        {XYZpi8,XYZmpi8},
        {XYZpi8,XYZmpi4},
        {XYZpi2,XYZpi2},
        {XYZpi2,XYZmpi4},
        {XII,XII}
    };
    vector<bool> expected_isCombine = {true,true,true,true,false,false,false,true,true,true,true,true};
    vector< vector<Rotation>> expected_results   = {{XYZpi2}, {}, {XYZpi2}, {XYZpi8}, {IYIpi2,XYZpi8}, {XZZmpi8,XYZpi8}, 
                            {XYZmpi4,XYZmpi8}, {}, {XYZmpi8}, {}, {XYZpi4},{XII2}};
    for(int idx = 0 ; idx < cases.size() ; ++idx){
        pair<bool,vector<Rotation>> results = gatelist.combineRotation(cases[idx][0],cases[idx][1]);
        if (expected_isCombine[idx] != results.first){
            cout << "isCombine case " << idx << " failed\n" ;
            return 1;
        }
        if (expected_results[idx] != results.second){
            cout << "expect :\n" ;
            for(Rotation R:expected_results[idx]){R.toStr();}
            cout << "got :\n" ;
            for(Rotation R:results.second){R.toStr();}
            cout << "results case " << idx << " failed\n" ;
            return 1;
        }
    }
    
    cout << "combineRotations passed\n" ;
    return 0;
}

int Test_implementNoOrderingRotationCombination(LysCompiler gatelist){

    vector<char> emptyc = {};
    vector<char> z = {'z'};
    Rotation III     = Rotation(0,emptyc,{});
    Rotation IZI     = Rotation(0,z,{1});
    Rotation YXZpi8  = Rotation(1,vector<char>{'y','x','z'},{0,1,2});
    Rotation YXZmpi4 = Rotation(-2,vector<char>{'y','x','z'},{0,1,2});
    Rotation YXZ     = Rotation(0,vector<char>{'y','x','z'},{0,1,2});
    Rotation YXZmpi8 = Rotation(-1,vector<char>{'y','x','z'},{0,1,2});

    vector< vector<Gate>> cases = {
        {III},
        {III,IZI},
        {YXZpi8,YXZmpi4,YXZ},
        {YXZpi8},
        {YXZ,YXZmpi4,YXZmpi4},
        {YXZ,YXZpi8,IZI},
        {YXZpi8,YXZpi8,IZI,YXZmpi4,YXZmpi8,YXZpi8}
    };
    vector< vector<Gate>> expected_results = {
        {}, 
        {IZI}, 
        {YXZmpi8, YXZ}, 
        {YXZpi8},
        {}, 
        {YXZ,YXZpi8,IZI}, 
        {IZI}
    };
    vector<bool> expected_isChange  = {true, true, true, false, true, false, true};
    for(int idx = 0 ; idx < cases.size() ; ++idx){
        bool results = gatelist.implementNoOrderingRotationCombination(cases[idx]);
        if (expected_isChange[idx] != results){
            cout << "isChange case " << idx << " failed\n" ;
            return 1;
        }
        if (expected_results[idx] != cases[idx]){
            cout << "results case " << idx << " failed\n" ;
            return 1;
        }
    }
    cout << "implementNoOrderingRotationCombination passed\n" ;
    return 0;
}

int Test_noOrderingRotationCombination(LysCompiler gatelist){

    vector<char> emptyc = {};
    Rotation III     = Rotation(0,emptyc,{});
    Rotation YXZpi8  = Rotation(1,vector<char>{'y','x','z'},{0,1,2});
    Rotation YXZpi4  = Rotation(2,vector<char>{'y','x','z'},{0,1,2});
    Rotation YXZ     = Rotation(0,vector<char>{'y','x','z'},{0,1,2});
    Rotation YXZmpi8 = Rotation(-1,vector<char>{'y','x','z'},{0,1,2});
    
    vector< vector<Gate>> cases = {
        {YXZ,YXZpi8,YXZpi8,YXZpi4,III},
        {YXZ,YXZpi4,YXZpi8,YXZpi4,YXZmpi8,YXZmpi8}
    };
    vector< vector<Gate>> expected_result = {
        {}, 
        {YXZmpi8} 
    };
    vector<bool> expected_isChange = {true, true};
    
    for(int idx = 0 ; idx < cases.size() ; ++idx){
        bool results = gatelist.noOrderingRotationCombination(cases[idx]);
        if (expected_isChange[idx] != results){
            cout << "isChange case " << idx << " failed\n" ;
            return 1;
        }
        if (expected_result[idx] != cases[idx]){
            cout << "results case " << idx << " failed\n" ;
            return 1;
        }
    }
    cout << "noOrderingRotationCombination passed\n" ;
    return 0;
}

int Test_applyCommutation(LysCompiler gatelist){
    vector<char> x = {'x'};
    vector<char> z = {'z'};
    vector<Rotation> nont = {
        Rotation(0,vector<char> {'z','x'},{0,1}),    //ZXIIII
        Rotation(2,vector<char> {'z','x'},{0,1}),    //ZXIIII
        Rotation(2,vector<char> {'z', 'y', 'x'}, {0,1,2}),  //ZYXIII
        Rotation(-2,vector<char> {'z', 'z', 'x'}, {0,1,2}),  //-ZZX
        Rotation(2,vector<char> {'z','z','z'},{0,1,2}),  // ZZZ
        Rotation(2,x,{0}),  // XIII
        Rotation(2,x,{2}),   //IIXII
        Rotation(2,vector<char> {'x','x','x'},{0,1,2}) //XXX
    };
    vector<Rotation> t = {
        Rotation(1,x,{0}),                     //XIIIIII         
        Rotation(1,vector<char> {'z','y'},{0,1}), // ZYIIII   => I(z)IIII
        Rotation(-1,vector<char> {'x', 'z', 'y'}, {0,1,2}), //-XZY   => (iZX)(iiXZZ)(iXiXZ) = YXZ
        Rotation(-1,vector<char>{'x', 'y', 'y'}, {0,1,2}),  //-XYY  => -i(ZX)(iZXZ)(iXXZ) = YXZ
        Rotation(1,vector<char>{'y','y','y'},{0,1,2}),   // YYY => -i(iZXZ)(iZXZ)(iZXZ) = XXX
        Rotation(1,z,{0}),   //ZIII   => -iXZ
        Rotation(1,z,{2}),  //IIZIII 
        Rotation(1,vector<char>{'z','z','z'},{0,1,2})  // ZZZ => -i (XZ)(XZ)(XZ)= +YYY
    };
    vector<Rotation> expected = {
        Rotation(-1,vector<char> {'x'},{0}),
        Rotation(1,vector<char> {'z'},{1}),
        Rotation(1,vector<char> {'z','x','y'},{2,1,0}),
        Rotation(1,vector<char> {'z','x','y'},{2,1,0}),
        Rotation(1,vector<char> {'x','x','x'},{2,1,0}),
        Rotation(-1,vector<char> {'y'},{0}),
        Rotation(-1,vector<char> {'y'},{2}),
        Rotation(1,vector<char> {'y','y','y'},{2,1,0}),
    };
    
    for(int idx = 0 ; idx < nont.size() ; ++idx){
        Rotation results = gatelist.applyCommutation(nont[idx],t[idx]);
        if (expected[idx] != results){
            cout << "got: \n";
            cout << results.toStr();
            cout << "expected \n" ;
            cout << expected[idx].toStr();
            cout << "applyCommutation case " << idx << " failed\n" ;
            return 1;
        }
    }
    
    cout << "applyCommutation passed\n" ;
    return 0;
}


int Test_pushTForwardThread(LysCompiler gatelist)
{
    //Empty test.
    vector<char> x = {'x'};
    vector<char> z = {'z'};
    vector<char> y = {'y'};
    vector<Gate> flatten_gates ;
    vector<Gate> expected_forward_pushed_gates ;
    vector<int> zero = {0};
    gatelist.pushTForwardThread(flatten_gates,0,flatten_gates.size(),zero,0);
    if (flatten_gates!=expected_forward_pushed_gates) {
        cout << "pushTForwardThread case empty failed\n" ;
        return 1;
    } 
    
    //Single tgate.
    flatten_gates = { Rotation(1,x,{0}) };
    expected_forward_pushed_gates = { Rotation(1,x,{0}) };
    gatelist.pushTForwardThread(flatten_gates,0,flatten_gates.size(),zero,0);
    if (flatten_gates!=expected_forward_pushed_gates) {
        cout << "pushTForwardThread case single tgate failed\n" ;
        return 1;
    }

    // Single non-tgate.
    flatten_gates = { Rotation(0,vector<char>{'z','x'},{0,1}) };
    expected_forward_pushed_gates = { Rotation(0,vector<char>{'z','x'},{0,1}) };
    gatelist.pushTForwardThread(flatten_gates,0,flatten_gates.size(),zero,0);
    if (flatten_gates!=expected_forward_pushed_gates) {
        cout << "pushTForwardThread case single non-tgate failed\n" ;
        return 1;
    }
    // All tgates.
    flatten_gates = { Rotation(1,x,{0}),
                      Rotation(-1,x,{2}),
                      Rotation(-1,vector<char>{'z','x'},{1,0}),
                      Rotation(1,vector<char>{'z','x'},{1,0}),
                      Rotation(-1,x,{2}),
                      Rotation(1,z,{2}) 
                    };
    expected_forward_pushed_gates = { Rotation(1,x,{0}),
                                      Rotation(-1,x,{2}),
                                      Rotation(-1,vector<char>{'z','x'},{1,0}),
                                      Rotation(1,vector<char>{'z','x'},{1,0}),
                                      Rotation(-1,x,{2}),
                                      Rotation(1,z,{2}) 
                                    };
    gatelist.pushTForwardThread(flatten_gates,0,flatten_gates.size(),zero,0);
    if (flatten_gates!=expected_forward_pushed_gates) {
        cout << "pushTForwardThread case all tgates failed\n" ;
        return 1;
    }
    //Single tgate vs many non-tgate.
    flatten_gates = { Rotation(0,vector<char>{'z','x'},{0,1}),
                      Rotation(0,x,{0}),
                      Rotation(2,vector<char>{'z','x'},{1,0}),
                      Rotation(-2,z,{1}),
                      Rotation(-2,x,{0}),
                      Rotation(2,z,{1}),
                      Rotation(2,vector<char>{'z','x'},{1,0}),
                      Rotation(2,x,{2}),
                      Rotation(1,z,{2}) 
                    };
    expected_forward_pushed_gates = { Rotation(-1,y,{2}),
                                      Rotation(0,vector<char>{'z','x'},{0,1}),
                                      Rotation(0,x,{0}),
                                      Rotation(2,vector<char>{'z','x'},{1,0}),
                                      Rotation(-2,z,{1}),
                                      Rotation(-2,x,{0}),
                                      Rotation(2,z,{1}),
                                      Rotation(2,vector<char>{'z','x'},{1,0}),
                                      Rotation(2,x,{2}) 
                                    };
    gatelist.pushTForwardThread(flatten_gates,0,flatten_gates.size(),zero,0);
    if (flatten_gates!=expected_forward_pushed_gates) {
        cout << "pushTForwardThread case Single tgate vs many non-tgate failed\n" ;
        return 1;
    }
    // An overall test.
    flatten_gates = { Rotation(0,vector<char>{'z','x'},{0,1}),
                      Rotation(1,x,{0}),
                      Rotation(0,x,{0}),
                      Rotation(-1,x,{2}),
                      Rotation(2,vector<char>{'z','x'},{1,0}),
                      Rotation(-2,z,{1}),
                      Rotation(-1,vector<char>{'z','x'},{1,0}),
                      Rotation(1,vector<char>{'z','x'},{1,0}),
                      Rotation(-2,x,{0}),
                      Rotation(-1,x,{2}),
                      Rotation(2,z,{1}),
                      Rotation(2,vector<char>{'z','x'},{1,0}),
                      Rotation(2,x,{2}),
                      Rotation(1,z,{2})
                    };
    expected_forward_pushed_gates = { Rotation(-1,x,{0}),
                                      Rotation(-1,x,{2}),
                                      Rotation(-1,vector<char>{'z','x'},{1,0}),
                                      Rotation(1,vector<char>{'z','x'},{1,0}),
                                      Rotation(-1,x,{2}),
                                      Rotation(-1,y,{2}),
                                      Rotation(0,vector<char>{'z','x'},{0,1}),
                                      Rotation(0,x,{0}),
                                      Rotation(2,vector<char>{'z','x'},{1,0}),
                                      Rotation(-2,z,{1}),
                                      Rotation(-2,x,{0}),
                                      Rotation(2,z,{1}),
                                      Rotation(2,vector<char>{'z','x'},{1,0}),
                                      Rotation(2,x,{2})
                                    };

    gatelist.pushTForwardThread(flatten_gates,0,flatten_gates.size(),zero,0);
    if (flatten_gates!=expected_forward_pushed_gates) {       
        cout << "pushTForwardThread case An overall test failed\n" ;
        return 1;
    }

    //Measure and Rotation that commute
    flatten_gates = {
        Measure(true,z,{1}),
        Rotation(-1,x,{0})
    };
    expected_forward_pushed_gates = {
        Rotation(-1,x,{0}),
        Measure(true,z,{1})
    };
    gatelist.pushTForwardThread(flatten_gates,0,flatten_gates.size(),zero,0);
    if (flatten_gates!=expected_forward_pushed_gates) {  
        toStrVariantVec(flatten_gates);
        cout << "pushTForwardThread case Measure and Rotation that commute test failed\n" ;
        return 1;
    }

    cout << "pushTForwardThread passed\n" ;
    return 0;
}


int Test_reduceLayerGreedyAlgo(LysCompiler gatelist){

    vector<char> x = {'x'};
    vector<char> z = {'z'};
    vector<char> y = {'y'};

    vector<Gate> used_gates = { //tgates
                   Rotation(1,x,{0}),
                   Rotation(-1,x,{2}),
                   Rotation(-1,vector<char>{'z','x'},{1,0}), 
                   Rotation(1,vector<char>{'z','x'},{1,0}), 
                   Rotation(1,z,{2}),
                 };

    // For information on the test, you can uncomment this code to see which gates commute with which. 
    // for gate_index in range(0,len(used_gates)):
    //     gate = used_gates[gate_index]
    //     this_list = {}
    //     for other_index in range(0, len(used_gates)):
    //         other = used_gates[other_index]
    //         if other_index != gate_index and gate.is_commute(other):
    //             this_list.append(other_index)
    //     print("gate index " + str(gate_index) + " commutes " + str(this_list) )

            
    // Empty list of gates.
    vector<Gate> flatten_gates = {};
    vector< vector<Gate>> expected_greedy_reduced_gates = {};
    vector< vector<Gate>> greedy_reduced_gates = gatelist.reduceLayerGreedyAlgo(flatten_gates);
    if (greedy_reduced_gates!=expected_greedy_reduced_gates) {
        cout << " greedy case empty list of gates failed\n" ;
        return 1;
    }
    // List of single gate.
    flatten_gates = {used_gates[0]};
    expected_greedy_reduced_gates = {{used_gates[0]}};
    greedy_reduced_gates = gatelist.reduceLayerGreedyAlgo(flatten_gates);
    if (greedy_reduced_gates!=expected_greedy_reduced_gates) {
        cout << " greedy case List of single gate failed\n" ;
        return 1;
    }
    
    // Two non commutable gates.
    flatten_gates = { used_gates[1], 
                      used_gates[4]
                    };
    expected_greedy_reduced_gates = { {used_gates[1]}, 
                                      {used_gates[4]}
                                    };
    greedy_reduced_gates = gatelist.reduceLayerGreedyAlgo(flatten_gates);
    if (greedy_reduced_gates!=expected_greedy_reduced_gates) {
        cout << " greedy case Two non commutable gates failed\n" ;
        return 1;
    }
    // Two commutable gates.
    flatten_gates = { used_gates[0], 
                      used_gates[1]
                    };
    expected_greedy_reduced_gates = { {used_gates[0], used_gates[1]}
                                    };
    greedy_reduced_gates = gatelist.reduceLayerGreedyAlgo(flatten_gates);
    if (greedy_reduced_gates!=expected_greedy_reduced_gates) {
        for(vector<Gate> vG:greedy_reduced_gates){
            cout << " ---- layer ---- \n"; 
            toStrVariantVec(vG);
        }
        cout << " greedy case Two commutable gates failed\n" ;
        return 1;
    }
    // Commutable, Non_Commutable, Commutable gates.
    flatten_gates = { used_gates[4], 
                      used_gates[1],
                      used_gates[3]
                    };
    expected_greedy_reduced_gates = { {used_gates[4], used_gates[3]}, 
                                      {used_gates[1]}
                                    };
    greedy_reduced_gates = gatelist.reduceLayerGreedyAlgo(flatten_gates);
    if (greedy_reduced_gates!=expected_greedy_reduced_gates) {
        cout << " greedy case Commutable, Non_Commutable, Commutable gates. failed\n" ;
        return 1;
    }
    // Non transitive commute. 0 and 1 are commutable, 1 and 6 are also commutable, but 0 and 6 aren't 
    flatten_gates = { used_gates[1], 
                      used_gates[3],
                      used_gates[4]
                    };
    expected_greedy_reduced_gates = { {used_gates[1], used_gates[3]}, 
                                      {used_gates[4]}
                                    };
    greedy_reduced_gates = gatelist.reduceLayerGreedyAlgo(flatten_gates);
    if (greedy_reduced_gates!=expected_greedy_reduced_gates) {
        cout << " greedy case Non transitive commute failed\n" ;
        return 1;
    }
    // Four commutable gates.
    flatten_gates = { used_gates[0], 
                      used_gates[1],
                      used_gates[2],
                      used_gates[3],
                    };
    expected_greedy_reduced_gates = { {used_gates[0], used_gates[1], used_gates[2], used_gates[3]}
                                    };
    greedy_reduced_gates = gatelist.reduceLayerGreedyAlgo(flatten_gates);
    if (greedy_reduced_gates!=expected_greedy_reduced_gates) {
        cout << " greedy case Four commutable gates failed\n" ;
        return 1;
    }
    
    // A more complex situation 
    flatten_gates = { used_gates[4],
                      used_gates[0], 
                      used_gates[1],
                      used_gates[2]
                    };
    expected_greedy_reduced_gates = { {used_gates[4], used_gates[0],used_gates[2]}, 
                                      {used_gates[1]}
                                    };
    greedy_reduced_gates = gatelist.reduceLayerGreedyAlgo(flatten_gates);
    if (greedy_reduced_gates!=expected_greedy_reduced_gates) {
        cout << " greedy case A more complex situation failed\n" ;
        return 1;
    }
    // Lets put them all in
    flatten_gates = { used_gates[0],
                      used_gates[1], 
                      used_gates[2],
                      used_gates[3],
                      used_gates[4]
                    };
    expected_greedy_reduced_gates = { {used_gates[0], used_gates[1],  used_gates[2],  used_gates[3]},
                                      {used_gates[4]}
                                    };
    greedy_reduced_gates = gatelist.reduceLayerGreedyAlgo(flatten_gates);
    if (greedy_reduced_gates!=expected_greedy_reduced_gates) {
        cout << " greedy case Lets put them all in failed\n" ;
        return 1;
    }

    // Lets put them all in
    flatten_gates = { used_gates[0],
                      used_gates[1], 
                      used_gates[2],
                      used_gates[4],
                      used_gates[3]
                    };
    expected_greedy_reduced_gates = { {used_gates[0], used_gates[1],  used_gates[2],  used_gates[3]},
                                      {used_gates[4]}
                                    };
    greedy_reduced_gates = gatelist.reduceLayerGreedyAlgo(flatten_gates);
    if (greedy_reduced_gates!=expected_greedy_reduced_gates) {
        cout << " greedy case Lets put them all in failed\n" ;
        return 1;
    }

    // Dummy 200 gates
    vector<Gate> flatten_gate(200,used_gates[0]);
    expected_greedy_reduced_gates = { vector<Gate>(200,used_gates[0])
                                    };
    greedy_reduced_gates = gatelist.reduceLayerGreedyAlgo(flatten_gate);
    if (greedy_reduced_gates!=expected_greedy_reduced_gates) {
        cout << " greedy case dummy 200 gates failed\n" ;
        return 1;
    }

    cout << "reduceLayerGreedyAlgo passed\n" ;
    return 0;
}

int Test_optimizeRotation(){

    vector<char> x = {'x'};
    vector<char> z = {'z'};
    vector<char> y = {'y'};

    Rotation XIII = Rotation(1,x,{0});
    Rotation XIIIpi2 = Rotation(2,x,{0});
    
    // Dummy 200 gates
    vector<Gate> flatten_gate(200,XIII);
    LysCompiler gatelist = LysCompiler(flatten_gate);
    vector<Gate> expected_circuit;
    gatelist.optimizeRotation();
    if (gatelist.circuit!=expected_circuit ) {
        cout << "optimizedRotation case dummy 200 gates failed\n" ;
        return 1;
    }

    vector<Gate> flatten_gate0(8,XIII);
    gatelist = LysCompiler(flatten_gate0);
    gatelist.optimizeRotation();
    if (gatelist.circuit!=expected_circuit){
        cout << "optimizedRotation case dummy 8 gates failed\n" ;
        return 1;
    }


    vector<Gate> flatten_gate2(208,XIII);
    gatelist = LysCompiler(flatten_gate2);
    gatelist.optimizeRotation();
    if (gatelist.circuit!=expected_circuit ) {
        cout << "optimizedRotation case dummy 208 gates failed\n" ;
        return 1;
    }

    vector<Gate> flatten_gate1(200,XIIIpi2);
    gatelist = LysCompiler(flatten_gate1);
    gatelist.optimizeRotation();
    if (gatelist.circuit!=expected_circuit){
        cout << "optimizedRotation case dummy 200 pi/2 gates failed\n" ;
        return 1;
    }


    cout << "optimizedRotation passed\n" ;
    return 0;

}


int Test_rearrange_clifford_gates(LysCompiler gatelist){
    vector<char> x = {'x'};
    vector<char> z = {'z'};
    vector<char> y = {'y'};
    Rotation XI  = Rotation(0,x,{0});
    Rotation ZI  = Rotation(0,z,{0});
    Rotation XY  = Rotation(0,vector<char>{'x','y'},{0,1}); 
    Rotation IZ  = Rotation(0,z,{1});
    Rotation ZZ  = Rotation(0,vector<char>{'z','z'},{0,1}); 

    vector<vector< Gate> > cases = {
        {XI,XY,ZI,ZZ,IZ},
        {IZ,ZI,ZZ,ZZ,ZI,ZI,IZ,ZZ},
        {XI,XY,ZI,ZZ,IZ,XI},
        {},
        {ZZ}    // The returned index is 1, which is out of bound for this input. Intentional?
    };

    vector<int> expected_index  = {3, 3, 3, 0, 1};
    vector<vector<Gate> > expected_result = {
        {XY,XI,ZZ,ZI,IZ},
        {ZZ,ZZ,ZZ,IZ,ZI,ZI,ZI,IZ},
        {XY,XI,ZZ,ZI,IZ,XI},
        {},
        {ZZ}    
    };
    vector<int> index_1qbit ;
    for( int idxCase = 0 ; idxCase < cases.size() ; idxCase++){
        gatelist.circuit = cases[idxCase] ; 
        index_1qbit.push_back(gatelist.RearrangeCliffordGates(-1,cases[idxCase].size()-1));
        cases[idxCase] = gatelist.circuit ;
    }
    if (expected_index!=index_1qbit) {
        cout << "rearrange clifford index fail\n" ;
        return 1;
    }
    if (expected_result!=cases) {
        cout << "rearrange clifford expected result fail\n" ;
        return 1;
    }

    cout << "RearrangeCliffordGates passed\n" ;
    return 0;
}

int Test_applyCommutationRM(LysCompiler gatelist){
    vector<char> x = {'x'};
    vector<char> z = {'z'};
    vector<char> y = {'y'};
    Rotation IXX         = Rotation(0,vector<char>{'x','x'},{1,2});
    Rotation XYZpi2      = Rotation(0,vector<char>{'x','y','z'},{0,1,2});
    Measure MZII         = Measure(true,z,{0});
    Rotation XXpi4       = Rotation(2,vector<char>{'x','x'},{0,1});
    Measure MYI          = Measure(true,y,{0});
    Measure MmYI         = Measure(false,y,{0});
    Rotation ZYZpi4      = Rotation(2,vector<char>{'z','y','z'},{0,1,2});
    Measure MXZY         = Measure(true,vector<char>{'x','z','y'},{0,1,2});
    Rotation ZYZmpi4     = Rotation(-2,vector<char>{'z','y','z'},{0,1,2});
    
    vector< pair<Rotation, Measure> > cases = {
        {XYZpi2,MZII},
        {XXpi4,MYI},
        {XXpi4,MmYI},
        {ZYZpi4,MXZY},
        {ZYZmpi4,MXZY}
     };
    vector<Measure> expected_result = {
        Measure(false,z,{0}),
        Measure(false,vector<char>{'z','x'},{0,1}),
        Measure(true,vector<char>{'z','x'},{0,1}),
        Measure(false,vector<char>{'y','x','x'},{0,1,2}),
        Measure(true,vector<char>{'y','x','x'},{0,1,2})
    };
    for( int caseIdx=0 ; caseIdx < cases.size() ; caseIdx++){
        Measure results = gatelist.applyCommutation(cases[caseIdx].first,cases[caseIdx].second);
        if (!(expected_result[caseIdx]==results)) {
            cout << "got : \n" << results.toStr();
            cout << "expected : \n"<< expected_result[caseIdx].toStr();
            cout << "absorbe rotation by measure Measure case " << caseIdx << " fail\n" ;
            return 1;
        }
    }

    cout << "absorb_rotation_by_measure passed\n" ;
    return 0;

}


int Test_basis_permutation(LysCompiler gatelist){
    vector<char> x = {'x'};
    vector<char> z = {'z'};
    vector<char> y = {'y'};
    Rotation XI      = Rotation(0,x,{0});
    Rotation ZI      = Rotation(0,z,{0});
    Rotation XY      = Rotation(0,vector<char>{'x','y'},{0,1}); 
    Rotation IZ      = Rotation(0,z,{1});
    Rotation ZZ      = Rotation(0,vector<char>{'z','z'},{0,1}); 
    Measure MIZ     = Measure(true,z,{1});
    Measure MZI     = Measure(true,z,{0});
 
    Rotation IXZI4   = Rotation(2,vector<char>{'x','z'},{1,2});
    Rotation IIIXm4  = Rotation(-2,x,{3});
    Rotation IXIIm4  = Rotation(-2,x,{1});
    Rotation IIZIm4  = Rotation(-2,z,{2});
    Rotation XZII4   = Rotation(2,vector<char>{'x','z'},{0,1});
    Rotation IIXI4   = Rotation(2,x,{2});
    Rotation XIIIm4  = Rotation(-2,x,{0});
    Rotation IZIIm4  = Rotation(-2,z,{1});
    Rotation XIIZ4   = Rotation(2,vector<char>{'x','z'},{0,3});
    Rotation IIIZm4  = Rotation(-2,z,{3});
    Rotation IZII4   = Rotation(2,z,{1});
    Rotation IIIZ4   = Rotation(2,z,{3});
    Rotation IXII4   = Rotation(2,x,{1});
    Rotation IIIX4   = Rotation(2,x,{3});
    Measure MZIII   = Measure(true,z,{0});
    Measure MIZII   = Measure(true,z,{1});
    Measure MIIZI   = Measure(true,z,{2});
    Measure MIIIZ   = Measure(true,z,{3});
    Measure MYZZY   = Measure(true,vector<char>{'y','z','z','y'},{0,1,2,3});
    Measure MXXII   = Measure(true,vector<char>{'x','x'},{0,1});
    Measure MIIZIm  = Measure(false,z,{2});
    Measure MXIIX   = Measure(true,vector<char>{'x','x'},{0,3});

    vector< vector<Gate> > cases = {
        {XI,XY,ZI,ZZ,IZ,MZI,MIZ},
        {IXZI4,IIIXm4,IXIIm4,IIZIm4,XZII4,IIXI4,XIIIm4,IZIIm4,XIIZ4,XIIIm4,IIIZm4,
          IZII4,IIIZ4,XIIIm4,IXII4,IIXI4,IIIX4,MZIII,MIZII,MIIZI,MIIIZ}
    };
    // Please note: the commuted over clifford are thrown out not by this function, but the runLysCompiler section processor
    vector< vector<Gate>  > expected_cases = {
        {Measure(true,z,{0}), Measure(false,z,{1}), XY, XI, ZZ, ZI, IZ},
        {MYZZY,MXXII,MIIZIm,MXIIX, IXZI4, IXIIm4, XZII4,
        IIIXm4, XIIZ4, IIZIm4,IIXI4,
        XIIIm4, IZIIm4,XIIIm4, IIIZm4, IZII4, IIIZ4,
        XIIIm4, IXII4, IIXI4, IIIX4}
    };
    vector<int> expected_numOfCommuted = {5,17};
    // Case of having no ancilla in the circuit. All measures are measuring data qubits.
    // All clifford should be thrown out after commuted over Measure
    for( int idxCase = 0 ; idxCase < cases.size() ; idxCase++){
        gatelist.circuit = cases[idxCase];
        int numOfCommuteGates = gatelist.basis_permutation(0); // will change cases in place and return the numCommuteGates
        if (!(gatelist.circuit == expected_cases[idxCase]) | (numOfCommuteGates != expected_numOfCommuted[idxCase])){
            cout << "combine rotation measurements Measures List No Ancilla case " << idxCase << " fail\n" ;
            cout << "Got : \n";
            toStrVariantVec(gatelist.circuit);
            return 1;
        }
    }
    cout << "basis_permutation No Ancilla passed\n" ;


    // Case of: there are 4 qubits, the last two are the ancilla
    Rotation XIII4a = Rotation( 2, x, {0});                                 // rotation only act on data 0
    Rotation IXII4a = Rotation( 2, x, {1});                                 // rotation only act on data 1
    Rotation IIXI4a = Rotation( 2, x, {2});                                 // rotation only act on ancilla 0
    Rotation XIZI4a = Rotation( 2, vector<char>{'x','z'}, {0,2});           // rotation act on both data and ancilla
    Rotation XIZX4a = Rotation( 2, vector<char>{'x','z','x'}, {0,2,3});     // rotation act on both data and ancilla
    Measure  MXIIIa = Measure(  true, x, {0});                              // only measure the data 0
    Measure  MIIXIa = Measure(  true, x, {2});                              // only measure the ancilla 0
    Measure  MIIIXa = Measure(  true, x, {3});                              // only measure the ancilla 1
    Measure  MXIXIa = Measure(  true, vector<char>{'x','x'}, {0,2});        // measure both the ancilla and data
    int ancBeginIdx = 2;                                                    // ancilla begins at index 2

    vector<vector<Gate>> cases_anc = {
        {XIII4a, IXII4a, MIIXIa},           // case 0: expect both Rs to commute over, numCommute to be 2
        {XIII4a, MIIXIa},                   // case 1: expect R to commute over, numCommute to be 1
        {IIXI4a, MIIXIa},                   // case 2: expect no action, numCommute to be 0
        {XIII4a, MXIIIa},                   // case 3: expect R to commute over and deleted, numCommute to be 0
        {IIXI4a, MXIIIa},                   // case 4: expect R to commute over, numCommute to be 1
        {XIZI4a, MIIXIa},                   // case 5: expect no action. numCommute to be 0
        {XIZX4a, MIIIXa}                    // case 6: expect no action. numCommute to be 0
    };

    vector<vector<Gate>> expected_gateList = {
        {MIIXIa, XIII4a, IXII4a},           // Case 0: must preserve the order of the Rs after commuted over   
        {MIIXIa, XIII4a},                   // Case 1: must preserve the order of the Rs after commuted over   
        {IIXI4a, MIIXIa}, 
        {MXIIIa},
        {MXIIIa, IIXI4a},
        {XIZI4a, MIIXIa},
        {XIZX4a, MIIIXa} 
    };

    vector<int> expected_numCommuted = {
        2, 1, 0, 0, 1, 0, 0
    };

    for( int idxCase = 0 ; idxCase < cases.size() ; idxCase++){

        gatelist.circuit = cases_anc[idxCase];
        int numOfCommuteGates = gatelist.basis_permutation(0); // will change cases in place and return the numCommuteGates
        
        if (!(gatelist.circuit == expected_gateList[idxCase]) | (numOfCommuteGates != expected_numCommuted[idxCase])){
            cout << "combine rotation measurements Measures List With Ancilla case " << idxCase << " fail\n" ;
            cout << "Got : \n";
            toStrVariantVec(cases_anc[idxCase]);
            return 1;
        }
    } 

    cout << "basis_permutation With Ancilla passed\n" ;

    return 0;
}   

int Test_runLysCompiler(){ 

    vector<char> z = {'z'};
    vector<char> x = {'x'};
    vector<Gate> vGate;
    vector<vector<Gate>> vvGate ;
    Measure MZII = Measure(true,z,{0});
    Measure MIZI = Measure(true,z,{1});
    Measure MIIZ = Measure(true,z,{2});

    Rotation TI = Rotation(1,z,{0});
    Rotation IT = Rotation(1,z,{1});
    Rotation ZI = Rotation(0,z,{0});
    Rotation IZ = Rotation(0,z,{1});
    Rotation XI = Rotation(-2,x,{0});
    Rotation XZ = Rotation(2,vector<char>{'x','z'},{0,1});
    Measure MXI = Measure(true,x,{0});
    Measure MIX = Measure(true,x,{1});
    Measure MmXI = Measure(false,x,{0});
    Measure MmIX = Measure(false,x,{1});

    // Testing idxToRemove, combine yes, layer no
    vector<vector<Gate>> gatesTestIdxToRemove;
    gatesTestIdxToRemove = {
        // case 0: circuit has only nonT and measure, expect all nonT to be removed and idxToRemove equals to length - clifford
        {ZI, IZ, XI, XZ, MXI, MIX},
        // case 1: circuit has t and nont, expect idxToRemove starts after the T
        {TI, IT, ZI, XI, XZ, MXI, MmIX},
        // case 2: circuit has only t, expect idxToRemove equals the length of the circuit
        {TI, IT, MmIX, MmXI},
        // case 3: circuit only has measure; expect idxToRemove equals the length of the circuit
        {MXI, MIX}
    };
    
    vector<int> expected_idxToRemove = {
        2,  // case 0
        4,  // case 1
        4,  // case 2
        2   // case 3
    };

    for( int idxCase = 0 ; idxCase < gatesTestIdxToRemove.size() ; idxCase++){
        LysCompiler compiler = LysCompiler(gatesTestIdxToRemove[idxCase]);
        pair<vector<vector<Gate>>, int> compilerResults = compiler.runLysCompiler(true, false); // since layer=false, we only care about the int idxToRemove; the vecvec will be empty
        int idxToRemove                                 = compilerResults.second;

        if ( idxToRemove != expected_idxToRemove[idxCase]){
            cout << "Test runLysCompiler test idxToRemove case " << idxCase << " fail\n" ;
            cout << "Got : \n";
            cout << "Index to remove " << idxToRemove << endl;
            toStrVariantVec(gatesTestIdxToRemove[idxCase]);
            return 1;
        }
    } 
  
    // case 5: if combine is false, idxToRemove should always to be same as the length of the circuit
        for( int idxCase = 0 ; idxCase < gatesTestIdxToRemove.size() ; idxCase++){
        LysCompiler compiler = LysCompiler(gatesTestIdxToRemove[idxCase]);
        pair<vector<vector<Gate>>, int> compilerResults = compiler.runLysCompiler(false, false); // since layer=false, we only care about the int idxToRemove; the vecvec will be empty
        int idxToRemove                                 = compilerResults.second;

        if ( idxToRemove != gatesTestIdxToRemove[idxCase].size()){
            cout << "Test runLysCompiler test idxToRemove case " << idxCase << " fail\n" ;
            cout << "Got : \n";
            cout << "Index to remove " << idxToRemove << endl;
            toStrVariantVec(gatesTestIdxToRemove[idxCase]);
            return 1;
        }
    } 
    
    cout << "Test runLysCompiler test idxToRemove case passed\n" ;

    //simple circuit

    vGate = {ZI,IZ,TI,IT,MXI,MIX} ;
    
    //no combine, no layer, measure
    LysCompiler gatelist = LysCompiler(vGate);
    pair<vector<vector<Gate>>,int>  results = gatelist.runLysCompiler(false,false);
    vvGate = {};
    if (results.first != vvGate){
        int count = 0;
        for (vector<Gate> layer:results.first){
            cout << "layer " << count << endl ;
            toStrVariantVec(layer);
            cout << "-----\n";
            count++;
        }
        cout << "LysCompiler failed simple circuit no combine, no layer, measure \n" ; 
        return 1;
    }

    //no combine, layer, measure
    gatelist = LysCompiler(vGate);
    results = gatelist.runLysCompiler(false,true);
    vvGate = {{TI,IT,ZI,IZ},{MXI},{MIX}};
    if (results.first != vvGate){
        cout << "Got : \n" ;
        for (vector<Gate> layer: results.first){
            toStrVariantVec(layer) ;
            cout << "------ \n" ;
        }
        cout << "Expected : \n" ;
        for (vector<Gate> layer: vvGate){
            toStrVariantVec(layer) ;
            cout << "------ \n" ;
        }
        cout << "LysCompiler failed simple circuit no combine, layer, measure  \n" ; 
        return 1;
    }

    //combine, layer, measure
    
    gatelist = LysCompiler(vGate);
    results = gatelist.runLysCompiler(true,true);
    vvGate = {{TI,IT},{MmXI},{MmIX},{ZI},{IZ}};
    if (results.first != vvGate){
        cout << "Got : \n" ;
        for (vector<Gate> layer: results.first){
            toStrVariantVec(layer) ;
            cout << "------ \n" ;
        }
        cout << "Expected : \n" ;
        for (vector<Gate> layer: vvGate){
            toStrVariantVec(layer) ;
            cout << "------ \n" ;
        }
        cout << "LysCompiler failed simple circuit combine, layer, measure \n" ; 
        return 1;
    }

    cout << "LysCompiler passed\n" ;
    return 0;
}


int TwoBGadder(){
    vector<char> z = {'z'};
    vector<char> x = {'x'};
    // these test are similar to Test_runLysCompiler but with a measure that has 
    // classically-controlled rotation

    // test 1: combine = false, layer = false
    //note : Lys will never have a circuit that has R-M-R-M
    // like this one, or if so, it doesn't treat the rotation
    // between the measure (no compilation for this part)
    vector<Gate> circuit = {
        Rotation(2,z,{4}),
        Rotation(2,x,{4}),
        Rotation(2,z,{4}),
        Rotation(1,z,{4}),
        Rotation(2,vector<char>{'z','x'},{0,4}),
        Rotation(-2,z,{0}),
        Rotation(-2,x,{4}),
        Rotation(2,vector<char>{'z','x'},{1,4}),
        Rotation(-2,z,{1}),
        Rotation(-2,x,{4}),
        Rotation(2,vector<char>{'z','x'},{4,0}),
        Rotation(-2,z,{4}),
        Rotation(-2,x,{0}),
        Rotation(2,vector<char>{'z','x'},{4,1}),
        Rotation(-2,z,{4}),
        Rotation(-2,x,{1}),
        Rotation(-1,z,{0}),
        Rotation(-1,z,{1}),
        Rotation(1,z,{4}),
        Rotation(2,vector<char>{'z','x'},{4,0}),
        Rotation(-2,z,{4}),
        Rotation(-2,x,{0}),
        Rotation(2,vector<char>{'z','x'},{4,1}),
        Rotation(-2,z,{4}),
        Rotation(-2,x,{1}),
        Rotation(2,z,{4}),
        Rotation(2,x,{4}),
        Rotation(2,z,{4}),
        Rotation(2,z,{4}),
        Rotation(2,vector<char>{'z','x'},{4,3}),
        Rotation(-2,z,{4}),
        Rotation(-2,x,{3}),
        Rotation(2,z,{4}),
        Rotation(2,x,{4}),
        Rotation(2,z,{4}),
        Measure(true,z,{4},{Rotation(2,vector<char>{'z','z'},{0,1}),Rotation(-2,z,{0}),Rotation(-2,z,{1})}),
        Rotation(2,vector<char>{'z','x'},{0,1}),
        Rotation(-2,z,{0}),
        Rotation(-2,x,{1}),
        Rotation(2,vector<char>{'z','x'},{2,3}),
        Rotation(-2,z,{2}),
        Rotation(-2,x,{3}),
        Measure(true,z,{0}),
        Measure(true,z,{1}),
        Measure(true,z,{2}),
        Measure(true,z,{3})
    };
    LysCompiler gatelist = LysCompiler(circuit,4);
    gatelist.runLysCompiler(false,false);
    vector<Gate> expected = {
        Rotation(1,x,{4}),
        Rotation(-1,vector<char>{'z','x'},{1,4}),
        Rotation(-1,vector<char>{'z','x'},{0,4}),
        Rotation(1,vector<char>{'z','z','x'},{0,1,4}),
        Rotation(2,z,{4}),
        Rotation(-2,z,{0}),
        Rotation(-2,z,{1}),
        Rotation(-2,x,{3}),
        Rotation(2,x,{4}),
        Rotation(2,z,{4}),
        Rotation(2,vector<char>{'z','x'},{0,4}),
        Rotation(0,x,{4}),
        Rotation(2,vector<char>{'z','x'},{1,4}),
        Rotation(0,vector<char>{'x','z'},{0,4}),
        Rotation(0,x,{0}),
        Rotation(0,vector<char>{'x','z'},{1,4}),
        Rotation(0,x,{1}),
        Rotation(2,z,{4}),
        Rotation(2,x,{4}),
        Rotation(0,z,{4}),
        Rotation(2,vector<char>{'z','x'},{4,3}),
        Rotation(2,x,{4}),
        Rotation(2,z,{4}),
        Measure(true,z,{4},{Rotation(2,vector<char>{'z','z'},{0,1}),Rotation(-2,z,{0}),Rotation(-2,z,{1})}),
        Rotation(2,vector<char>{'z','x'},{0,1}),
        Rotation(-2,z,{0}),
        Rotation(-2,x,{1}),
        Rotation(2,vector<char>{'z','x'},{2,3}),
        Rotation(-2,z,{2}),
        Rotation(-2,x,{3}),
        Measure(true,z,{0}),
        Measure(true,z,{1}),
        Measure(true,z,{2}),
        Measure(true,z,{3})
    };
    
    if(expected != gatelist.circuit){
        cout << "Gadder false-false failed \n";
        cout << " Got : \n" ; 
        toStrVariantVec(gatelist.circuit);
        cout << " Expected : \n" ; 
        toStrVariantVec(expected);
        for(int idxG = 0; idxG < expected.size() ; idxG++){
            if (expected[idxG] != gatelist.circuit[idxG]){
                cout << "at index " << idxG << endl;
            }
        }
    
        return 1;
    }

    //test 2 : combine = true, layer = false
    // first part of the previous circuit (cut as it is suppose to
    // be before runLysCompiler)
    circuit = {
        Rotation(2,z,{4}),
        Rotation(2,x,{4}),
        Rotation(2,z,{4}),
        Rotation(1,z,{4}),
        Rotation(2,vector<char>{'z','x'},{0,4}),
        Rotation(-2,z,{0}),
        Rotation(-2,x,{4}),
        Rotation(2,vector<char>{'z','x'},{1,4}),
        Rotation(-2,z,{1}),
        Rotation(-2,x,{4}),
        Rotation(2,vector<char>{'z','x'},{4,0}),
        Rotation(-2,z,{4}),
        Rotation(-2,x,{0}),
        Rotation(2,vector<char>{'z','x'},{4,1}),
        Rotation(-2,z,{4}),
        Rotation(-2,x,{1}),
        Rotation(-1,z,{0}),
        Rotation(-1,z,{1}),
        Rotation(1,z,{4}),
        Rotation(2,vector<char>{'z','x'},{4,0}),
        Rotation(-2,z,{4}),
        Rotation(-2,x,{0}),
        Rotation(2,vector<char>{'z','x'},{4,1}),
        Rotation(-2,z,{4}),
        Rotation(-2,x,{1}),
        Rotation(2,z,{4}),
        Rotation(2,x,{4}),
        Rotation(2,z,{4}),
        Rotation(2,z,{4}),
        Rotation(2,vector<char>{'z','x'},{4,3}),
        Rotation(-2,z,{4}),
        Rotation(-2,x,{3}),
        Rotation(2,z,{4}),
        Rotation(2,x,{4}),
        Rotation(2,z,{4}),
        Measure(true,z,{4},{Rotation(2,vector<char>{'z','z'},{0,1}),Rotation(-2,z,{0}),Rotation(-2,z,{1})})
    };
    gatelist = LysCompiler(circuit,4);
    gatelist.runLysCompiler(true,false);
    expected = {
        Rotation(1,x,{4}),
        Rotation(-1,vector<char>{'z','x'},{1,4}),
        Rotation(-1,vector<char>{'z','x'},{0,4}),
        Rotation(1,vector<char>{'z','z','x'},{0,1,4}),
        Rotation(2,z,{4}),
        Rotation(2,x,{4}),
        Rotation(2,z,{4}),
        Rotation(2,vector<char>{'z','x'},{0,4}),
        Rotation(2,vector<char>{'z','x'},{1,4}),
        Rotation(0,x,{4}),
        Rotation(-2,z,{0}),
        Rotation(0,vector<char>{'x','z'},{0,4}),
        Rotation(-2,z,{1}),
        Rotation(0,vector<char>{'x','z'},{1,4}),
        Rotation(2,z,{4}),
        Rotation(2,x,{4}),
        Rotation(2,vector<char>{'z','x'},{4,3}),
        Measure(false,vector<char>{'y'},{4},{Rotation(2,vector<char>{'z','z'},{0,1}),Rotation(2,z,{0}),Rotation(2,z,{1})}),
        Rotation(-2,x,{3}),
        Rotation(0,x,{0}),
        Rotation(0,x,{1})
    };
    
    if(expected != gatelist.circuit){
        cout << "Gadder true-false part 1 failed \n";
        cout << " Got : \n" ; 
        toStrVariantVec(gatelist.circuit);
        cout << " Expected : \n" ; 
        toStrVariantVec(expected);
        for(int idxG = 0; idxG < expected.size() ; idxG++){
            if (expected[idxG] != gatelist.circuit[idxG]){
                cout << "at index " << idxG << endl;
            }
        }
        return 1;
    }

    //test 3 : combine = true, layer = false
    //note:  second part of the first circuit + the 
    // gate passed to the second part from "higher"
    // functions (before call to this->runLysCompiler,
    // should be done in runLysCompiler.cpp
    circuit = {
        Rotation(-2,x,{3}),
        Rotation(0,x,{0}),
        Rotation(0,x,{1}),
        Rotation(2,vector<char>{'z','x'},{0,1}),
        Rotation(-2,z,{0}),
        Rotation(-2,x,{1}),
        Rotation(2,vector<char>{'z','x'},{2,3}),
        Rotation(-2,z,{2}),
        Rotation(-2,x,{3}),
        Measure(true,z,{0}),
        Measure(true,z,{1}),
        Measure(true,z,{2}),
        Measure(true,z,{3})
    };
    gatelist = LysCompiler(circuit,4);
    gatelist.runLysCompiler(true,false);
    expected = {
        Measure(false,z,{0}),
        Measure(true,vector<char>{'z','z'},{0,1}),
        Measure(true,z,{2}),
        Measure(false,vector<char>{'z','y'},{2,3}),
        Rotation(2,vector<char>{'z','x'},{2,3}),
        Rotation(0,x,{0}),
        Rotation(2,vector<char>{'z','x'},{0,1}),
        Rotation(0,x,{3}),
        Rotation(2,x,{1}),
        Rotation(-2,z,{2}),
        Rotation(-2,z,{0})
    };
    if(expected != gatelist.circuit){
        cout << "Gadder true-false part 2 failed \n";
        cout << " Got : \n" ; 
        toStrVariantVec(gatelist.circuit);
        cout << " Expected : \n" ; 
        toStrVariantVec(expected);
        for(int idxG = 0; idxG < expected.size() ; idxG++){
            if (expected[idxG] != gatelist.circuit[idxG]){
                cout << "at index " << idxG << endl;
            }
        }
    
        return 1;
    }

    cout << "Gadder passed \n";
    return 0;
}

int main(){
    LysCompiler gatelist = LysCompiler({Rotation(1,vector<char>{},{})});
    vector<int> results = {
        Test_defaultInitiatization(),
        Test_combineRotation(gatelist),
        Test_implementNoOrderingRotationCombination(gatelist),
        Test_noOrderingRotationCombination(gatelist),
        Test_rearrange_clifford_gates(gatelist),
        Test_applyCommutationRM(gatelist),
        Test_basis_permutation(gatelist),
        Test_applyCommutation(gatelist),
        Test_pushTForwardThread(gatelist),
        Test_reduceLayerGreedyAlgo(gatelist),
        Test_optimizeRotation(),
        Test_runLysCompiler(),
        TwoBGadder()
    };
    int count = 0 ;
    int nTests = results.size();
    for (int idx = 0 ; idx < nTests ; ++idx) {
        count = count + results[idx];
    }
    cout << "------------------------------------------\n";
    cout << "Tests passed in test_LysCompiler: " << nTests-count << "/" << nTests <<"\n";
    cout << "------------------------------------------\n";

    // TwoBGadder();
    return 0;
}
