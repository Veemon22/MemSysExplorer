# NVBit repository and target directory
NVBIT_REPO := https://github.com/NVlabs/NVBit.git
NVBIT_DIR := nvbit_release
NVBIT_ARCHIVE = nvbit-Linux-x86_64-1.7.4.tar.bz2

# Required Versions
REQUIRED_DRIVER_VERSION := 560
REQUIRED_CUDA_VERSION := 12

# Paths to setup scripts (referencing but not sourcing)
SETUP_ENV_SCRIPT := $(APPS_HOME)/tools/

.PHONY: nvbit clean check_nvidia check_cuda check_all build_client all

nvbit: check_all
	@if [ -d "$(NVBIT_DIR)" ]; then \
		echo "NVBit is already installed in $(NVBIT_DIR), proceeding to build process."; \
	else \
		echo "Downloading NVBit"; \
		wget --show-progress https://github.com/NVlabs/NVBit/releases/download/v1.7.4/nvbit-Linux-x86_64-1.7.4.tar.bz2; \
		echo "Extracting NVBit..."; \
		tar -xvjf "$(NVBIT_ARCHIVE)"; \
		rm -f "$(NVBIT_ARCHIVE)"; \
		echo "NVBit installed in $(NVBIT_DIR)"; \
	fi
	@$(MAKE) build_client

clean:
	@rm -rf $(NVBIT_DIR) $(NVBIT_ARCHIVE) lib
	@rm -f *.so *.o ws_tsearch.o
	@echo "Cleaned NVBit installation."

# Check if an NVIDIA GPU is available and has a supported driver version
check_nvidia:
	@echo "Checking for NVIDIA GPU and driver version..."
	@if ! command -v nvidia-smi > /dev/null 2>&1; then \
		echo "Error: No NVIDIA GPU detected or NVIDIA drivers are not installed."; \
		echo "Please install the correct driver: https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/index.html"; \
		exit 1; \
	else \
		DRIVER_VERSION=$$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | cut -d. -f1); \
		if [ "$$DRIVER_VERSION" -lt "$(REQUIRED_DRIVER_VERSION)" ]; then \
			echo "Warning: Installed NVIDIA driver version $$DRIVER_VERSION is lower than required ($(REQUIRED_DRIVER_VERSION))."; \
			echo "Update the driver: https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/index.html"; \
			exit 1; \
		else \
			echo "NVIDIA driver version $$DRIVER_VERSION is valid (>= $(REQUIRED_DRIVER_VERSION))."; \
		fi; \
		nvidia-smi; \
	fi

# Check if CUDA is installed and version is at least 12.x
check_cuda:
	@echo "Checking for CUDA installation..."
	@if ! command -v nvcc > /dev/null 2>&1; then \
		echo "CUDA is not available!"; \
		echo "You may need to source: $(SETUP_ENV_SCRIPT)"; \
		echo "Or install CUDA: https://developer.nvidia.com/cuda-downloads"; \
		exit 1; \
	else \
		CUDA_VERSION=$$(nvcc --version | grep "release" | sed -n 's/.*release \([0-9]*\)\..*/\1/p'); \
		if [ "$$CUDA_VERSION" -lt "$(REQUIRED_CUDA_VERSION)" ]; then \
			echo "Warning: CUDA version $$CUDA_VERSION is lower than required ($(REQUIRED_CUDA_VERSION))."; \
			echo "Update CUDA: https://developer.nvidia.com/cuda-downloads"; \
			exit 1; \
		else \
			echo "CUDA version $$CUDA_VERSION is valid (>= $(REQUIRED_CUDA_VERSION))."; \
		fi; \
	fi

check_all: check_nvidia check_cuda
	@echo "System is ready for NVBit Profilers."

# NVCC and PTXAS configurations
NVCC=nvcc -ccbin=$(CXX) -D_FORCE_INLINES
PTXAS=ptxas

NVCC_VER_REQ=10.1
NVCC_VER=$(shell $(NVCC) --version | grep release | cut -f2 -d, | cut -f3 -d' ')
NVCC_VER_CHECK=$(shell echo "${NVCC_VER} >= $(NVCC_VER_REQ)" | bc)

ifeq ($(NVCC_VER_CHECK),0)
$(error ERROR: nvcc version >= $(NVCC_VER_REQ) required to compile an nvbit tool! Instrumented applications can still use lower versions of nvcc.)
endif

PTXAS_VER_ADD_FLAG=12.3
PTXAS_VER=$(shell $(PTXAS) --version | grep release | cut -f2 -d, | cut -f3 -d' ')
PTXAS_VER_CHECK=$(shell echo "${PTXAS_VER} >= $(PTXAS_VER_ADD_FLAG)" | bc)

ifeq ($(PTXAS_VER_CHECK), 0)
MAXRREGCOUNT_FLAG=-maxrregcount=24
else
MAXRREGCOUNT_FLAG=
endif

NVBIT_PATH=./nvbit_release/core
COMMON_PATH=../common

INCLUDES=-I$(NVBIT_PATH) -I$(COMMON_PATH)/include

LIBS=-L$(NVBIT_PATH) -lnvbit

# Common library sources
COMMON_SOURCES=$(COMMON_PATH)/src/ws_tsearch.c
NVCC_PATH=-L $(subst bin/nvcc,lib64,$(shell which nvcc | tr -s /))

SOURCES=$(wildcard *.cu)

OBJECTS=$(SOURCES:.cu=.o)
COMMON_OBJECTS=ws_tsearch.o
ARCH?=all

mkfile_path := $(abspath $(lastword $(MAKEFILE_LIST)))
current_dir := $(notdir $(patsubst %/,%,$(dir $(mkfile_path))))

NVBIT_TOOL=lib/$(current_dir).so

build_client: lib $(NVBIT_TOOL)

lib:
	@mkdir -p lib

$(NVBIT_TOOL): $(OBJECTS) $(COMMON_OBJECTS) $(NVBIT_PATH)/libnvbit.a
	$(NVCC) -arch=$(ARCH) -O3 $(OBJECTS) $(COMMON_OBJECTS) $(LIBS) $(NVCC_PATH) -lcuda -lcudart_static -shared -o $@

%.o: %.cu
	$(NVCC) -dc -c -std=c++11 $(INCLUDES) -Xptxas -cloning=no -Xcompiler -Wall -arch=$(ARCH) -O3 -Xcompiler -fPIC $< -o $@

inject_funcs.o: inject_funcs.cu
	$(NVCC) $(INCLUDES) $(MAXRREGCOUNT_FLAG) -Xptxas -astoolspatch --keep-device-functions -arch=$(ARCH) -Xcompiler -Wall -Xcompiler -fPIC -c $< -o $@

# Compile common library sources (C code) - must use CC not CXX for C files
# Note: ws_tsearch.c already defines _GNU_SOURCE internally, so we don't pass it here
ws_tsearch.o: $(COMMON_PATH)/src/ws_tsearch.c
	$(CC) -c -O3 -fPIC $(INCLUDES) $< -o $@

