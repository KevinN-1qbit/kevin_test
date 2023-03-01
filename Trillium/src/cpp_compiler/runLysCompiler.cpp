#include "Operation.hpp"
#include "Operation.cpp"

#include "Rotation.hpp"
#include "Rotation.cpp"

#include "Measure.hpp"
#include "Measure.cpp"

#include "LysCompiler.hpp"
#include "LysCompiler.cpp"

#include <boost/python.hpp>
#include <boost/python/def.hpp>
#include <boost/python/suite/indexing/map_indexing_suite.hpp>
#include <boost/python/suite/indexing/vector_indexing_suite.hpp>

using namespace std;
namespace py = boost::python;


py::list vRtoPythonList(const std::vector<Rotation>& vec)
{
    py::object get_iter = py::iterator<std::vector<Rotation> >();
    py::object iter = get_iter(vec);
    py::list l(iter);
    return l;
}

py::list vMtoPythonList(const std::vector<Measure>& vec)
{
    py::object get_iter = py::iterator<std::vector<Measure> >();
    py::object iter = get_iter(vec);
    py::list l(iter);
    return l;
}

py::list vInttoPythonList(const std::vector<int>& vec)
{
    py::object get_iter = py::iterator<std::vector<int> >();
    py::object iter = get_iter(vec);
    py::list l(iter);
    return l;
}

vector<int> toCppInt(py::list& pylist) {
    std::vector<int> indices;

    for(int i=0; i < py::len(pylist); i++) {
        int j = py::extract<int>(pylist[i]);
        indices.push_back(j);
    }
    return indices; 
}


py::tuple outputToPythonObj (vector<shared_ptr<Operation>> compilerResults) {
    vector<Rotation> compiledR;
    vector<Measure> compiledM;
    vector<int> rotIndex;
    vector<int> meaIndex;

    for (int i=0; i < compilerResults.size(); i++)
    {
        if (compilerResults[i]->isRotation()) {
            Rotation r = *static_pointer_cast<Rotation>(compilerResults[i]);
            compiledR.push_back(r);
            rotIndex.push_back(i);
        }
        else {
            Measure m = *static_pointer_cast<Measure>(compilerResults[i]);
            compiledM.push_back(m);
            meaIndex.push_back(i);
        }
    }

    py::list compiledRotation = vRtoPythonList(compiledR);
    py::list compiledMeasure  = vMtoPythonList(compiledM);
    py::list compiledRindex   = vInttoPythonList(rotIndex);
    py::list compiledMindex   = vInttoPythonList(meaIndex);

    py::tuple returnPair;
    returnPair = py::make_tuple(compiledRotation, compiledRindex, compiledMeasure, compiledMindex);

    return returnPair;
}

py::tuple run_lys_with_mea(vector<Rotation> rotations, vector<int> roIndex, vector<Measure> measures, vector<int> meIndex, bool combine) {
    // the circuit has non-default measurement in the middle or at the end of the circuit
//    std::vector<Gate> gates(roIndex.size() + meIndex.size());
    std::vector<std::shared_ptr<Operation>> gates(roIndex.size() + meIndex.size());

    for (int i=0; i< roIndex.size(); i++){
        gates[roIndex[i]] = make_shared<Rotation>(rotations[i]);
    }
    for (int i=0; i< meIndex.size(); i++){
        gates[meIndex[i]] = make_shared<Measure>(measures[i]);
    }

    LysCompiler compiler = LysCompiler(move(gates));
    pair<vector<vector<std::shared_ptr<Operation>> >, int> compilerResults_layered = compiler.runLysCompiler(combine, false);
    int startingIdxToRemoveAfterMeasure   = compilerResults_layered.second; // if layer==false, we only care about startingIdxToRemoveAfterMeasure, the "compilerResults_layered" itself will be empty 
    vector<shared_ptr<Operation>> compiledVec;                           // vector that will hold the compiled circuit output
    compiledVec.insert(compiledVec.end(), compiler.circuit.begin(), compiler.circuit.begin() + startingIdxToRemoveAfterMeasure);

    py::tuple outputPython = outputToPythonObj(move(compiledVec));

    return outputPython;
}


