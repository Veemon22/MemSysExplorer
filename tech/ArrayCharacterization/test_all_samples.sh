#!/bin/bash

CONFIG_DIR="/Users/ashleybao/Documents/College/MemSysExplorer/tech/ArrayCharacterization/sample_configs"
RESULTS_DIR="/Users/ashleybao/Documents/College/MemSysExplorer/tech/ArrayCharacterization/sample_configs/sample_results"

mkdir -p "$RESULTS_DIR"

while IFS= read -r cfg; do
  rel="${cfg#$CONFIG_DIR/}"
  out="$RESULTS_DIR/${rel%.cfg}.out"

  mkdir -p "$(dirname "$out")"

  echo "Running NVSim on $cfg"
  ./nvsim "$cfg" > "$out" 2>&1
done < <(find "$CONFIG_DIR" -type f -name "*.cfg")
