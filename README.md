# Hansa Transpiler

This repo contains the source code for the Hansa Transpiler

# Submodule 

This repo uses submodules. When pulling this repo for the first time, initialize the qarrot-optimizer submodule using:

git submodule update --init

To pull latest changes from the submodule, update the submodule with:

git submodule update --remote

# Quickstart Guide with Docker

There is a docker image with all the required dependencies installed.

First, login to quay so you can pull a pre-built image.

```docker login -u="1qbit+hansabot" -p="FSVHKK9U91V24FG49BDV8RXMWKCXTKJK19PHSXYZLNO2DNYE2A6LE8OO84D8JUAL" quay.io ```


Then run the `make transpiler` command to generate a transpiled circuit.

```
make transpiler \
    INPUT_CIRCUIT=$(pwd)/data/input/test_circuits/qasm_test_10_lines.qasm \
    OUTPUT_DIR=$(pwd)/data/output \
    OUTPUT_FILENAME=transpiled_circuit.txt \
    EPSILON=1
```

This should produce a `transpiled_circuit.txt` in your `OUTPUT_DIR` folder.

* Important Note: File paths should be absolute to ensure proper volume mounting.

### List of Arguments for the `make transpiler` command:


| Parameter                    | Description                                                      |
|----------------------------- | --------------------------------------------------------------   |
| INPUT_CIRCUIT                | Absolute path to the input circuit file.                         |
| OUPUT_DIR                    | Output directory.                                                |
| OUTPUT_FILENAME              | Name of output transpiled circuit.                               |
| LANGUAGE                     | Choose the language of the circuit file. [qasm, projectq]        |
| OPTIMIZER_EXECUTABLE         | File path of optimizer executable|
| REMOVE_NON_T (optional)      | Choose whether to transform the circuit to remove the non-T rotations. Default is True.|
| RECOMPILE (optional)         | Choose whether to recompile the cpp source code. Default is False.|
| EPSILON (optional)           | Set the value of decomposition precision. Positive values only. Smaller values give higher precision. Default is 1e-10.|
| BYPASS_OPTIMIZATION (optional)| Choose whether or not to skip the optimization step to speed up process. Only generates basis conversion file. Default is False.|

* You can find instructions on how to build the submodule optimizer executable here [https://github.com/1QB-Information-Technologies/qarrot-optimizer]

# Building and Running Docker container

You can also build and enter the docker container yourself with the following `make` commands:

1. `make build`

This will build a docker image for the transpiler with all the libaries and dependencies installed already.

2. `make run`

This will use the docker image we have built to start up a running docker container.

From here you can run the transpiler code within `src/main.py` file. Here is an example:
```
python3 src/main.py \
    -input data/input/test_circuits/qasm_test_10_lines.qasm \
    -language qasm
```
In this example we are running the test circuit file through the transpiler code in `main.py` which will
will generate a transpiled circuit file within the folder `/data/output`.

The parameters for the transpiler using the `main.py` file are as follows:

| Parameter                   | Description                                                      |
|---------------------------- | --------------------------------------------------------------   |
| input                       | Absolute path to the input circuit file.                         |
| language                    | Choose the language of the circuit file. [qasm, projectq]        |
| optimizer_executable        | File path of optimizer executable.                               |
| output_filename (optional)  | Name of output transpiled circuit.                               |
| remove_non_t (optional)     | Choose whether to transform the circuit to remove the non-T rotations. Default is True.|
| recompile_cpp (optional)    | Choose whether to recompile the cpp source code. Default is False.|
| epsilon (optional)          | Set the value of decomposition precision. Positive values only. Smaller values give higher precision. Default is 1e-10.|

* You can find instructions on how to build the submodule optimizer executable here [https://github.com/1QB-Information-Technologies/qarrot-optimizer]

## Running Smoke Tests with Docker
Start up the docker containers with this command:
```
docker-compose up -d
```

After the containers are up and running you can run this command to execute the smoke tests:
```
docker exec tests python3 transpiler/transpiler_smoke_tests.py
```

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
* This has been verified to work on Macbook Intel chips.

Guide to run the transpiler to generate a transpiled circuit file:

1. Once you have cloned the repo, install dependencies by navigating into the top-level directory of the repository and running:

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
This will build and compile the transpiler C++ code.

### Apple Silicon Chip setup tips

If you are trying to run this on an Apple Silicon chip environment you may face some issues while running `cmake .` with linking the python libraries.

Here is a work around that may fix the issue:

```
cmake . \
-DPYTHON_INCLUDE_DIR=$(python3 -c "import sysconfig; print(sysconfig.get_path('include'))")  \
-DPYTHON_LIBRARY=$(python3 -c "import sysconfig; print(sysconfig.get_config_var('LIBDIR'))")
```

3. From the root folder you can now run the main transpiler code to generate a transpiled circuit file using the `src/main.py` file.

Here is an example:

```
python3 src/main.py \
    -input data/input/test_circuits/qasm_test_10_lines.qasm \
    -language qasm
```
This will generate a transpiled circuit file within the folder `/data/output` folder by default.

If you are having problems with file imports please try adding the `PYTHONPATH` of the root directory as an env variable:

`export PYTHONPATH=$PWD:$PYTHONPATH`
