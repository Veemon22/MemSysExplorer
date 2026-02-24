"""Public API for trace-analysis tooling."""

from .address_mapping import (
    MemoryConfig,
    AddressMapper,
    RefreshTracker,
    get_default_config,
    load_trace,
    run_simulation,
    estimate_nominal_retention_us,
)
from .dram_physics import (
    load_dram_params,
    find_refresh_time_for_fault_rate,
)

__all__ = [
    "MemoryConfig",
    "AddressMapper",
    "RefreshTracker",
    "get_default_config",
    "load_trace",
    "run_simulation",
    "estimate_nominal_retention_us",
    "load_dram_params",
    "find_refresh_time_for_fault_rate",
]
