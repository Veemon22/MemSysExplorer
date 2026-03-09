2. Metadata Collection
======================

MemSysExplorer includes built-in support for collecting **system-level metadata** to accompany memory profiling outputs. This metadata provides detailed context about the hardware and software environment in which the profiling was performed, ensuring accurate interpretation and reproducibility of results.

.. note::

   The `BaseMetadata` class assumes a **Linux-based system**. Users on other platforms may encounter incomplete or missing metadata fields unless modified.

   The `BaseMetadata` implementation can be found in the repository here:
   `BaseMetadata.py <https://github.com/duca181/MemSysExplorer/blob/apps_dev/apps/profilers/BaseMetadata.py>`_

   In the future, we will provide **community metadata profiles** collected from different systems to help users compare workload behaviors across architectures.

.. important::

   Every profiler must **enforce integration of `BaseMetadata`** or its subclass. Metadata collection is essential to ensure that workload traces are **reproducible** and properly **contextualized** based on their execution environment.

2.1 Collected Metadata Includes
-------------------------------

- **GPU Information**
  - Device name, driver version, and available GPU memory (`nvidia-smi`)

- **CPU Information**
  - Full `lscpu` dump, including architecture, core/thread counts, CPU family/model, etc.

- **Cache Hierarchy**
  - Sizes of L1 instruction/data, L2, and L3 caches from `/sys/devices/system/cpu/cpu0/cache`

- **Main Memory (DRAM)**
  - Total physical memory size in megabytes (`/proc/meminfo`)

- **Software Environment**
  - Operating system name and version
  - Installed compiler versions (e.g., GCC, Clang, AOCC)
  - BIOS and firmware information (`dmidecode`)
  - Filesystem type
  - Power policy and CPU governor

2.2 Class Structure
-------------------

The `BaseMetadata` class implements the following key methods:

- ``gpu_info()`` – Extracts GPU specifications
- ``cpu_info()`` – Parses CPU attributes from `lscpu`
- ``cache_info()`` – Returns cache sizes per level
- ``dram_info()`` – Measures DRAM size from system memory
- ``software_info()`` – Reports OS, kernel, compilers, BIOS, and policy info
- ``as_dict()`` – Converts all metadata to a single dictionary object
- ``__repr__()`` – Provides a human-readable summary string

2.3 Integration
---------------

Each profiler in MemSysExplorer (e.g., ``dynamorio``, ``perf``, ``sniper``, ``nvbit``, ``ncu``) may inherit from the ``BaseMetadata`` class or integrate its output into their reporting structures.

.. important::

   The use of ``BaseMetadata`` is **mandatory** across all profilers to ensure a **unified and reproducible profiling environment**. Reproducibility across profiling runs requires consistent capture of both hardware and software environment metadata.

To support consistent experimentation and collaboration, MemSysExplorer will include a **community-contributed database** of workload metadata and profiler outputs. This shared repository will facilitate reproducible research, cross-platform comparisons, and collaborative benchmarking across research groups.

2.4 Metadata Structure Reference
--------------------------------

The ``memsysmetadata_<profiler>.json`` file contains system and environment information captured during profiling. Below is a detailed reference for each field.

2.4.1 System Information
~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Field
     - Description
   * - ``gpu_name``
     - Name of detected GPU (e.g., "NVIDIA GeForce RTX 3080")
   * - ``driver_version``
     - GPU driver version string
   * - ``gpu_memory_MB``
     - Total GPU memory in megabytes
   * - ``dram_size_MB``
     - Total system DRAM in megabytes

2.4.2 CPU Information (cpu_info)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Field
     - Description
   * - ``Architecture``
     - CPU architecture (e.g., "x86_64", "aarch64")
   * - ``CPU op-mode(s)``
     - Supported operation modes (e.g., "32-bit, 64-bit")
   * - ``Address sizes``
     - Physical and virtual address bit widths
   * - ``Model name``
     - Full CPU model string (e.g., "Intel(R) Core(TM) i9-12900K")
   * - ``CPU(s)``
     - Total number of logical CPUs
   * - ``Thread(s) per core``
     - Number of threads per physical core
   * - ``Core(s) per socket``
     - Number of cores per CPU socket
   * - ``Socket(s)``
     - Number of CPU sockets
   * - ``CPU MHz``
     - Current CPU frequency in MHz
   * - ``CPU max MHz``
     - Maximum CPU frequency
   * - ``L1d cache``
     - L1 data cache size (from lscpu)
   * - ``L1i cache``
     - L1 instruction cache size
   * - ``L2 cache``
     - L2 cache size
   * - ``L3 cache``
     - L3 cache size

