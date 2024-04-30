#Set the minimum requirements and the c++ language standard 
cmake_minimum_required(VERSION 3.1.3)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

option(OPTIMIZE_FOR_BUILD_MACHINE, "Build with -march=native, optimizing for the machine you're building on at the cost of a portable binary" OFF)

# Set build type. Default to "Release". Possible values are:
# - Release
# - Debug
# - MinSizeRel (optimize for binary size, unlikely we need this)
# - RelWithDebInfo (optimize like Release but include debug information ("-g"))
# see https://cmake.org/cmake/help/latest/manual/cmake-buildsystem.7.html#build-configurations
if (NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE "RELEASE")
endif()


if (OPTIMIZE_FOR_BUILD_MACHINE)
  add_compile_options("-march=native")
endif()


# enable more warnings (-W = all)
add_compile_options("-Wall")


# Find the python package
FIND_PACKAGE(PythonInterp)

# Current code requires Python 3+
if (PYTHONINTERP_FOUND)
  if (UNIX AND NOT APPLE)
    if (PYTHON_VERSION_MAJOR EQUAL 3)
        FIND_PACKAGE(Boost COMPONENTS python${PYTHON_VERSION_SUFFIX})
        FIND_PACKAGE(PythonInterp 3)
        FIND_PACKAGE(PythonLibs 3 REQUIRED)
        #if (NOT Boost_FOUND)
        #    message(FATAL_ERROR "Unable to find Boost. Minimum required version is boost-python3")
        #endif()
    else()
        message(FATAL_ERROR "Unable to find correct Python version. Minimum required version is Python 3")
    endif()
  else()    
    if (PYTHON_VERSION_MAJOR EQUAL 3)
        FIND_PACKAGE(Boost COMPONENTS python${PYTHON_VERSION_MAJOR}${PYTHON_VERSION_MINOR})
        FIND_PACKAGE(PythonInterp 3)
        FIND_PACKAGE(PythonLibs 3 REQUIRED)
        #if (NOT Boost_FOUND)
        #    message(FATAL_ERROR "Unable to find Boost. Minimum required version is boost-python3")
        #endif()
    else()
        message(FATAL_ERROR "Unable to find correct Python version. Minimum required version is Python 3")
    endif()
  endif()
else()
    message("Python not found")
endif()

message(STATUS "PYTHON_LIBRARIES = ${PYTHON_LIBRARIES}")
message(STATUS "PYTHON_EXECUTABLE = ${PYTHON_EXECUTABLE}")
message(STATUS "PYTHON_INCLUDE_DIRS = ${PYTHON_INCLUDE_DIRS}")
message(STATUS "Boost version: ${Boost_VERSION}")
message(STATUS "Boost_LIBRARIES = ${Boost_LIBRARIES}")
message(STATUS "CMAKE_BUILD_TYPE = ${CMAKE_BUILD_TYPE}")

ENABLE_TESTING()

# Must ensure the target NAME ('runLysCompiler' in this case) is the same as the python module name BOOST_PYTHON_MODULE(NAME)
python_add_module(runLysCompiler runLysCompiler.cpp)
#target_compile_options(runLysCompiler PUBLIC "-Wno-dev") # attempt to suppress warnings
target_include_directories(runLysCompiler PUBLIC ${Boost_INCLUDE_DIRS} ${PYTHON_INCLUDE_DIRS})
target_link_libraries(runLysCompiler ${Boost_LIBRARIES} ${PYTHON_LIBRARIES})