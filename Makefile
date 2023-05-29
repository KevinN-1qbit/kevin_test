# Docker config
IMAGE_NAME                      ?= quay.io/1qbit/hansa:compiler

HOME_DIR                        ?= /workspace
VERSION                         ?= v0.2

# Default compiler config
GENERATE_HLA_SCHEDULE           ?= False
DUAL_MODE                       ?= False

.PHONY: compiler build push pull run exec

compiler: pull run

build:
	docker build -f Dockerfile -t $(IMAGE_NAME).${VERSION} .

push:
	docker push $(IMAGE_NAME).${VERSION}

pull:
	@docker image inspect $(IMAGE_NAME).${VERSION} > /dev/null 2>&1 || docker pull $(IMAGE_NAME).${VERSION}

run:
	docker run \
		-v $(INPUT_T_CIRCUIT):$(HOME_DIR)/data/inputs/transpiled_circuits$(INPUT_T_CIRCUIT) \
		-v $(OUTPUT_DIR):$(HOME_DIR)/data/outputs \
		$(if $(INPUT_LAYOUT), \
			-v $(INPUT_LAYOUT):$(HOME_DIR)/data/inputs/layout_files$(INPUT_LAYOUT)) \
		$(if $(INPUT_HLASCHEDULER_PARAMS), \
			-v $(INPUT_HLASCHEDULER_PARAMS):$(HOME_DIR)/data/inputs/hla_scheduler_params$(INPUT_HLASCHEDULER_PARAMS)) \
		$(IMAGE_NAME).${VERSION} bash -c \
		"python3 src/main.py --input_t_circuit $(HOME_DIR)/data/inputs/transpiled_circuits$(INPUT_T_CIRCUIT) \
		--output_dir $(HOME_DIR)/data/outputs \
		$(if $(OUTPUT_REPORT_FILENAME), --output_report_filename $(OUTPUT_REPORT_FILENAME)) \
		$(if $(INPUT_LAYOUT), --input_layout $(HOME_DIR)/data/inputs/layout_files$(INPUT_LAYOUT)) \
		$(if $(INPUT_HLASCHEDULER_PARAMS), --input_hla_scheduler_params $(HOME_DIR)/data/inputs/hla_scheduler_params$(INPUT_HLASCHEDULER_PARAMS)) \
		--generate_hla_schedule $(GENERATE_HLA_SCHEDULE) \
		--dual_mode $(DUAL_MODE)"
