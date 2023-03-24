CXX=g++
CFLAGS =-lm -pthread -O3 -std=c++17 -march=native -Wall -funroll-loops -Wno-unused-result -w # TODO: Remove the -w to see some of the warnings
DEPENDENCIES=../cpp_compiler/Operation.cpp ../cpp_compiler/Rotation.cpp ../cpp_compiler/Measure.cpp ../cpp_compiler/LysCompiler.cpp

tests :test_Operation.cpp test_Rotation.cpp test_Measure.cpp  $(DEPENDENCIES) 
	@echo "-------------------------"
	@echo "--Clear Previous Makes---"
	@echo "-------------------------"
	rm -f test_Operation test_Rotation test_Measure test_LysCompiler
	rm -f ../cpp_compiler/*.o
	rm -f ../cpp_compiler/*.so
	rm -f *.tmp

	@echo "-------------------------"
	@echo "-------Make Tests--------"
	@echo "-------------------------"
	$(CXX) $(CFLAGS) $(DEPENDENCIES) -o test_Operation test_Operation.cpp
	$(CXX) $(CFLAGS) $(DEPENDENCIES) -o test_Rotation test_Rotation.cpp
	$(CXX) $(CFLAGS) $(DEPENDENCIES) -o test_Measure test_Measure.cpp 
	$(CXX) $(CFLAGS)  $(DEPENDENCIES) -o  test_LysCompiler test_LysCompiler.cpp

	@echo "-------------------------"
	@echo "-----BEGIN TESTS---------"
	@echo "-------------------------"
	./test_Operation
	./test_Rotation
	./test_Measure
	./test_LysCompiler


	@echo "-------------------------"
	@echo "-------Clear Makes-------"
	@echo "-------------------------"
	rm -f test_Operation test_Rotation test_Measure test_LysCompiler
	rm -f ../cpp_compiler/*.o
	rm -f ../cpp_compiler/*.so
	rm -f *.tmp

	@echo "-------------------------"
	@echo "----------Done-----------"
	@echo "-------------------------"