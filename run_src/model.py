from run_src.utils import *

def evaluate(sys_cfg, apps_result, tech_result):
    DesignTarget = sys_cfg.get('DesignTarget')
    WordWidth = sys_cfg.get('WordWidth', 0) / 8 # scale bits to bytes
    benchmark = apps_result.get('benchmark_name', 'unknown')

    if DesignTarget == "cache":
        # Extract benchmark data: assume data is from Sniper or Perf
        load_hits    = apps_result.get('load_hits', 0)
        load_misses  = apps_result.get('load_misses', 0)
        store_hits   = apps_result.get('store_hits', 0)
        store_misses = apps_result.get('store_misses', 0)
        time         = (apps_result.get('execution_time', 0)) # (seconds)

        # Extract tech data
        read_hit_latency         = tech_result.get('cache_hit_latency', 0)          # (ns)
        read_miss_latency        = tech_result.get('cache_miss_latency', 0)
        write_latency            = tech_result.get('cache_write_latency', 0)
        read_bw                  = tech_result.get('data_array_read_bw', 0)
        write_bw                 = tech_result.get('data_array_write_bw', 0)        # Bps
        read_hit_dynamic_energy  = tech_result.get('cache_hit_dynamic_energy', 0)   # (nJ per access)
        read_miss_dynamic_energy = tech_result.get('cache_miss_dynamic_energy', 0)
        write_dynamic_energy     = tech_result.get('cache_write_dynamic_energy', 0)
        leakage_power_total      = tech_result.get('cache_total_leakage_power', 0)  # (mW)

        # Latency calculations (scale to ms)
        read_latency_total  = (load_hits * read_hit_latency + load_misses * read_miss_latency) * 1.0e-6
        write_latency_total = (store_hits + store_misses) * write_latency * 1.0e-6
        total_latency       = read_latency_total + write_latency_total

        # Energy calculations (scale to mJ)
        read_energy_total  = (load_hits * read_hit_dynamic_energy + load_misses * read_miss_dynamic_energy) * 1.0e-6
        write_energy_total = (store_hits + store_misses) * write_dynamic_energy * 1.0e-6
        total_energy       = read_energy_total + write_energy_total

        # Power calculations (mW)
        read_power_total  = read_energy_total / time if time else 0
        write_power_total = write_energy_total / time if time else 0
        total_power       = leakage_power_total + read_power_total + write_power_total

        # bandwidth (not yet implemented)
        rps = (load_hits + load_misses) / time if time else 0
        wps = (store_hits + store_misses) / time if time else 0
        read_bw_utilization = 100 * (rps * WordWidth) / read_bw if read_bw else 0
        write_bw_utilization = 100 * (wps * WordWidth) / write_bw if write_bw else 0

    else: # assume DesignTarget is 'RAM' and memory statistics are from DynamoRIO
        writes  = apps_result.get('total_writes', 0)
        reads   = apps_result.get('total_reads', 0)
        time    = (apps_result.get('execution_time', 0)) * 1.0e-6 # (scale us to seconds)

        read_latency         = tech_result.get('read_latency', 0)                  # ns
        write_latency        = tech_result.get('write_latency', 0)
        read_bw              = tech_result.get('read_bw', 0)                       # Bps
        write_bw             = tech_result.get('write_bw', 0)
        write_dynamic_energy = tech_result.get('write_dynamic_energy', 0) * 1.0e-3 # (scale pJ to nJ per access)
        read_dynamic_energy  = tech_result.get('read_dynamic_energy', 0) * 1.0e-3
        leakage_power_total        = tech_result.get('leakage_power', 0)           # (mW)

        read_latency_total  = reads * read_latency  * 1.0e-6 # scale to ms
        write_latency_total = writes * write_latency * 1.0e-6
        total_latency       = read_latency_total + write_latency_total

        read_energy_total  = reads  * read_dynamic_energy  * 1.0e-6 # mJ
        write_energy_total = writes * write_dynamic_energy * 1.0e-6
        total_energy       = read_energy_total + write_energy_total

        read_power_total  = read_energy_total  / time if time else 0 # mW
        write_power_total = write_energy_total / time if time else 0
        total_power = leakage_power_total + read_power_total + write_power_total

        rps = reads / time if time else 0
        wps = writes / time if time else 0
        read_bw_utilization = 100 * (rps * WordWidth) / read_bw if read_bw else 0
        write_bw_utilization = 100 * (wps * WordWidth) / write_bw if write_bw else 0

    return {
        "benchmark":                    benchmark,
        "total_read_latency_ms":        read_latency_total,
        "total_write_latency_ms":       write_latency_total,
        "total_latency_ms":             total_latency,
        "total_read_energy_mJ":         read_energy_total,
        "total_write_energy_mJ":        write_energy_total,
        "total_energy_mJ":              total_energy,
        "total_dynamic_read_power_mW":  read_power_total,
        "total_dynamic_write_power_mW": write_power_total,
        "total_power_mW":               total_power,
        "read_bw_utilization_%":        read_bw_utilization,
        "write_bw_utilization_%":       write_bw_utilization
    }