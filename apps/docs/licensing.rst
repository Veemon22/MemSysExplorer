6. Licensing and Attribution
============================

This project integrates several third-party profilers to support memory and performance analysis. Each profiler is used in accordance with its respective license. The following provides attribution and licensing details for all integrated profiling tools.

5.1 Nsight Compute
------------------

Nsight Compute is a proprietary GPU profiling tool developed and distributed by NVIDIA Corporation.

- **Product Name:** NVIDIA Nsight Compute
- **License:** Proprietary
- **Usage:** Non-commercial and development use only
- **License URL:** https://developer.nvidia.com/nsight-compute-eula

You must comply with the NVIDIA End User License Agreement when using Nsight Compute.

5.2 NVBit
---------

NVBit (NVIDIA Binary Instrumentation Tool) is developed by NVIDIA for dynamic instrumentation of GPU binaries.

- **Academic Reference:**

  Oreste Villa, Mark Stephenson, David Nellans, and Stephen W. Keckler.  
  *NVBit: A Dynamic Binary Instrumentation Framework for NVIDIA GPUs.*  
  In *Proceedings of the 52nd Annual IEEE/ACM International Symposium on Microarchitecture (MICRO '52)*, 372–383.  
  DOI: https://doi.org/10.1145/3352460.3358307

- **License:** NVBit is distributed under NVIDIA's proprietary license.

5.3 DynamoRIO
-------------

DynamoRIO is a dynamic binary instrumentation framework for runtime code analysis.

- **Project URL:** https://dynamorio.org/
- **License:** BSD License
- **License URL:** https://dynamorio.org/page_license.html

DynamoRIO is free software distributed under a BSD-style license. You may use, modify, and distribute it with attribution.

5.4 Sniper Simulator
--------------------

Sniper is a high-speed architectural simulator for multicore processors.

- **Project:** Sniper Multicore Simulator
- **License:** GNU General Public License (GPL) v3
- **License URL:** https://www.gnu.org/licenses/gpl-3.0.html

- **Academic Reference:**

  Trevor E. Carlson, Wim Heirman, and Lieven Eeckhout.  
  *Sniper: Exploring the Level of Abstraction for Scalable and Accurate Parallel Multi-Core Simulation.*  
  In *Proceedings of SC'11: International Conference for High Performance Computing, Networking, Storage and Analysis*.  
  DOI: https://doi.org/10.1145/2063384.2063454

5.5 Perf
--------

`perf` is part of the Linux kernel performance monitoring subsystem.

- **License:** GNU General Public License (GPL) v2 (as part of the Linux kernel)
- **Project URL:** https://perf.wiki.kernel.org/

- **Usage:** `perf` is included with the Linux kernel and subject to its licensing terms.

5.6 Acknowledgments
-------------------

All third-party tools are the intellectual property of their respective owners. MemSysExplorer does not distribute any of these binaries directly. Users are responsible for installing and using each profiler according to its license.

5.7 Academic References
-----------------------

The design and methodology of MemSysExplorer are informed by prior research in instrumentation, memory hierarchy analysis, and event-driven simulation:

- L. Pentecost et al., *"NVMExplorer: A Framework for Cross-Stack Comparisons of Embedded Non-Volatile Memories,"* IEEE HPCA, 2022.  
- A. Hankin et al., *"Evaluation of Non-Volatile Memory Based Last Level Cache Given Modern Use Case Behavior,"* IEEE IISWC, 2019.  
- M. Lui et al., *"Towards Cross-Framework Workload Analysis via Flexible Event-Driven Interfaces,"* IEEE ISPASS, 2018.  
- N. Nethercote and J. Seward, *"Valgrind: A Framework for Heavyweight Dynamic Binary Instrumentation,"* ACM SIGPLAN Notices, 2007.

