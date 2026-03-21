# Makefile for test programs

CC = gcc
NVCC = nvcc
CFLAGS = -Wall -O2
NVCCFLAGS = -O2
LDFLAGS = -lm

# Source files
C_SRCS = sample.c
CUDA_SRCS = sample_gpu.cu

# Binary names (remove extensions)
C_BINS = $(C_SRCS:.c=)
CUDA_BINS = $(CUDA_SRCS:.cu=)

.PHONY: all clean cpu gpu

all: cpu

cpu: $(C_BINS)

gpu: $(CUDA_BINS)

sample: sample.c
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

sample_gpu: sample_gpu.cu
	$(NVCC) $(NVCCFLAGS) -o $@ $<

clean:
	rm -f $(C_BINS) $(CUDA_BINS)
