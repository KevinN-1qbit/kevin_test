BUILD_ARGS_TAG 	= latest

# Default Transpiler configs
combine 		= True
recompile 		= False
epsilon			= 1e-10	

# Build docker image
.PHONY: build
build:
	docker build . -t quay.io/1qbit/hansa:${BUILD_ARGS_TAG} -f Dockerfile

# Push image to repo
.PHONY: push
push:
	docker push quay.io/1qbit/hansa:${BUILD_ARGS_TAG}

# Pull image and build transpiled circuit
.PHONY: transpiler
transpiler:
	docker build . -t quay.io/1qbit/hansa:${BUILD_ARGS_TAG} -f Dockerfile
	docker run -v ${transpiled_circuit_path}:/workspace/Trillium/data/output -v $(input):/workspace/Trillium/input$(input) \
	quay.io/1qbit/hansa:${BUILD_ARGS_TAG} bash -c \
	"python3 lys.py -input /workspace/Trillium/input$(input) -language $(language) -combine $(combine) -recompile $(recompile) -epsilon $(epsilon)" 
