BUILD_ARGS_TAG ?= latest

CIRCUIT_PATH 	= ${circuit_path}

# Transpiler configs
INPUT_FILE 		= ${input_file}
LANGUAGE 		= ${language}
COMBINE 		= ${combine}
RECOMPILE_CPP 	= ${recompile_cpp}
EPISLON 		= ${epsilon}


build:
	docker build . -t quay.io/1qbit/hansa:${BUILD_ARGS_TAG} -f Dockerfile

push:
	docker push quay.io/1qbit/hansa:${BUILD_ARGS_TAG}

transpiler:
	docker run -i -v ${CIRCUIT_PATH}:/workspace/Trillium/data quay.io/1qbit/hansa:${BUILD_ARGS_TAG} bash -c \ 
	""python3 lys.py -input data/input/test_circuits/qasm_test_10_lines.qasm -language qasm "" 

kevintest:
	if [ -z "$(CIRCUIT_PATH)" ]; then \
		echo "Hello World"; \
	else \
		echo $(CIRCUIT_PATH); \
	fi

.PHONY: my_target
my_target:
	if [ -z "$(PARAM)" ]; then \
		echo "Hello World"; \
	else \
		echo $(PARAM); \
	fi

