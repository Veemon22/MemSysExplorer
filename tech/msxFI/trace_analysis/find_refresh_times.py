#!/usr/bin/env python3
"""Generate WWL_Swing-to-refresh-interval tables for DRAM333T."""

import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

script_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.abspath(os.path.join(script_dir, ".."))
sys.path.insert(0, os.path.dirname(repo_root))

from msxFI.fi_utils import (
    cdf_tail_for_sigma_multiple,
    compute_dram_calibration_scale,
    spread_to_sigma,
)

try:
    from .dram_physics import load_dram_params, find_refresh_time_for_fault_rate
except ImportError:
    from dram_physics import load_dram_params, find_refresh_time_for_fault_rate


def parse_args():
    parser = argparse.ArgumentParser(
        description="Calculate required refresh intervals for different WWL_Swing voltages and target cell fault rates."
    )
    parser.add_argument('--mem-model', type=str, default='dram333t',
                        choices=['dram333t'],
                        help="DRAM memory model to use (only dram333t is supported).")
    parser.add_argument('--wwl_swing-start', type=float, default=1.2,
                        help="Start of the WWL_Swing sweep range in volts (default: 1.2).")
    parser.add_argument('--wwl_swing-stop', type=float, default=2.0,
                        help="End of the WWL_Swing sweep range in volts (default: 2.0).")
    parser.add_argument('--wwl_swing-step', type=float, default=0.05,
                        help="Step size for the WWL_Swing sweep in volts (default: 0.05).")
    return parser.parse_args()


def main():
    args = parse_args()

    dist_args = load_dram_params(args.mem_model)
    tech_node_data = dist_args[0]

    sigma_multiple = 3.5
    vth_spread = 0.05
    nominal_refresh_time = 501e-6
    nominal_wwl_swing = tech_node_data.get("wwl_swing", 1.4)
    nominal_vdd = tech_node_data["vdd"]

    wwl_swing_values = np.arange(args.wwl_swing_start, args.wwl_swing_stop + args.wwl_swing_step / 2, args.wwl_swing_step)

    nominal_vth_sigma = spread_to_sigma(vth_spread, sigma_multiple)
    nominal_fault_rate = cdf_tail_for_sigma_multiple(sigma_multiple)

    fault_rate_targets = [
        {'label': 'Nominal', 'key': 'RT_nominal', 'value': nominal_fault_rate},
        {'label': 'FR=1e-4', 'key': 'RT_1e-04', 'value': 1e-4},
        {'label': 'FR=1e-5', 'key': 'RT_1e-05', 'value': 1e-5},
        {'label': 'FR=1e-6', 'key': 'RT_1e-06', 'value': 1e-6},
        {'label': 'FR=1e-7', 'key': 'RT_1e-07', 'value': 1e-7},
    ]

    calibration_scale = compute_dram_calibration_scale(
        dist_args,
        nominal_vth_sigma,
        nominal_fault_rate,
        nominal_refresh_time,
        nominal_vdd,
    )

    results = []

    print(f"Finding refresh times for {args.mem_model.upper()} model...")
    print(f"Configured sigma multiple: +/-{sigma_multiple} sigma")
    print(f"Vth spread (+/-): {vth_spread*1e3:.2f} mV -> sigma: {nominal_vth_sigma*1e3:.2f} mV")
    print(
        f"Nominal reference: wwl_swing={nominal_wwl_swing:.2f} V, "
        f"VDD={nominal_vdd:.2f} V, refresh={nominal_refresh_time*1e6:.1f} us"
    )
    print("-" * 100)
    column_width = 20
    header = " | ".join([f"{target['label']:{column_width}}" for target in fault_rate_targets])
    print(f"{'WWL_Swing (V)':>8} | {header}")
    print("-" * 100)

    for wwl_swing in wwl_swing_values:
        refresh_times = []
        row_str = f"{wwl_swing:8.2f} |"

        for target in fault_rate_targets:
            refresh_time = find_refresh_time_for_fault_rate(
                target['value'],
                dist_args,
                vth_sigma=nominal_vth_sigma,
                custom_wwl_swing=wwl_swing,
                calibration_scale=calibration_scale,
                on_error="nan",
            )
            refresh_times.append((target['key'], refresh_time))

            if np.isnan(refresh_time):
                formatted = "N/A"
            elif refresh_time < 1e-3:
                formatted = f"{refresh_time*1e6:10.2f}us"
            elif refresh_time < 1:
                formatted = f"{refresh_time*1e3:10.2f}ms"
            else:
                formatted = f"{refresh_time:11.3f}s"

            row_str += f" {formatted:>{column_width}} |"

        print(row_str)

        row_entry = {'wwl_swing': wwl_swing}
        for key, value in refresh_times:
            row_entry[key] = value
        results.append(row_entry)

    print("-" * 100)

    df = pd.DataFrame(results)
    reports_dir = os.path.join(script_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    csv_path = os.path.join(reports_dir, "refresh_times_vs_wwl_swing.csv")
    df.to_csv(csv_path, index=False)
    print("\nResults saved to reports/refresh_times_vs_wwl_swing.csv")

    plot_data = {
        'mem_model': args.mem_model,
        'calibration': {
            'sigma_multiple': sigma_multiple,
            'vth_spread_mv': vth_spread * 1e3,
            'sigma_stddev_mv': nominal_vth_sigma * 1e3,
            'nominal_refresh_us': nominal_refresh_time * 1e6,
            'nominal_wwl_swing': nominal_wwl_swing,
            'nominal_vdd': nominal_vdd,
        },
        'wwl_swing_values': wwl_swing_values.tolist(),
        'fault_rate_targets': {target['key']: target['value'] for target in fault_rate_targets},
        'refresh_times': {target['key']: [] for target in fault_rate_targets}
    }

    for target in fault_rate_targets:
        for result in results:
            plot_data['refresh_times'][target['key']].append(result.get(target['key'], np.nan))

    json_path = os.path.join(reports_dir, "refresh_times_data.json")
    with open(json_path, 'w') as f:
        json.dump(plot_data, f, indent=2)
    print("Plot data saved to reports/refresh_times_data.json")


if __name__ == "__main__":
    main()
