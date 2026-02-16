# MemSysExplorer: Overview

This repository contains source code and datasets for the MemSysExplorer project, supported by [NSF CIRC Award #2346435](https://www.nsf.gov/awardsearch/showAward?AWD_ID=2346435&HistoricalAwards=false). 
MemSysExplorer will provide a cross-community design space exploration and evaluation framework offering researchers the capability of providing design inputs and simulating the resulting memory system solutions at different levels of the design stack, which are broadly defined as 1) application design space, 2) system design space, and 3) technology design space. 
Users can configure each level independently and evaluate the holistic impact of specific design optimizations. 
The framework's flexibility in generating a large variety of design solutions is supplemented by an integrated web-based data visualization tool to simplify the result navigation and filter to identify optimal design points.

***Stay tuned with updates, explore example data, and get in touch with our team via our [MSX webpage](https://msx.ece.tufts.edu/).***

## Contents

Our initial release (June 2025) contains the following components and features.  Please navigate to each subdirectory for additional documentation, description, and materials for how to get started, and check back often for updates and additional features.  

- **`apps`**: provides a configurable user interface and infrastructure for conducting workload characterization across different styles of workload profiling tools to extract memory access characteristics (dynamic binary instrumentation, architectural simulator, and hardware performance counters) and across multiple target hardware platforms (multiple memory hierarchy levels in both CPU and NVIDIA GPU systems)
- **`dataviz`**: source code, tutorials, and example data for the interactive data visualizations (which are also deployed on the project website), for users to be able to easily and clearly explore, filter, and refine data collected using MemSysExplorer
- **`tech`**: source code for two distinct components are provided;
	- `ArrayCharacterization` extends features of prior tools to conduct memory array design exploration and characterization for a wide range of technology options (i.e., provided memory cell properties and design constraints, how will a memory array perform in terms of power, area, and performance)
	- `msxFI` provides a standalone user interface for conducting fault injection and resilience studies across a range of memory technologies, fault models, and target applications

## End-toEnd Pipeline

The end-to-end script `run.py` interfaces with apps and tech tools and models latency and power for a given combination of workload, system, and technology parameters.

Run the script using the command:

```
python3 run.py --config /path/to/config
```

Example configuration file:

```
system:
  DesignTarget: cache
  Capacity:
    Value: 128
    Unit: KB
  WordWidth: 128 # bits
apps:
  run: new
  profiler: perf
  level: l2
  executable: "python3 configs/perf_run_config/hello.py"
tech:
  run: new  
  array_characterization_config: configs/tech_configs/sample_configs/sample_FeFET_32nm_tech_config.yaml
```

Config files have three components: system, apps, and tech.

- System: requires parameters `DesignTarget`, `Capacity`, and `WordWidth`. Currently, the only supported option for `DesignTarget` is cache.
- Apps: we can use a new or existing run from the apps interfaces. When using a new run, set `run` to 'new' and provide `profiler`, `level`, and `executable`. If using results from an existing run, set `run` to 'existing' and provide a path to those results. The end-to-end script currently only supports profiling with perf.
- Tech: requires parameters `run` and `array_characterization_config`. We can also use an existing run as in the apps section. Note that there is overlap between system parameters and ones in example array characterization configuration files; if they conflict, we use system parameters.

More example configuration files are provided in the `config` directory.

Send us any issues or suggestions!
