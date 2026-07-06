CLANG := clang
CC := gcc

SRC_DIR := src
INC_DIR := include
BUILD_DIR := build
USERSPACE_DIR := ../userspace

BPF_SRC := $(SRC_DIR)/collector.bpf.c
BPF_OBJ := $(BUILD_DIR)/collector.bpf.o

LOADER_SRC := $(USERSPACE_DIR)/loader.c
TELEMETRY_SRC := $(USERSPACE_DIR)/telemetry.c
LOADER_BIN := $(BUILD_DIR)/loader

LIBBPF_LIBS := $(shell pkg-config --libs libbpf)

BPF_CFLAGS := \
	-target bpf \
	-D__TARGET_ARCH_x86 \
	-O2 \
	-g \
	-I$(INC_DIR)

all: $(BPF_OBJ) $(LOADER_BIN)

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(BPF_OBJ): $(BPF_SRC) | $(BUILD_DIR)
	$(CLANG) $(BPF_CFLAGS) -c $< -o $@

$(LOADER_BIN): \
	$(LOADER_SRC) \
	$(TELEMETRY_SRC) \
	$(USERSPACE_DIR)/telemetry.h \
	$(INC_DIR)/collector.h \
	$(BPF_OBJ) | $(BUILD_DIR)
	$(CC) \
	$(LOADER_SRC) \
	$(TELEMETRY_SRC) \
	-o $(LOADER_BIN) \
	$(LIBBPF_LIBS) \
	-lm


clean:
	rm -rf $(BUILD_DIR)

.PHONY: all clean