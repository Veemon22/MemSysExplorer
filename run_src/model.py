from run_src.utils import *

def evaluate(DesignTarget, apps_result, tech_result):
    """
    Evaluate a single benchmark against a single tech configuration.
    
    Args:
        apps_result: dict with benchmark data (total_hits, total_misses, etc.)
        tech_result: dict with tech characterization data
    
    Returns:
        dict with evaluation results
    """
    if DesignTarget == "cache":
        # Extract benchmark data
        if 'total_hits' in apps_result:
            hits = apps_result.get('total_hits', 0)
        else:
            hits = apps_result.get('load_hits', 0) + apps_result.get('store_hits', 0)
        if 'total_misses' in apps_result:             
            misses = apps_result.get('total_misses', 0)
        else:
            misses = apps_result.get('store_misses', 0) + apps_result.get('load_misses', 0)
        writes = apps_result.get('total_writes', 0)
        reads = apps_result.get('total_reads', 0)
        time = apps_result.get('time_elapsed', 0)
        
        # Extract tech data
        hitlatency = tech_result.get('cache_hit_latency', 0)  # (ns)
        misslatency = tech_result.get('cache_miss_latency', 0)
        writelatency = tech_result.get('cache_write_latency', 0)

        hitenergy = tech_result.get('cache_hit_dynamic_energy', 0)  # (nJ per access)
        missenergy = tech_result.get('cache_miss_dynamic_energy', 0)
        writeenergy = tech_result.get('cache_write_dynamic_energy', 0)

        leakagepower = tech_result.get('cache_total_leakage_power', 0)  # (mW)

        # latency calculations (ms)
        hitlatency_total = hits * hitlatency * 10.e-6
        misslatency_total = misses * misslatency * 10.e-6
        writelatency_total = writes * writelatency * 10.e-6
        total_latency = hitlatency_total + misslatency_total + writelatency_total

        # energy calculations (mJ)
        hitenergy_total = hits * hitenergy * 10.e-6
        missenergy_total = misses * missenergy * 10.e-6
        writeenergy_total = writes * writeenergy * 10.e-6
        total_energy = hitenergy_total + missenergy_total + writeenergy_total

        # power calculations (mW)
        hitpower = hitenergy_total / time if time else 0
        misspower = missenergy_total / time if time else 0
        writepower = writeenergy_total / time if time else 0
        total_power = leakagepower + hitpower + misspower + writepower 

        return {
            "total_hit_latency_ms": hitlatency_total,
            "total_miss_latency_ms": misslatency_total,
            "total_write_latency_ms": writelatency_total,
            "total_latency_ms": total_latency,
            "total_hit_energy_mJ": hitenergy_total,
            "total_miss_energy_mJ": missenergy_total,
            "total_write_energy_mJ": writeenergy_total,
            "total_energy_mJ": total_energy,
            "total_hit_power_mW": hitpower,
            "total_miss_power_mW": misspower,
            "total_write_power_mW": writepower,
            "total_power_mW": total_power
        }
    else:
        return None
