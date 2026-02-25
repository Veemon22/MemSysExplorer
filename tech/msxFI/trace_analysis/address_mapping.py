#!/usr/bin/env python3
"""eDRAM trace simulation with row-level refresh coupling."""

from typing import Tuple, Dict, Optional, List, Callable
from dataclasses import dataclass
from functools import lru_cache
from statistics import NormalDist
import math
import csv
import os
import sys

_MSXFI_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(_MSXFI_ROOT))
from msxFI import fi_config
from msxFI.fi_utils import (
    cdf_tail_for_sigma_multiple,
    compute_dram_calibration_scale,
    get_dram_type_config,
    spread_to_sigma,
)
try:
    from .dram_physics import (
        load_dram_params,
        find_refresh_time_for_fault_rate,
        retention_lognormal_params,
    )
except ImportError:
    from dram_physics import (
        load_dram_params,
        find_refresh_time_for_fault_rate,
        retention_lognormal_params,
    )


@dataclass
class MemoryConfig:
    """Memory organization parameters."""
    bank_rows: int
    bank_cols: int
    mats_per_bank: int
    subarrays_per_mat: int
    subarray_rows: int
    subarray_cols: int
    block_size_bytes: int
    cells_per_block: Optional[int] = None
    banks_per_refresh_group: int = 2
    mats_per_bank_in_refresh_group: Optional[int] = None

    def __post_init__(self):
        if self.cells_per_block is None:
            self.cells_per_block = self.block_size_bytes * 8
        if self.mats_per_bank_in_refresh_group is None:
            self.mats_per_bank_in_refresh_group = self.mats_per_bank

        self.row_size_bytes = self.subarray_cols // 8
        self.cache_lines_per_row = self.row_size_bytes // self.block_size_bytes

        if self.row_size_bytes < self.block_size_bytes:
            raise ValueError(
                f"Row size ({self.row_size_bytes}B) < block size ({self.block_size_bytes}B)")

        for name, value in [
            ('bank_rows', self.bank_rows), ('bank_cols', self.bank_cols),
            ('mats_per_bank', self.mats_per_bank),
            ('subarrays_per_mat', self.subarrays_per_mat),
            ('subarray_rows', self.subarray_rows),
            ('subarray_cols', self.subarray_cols),
            ('block_size_bytes', self.block_size_bytes),
        ]:
            if value <= 0 or not self._is_power_of_2(value):
                raise ValueError(f"{name} must be positive power of 2, got {value}")

        if not (0 < self.banks_per_refresh_group and
                self._is_power_of_2(self.banks_per_refresh_group)):
            raise ValueError(f"banks_per_refresh_group invalid: {self.banks_per_refresh_group}")

        if not (0 < self.mats_per_bank_in_refresh_group <= self.mats_per_bank and
                self._is_power_of_2(self.mats_per_bank_in_refresh_group)):
            raise ValueError(f"mats_per_bank_in_refresh_group invalid")

    @staticmethod
    def _is_power_of_2(n: int) -> bool:
        return n > 0 and (n & (n - 1)) == 0

    def get_total_capacity_bytes(self) -> int:
        total_cells = (self.bank_rows * self.bank_cols * self.mats_per_bank *
                       self.subarrays_per_mat * self.subarray_rows * self.subarray_cols)
        return total_cells // 8

    def get_total_subarrays(self) -> int:
        return self.bank_rows * self.bank_cols * self.mats_per_bank * self.subarrays_per_mat

    def get_total_banks(self) -> int:
        return self.bank_rows * self.bank_cols


