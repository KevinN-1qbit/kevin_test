BUILD_ARGS_TAG 	= latest

# Default Transpiler configs
combine 		= True
recompile 		= False
epsilon			= 1e-10	

.PHONY: build
build:
	docker build . -t quay.io/1qbit/hansa:${BUILD_ARGS_TAG} -f Dockerfile

.PHONY: push
push:
	docker push quay.io/1qbit/hansa:${BUILD_ARGS_TAG}

.PHONY: transpiler
transpiler:
	docker run -v ${circuit_path}:/workspace/Trillium/data/output -v $(input):$(input) \
	quay.io/1qbit/hansa:${BUILD_ARGS_TAG} bash -c \
	"python3 Trillium/lys.py -input $(input) -language $(language) -combine $(combine) -recompile $(recompile) -epsilon $(epsilon)" 
