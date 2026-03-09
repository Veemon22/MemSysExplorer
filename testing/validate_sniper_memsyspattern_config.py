#!/usr/bin/env python3
import sys
import json
import configparser

def get_total_cores(config_file):
    """Parse Sniper config to get total_cores and L1 D-cache line size."""
    parser = configparser.ConfigParser()
    parser.read(config_file)

    try:
        total_cores = int(parser['general']['total_cores'])
    except KeyError:
        print("Error: 'total_cores' not found in [general] section of config.")
        sys.exit(1)

    try:
        cache_line_size = int(parser['perf_model/l1_dcache']['cache_block_size'])
    except KeyError:
        print("Error: 'cache_block_size' not found in [perf_model/l1_dcache] section.")
        sys.exit(1)

    return total_cores, cache_line_size

def validate_output(output_file, total_cores, cache_line_size):
    """Validate JSON output against config."""
    try:
        with open(output_file, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading output file: {e}")
        sys.exit(1)

    # 1. Check number of cores
    output_cores = len(data)
    if output_cores != total_cores:
        print(f"❌ Number of cores mismatch: Config={total_cores}, Output={output_cores}")
    else:
        print(f"✅ Number of cores matches: {total_cores}")

    # 2. Check read/write sizes and histogram totals
    size_errors = False
    histogram_errors = False
    for core_idx, core in enumerate(data):
        # Read/write size vs cache line
        if core['total_reads'] > 0 and core['read_size'] != cache_line_size:
            print(f"❌ Core {core_idx}: read_size {core['read_size']} != cache line {cache_line_size}")
            size_errors = True
        if core['total_writes'] > 0 and core['write_size'] != cache_line_size:
            print(f"❌ Core {core_idx}: write_size {core['write_size']} != cache line {cache_line_size}")
            size_errors = True

        # Histogram sums
        read_hist_sum = sum(core['read_size_histogram'].values())
        write_hist_sum = sum(core['write_size_histogram'].values())
        if read_hist_sum != core['total_reads']:
            print(f"❌ Core {core_idx}: sum of read_size_histogram ({read_hist_sum}) != total_reads ({core['total_reads']})")
            histogram_errors = True
        if write_hist_sum != core['total_writes']:
            print(f"❌ Core {core_idx}: sum of write_size_histogram ({write_hist_sum}) != total_writes ({core['total_writes']})")
            histogram_errors = True

    if not size_errors:
        print(f"✅ All active core read/write sizes match cache line ({cache_line_size} bytes)")
    if not histogram_errors:
        print(f"✅ All core read/write histograms sum to total_reads/total_writes")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <config_file> <output_json_file>")
        sys.exit(1)

    config_file = sys.argv[1]
    output_file = sys.argv[2]

    total_cores, cache_line_size = get_total_cores(config_file)
    validate_output(output_file, total_cores, cache_line_size)