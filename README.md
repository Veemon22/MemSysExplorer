# MemSysExplorer: Overview

This repository contains source code and datasets for the MemSysExplorer project, supported by [NSF CIRC Award #2346435](https://www.nsf.gov/awardsearch/showAward?AWD_ID=2346435&HistoricalAwards=false). 
MemSysExplorer will provide a cross-community design space exploration and evaluation framework offering researchers the capability of providing design inputs and simulating the resulting memory system solutions at different levels of the design stack, which are broadly defined as 1) application design space, 2) system design space, and 3) technology design space. 
Users can configure each level independently and evaluate the holistic impact of specific design optimizations. 
The framework's flexibility in generating a large variety of design solutions is supplemented by an integrated web-based data visualization tool to simplify the result navigation and filter to identify optimal design points.

***Stay tuned with updates, explore example data, and get in touch with our team via our [MSX webpage](https://msx.ece.tufts.edu/).***

## Contents

Our initial release (June 2025) contains the following components and features. Please navigate to each subdirectory for additional documentation, description, and materials for how to get started, and check back often for updates and additional features.

- **`apps`**: provides a configurable user interface and infrastructure for conducting workload characterization across different styles of workload profiling tools to extract memory access characteristics (dynamic binary instrumentation, architectural simulator, and hardware performance counters) and across multiple target hardware platforms (multiple memory hierarchy levels in both CPU and NVIDIA GPU systems)
- **`dataviz`**: source code, tutorials, and example data for the interactive data visualizations (which are also deployed on the project website), for users to be able to easily and clearly explore, filter, and refine data collected using MemSysExplorer
- **`tech`**: source code for two distinct components are provided;
	- `ArrayCharacterization` extends features of prior tools to conduct memory array design exploration and characterization for a wide range of technology options (i.e., provided memory cell properties and design constraints, how will a memory array perform in terms of power, area, and performance)
	- `msxFI` provides a standalone user interface for conducting fault injection and resilience studies across a range of memory technologies, fault models, and target applications
- **End-to-End Pipeline**: `run.py` interfaces with the `apps` and `tech` components to model latency, energy, and power for a given combination of workload, system, and technology parameters. The following files and directories make up the pipeline:
	- **`run.py`**: main entry point — parses the config file, orchestrates profiling, array characterization, and the analytical model, and writes all outputs
	- **`run_src/`**: supporting modules used by `run.py`, including the profiler and NVSim interfaces (`interfaces.py`), the analytical model (`model.py`), and shared utility functions (`utils.py`)
	- **`configs/`**: example and user-provided YAML config files for driving pipeline runs — see `configs/README.md` for a full breakdown of what is available and how to structure your own
	- **`results/`**: pipeline run outputs, automatically organized by run — see `results/README.md` for a full breakdown of the directory structure and output files

---

## End-to-End Pipeline

The end-to-end script `run.py` ties together the `apps` and `tech` components and computes workload-level latency, energy, and power for a given combination of workload, system configuration, and memory technology. For details on each component individually, refer to their respective subdirectory READMEs.

Run the script using the command:

```bash
python3 run.py --config /path/to/config.yaml
```

All required binaries (NVSim, Sniper, DynamoRIO) are built automatically if not already present — no manual build step is needed before running.

---

### Configuration File

Every run is driven by a single YAML config file with three required top-level sections: `system`, `apps`, and `tech`. For a full breakdown of all fields, options, and example configs, see `configs/README.md`.

- **`system`** defines the memory design target, capacity, word width, and optimization target. It also controls capacity sweeps across multiple values in a single run. System values take precedence over any overlapping fields in a tech config.
- **`apps`** controls workload profiling — either launching a new profiling run with Sniper or DynamoRIO, or pointing the pipeline at output from a previous run. The profiler chosen must be compatible with the design target (Sniper → cache, DynamoRIO → RAM).
- **`tech`** controls array characterization via NVSim — either running new characterizations from a tech config file or directory, or reusing existing NVSim result files. When reusing existing results, the pipeline validates that the stored capacity and optimization target match your system config.

---

### Analytical Model

Once profiling and array characterization are complete, the analytical model (`run_src/model.py`) combines the workload access counts from `apps` with the per-access latency, energy, and leakage values from `tech` to compute workload-level totals. For more detail on the underlying functions, see `run_src/`.

---

### Output

Each run produces a directory under `results/` that is automatically numbered so previous runs are never overwritten:

```
results/<config_name>_<N>/
├── apps_output/        # pattern config JSONs from profiling
├── tech_output/        # NVSim result YAMLs from array characterization
└── model_output/       # final results CSV
```

The final CSV at `model_output/<config_name>_results.csv` contains one row per workload × memory technology × capacity combination. For a full breakdown of output columns and how to interpret result files, see `results/README.md`.

---

Send us any issues or suggestions!