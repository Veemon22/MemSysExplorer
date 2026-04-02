# Compilers
CC = gcc
NVCC = nvcc

# Compiler flags
CFLAGS = -Wall -O3
NVCCFLAGS = -O3
LIBS = -lm

# Target names
CPU_TARGET = small_cpu_workload
GPU_TARGET = small_gpu_workload

# Source files
CPU_SRC = small_cpu_workload.c
GPU_SRC = small_gpu_workload.cu

# Default rule: build both
all: $(CPU_TARGET) $(GPU_TARGET)

# Build CPU workload
$(CPU_TARGET): $(CPU_SRC)
	$(CC) $(CFLAGS) -o $(CPU_TARGET) $(CPU_SRC) $(LIBS)

# Build GPU workload
$(GPU_TARGET): $(GPU_SRC)
	$(NVCC) $(NVCCFLAGS) -o $(GPU_TARGET) $(GPU_SRC)

# Clean up build artifacts
clean:
	rm -f $(CPU_TARGET) $(GPU_TARGET)

# Phony targets to prevent conflicts with files named 'all' or 'clean'
.PHONY: all clean