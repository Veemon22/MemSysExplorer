# Makefile for test programs

CC = gcc
CFLAGS = -Wall -O2
LDFLAGS = -lm

# Source files
SRCS = sample.c
# Binary names (remove .c extension)
BINS = $(SRCS:.c=)

.PHONY: all clean

all: $(BINS)

sample: sample.c
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

clean:
	rm -f $(BINS)