2.4.3 Cache Hierarchy (cpu_cache)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Field
     - Description
   * - ``L1d``
     - L1 data cache size in bytes (from /sys/devices)
   * - ``L1i``
     - L1 instruction cache size in bytes
   * - ``L2``
     - L2 cache size in bytes
   * - ``L3``
     - L3 cache size in bytes

2.4.4 Software Information (software_info)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Field
     - Description
   * - ``OS``
     - Operating system name and version
   * - ``Kernel``
     - Kernel version string
   * - ``gcc_version``
     - GCC compiler version
   * - ``clang_version``
     - Clang compiler version (if installed)
   * - ``FileSystem``
     - Filesystem type of the working directory
   * - ``BIOS_version``
     - BIOS/firmware version (requires sudo)
   * - ``power_policy``
     - Current CPU power policy
   * - ``cpu_governor``
     - CPU frequency governor setting

2.4.5 Profiler-Specific Fields
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Field
     - Description
   * - ``dynamorio_version``
     - DynamoRIO version (for dynamorio profiler)
   * - ``cuda_version``
     - CUDA version (for nvbit/ncu profilers)
   * - ``sniper_version``
     - Sniper version (for sniper profiler)
   * - ``perf_version``
     - Perf version (for perf profiler)

2.5 PatternConfig Structure Reference
-------------------------------------

The ``memsyspatternconfig_<workload>.json`` file contains aggregated memory statistics from the profiling run. Below is a detailed reference for each field.

2.5.1 Experiment Information
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Field
     - Description
   * - ``exp_name``
     - Experiment/profiler name (e.g., "dynamorio", "sniper")
   * - ``benchmark_name``
     - Name of the profiled workload or benchmark

2.5.2 Read/Write Statistics
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Field
     - Description
   * - ``read_freq``
     - Read frequency (operations per second or ratio)
   * - ``total_reads``
     - Total read operations count
   * - ``write_freq``
     - Write frequency (operations per second or ratio)
   * - ``total_writes``
     - Total write operations count
   * - ``read_size``
     - Average read size in bytes
   * - ``write_size``
     - Average write size in bytes

2.5.3 Detailed Counters
~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Field
     - Description
   * - ``total_writes_i``
     - Instruction write count
   * - ``total_writes_d``
     - Data write count
   * - ``total_reads_d``
     - Data read count
   * - ``total_reads_i``
     - Instruction read count

2.5.4 Memory Footprint
~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Field
     - Description
   * - ``workingset_size``
     - Working set size in bytes (unique memory addresses accessed)
   * - ``workingset_size_hll``
     - Approximate WSS using HyperLogLog (if available)

2.5.5 Units Reference 
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``unit`` dictionary specifies the measurement unit for each metric field:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Field
     - Unit
   * - ``read_freq`` / ``write_freq``
     - "ops/sec" or "ratio"
   * - ``total_reads`` / ``total_writes``
     - "count"
   * - ``read_size`` / ``write_size``
     - "bytes"
   * - ``workingset_size``
     - "bytes"

2.6 Profiler-Specific Output Differences
----------------------------------------

Different profilers capture different subsets of metrics based on their instrumentation capabilities. The table below shows which fields are populated by each profiler:

.. list-table::
   :header-rows: 1
   :widths: 20 16 16 16 16 16

   * - Field
     - DynamoRIO
     - Perf
     - Sniper
     - NVBit
     - NCU
   * - ``total_reads``
     - Yes
     - Yes
     - Yes
     - Yes
     - Yes
   * - ``total_writes``
     - Yes
     - Yes
     - Yes
     - Yes
     - Yes
   * - ``workingset_size``
     - Yes
     - No
     - Yes
     - Yes
     - No
   * - ``read_size`` / ``write_size``
     - Yes
     - No
     - No
     - Yes
     - No
   * - ``cache_hits`` (L1)
     - No
     - Yes
     - Yes
     - No
     - No
   * - ``cache_misses`` (L1)
     - No
     - Yes
     - Yes
     - No
     - No
   * - ``cache_hits`` (L2)
     - No
     - Yes
     - Yes
     - No
     - Yes
   * - ``cache_misses`` (L2)
     - No
     - Yes
     - Yes
     - No
     - Yes
   * - ``cache_hits`` (L3)
     - No
     - Partial
     - Yes
     - No
     - No
   * - ``dram_accesses``
     - No
     - No
     - Yes
     - No
     - Yes
   * - ``memory_bandwidth``
     - No
     - Yes
     - Yes
     - No
     - Yes
   * - ``kernel_metrics``
     - No
     - No
     - No
     - No
     - Yes

**Legend:**

- **Yes**: Field is fully supported and populated
- **No**: Field is not available with this profiler
- **Partial**: Field is available on some hardware/kernel versions

