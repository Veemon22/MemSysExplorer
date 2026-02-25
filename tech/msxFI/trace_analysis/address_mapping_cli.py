"""CLI entry for address-mapping trace simulation."""

import argparse
import os

from msxFI import fi_config


def _load_components():
    try:
        from .address_mapping import (
            MemoryConfig,
            AddressMapper,
            RefreshTracker,
            get_default_config,
            estimate_nominal_retention_us,
            run_simulation,
        )
    except ImportError:
        from address_mapping import (
            MemoryConfig,
            AddressMapper,
            RefreshTracker,
            get_default_config,
            estimate_nominal_retention_us,
            run_simulation,
        )
    return (
        MemoryConfig,
        AddressMapper,
        RefreshTracker,
        get_default_config,
        estimate_nominal_retention_us,
        run_simulation,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="eDRAM LLC Retention Fault Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Trace format (CSV):
  timestamp,address,operation
  1000,0x7ffed34b9,1
  ...
  (timestamp in ns, operation: 1=write, 0=read)

Examples:
  python address_mapping.py
  python address_mapping.py --trace trace.csv --retention 100
  python address_mapping.py --trace trace.csv --mem-model dram1t --retention 100
  python address_mapping.py --trace trace.csv --bank-rows 16 --bank-cols 32
""",
    )
    parser.add_argument("--trace", type=str, help="Trace file path (CSV)")
    parser.add_argument(
        "--retention",
        type=float,
        default=None,
        help="Retention reference in microseconds for the per-bit retention distribution. "
        "If omitted: dram1t=64000us, dram3t=100us, dram333t=501us at wwl_swing=1.4V.",
    )
    parser.add_argument(
        "--mem-model",
        type=str,
        default="dram333t",
        choices=["dram1t", "dram3t", "dram333t"],
        help="DRAM memory model (default: dram333t). "
        "dram1t: reads also refresh, dram3t/dram333t: only writes refresh",
    )
    parser.add_argument("-v", "--verbose", action="store_true")

    cfg = parser.add_argument_group("Memory Configuration")
    cfg.add_argument("--bank-rows", type=int, default=32, help="Number of bank rows (default: 32)")
    cfg.add_argument("--bank-cols", type=int, default=64, help="Number of bank columns (default: 64)")
    cfg.add_argument("--mats-per-bank", type=int, default=4, help="Number of mats per bank (default: 4)")
    cfg.add_argument(
        "--subarrays-per-mat",
        type=int,
        default=1,
        help="Number of subarrays per mat (default: 1)",
    )
    cfg.add_argument("--subarray-rows", type=int, default=16, help="Number of rows per subarray (default: 16)")
    cfg.add_argument(
        "--subarray-cols",
        type=int,
        default=1024,
        help="Number of columns (bits) per subarray (default: 1024)",
    )
    cfg.add_argument("--block-size", type=int, default=64, help="Cache block size in bytes (default: 64)")

    ref = parser.add_argument_group("Refresh Configuration")
    ref.add_argument(
        "--banks-per-refresh",
        type=int,
        default=2,
        help="Banks co-activated per refresh group (default: 2)",
    )
    ref.add_argument(
        "--mats-per-refresh",
        type=int,
        default=4,
        help="Mats per bank in refresh group (default: 4)",
    )
    ref.add_argument(
        "--refresh-interval",
        type=float,
        default=None,
        help="Explicit periodic refresh interval in microseconds. "
        "If not set, only write accesses provide refresh.",
    )

    phy = parser.add_argument_group("Physics Model")
    phy.add_argument(
        "--wwl_swing",
        type=float,
        default=None,
        help="Wordline voltage in V, only effective for dram333t "
        "(default: model nominal)",
    )
    phy.add_argument(
        "--vth-sigma",
        type=float,
        default=50.0,
        help=argparse.SUPPRESS,
    )
    return parser


def print_results(result: dict) -> None:
    print("\n" + "=" * 60)
    print("Simulation Results")
    print("=" * 60)
    print("\nConfiguration:")
    retention_label = "Retention reference"
    print(f"  {retention_label}: {result['retention_time_us']:.1f} us")
    refresh_iv = result.get("refresh_interval_us")
    if refresh_iv is not None:
        print(f"  Explicit refresh interval: {refresh_iv:.1f} us")
    else:
        print("  Explicit refresh: none, write-interval-only retention check")

    print("\nAccess Statistics:")
    print(f"  Total accesses: {result['total_accesses']}")
    print(f"  Total writes: {result['total_writes']}")
    print(f"  Total reads: {result['total_reads']}")

    cfg = result.get("config")
    if cfg is not None:
        coact = cfg.banks_per_refresh_group * cfg.mats_per_bank_in_refresh_group * cfg.subarrays_per_mat
        refresh_note = f" ({result['total_writes']} writes x {coact} co-activated rows)"
    else:
        refresh_note = ""
    print("\nRefresh Statistics:")
    print(f"  Write refreshes: {result['stats']['write_refreshes']}{refresh_note}")
    if result["stats"].get("read_refreshes", 0):
        print(f"  Read refreshes: {result['stats']['read_refreshes']}")

    print("\nFault Statistics:")
    print(f"  Tracked cells: {result.get('total_tracked_cells', 0)} (bit-cells in tracked rows)")
    print(f"  Faulty cells: {result['faulty_cells']} (expected faulty bit-cells)")
    print(
        f"  Fault events: {result.get('fault_events', 0)} "
        "(expected fault occurrences across intervals, same bit-cell can contribute multiple times)"
    )
    print(f"  Cell fault rate: {result['cell_fault_rate'] * 100:.6f}% (faulty / tracked)")


def run_demo() -> None:
    _, AddressMapper, RefreshTracker, get_default_config, _, _ = _load_components()
    config = get_default_config()
    mapper = AddressMapper(config)
    mapper.print_config()

    print("\nAddress Decoding Examples:")
    for addr in [0x0, 0x1F1234A, 0x11234A0]:
        comp = mapper.decode_address(addr)
        print(
            f"  {comp['address']}: bank({comp['bank_row']},{comp['bank_col']}) "
            f"mat{comp['mat_idx']} subarray{comp['subarray_id']} row{comp['subarray_row']}"
        )

    print("\nCo-activated Subarrays:")
    coact = mapper.get_coactivated_subarrays(0x127F01)
    print(f"  Address 0x127F01 co-activates {len(coact)} subarrays")
    for sid, row in coact[:4]:
        print(f"    Subarray {sid}, Row {row}")
    if len(coact) > 4:
        print("    ...")

    print("\n" + "=" * 60)
    print("Fault Simulation Demo (interval threshold rule)")
    print("=" * 60)

    tracker = RefreshTracker(mapper, refresh_interval_us=501.0, retention_time_us=501.0)
    addresses = [0x0, 0x0, 0x0]
    timestamps = [0.0, 30.0, 600.0]
    operations = ["w", "r", "r"]

    print("\nAccess sequence:")
    for addr, ts, op in zip(addresses, timestamps, operations):
        action = "write" if op == "w" else "read"
        print(f"  t={ts:5.1f}us: {action} {hex(addr)}")

    result = tracker.simulate(addresses, timestamps, operations)
    print(
        f"\nResults: faulty cells={result['faulty_cells']}, "
        f"cell fault rate={result['cell_fault_rate'] * 100:.6f}%"
    )


def run_cli(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    MemoryConfig, _, _, _, estimate_nominal_retention_us, run_simulation = _load_components()

    if not args.trace:
        run_demo()
        return 0

    if not os.path.exists(args.trace):
        print(f"Error: {args.trace} not found")
        return 1

    try:
        config = MemoryConfig(
            bank_rows=args.bank_rows,
            bank_cols=args.bank_cols,
            mats_per_bank=args.mats_per_bank,
            subarrays_per_mat=args.subarrays_per_mat,
            subarray_rows=args.subarray_rows,
            subarray_cols=args.subarray_cols,
            block_size_bytes=args.block_size,
            banks_per_refresh_group=args.banks_per_refresh,
            mats_per_bank_in_refresh_group=args.mats_per_refresh,
        )
    except ValueError as exc:
        print(f"Configuration error: {exc}")
        return 1

    refresh_policy = "readwrite" if args.mem_model == "dram1t" else "write"
    user_wwl_swing = args.wwl_swing
    if args.mem_model != "dram333t" and user_wwl_swing is not None:
        print(f"Note: --wwl_swing is only effective for DRAM333T, ignoring for {args.mem_model.upper()}.")
        user_wwl_swing = None

    if args.retention is not None:
        retention_us = args.retention
        retention_note = "Retention reference"
    elif args.mem_model == "dram333t" and user_wwl_swing is not None:
        retention_us = estimate_nominal_retention_us(args.mem_model, user_wwl_swing)
        retention_note = "Retention reference"
    else:
        retention_us = fi_config.default_retention_us[args.mem_model]
        retention_note = "Retention reference"
    refresh_interval_us = args.refresh_interval

    print(f"Trace: {args.trace}")
    print(f"Memory model: {args.mem_model.upper()} (refresh policy: {refresh_policy})")
    print(f"{retention_note}: {retention_us:.3f} us")
    if refresh_interval_us is not None:
        print(
            "Fault rule: per-bit retention follows DRAM physics distribution, explicit refreshes are inserted between writes, "
            "and each gap contributes bit-level fault probability"
        )
    else:
        print("Fault rule: per-bit retention follows DRAM physics distribution and interval since last write sets fault probability")
    if refresh_interval_us is not None:
        print(f"Explicit refresh interval: {refresh_interval_us} us")
    else:
        print("Explicit refresh: none, write-interval-only retention check")

    if args.verbose:
        print("\nMemory Configuration:")
        print(f"  Banks: {args.bank_rows} x {args.bank_cols}")
        print(f"  Mats/Bank: {args.mats_per_bank}")
        print(f"  Subarrays/Mat: {args.subarrays_per_mat}")
        print(f"  Subarray: {args.subarray_rows} rows x {args.subarray_cols} bits")
        print(f"  Block size: {args.block_size} bytes")
        print(f"  Refresh group: {args.banks_per_refresh} banks x {args.mats_per_refresh} mats")

    try:
        result = run_simulation(
            args.trace,
            config,
            args.verbose,
            refresh_policy=refresh_policy,
            refresh_interval_us=refresh_interval_us,
            mem_model=args.mem_model,
            wwl_swing=user_wwl_swing,
            retention_time_us=retention_us,
            retention_is_default=(args.retention is None),
        )
    except ValueError as exc:
        print(f"Input error: {exc}")
        return 1
    print_results(result)
    return 0