py::tuple run_lys_default_mea(int numDefaultMeasurements, vector<Rotation> rotations, bool combine) {
    // the circuit has no measurement and we append a default measurement at the end 
//    std::vector<Gate> gates(rotations.size());
    std::vector<std::shared_ptr<Operation>> gates;
    gates.reserve(rotations.size());
//    for (int i=0; i< rotations.size(); i++) gates[i] = rotations[i];
    for (int i=0; i< rotations.size(); i++){
        gates.emplace_back(std::make_shared<Rotation>(rotations[i]));
    }

    LysCompiler compiler = LysCompiler(numDefaultMeasurements, move(gates));
    pair<vector<vector<std::shared_ptr<Operation>> >, int> compilerResults_layered = compiler.runLysCompiler(combine, false); // if layer==false, this will return an empty list
    int startingIdxToRemoveAfterMeasure   = compilerResults_layered.second; // if layer==false, we only care about startingIdxToRemoveAfterMeasure, the "compilerResults_layered" itself will be empty 
    vector<shared_ptr<Operation>> compiledVec;                           // vector that will hold the compiled circuit output
    compiledVec.insert(compiledVec.end(), compiler.circuit.begin(), compiler.circuit.begin() + startingIdxToRemoveAfterMeasure);

    py::tuple outputPython = outputToPythonObj(move(compiledVec));

    return outputPython;
        
}

py::tuple run_lys_section(vector<vector<Rotation>> rotVecVec, vector<vector<int>> rotInd, vector<vector<Measure>> meaVecVec, vector<vector<int>> meaInd, py::list ancilla, bool combine) {

    int ancillaBegin = py::extract<int>(ancilla[0]);

    // first, construct this gateVecVec, which holds the input circuit. Each sub-array holds the section circuit
    vector<vector<shared_ptr<Operation>>> gateVecVec(rotVecVec.size());
    int measOutputPosition = 0;
    for (int i=0; i< rotVecVec.size(); i++){
        vector<shared_ptr<Operation>> gate_section(rotInd[i].size() + meaInd[i].size());

        for (int j=0; j< rotInd[i].size(); j++){
            gate_section.emplace_back(make_shared<Rotation>(rotVecVec[i][j]));
        }
        for (int j=0; j< meaInd[i].size(); j++){
            meaVecVec[i][j].outputPosition = measOutputPosition;
            measOutputPosition++;
            gate_section.emplace_back(make_shared<Measure>(meaVecVec[i][j]));
        }
        gateVecVec[i] = move(gate_section);
    }

    vector<shared_ptr<Operation>> compiledVec;  // vector that will hold the compiled circuit output

    // Process each section in a sequential order. For each section, create a compiler obj
    for (int i=0; i < gateVecVec.size(); i++) {
        // Step 1
        // Construct the compiler and run the compiler. The compiler will change the list of gates in-place.
        // startingIdxToRemoveAfterMeasure: the index at which commuted cliffords begin; all gates from this index startingIdxToRemoveAfterMeasure (inclusive) to the end of the list,
        // will be inserted into the beginning of the next section, and not included in the current section's output
        LysCompiler compiler                            = LysCompiler(move(gateVecVec[i]), ancillaBegin);
        pair<vector<vector<std::shared_ptr<Operation>>>, int> compilerResults = compiler.runLysCompiler(combine, false); // since layer=false, we only care about the int startingIdxToRemoveAfterMeasure; the vecvec will be empty
        int startingIdxToRemoveAfterMeasure             = compilerResults.second;

        // Step 2
        // insert the cliffords on not-measured qubits from the current section into the next section
        if (i < gateVecVec.size() - 1) {
            gateVecVec[i+1].insert(gateVecVec[i+1].begin(), compiler.circuit.begin() + startingIdxToRemoveAfterMeasure, compiler.circuit.end() );
        }

        // Step 3
        // then, append the compiled circuit from this section to the output vector. This compiler.circuit includes the commuted over Cliffords,
        // and thus, we only append up until startingIdxToRemoveAfterMeasure - 1 (inclusive)
        compiledVec.insert(compiledVec.end(), compiler.circuit.begin(), compiler.circuit.begin() + startingIdxToRemoveAfterMeasure);
    }

    // return the output cpp objects as python objects
    py::tuple outputPython = outputToPythonObj(compiledVec);

    return outputPython;
}


