#!/bin/bash

CONFIG_DIR="/home/abao26/MemSysExplorer/tech/ArrayCharacterization/sample_configs"
RESULTS_DIR="./nvsim_results"

mkdir -p "$RESULTS_DIR"

find "$CONFIG_DIR" -type f -name "*.yaml" | while read -r yaml; do
    rel="${yaml#$CONFIG_DIR/}"
    out="$RESULTS_DIR/${rel%.yaml}.out"

    mkdir -p "$(dirname "$out")"

    echo "Running NVSim on $yaml"
    /home/abao26/MemSysExplorer/tech/ArrayCharacterization/nvsim "$yaml" > "$out" 2>&1
done