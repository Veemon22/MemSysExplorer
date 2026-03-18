Perf Documentation
==============================

Perfs leverage **Hardware Performance Counters (HPC)** to collect low-level hardware metrics from CPUs. 
These profiler provide valuable insights into memory access patterns, kernel performance, and overall system efficiency. 

The profiling workflow in MemSysExplorer consists of two core actions, as provided by the main interface:

1. **Profiling (`profiling`)** – Captures runtime execution metrics by specifying the required executable.
2. **Metric Extraction (`extract_metrics`)** – Analyzes generated reports to extract memory and performance-related metrics.

When using the `both` action, profiling and metric extraction are performed sequentially.

.. important::

   **MemSysExplorer GitHub Repository**

   Refer to the codebase for the latest update: https://github.com/duca181/MemSysExplorer/tree/apps_dev/apps/profilers/perf

   To learn more about license terms and third-party attribution, refer to the :doc:`../licensing` page.

Supported Architectures
-----------------------

The ``--arch`` flag specifies the CPU architecture. This determines which perf events are collected:

.. list-table::
   :header-rows: 1

   * - Architecture
     - Flag
     - Notes
   * - Intel
     - ``--arch intel``
     - Default. Supports L1, L2, L3, DRAM levels
   * - AMD
     - ``--arch amd``
     - Supports L1, L2, L3, DRAM levels

Each architecture has different perf event names for the same metrics. The profiler automatically selects the correct events based on the ``--arch`` flag.

Supported Memory Levels
-----------------------

The ``--level`` flag defines the memory hierarchy level to analyze:

.. list-table::
   :header-rows: 1

   * - Level
     - Description
     - Key Metrics
   * - ``l1``
     - L1 Data Cache
     - loads, stores, load misses
   * - ``l2``
     - L2 Cache
     - load hits/misses, RFO (stores)
   * - ``l3``
     - L3/LLC Cache
     - hits, misses, loads
   * - ``dram``
     - Main Memory
     - local/remote DRAM accesses
   * - ``all``
     - All levels
     - Collects all available counters

Each level maps to a predefined set of ``perf`` events selected to best approximate that layer's behavior.

Required Arguments
------------------

To execute Perf profiling, specific arguments are required based on the chosen action. The necessary arguments are defined in the code as follows:

.. code-block:: python

    @classmethod
    def required_profiling_args(cls):
        """
        Return required arguments for the profiling method.
        """
        return ["executable", "level"]

    @classmethod
    def required_extract_args(cls, action):
        """
        Return required arguments for the extract_metrics method.
        """
        if action == "extract_metrics":
            return ["report_file"]
        else:
            return []

Optional Arguments
------------------

* ``--arch``: CPU architecture (``intel`` or ``amd``). Default: ``intel``
* ``--repeat``: Number of measurement repeats. Default: ``3``
* ``--report_file``: (For ``extract_metrics``) The path to the saved ``perf`` output log.

Example Usage
-------------

Below are examples of how to execute the profiling tool with different actions and configurations:

- **Run profiling on Intel (default):**

  .. code-block:: bash

     python main.py --profiler perf --action both --level l2 --executable ./executable

- **Run profiling on AMD:**

  .. code-block:: bash

     python main.py --profiler perf --action both --level l2 --arch amd --executable ./executable

- **Profile DRAM level on Intel:**

  .. code-block:: bash

     python main.py --profiler perf --action both --level dram --arch intel --executable ./executable

- **Profile all memory levels:**

  .. code-block:: bash

     python main.py --profiler perf --action both --level all --executable ./executable

- **Extracting metrics from an existing report:**

  .. code-block:: bash

     python main.py --profiler perf --action extract_metrics --level l2 --report_file ./perf_output.log

.. note::
   Both Intel and AMD architectures are supported via the ``--arch`` flag. Some counters may be unavailable depending on your specific CPU model.

Sample Output
-------------

This profiler generates output traces that follow the standardized format defined by the MemSysExplorer Application Interface.
     
Troubleshooting
---------------

If you encounter issues while running or extracting metrics using the Perf profiler, consider the following checks:

- **Ensure `perf` is installed and available** in your environment.

  You can verify this by running:

  .. code-block:: bash

     which perf
     perf --version

- **Check whether hardware performance counters are accessible**.

  On many Linux systems, user access to counters is restricted by default. You may need to reduce the kernel's perf event restriction level:

  .. code-block:: bash

     sudo sh -c 'echo -1 > /proc/sys/kernel/perf_event_paranoid'

  Alternatively, configure access with:

  .. code-block:: bash

     sudo sysctl -w kernel.perf_event_paranoid=-1

- **Ensure you are running on a supported architecture.**
  MemSysExplorer's ``perf`` integration supports both **Intel** and **AMD** CPUs via the ``--arch`` flag. Some counters may be missing or unsupported on ARM or virtualized environments. If you see many ``<not supported>`` events, verify you're using the correct ``--arch`` flag for your CPU.

- **Check for compatibility with your Linux kernel version and `perf` version.**

  MemSysExplorer assumes compatibility with `perf` versions is above 6.x. Run:

  .. code-block:: bash

     uname -r
     perf --version

  to check kernel and `perf` versions.

If the profiler fails silently or skips metrics, it's likely due to unsupported or inaccessible counters. Consider testing a different memory level (``--level l1``, ``l2``, ``l3``, ``dram``, or ``all``) or verifying your ``--arch`` flag matches your CPU architecture.