/**
 * @brief A function for returning the xBasis and zBasis bitsets as strings for Rotation objs.
 * 
 * @note This function is a temporary fix since we have not been able use boost to return 
 * the string without a function.
 * 
 * @return boost::python::tuple which is a python tuple with two strings.
 */
boost::python::tuple return_rotation_basis_string(Rotation rot) { 
    boost::python::tuple returnPair;
    returnPair = boost::python::make_tuple(rot.xBasis.to_string(), rot.zBasis.to_string());
    return returnPair;
}
BOOST_PYTHON_FUNCTION_OVERLOADS(return_rotation_basis_strings_overloads, return_rotation_basis_string, 1, 1)


/**
 * @brief A function for returning the xBasis and zBasis bitsets as strings for Measure objs.
 * 
 * @note This function is a temporary fix since we have not been able use boost to return 
 * the string without a function.
 * 
 * @return boost::python::tuple which is a python tuple with two strings.
 */
boost::python::tuple return_measure_basis_string(Measure mea) { 
    boost::python::tuple returnPair;
    returnPair = boost::python::make_tuple(mea.xBasis.to_string(), mea.zBasis.to_string());
    return returnPair;
}
BOOST_PYTHON_FUNCTION_OVERLOADS(return_measure_basis_strings_overloads, return_measure_basis_string, 1, 1)



int main(){
    return 0;
}

BOOST_PYTHON_MODULE(runLysCompiler)
{
    using namespace boost::python;
    class_<Operation>("Operation")
        .add_property("xBasis", &Operation::xBasis) 
        .add_property("zBasis", &Operation::zBasis)
      ;
    
    class_<Rotation>("Rotation")
        .add_property("xBasis", &Rotation::xBasis)
        .add_property("zBasis", &Rotation::zBasis)
        .add_property("angle", &Rotation::angle)
        .def(init<>())
        .def(init<int, std::string, std::string>())
      ;

    class_<Measure>("Measure")
        .add_property("xBasis", &Measure::xBasis)
        .add_property("zBasis", &Measure::zBasis)
        .add_property("phase", &Measure::phase)
        .def(init<>())
        .def(init<int, std::string, std::string>())
      ;

    class_<std::vector<Rotation> >("RotVec")
        .def(vector_indexing_suite<std::vector<Rotation> >() )
    ;

    class_<std::vector<Measure> >("MeaVec")
        .def(vector_indexing_suite<std::vector<Measure> >() )
    ;

    class_<std::vector<vector<Rotation>> >("RotVecVec")
        .def(vector_indexing_suite<std::vector<vector<Rotation>> >() )
    ;

    class_<std::vector<vector<Measure>> >("MeaVecVec")
        .def(vector_indexing_suite<std::vector<vector<Measure>> >() )
    ;

//    class_<std::vector<Gate> >("GateVec")
//        .def(vector_indexing_suite<std::vector<Gate> >() )
    ;

    class_<std::vector<int> >("indexVec")
        .def(vector_indexing_suite<std::vector<int> >() )
    ;

    class_<std::vector<vector<int>> >("indexVecVec")
        .def(vector_indexing_suite<std::vector<vector<int>> >() )
    ;

    def("toCppInt", toCppInt);

    def("run_lys_with_mea", run_lys_with_mea);

    def("run_lys_default_mea", run_lys_default_mea);

    def("run_lys_section", run_lys_section);

    def("return_rotation_basis_string", &return_rotation_basis_string, return_rotation_basis_strings_overloads(args("rot")));

    def("return_measure_basis_string", &return_measure_basis_string, return_measure_basis_strings_overloads(args("meas")));

}

