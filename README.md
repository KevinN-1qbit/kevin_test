# Hansa Transpiler

This repo contains the source code for the Hansa Transpiler


# Quickstart Guide with Docker

There is a docker image with all the required dependencies installed.

First, login to quay so you can pull a pre-built image

```docker login -u="1qbit+hansabot" -p="FSVHKK9U91V24FG49BDV8RXMWKCXTKJK19PHSXYZLNO2DNYE2A6LE8OO84D8JUAL" quay.io ```


Then run the make transpiler command to generate a transpiled circuit

```
make transpiler \
    INPUT_CIRCUIT=$(pwd)/data/input/test_circuits/qasm_test_10_lines.qasm \
    OUTPUT_DIR=$(pwd)/data/output \
    OUTPUT_FILENAME=transpiled_circuit.txt \
    EPSILON=1
```

This should produce a `transpiled_circuit.txt` in your `OUTPUT_DIR` folder.

* Important Note: File paths should be absolute to ensure proper volume mounting


### List of Command Arguments for the Transpiler:


| Parameter                | URL                                                              |
|------------------------ | --------------------------------------------------------------   |
| INPUT_CIRCUIT           | Absolute path to the input circuit file.                         |
| OUPUT_DIR               | Output directory.                                                 |
| OUTPUT_FILENAME         | Name of output transpiled circuit.                                |
| LANGUAGE                | Choose the language of the circuit file. [qasm, projectq]        |
| COMBINE (optional)      | Choose whether to combine the non-T rotations with measurement. Default is True|
| RECOMPILE (optional)    | Choose whether to recompile the cpp source code. Default is False|
| EPSILON (optional)      | Set the value of decomposition precision. Positive values only. Smaller values give higher precision. Default is 1e-10|


# Getting started Local Development:

### Prerequisites:
Python 3.8 +

Cpp standard 11+

Boost-python3

CMAKE 3.1.3+

Make tools

Numpy 

### Setting up the environment:
For MacOS, we recommend you install/update the following prerequisites through Homebrew:

```brew install boost-python3```

```brew install cmake```

```brew install make```


### Running the Transpiler:

Guide to run the transpiler to generate a transpiled circuit file

1. Once you have cloned the repo, install dependencies by navigating into the top-level directory of the repository and running

```
pip install -e .
```

2. Navigate to the folder `src/cpp_compiler`. This folder includes all the main optimized C++ for the actual compiler. It uses Boost to connect to the python modules within the `src/python_wrapper` folder. From here run the following commands.

```
cmake .
```

```
make
```

This will build and compile the transpiler C++ code

3. From the root folder you can now run the main transpiler code to generate a transpiled circuit file using the `src/lys.py` file.

Here is an example:

```
python3 src/lys.py \
    -input data/input/test_circuits/qasm_test_10_lines.qasm \
    -language qasm
```
This will generate a transpiled circuit file within the folder `/data/output` folder by default

