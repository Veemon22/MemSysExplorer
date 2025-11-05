Sniper Simulator Documentation
==============================

The **SniperProfiler** integrates the Sniper architectural simulator into MemSysExplorer to evaluate memory system behavior at cycle-level precision. It allows users to configure memory hierarchy models, run simulations with real applications, and extract detailed memory performance statistics.

Sniper is particularly useful for modeling the impact of emerging memory technologies by simulating read/write latencies at different levels of the memory hierarchy (L1, L2, L3, DRAM).

.. important::

   **MemSysExplorer GitHub Repository**

   Refer to the codebase for the latest update:: https://github.com/duca181/MemSysExplorer/tree/apps_dev/apps/profilers/sniper

   To learn more about license terms and third-party attribution, refer to the :doc:`../licensing` page.

Workflow Overview
-----------------

The Sniper integration in MemSysExplorer supports two actions:

1. **Profiling (`profiling`)** – Runs the Sniper simulation using the provided configuration file and application binary.
2. **Metric Extraction (`extract_metrics`)** – Processes the Sniper output to extract memory access statistics from the simulation.

When using the `both` action, profiling and metric extraction are executed in sequence.

Required Arguments
------------------

The following arguments are required for each mode:

.. code-block:: python

   @classmethod
   def required_profiling_args(cls):
       return ["config", "executable"]

   @classmethod
   def required_extract_args(cls, action):
       if action == "extract_metrics":
           return ["results_dir", "level"]
       else:
           return []

- `--config` – Path to the Sniper configuration file
- `--executable` – Binary to run during simulation
- `--results_dir` – Directory where Sniper output is stored
- `--level` – Memory level to analyze (`l1`, `l2`, `l3`, or `dram`)

Example Usage
-------------

- **Run simulation and collect stats:**

  .. code-block:: bash

     python3 main.py --profiler sniper --action both \
         --config config/skylake.cfg \
         --level l3 \
         --results_dir ./output_path \
         --executable ./your_app

- **Only extract metrics from prior run:**

  .. code-block:: bash

     python3 main.py --profiler sniper --action extract_metrics \
         --results_dir ./sim_output \
         --level dram

Customizing Memory Modeling
---------------------------

Sniper allows you to adjust the memory latency at each cache level to simulate the behavior of different memory technologies (e.g., DRAM, NVM, SRAM).

To model a specific memory technology, modify the appropriate section of your Sniper configuration file (e.g., `config/skylake.cfg`) by adding latency settings to the corresponding memory level:

.. code-block:: ini

   [perf_model/l3_cache]
   rw_enabled = true
   read_access_time = 100
   write_access_time = 50000

You may also apply the same structure to:

- `[perf_model/l1_cache]`
- `[perf_model/l2_cache]`
- `[perf_model/dram]`

This allows you to evaluate how latency-sensitive workloads perform under different memory configurations.

.. note::

   **Sniper is currently the only profiler in the MemSysExplorer ecosystem** that supports detailed memory modeling through configurable latency values. This makes it uniquely suited for architectural experiments involving emerging memory technologies. Although tools like **DynamoRIO** can be extended with attached cache models, and full-system simulators such as **gem5** or **GPGPU-Sim** offer similar capabilities, those integrations are still under development or external to MemSysExplorer.

**Example Config**

MemSysExplorer provides an example configuration file at:

.. code-block:: text

   config/skylake.cfg

This file can be used as a starting point and modified to reflect custom memory hierarchies and latency values.

Sample Output
-------------

After simulation, memory access statistics are extracted from Sniper’s output using a helper script (`snipermem.py`). The resulting metrics are saved in a CSV file:

.. code-block:: text

   memsysstats.out

This file contains read/write counts, latency breakdowns, and memory-level statistics (e.g., L1, L2, L3, DRAM).

.. note::

   Ensure that memory statistics collection is enabled in the Sniper configuration file. If the relevant settings are not enabled, Sniper will not generate usable memory data, and the metrics will be omitted from the final output.

In addition to the CSV file, the full set of outputs from the Sniper simulator is also produced. For more details on these files and additional configuration options, refer to the official documentation:

https://snipersim.org/w/The_Sniper_Multi-Core_Simulator


Troubleshooting
---------------

- **Missing Sniper binary:**
  Make sure `run-sniper` is located in `profilers/snipersim/` or update the path in the script.

- **Missing stats script:**
  Ensure `snipermem.py` exists in `snipersim/tools/`.

- **Invalid config section:**
  Sniper requires correctly formatted `[perf_model/*]` blocks. Refer to the official [Sniper documentation](https://snipersim.org) for details.

