"""Shared DRAM333T physics helpers for trace-analysis tools."""

from __future__ import annotations

import math
import os
import pickle
import warnings
from typing import Tuple

import numpy as np
import scipy.stats as ss
from scipy.optimize import brentq

from msxFI import fi_config


DistArgs = Tuple[dict, float, int]
K_B = 1.380649e-23
Q_E = 1.60217663e-19
DEFAULT_WWL_SWING = 1.4


def load_dram_params(mem_model: str = "dram333t") -> DistArgs:
    """Load DRAM parameter tuple: (tech_node_data, temperature, selected_size)."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    mem_data_path = os.path.join(repo_root, "mem_data")
    dram_params_path = os.path.join(mem_data_path, fi_config.mem_dict[mem_model])

    with open(dram_params_path, "rb") as f:
        dram_params_data = pickle.load(f)

    available_sizes = sorted(dram_params_data.keys())
    selected_size = None
    for size in reversed(available_sizes):
        if size <= fi_config.feature_size:
            selected_size = size
            break
    if selected_size is None:
        selected_size = available_sizes[0]

    tech_node_data = dram_params_data[selected_size]
    return (tech_node_data, fi_config.temperature, selected_size)


def fault_rate_gen(
    dist_args: DistArgs,
    refresh_time: float,
    vth_sigma: float = 0.05,
    custom_wwl_swing: float | None = None,
    calibration_scale: float = 1.0,
) -> float:
    """DRAM cell fault probability for one refresh interval."""
    if refresh_time is None:
        raise ValueError("refresh_time is required for DRAM models")

    tech_node_data, temperature, _ = dist_args
    cap_F = tech_node_data["CellCap"]
    available_temps = sorted(tech_node_data["Ioff"].keys())
    temp_diffs = [abs(temp - temperature) for temp in available_temps]
    selected_temp = available_temps[temp_diffs.index(min(temp_diffs))]

    median_Ioff = tech_node_data["Ioff"][selected_temp]
    if custom_wwl_swing is not None:
        ss_v_per_dec = fi_config.SS * 1e-3
        delta_v = custom_wwl_swing - tech_node_data["vdd"]
        median_Ioff *= 10 ** (-delta_v / ss_v_per_dec)

    median_Ioff *= calibration_scale

    Vt = (K_B * selected_temp) / Q_E
    n_factor = fi_config.SS * 1e-3 / (Vt * math.log(10))
    sigma_ln_Ioff = vth_sigma / (n_factor * Vt)
    ln_mu = np.log(median_Ioff)
    I_critical = (cap_F * tech_node_data["vdd"] / 2) / refresh_time
    z = (np.log(I_critical) - ln_mu) / sigma_ln_Ioff
    cdf = 1.0 - ss.norm.cdf(z)
    return max(0.0, cdf)


def retention_lognormal_params(
    dist_args: DistArgs,
    vth_sigma: float = 0.05,
    custom_wwl_swing: float | None = None,
    calibration_scale: float = 1.0,
) -> tuple[float, float]:
    """Return ln-domain retention parameters: ln(t_ret) ~ N(mu_ln_t, sigma_ln_t)."""
    if vth_sigma is None or vth_sigma <= 0:
        raise ValueError("vth_sigma must be positive")

    tech_node_data, temperature, _ = dist_args
    cap_F = tech_node_data["CellCap"]
    vdd = tech_node_data["vdd"]
    available_temps = sorted(tech_node_data["Ioff"].keys())
    temp_diffs = [abs(temp - temperature) for temp in available_temps]
    selected_temp = available_temps[temp_diffs.index(min(temp_diffs))]

    median_Ioff = tech_node_data["Ioff"][selected_temp]
    if custom_wwl_swing is not None:
        ss_v_per_dec = fi_config.SS * 1e-3
        delta_v = custom_wwl_swing - vdd
        median_Ioff *= 10 ** (-delta_v / ss_v_per_dec)

    median_Ioff *= calibration_scale

    Vt = (K_B * selected_temp) / Q_E
    n_factor = fi_config.SS * 1e-3 / (Vt * math.log(10))
    sigma_ln_Ioff = vth_sigma / (n_factor * Vt)

    mu_ln_t = math.log(cap_F * vdd / 2.0) - math.log(median_Ioff)
    sigma_ln_t = sigma_ln_Ioff
    return mu_ln_t, sigma_ln_t


def find_refresh_time_for_fault_rate(
    target_fault_rate: float,
    dist_args: DistArgs,
    vth_sigma: float = 0.05,
    custom_wwl_swing: float | None = None,
    calibration_scale: float = 1.0,
    min_refresh: float = 1e-7,
    max_refresh: float = 100.0,
    on_error: str = "raise",
) -> float:
    """Solve refresh time for a target DRAM cell fault probability."""

    def fault_rate_at_refresh_time(refresh_time: float) -> float:
        return (
            fault_rate_gen(
                dist_args,
                refresh_time=refresh_time,
                vth_sigma=vth_sigma,
                custom_wwl_swing=custom_wwl_swing,
                calibration_scale=calibration_scale,
            )
            - target_fault_rate
        )

    try:
        f_min = fault_rate_at_refresh_time(min_refresh)
        f_max = fault_rate_at_refresh_time(max_refresh)

        if f_min * f_max > 0:
            if abs(f_min) < abs(f_max):
                return min_refresh if f_min > 0 else max_refresh
            return max_refresh if f_max < 0 else min_refresh

        return brentq(fault_rate_at_refresh_time, min_refresh, max_refresh, xtol=1e-12)
    except Exception as exc:
        msg = (
            "refresh-time solve failed "
            f"(target={target_fault_rate:.3e}, vth_sigma={vth_sigma:.3e}, "
            f"custom_wwl_swing={custom_wwl_swing}, bounds=[{min_refresh:.3e}, {max_refresh:.3e}])"
        )
        if on_error == "nan":
            warnings.warn(f"{msg}: {exc}", RuntimeWarning, stacklevel=2)
            return np.nan
        raise RuntimeError(msg) from exc
