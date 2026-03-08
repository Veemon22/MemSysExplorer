import json
import math
import sys

def is_power_of_two(n):
    """Check if a number is a power of 2 (e.g., 1, 2, 4, 8, 16...)."""
    if n <= 0:
        return False
    # A binary trick: n & (n-1) is 0 only for powers of 2
    return (n & (n - 1)) == 0

def validate_memsyspattern_config(file_path):
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading file '{file_path}': {e}")
        return

    # Extract values
    r_size = data.get("read_size")
    w_size = data.get("write_size")
    r_freq = data.get("read_freq")
    w_freq = data.get("write_freq")
    t_reads = data.get("total_reads")
    t_writes = data.get("total_writes")
    exec_time = data.get("execution_time")

    results = []

    # 1. Check if read_size and write_size are powers of 2
    if is_power_of_two(r_size) and is_power_of_two(w_size):
        results.append("✅ Read/Write sizes are powers of 2.")
    else:
        results.append(f"❌ Size Error: Read({r_size}) or Write({w_size}) is not a power of 2.")

    # 2. Check Read Frequency: read_freq = total_reads / execution_time
    expected_r_freq = t_reads / exec_time
    if math.isclose(r_freq, expected_r_freq, rel_tol=1e-5):
        results.append("✅ Read frequency calculation is correct.")
    else:
        results.append(f"❌ Frequency Error: Expected Read Freq {expected_r_freq}, got {r_freq}")

    # 3. Check Write Frequency: write_freq = total_writes / execution_time
    expected_w_freq = t_writes / exec_time
    if math.isclose(w_freq, expected_w_freq, rel_tol=1e-5):
        results.append("✅ Write frequency calculation is correct.")
    else:
        results.append(f"❌ Frequency Error: Expected Write Freq {expected_w_freq}, got {w_freq}")

    # Print Report
    print(f"\n--- Validation Report for {file_path} ---")
    for r in results:
        print(r)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 validate_drio_memsyspattern_config.py <path_to_json_file>")
        sys.exit(1)
    file_path = sys.argv[1]
    validate_memsyspattern_config(file_path)