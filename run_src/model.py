from run_src.utils import *

def evaluate(DesignTarget, apps_result, tech_result):
    benchmark = apps_result.get('benchmark_name', 'unknown')

    if DesignTarget == "cache":
        # Extract benchmark data
        load_hits    = apps_result.get('load_hits', 0)
        load_misses  = apps_result.get('load_misses', 0)
        store_hits   = apps_result.get('store_hits', 0)
        store_misses = apps_result.get('store_misses', 0)
        reads        = apps_result.get('total_reads', 0)
        writes       = apps_result.get('total_writes', 0)
        time         = (apps_result.get('execution_time') or 0)* 1000

        # Extract tech data
        hitlatency   = tech_result.get('cache_hit_latency', 0)          # (ns)
        misslatency  = tech_result.get('cache_miss_latency', 0)
        writelatency = tech_result.get('cache_write_latency', 0)
        hitenergy    = tech_result.get('cache_hit_dynamic_energy', 0)   # (nJ per access)
        missenergy   = tech_result.get('cache_miss_dynamic_energy', 0)
        writeenergy  = tech_result.get('cache_write_dynamic_energy', 0)
        leakagepower = tech_result.get('cache_total_leakage_power', 0)  # (mW)

        # Latency calculations (ms)
        hit_latency_total   = (load_hits + store_hits)     * hitlatency   * 1.0e-6
        miss_latency_total  = (load_misses + store_misses) * misslatency  * 1.0e-6
        read_latency_total  = reads                        * hitlatency   * 1.0e-6
        write_latency_total = writes                       * writelatency * 1.0e-6
        total_latency       = read_latency_total + write_latency_total

        # Energy calculations (mJ)
        hit_energy_total    = (load_hits + store_hits)     * hitenergy   * 1.0e-6
        miss_energy_total   = (load_misses + store_misses) * missenergy  * 1.0e-6
        read_energy_total   = reads                        * hitenergy   * 1.0e-6
        write_energy_total  = writes                       * writeenergy * 1.0e-6
        total_energy        = read_energy_total + write_energy_total

        # Power calculations (mW)
        read_power  = read_energy_total  / time if time else 0
        write_power = write_energy_total / time if time else 0
        total_power = leakagepower + read_power + write_power

        return {
            "benchmark":             benchmark,
            "total_reads":           reads,
            "total_writes":          writes,
            "total_hits":            load_hits + store_hits,
            "total_misses":          load_misses + store_misses,
            "total_hit_latency_ms":  hit_latency_total,
            "total_miss_latency_ms": miss_latency_total,
            "total_read_latency_ms": read_latency_total,
            "total_write_latency_ms":write_latency_total,
            "total_latency_ms":      total_latency,
            "total_hit_energy_mJ":   hit_energy_total,
            "total_miss_energy_mJ":  miss_energy_total,
            "total_read_energy_mJ":  read_energy_total,
            "total_write_energy_mJ": write_energy_total,
            "total_energy_mJ":       total_energy,
            "total_read_power_mW":   read_power,
            "total_write_power_mW":  write_power,
            "total_power_mW":        total_power,
        }

    else:
        writes  = apps_result.get('total_writes', 0)
        reads   = apps_result.get('total_reads', 0)
        time    = (apps_result.get('execution_time', 0) or 0) * 1000

        readlatency  = tech_result.get('read_latency', 0)          # ns
        writelatency = tech_result.get('write_latency', 0)
        writeenergy  = tech_result.get('write_dynamic_energy', 0)  # (nJ per access)
        readenergy   = tech_result.get('read_dynamic_energy', 0)
        leakagepower = tech_result.get('leakage_power', 0)         # (mW)

        read_latency_total  = reads  * readlatency  * 1.0e-6
        write_latency_total = writes * writelatency * 1.0e-6
        total_latency       = read_latency_total + write_latency_total

        read_energy_total   = reads  * readenergy  * 1.0e-6
        write_energy_total  = writes * writeenergy * 1.0e-6
        total_energy        = read_energy_total + write_energy_total

        read_power  = read_energy_total  / time if time else 0
        write_power = write_energy_total / time if time else 0
        total_power = leakagepower + read_power + write_power

        return {
            "benchmark":              benchmark,
            "total_reads":            reads,
            "total_writes":           writes,
            "total_read_latency_ms":  read_latency_total,
            "total_write_latency_ms": write_latency_total,
            "total_latency_ms":       total_latency,
            "total_read_energy_mJ":   read_energy_total,
            "total_write_energy_mJ":  write_energy_total,
            "total_energy_mJ":        total_energy,
            "total_read_power_mW":    read_power,
            "total_write_power_mW":   write_power,
            "total_power_mW":         total_power,
        }