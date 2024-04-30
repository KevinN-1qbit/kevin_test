# Docker configs
IMAGE_NAME      ?= quay.io/1qbit/qarrot-transpiler
HOME_DIR		?= /app
VERSION 		?= node.v0.1

# Default Transpiler configs
LANGUAGE 		?= qasm
REMOVE_NON_T 	?= True
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

# Run docker container
.PHONY: run
run:
	docker run -it -v `pwd`/data/output:$(HOME_DIR)/data/output --rm ${IMAGE_NAME}.${VERSION} bash

# Run transpiler
.PHONY: transpiler
transpiler:
	docker run -v $(INPUT_CIRCUIT):$(HOME_DIR)/data$(INPUT_CIRCUIT) \
		-v ${OUTPUT_DIR}:$(HOME_DIR)/data/output \
		${IMAGE_NAME}.${VERSION} bash -c \
		"python3 src/main.py -input $(HOME_DIR)/data$(INPUT_CIRCUIT) \
		-output_filename ${OUTPUT_FILENAME} \
		-language $(LANGUAGE) -remove_non_t $(REMOVE_NON_T) \
		-recompile $(RECOMPILE) -epsilon $(EPSILON)"

# make hansa: brings up HANSA containers [transpiler, compiler]
.PHONY: up
up:
	docker compose up -d

.PHONY: build
build:
	docker compose build


# make down: brings up HANSA containers [transpiler, compiler]
.PHONY: down
down:
	docker compose down
