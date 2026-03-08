#!/bin/bash

BASE_DIR="/home/abao26/MemSysExplorer/tech/ArrayCharacterization"
CONFIG_DIR="$BASE_DIR/sample_configs"
RESULTS_DIR="./nvsim_results"

mkdir -p "$RESULTS_DIR"

find "$CONFIG_DIR" -type f -name "*.yaml" | while read -r yaml; do
    rel="${yaml#$CONFIG_DIR/}"
    out="$RESULTS_DIR/${rel%.yaml}.out"

    mkdir -p "$(dirname "$out")"

    echo "Running NVSim on $yaml"

    (
        cd "$BASE_DIR" || exit 1
        ./nvsim "sample_configs/$rel"
    ) > "$out" 2>&1

done