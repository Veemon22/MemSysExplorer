#!/bin/bash

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
EXEC_DIR="$SCRIPT_DIR/../tech/ArrayCharacterization"
RESULTS_DIR="$SCRIPT_DIR/msxac_results"

cd "$EXEC_DIR" || { echo "Error: Could not find $EXEC_DIR"; exit 1; }

CONFIG_DIR="./sample_configs"

mkdir -p "$RESULTS_DIR"

find "$CONFIG_DIR" -type f -name "*.yaml" | while read -r yaml; do
    rel="${yaml#$CONFIG_DIR/}"
    out="$RESULTS_DIR/${rel%.yaml}.out"

    mkdir -p "$(dirname "$out")"

    echo "Running msxac on $yaml"
    echo "Saving output to $out"

    ./msxac "sample_configs/$rel" > "$out" 2>&1

done