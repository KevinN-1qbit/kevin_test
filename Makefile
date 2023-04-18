# Docker configs
VERSION 		?= latest
HOME_DIR		?= /workspace/Trillium

# Default Transpiler configs
LANGUAGE 		?= qasm
COMBINE 		?= True
RECOMPILE 		?= False
EPSILON			?= 1e-10

# Build docker image
.PHONY: build
build:
	docker build . -t quay.io/1qbit/hansa:transpiler -f Dockerfile

# Push image to repo
.PHONY: push
push:
	docker push quay.io/1qbit/hansa:transpiler

# Run transpiler
.PHONY: transpiler
transpiler:
	docker run -v $(INPUT_CIRCUIT):$(HOME_DIR)/data/$(INPUT_CIRCUIT) \
		-v ${OUTPUT_DIR}:$(HOME_DIR)/data/output \
		quay.io/1qbit/hansa:transpiler bash -c \
		"python3 lys.py -input $(HOME_DIR)/data/$(INPUT_CIRCUIT) \
		-output_filename ${OUTPUT_FILENAME} \
		-language $(LANGUAGE) -combine $(COMBINE) \
		-recompile $(RECOMPILE) -epsilon $(EPSILON)"
