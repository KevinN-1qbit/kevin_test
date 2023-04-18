# Docker configs
IMAGE_NAME      ?= quay.io/1qbit/hansa:transpiler
HOME_DIR		?=/workspace/Trillium
VERSION 		?= v0.1

# Default Transpiler configs
LANGUAGE 		?= qasm
COMBINE 		?= True
RECOMPILE 		?= False
EPSILON			?= 1e-10

# Build docker image
.PHONY: build
build:
	docker build . -t ${IMAGE_NAME}.${VERSION} -f Dockerfile

# Push image to repo
.PHONY: push
push:
	docker push ${IMAGE_NAME}.${VERSION}

# Run transpiler
.PHONY: transpiler
transpiler:
	docker run -v $(INPUT_CIRCUIT):$(HOME_DIR)/data/$(INPUT_CIRCUIT) \
		-v ${OUTPUT_DIR}:$(HOME_DIR)/data/output \
		${IMAGE_NAME}.${VERSION} bash -c \
		"python3 lys.py -input $(HOME_DIR)/data/$(INPUT_CIRCUIT) \
		-output_filename ${OUTPUT_FILENAME} \
		-language $(LANGUAGE) -combine $(COMBINE) \
		-recompile $(RECOMPILE) -epsilon $(EPSILON)"