class AddressMapper:
    """
    Physical address decoder for hierarchical memory.
    
    Bit layout (LSB to MSB):
    [block_offset | col | row | subarray_idx | mat_idx | bank_col | bank_row]
    """

    def __init__(self, config: MemoryConfig):
        self.config = config
        self._init_bit_fields()

    def _init_bit_fields(self):
        c = self.config
        self.block_offset_bits = int(math.log2(c.block_size_bytes))
        self.subarray_col_bits = int(math.log2(c.cache_lines_per_row)) if c.cache_lines_per_row > 1 else 0
        self.subarray_row_bits = int(math.log2(c.subarray_rows))
        self.subarray_idx_bits = int(math.log2(c.subarrays_per_mat)) if c.subarrays_per_mat > 1 else 0
        self.mat_bits = int(math.log2(c.mats_per_bank)) if c.mats_per_bank > 1 else 0
        self.bank_col_bits = int(math.log2(c.bank_cols))
        self.bank_row_bits = int(math.log2(c.bank_rows))

        self.block_offset_shift = 0
        self.subarray_col_shift = self.block_offset_bits
        self.subarray_row_shift = self.subarray_col_shift + self.subarray_col_bits
        self.subarray_idx_shift = self.subarray_row_shift + self.subarray_row_bits
        self.mat_shift = self.subarray_idx_shift + self.subarray_idx_bits
        self.bank_col_shift = self.mat_shift + self.mat_bits
        self.bank_row_shift = self.bank_col_shift + self.bank_col_bits
        self.total_address_bits = self.bank_row_shift + self.bank_row_bits

        self.block_offset_mask = (1 << self.block_offset_bits) - 1
        self.subarray_col_mask = (1 << self.subarray_col_bits) - 1
        self.subarray_row_mask = (1 << self.subarray_row_bits) - 1
        self.subarray_idx_mask = (1 << self.subarray_idx_bits) - 1
        self.mat_mask = (1 << self.mat_bits) - 1
        self.bank_col_mask = (1 << self.bank_col_bits) - 1
        self.bank_row_mask = (1 << self.bank_row_bits) - 1

    def decode_address(self, address: int) -> Dict:
        components = {
            'address': hex(address),
            'block_offset': (address >> self.block_offset_shift) & self.block_offset_mask,
            'subarray_col': (address >> self.subarray_col_shift) & self.subarray_col_mask,
            'subarray_row': (address >> self.subarray_row_shift) & self.subarray_row_mask,
            'subarray_idx': (address >> self.subarray_idx_shift) & self.subarray_idx_mask,
            'mat_idx': (address >> self.mat_shift) & self.mat_mask,
            'bank_col': (address >> self.bank_col_shift) & self.bank_col_mask,
            'bank_row': (address >> self.bank_row_shift) & self.bank_row_mask,
        }
        gid, sid = self.get_ids(address)
        components['activation_group_id'] = gid
        components['subarray_id'] = sid
        return components

    def get_ids(self, address: int) -> Tuple[Tuple[int, int, int, int], int]:
        bank_col = (address >> self.bank_col_shift) & self.bank_col_mask
        bank_row = (address >> self.bank_row_shift) & self.bank_row_mask
        mat_idx = (address >> self.mat_shift) & self.mat_mask
        subarray_idx = (address >> self.subarray_idx_shift) & self.subarray_idx_mask
        subarray_row = (address >> self.subarray_row_shift) & self.subarray_row_mask

        c = self.config
        bank_col_group = bank_col // c.banks_per_refresh_group
        mat_group = mat_idx // c.mats_per_bank_in_refresh_group
        activation_group_id = (bank_row, bank_col_group, mat_group, subarray_row)

        subarray_id = (bank_row * c.bank_cols * c.mats_per_bank * c.subarrays_per_mat +
                       bank_col * c.mats_per_bank * c.subarrays_per_mat +
                       mat_idx * c.subarrays_per_mat + subarray_idx)

        return activation_group_id, subarray_id

    def get_coactivated_subarrays(self, address: int) -> List[Tuple[int, int]]:
        """Return (subarray_id, row_id) pairs sharing the same wordline."""
        comp = self.decode_address(address)
        c = self.config

        bank_row = comp['bank_row']
        bank_col = comp['bank_col']
        mat_idx = comp['mat_idx']
        row_id = comp['subarray_row']

        bc_start = (bank_col // c.banks_per_refresh_group) * c.banks_per_refresh_group
        mat_start = (mat_idx // c.mats_per_bank_in_refresh_group) * c.mats_per_bank_in_refresh_group

        result = []
        for bc in range(bc_start, min(bc_start + c.banks_per_refresh_group, c.bank_cols)):
            for m in range(mat_start, min(mat_start + c.mats_per_bank_in_refresh_group, c.mats_per_bank)):
                for sa in range(c.subarrays_per_mat):
                    sid = (bank_row * c.bank_cols * c.mats_per_bank * c.subarrays_per_mat +
                           bc * c.mats_per_bank * c.subarrays_per_mat +
                           m * c.subarrays_per_mat + sa)
                    result.append((sid, row_id))
        return result

    def print_config(self):
        c = self.config
        print(f"Memory Organization:")
        print(f"  Banks: {c.bank_rows} x {c.bank_cols}")
        print(f"  Mats/Bank: {c.mats_per_bank}")
        print(f"  Subarrays/Mat: {c.subarrays_per_mat}")
        print(f"  Subarray: {c.subarray_rows} rows x {c.subarray_cols} bits")
        print(f"  Block size: {c.block_size_bytes} bytes")
        print(f"\nRow Configuration:")
        print(f"  Row width: {c.row_size_bytes} bytes")
        print(f"  Cache lines/row: {c.cache_lines_per_row}")
        print(f"\nRefresh Groups:")
        print(f"  Banks/group: {c.banks_per_refresh_group}")
        print(f"  Mats/bank: {c.mats_per_bank_in_refresh_group}")
        coact = c.banks_per_refresh_group * c.mats_per_bank_in_refresh_group * c.subarrays_per_mat
        print(f"  Co-activated subarrays: {coact}")
        print(f"\nAddress bits: {self.total_address_bits} total")


class RefreshTracker:
    """
    Tracks row refresh state for retention fault simulation.

    Refresh policy:
      - "write": only writes refresh rows (default)
      - "readwrite": reads also refresh rows (e.g., 1T DRAM)

    Rows sharing wordline are refreshed together.
    """

    def __init__(self, mapper: AddressMapper,
                 refresh_policy: str = "write",
                 refresh_interval_us: float = None,
                 retention_time_us: float = None,
                 retention_cdf_fn: Callable[[float], float] = None):
        self.mapper = mapper
        self.refresh_policy = refresh_policy
        self.refresh_interval_us = refresh_interval_us
        self.refresh_interval_s = refresh_interval_us * 1e-6 if refresh_interval_us is not None else None
        self.retention_time_us = retention_time_us
        self.retention_time_s = retention_time_us * 1e-6 if retention_time_us is not None else None
        self.retention_cdf_fn = retention_cdf_fn
        if self.refresh_interval_s is not None and self.refresh_interval_s <= 0:
            raise ValueError("refresh_interval_us must be positive when provided")
        if self.retention_time_s is not None and self.retention_time_s <= 0 and self.retention_cdf_fn is None:
            raise ValueError("retention_time_us must be positive when provided")
        if refresh_policy not in {"write", "readwrite"}:
            raise ValueError(f"Unsupported refresh_policy '{refresh_policy}'")
        self.refresh_on_read = refresh_policy == "readwrite"
        self._last_refresh: Dict[Tuple[int, int], float] = {}
        self._last_write_refresh: Dict[Tuple[int, int], float] = {}
        self._max_gap_s: Dict[Tuple[int, int], float] = {}
        self._expected_fault_events = 0.0
        self._bit_cells_per_tracked_unit = self.mapper.config.subarray_cols
        self.stats = {
            'total_writes': 0,
            'total_reads': 0,
            'write_refreshes': 0,
            'read_refreshes': 0,
        }

    def _count_explicit_refreshes(self, write_interval_s: float) -> int:
        """Count explicit refreshes inserted strictly between two write timestamps."""
        if self.refresh_interval_s is None:
            return 0
        interval_s = max(write_interval_s, 0.0)
        if interval_s <= 0.0:
            return 0
        # For ratio = interval/period, count refresh points m*period where 0 < m*period < interval.
        ratio = interval_s / self.refresh_interval_s
        return max(0, int(math.floor(math.nextafter(ratio, -math.inf))))

    def _max_unrefreshed_gap_from_write_interval(self, write_interval_s: float) -> float:
        interval_s = max(write_interval_s, 0.0)
        explicit_count = self._count_explicit_refreshes(interval_s)
        if explicit_count > 0:
            return self.refresh_interval_s
        return interval_s

    def _fault_probability_for_gap(self, max_gap_s: float) -> float:
        if self.retention_cdf_fn is not None:
            p = self.retention_cdf_fn(max_gap_s)
            return min(max(p, 0.0), 1.0)
        if self.retention_time_s is None:
            return 0.0
        return 1.0 if max_gap_s > self.retention_time_s else 0.0

    def _refresh_rows(self, address: int, timestamp: float, source: str) -> int:
        """Refresh rows sharing the wordline. Returns number of rows refreshed."""
        coactivated = self.mapper.get_coactivated_subarrays(address)
        for sid, row in coactivated:
            key = (sid, row)
            self._last_refresh[key] = timestamp
            if source == 'write':
                if key in self._last_write_refresh:
                    write_interval_s = timestamp - self._last_write_refresh[key]
                    max_gap_s = self._max_unrefreshed_gap_from_write_interval(write_interval_s)
                    self._max_gap_s[key] = max(self._max_gap_s.get(key, 0.0), max_gap_s)
                    p_fault = self._fault_probability_for_gap(max_gap_s)
                    self._expected_fault_events += self._bit_cells_per_tracked_unit * p_fault
                elif key not in self._max_gap_s:
                    self._max_gap_s[key] = 0.0
                self._last_write_refresh[key] = timestamp
        if source == 'write':
            self.stats['total_writes'] += 1
            self.stats['write_refreshes'] += len(coactivated)
        elif source == 'read':
            self.stats['read_refreshes'] += len(coactivated)
        else:
            raise ValueError(f"Unknown refresh source '{source}'")
        return len(coactivated)

    def write(self, address: int, timestamp: float) -> int:
        """Process write operation. Returns number of rows refreshed."""
        return self._refresh_rows(address, timestamp, source='write')

    def simulate(self, addresses: List[int], timestamps_us: List[float],
                 operations: List[str]) -> Dict:
        """Run fault simulation on an access trace."""
        if not (len(addresses) == len(timestamps_us) == len(operations)):
            raise ValueError("Input lists must have equal length")

        for addr, ts_us, op in zip(addresses, timestamps_us, operations):
            ts_s = ts_us * 1e-6
            if op == 'r':
                self.stats['total_reads'] += 1
                if self.refresh_on_read:
                    self._refresh_rows(addr, ts_s, source='read')
            else:
                self.write(addr, ts_s)

        if timestamps_us and self._last_write_refresh:
            trace_end_s = max(timestamps_us) * 1e-6
            for key, last_write_s in self._last_write_refresh.items():
                tail_interval_s = trace_end_s - last_write_s
                max_gap_s = self._max_unrefreshed_gap_from_write_interval(tail_interval_s)
                self._max_gap_s[key] = max(self._max_gap_s.get(key, 0.0), max_gap_s)
                p_fault = self._fault_probability_for_gap(max_gap_s)
                self._expected_fault_events += self._bit_cells_per_tracked_unit * p_fault

        total_reads = sum(1 for op in operations if op == 'r')
        total_tracked_units = len(self._last_write_refresh)
        total_tracked_cells = total_tracked_units * self._bit_cells_per_tracked_unit
        expected_faulty_cells = 0.0
        for key in self._last_write_refresh:
            p_fault = self._fault_probability_for_gap(self._max_gap_s.get(key, 0.0))
            expected_faulty_cells += self._bit_cells_per_tracked_unit * p_fault
        faulty_cells = int(round(expected_faulty_cells))
        fault_events = int(round(self._expected_fault_events))
        cell_fault_rate = (
            expected_faulty_cells / total_tracked_cells if total_tracked_cells > 0 else 0.0
        )
        return {
            'total_accesses': len(addresses),
            'total_writes': sum(1 for op in operations if op == 'w'),
            'total_reads': total_reads,
            'faulty_cells': faulty_cells,
            'fault_events': fault_events,
            'total_tracked_cells': total_tracked_cells,
            'cell_fault_rate': cell_fault_rate,
            'stats': self.stats.copy(),
        }

    def reset(self):
        self._last_refresh.clear()
        self._last_write_refresh.clear()
        self._max_gap_s.clear()
        self._expected_fault_events = 0.0
        self.stats = {
            'total_writes': 0,
            'total_reads': 0,
            'write_refreshes': 0,
            'read_refreshes': 0,
        }

def get_default_config() -> MemoryConfig:
    return MemoryConfig(
        bank_rows=32, bank_cols=64, mats_per_bank=4, subarrays_per_mat=1,
        subarray_rows=16, subarray_cols=1024, block_size_bytes=64,
        banks_per_refresh_group=2, mats_per_bank_in_refresh_group=4)


def load_trace(path: str) -> Tuple[List[int], List[float], List[str]]:
    """Load CSV trace and convert timestamps from ns to us."""
    addresses, timestamps_us, operations = [], [], []
    with open(path) as f:
        for row_idx, row in enumerate(csv.DictReader(f), start=2):
            ts_ns = float(row['timestamp'])
            timestamps_us.append(ts_ns / 1000.0)
            addr = row['address'].strip()
            addresses.append(int(addr, 16) if addr.startswith('0x') else int(addr))
            op_raw = row.get('operation', '').strip()
            try:
                op_val = int(float(op_raw))
            except ValueError as exc:
                raise ValueError(
                    f"Invalid operation value '{op_raw}' at CSV line {row_idx}. "
                    "Expected 1 for write or 0 for read."
                ) from exc
            if op_val == 1:
                operations.append('w')
            elif op_val == 0:
                operations.append('r')
            else:
                raise ValueError(
                    f"Invalid operation value '{op_raw}' at CSV line {row_idx}. "
                    "Expected 1 for write or 0 for read."
                )
    return addresses, timestamps_us, operations


@lru_cache(maxsize=128)
def estimate_nominal_retention_us(mem_model: str, wwl_swing: float) -> float:
    """Estimate nominal retention at a given WWL_Swing using the same model as find_refresh_times.py."""
    type_cfg = get_dram_type_config(mem_model)
    sigma_multiple = type_cfg["sigma_multiple"]
    nominal_refresh_s = type_cfg["refresh_time"] * 1e-6
    vth_spread = 0.05
    nominal_vth_sigma = spread_to_sigma(vth_spread, sigma_multiple)
    nominal_fault_rate = cdf_tail_for_sigma_multiple(sigma_multiple)

    dist_args = load_dram_params(mem_model)
    tech_node_data = dist_args[0]
    nominal_vdd = tech_node_data["vdd"]

    calibration_scale = compute_dram_calibration_scale(
        dist_args,
        nominal_vth_sigma,
        nominal_fault_rate,
        nominal_refresh_s,
        nominal_vdd,
    )

    refresh_s = find_refresh_time_for_fault_rate(
        nominal_fault_rate,
        dist_args,
        vth_sigma=nominal_vth_sigma,
        custom_wwl_swing=wwl_swing,
        calibration_scale=calibration_scale,
        on_error="raise",
    )
    return refresh_s * 1e6


def build_retention_cdf_fn(
    mem_model: str,
    wwl_swing: float,
    vth_sigma_mv: float,
    retention_time_us: float,
) -> Callable[[float], float]:
    """
    Build per-bit retention CDF from the DRAM physics model.

    Returned callable maps a refresh gap (seconds) to fault probability:
    P(retention <= gap), which is applied at bit-cell granularity.
    """
    dist_args = load_dram_params(mem_model)
    tech_node_data = dist_args[0]
    type_cfg = get_dram_type_config(mem_model)
    sigma_multiple = type_cfg["sigma_multiple"]
    nominal_refresh_s = type_cfg["refresh_time"] * 1e-6
    nominal_fault_rate = cdf_tail_for_sigma_multiple(sigma_multiple)
    vth_spread = vth_sigma_mv / 1000.0
    vth_sigma = spread_to_sigma(vth_spread, sigma_multiple)
    nominal_vdd = tech_node_data["vdd"]

    calibration_scale = compute_dram_calibration_scale(
        dist_args,
        vth_sigma,
        nominal_fault_rate,
        nominal_refresh_s,
        nominal_vdd,
    )

    mu_ln_t, sigma_ln_t = retention_lognormal_params(
        dist_args,
        vth_sigma=vth_sigma,
        custom_wwl_swing=wwl_swing,
        calibration_scale=calibration_scale,
    )

    normal = NormalDist()
    target_reference_s = retention_time_us * 1e-6
    reference_z = normal.inv_cdf(nominal_fault_rate)
    current_reference_s = math.exp(mu_ln_t + sigma_ln_t * reference_z)
    if current_reference_s > 0 and target_reference_s > 0:
        mu_ln_t += math.log(target_reference_s / current_reference_s)

    def retention_cdf(gap_s: float) -> float:
        if gap_s <= 0:
            return 0.0
        z = (math.log(gap_s) - mu_ln_t) / sigma_ln_t
        return min(max(normal.cdf(z), 0.0), 1.0)

    return retention_cdf


def run_simulation(trace_path: str, config: MemoryConfig = None,
                   verbose: bool = False, refresh_policy: str = "write",
                   refresh_interval_us: float = None,
                   mem_model: str = 'dram333t',
                   wwl_swing: float = None, vth_sigma_mv: float = 50.0,
                   retention_time_us: float = None,
                   retention_is_default: bool = True) -> Dict:
    if config is None:
        config = get_default_config()
    if retention_time_us is None:
        if mem_model == "dram333t" and wwl_swing is not None:
            retention_time_us = estimate_nominal_retention_us(mem_model, wwl_swing)
        else:
            retention_time_us = fi_config.default_retention_us.get(mem_model, 501.0)
    retention_cdf_fn = build_retention_cdf_fn(
        mem_model=mem_model,
        wwl_swing=wwl_swing,
        vth_sigma_mv=vth_sigma_mv,
        retention_time_us=retention_time_us,
    )
    mapper = AddressMapper(config)
    tracker = RefreshTracker(mapper, refresh_policy=refresh_policy,
                             refresh_interval_us=refresh_interval_us,
                             retention_time_us=retention_time_us,
                             retention_cdf_fn=retention_cdf_fn)

    addresses, timestamps, operations = load_trace(trace_path)

    if verbose:
        print(f"Loaded trace: {len(addresses)} accesses")
        print(f"  Time range: {timestamps[0]:.1f}us - {timestamps[-1]:.1f}us")
        print(f"  Writes: {sum(1 for op in operations if op == 'w')}")
        print(f"  Reads: {sum(1 for op in operations if op == 'r')}")

    result = tracker.simulate(addresses, timestamps, operations)
    result['retention_time_us'] = retention_time_us
    result['retention_is_default'] = retention_is_default
    result['refresh_interval_us'] = refresh_interval_us
    result['config'] = config
    return result


if __name__ == '__main__':
    try:
        from .address_mapping_cli import run_cli
    except ImportError:
        from address_mapping_cli import run_cli
    sys.exit(run_cli())
