import csv
import re
import os
import sys
import yaml



def extract_value(val):
            if isinstance(val, str):
                return float(val.split()[0])
            return val

def choosing_tech_yaml(sys_cfg):
    """
    Choose appropriate tech YAML based on system config.
    Currently supports only cache design target.
    """

    if sys_cfg.get("DesignTarget") == "cache":
        print(f"Choosing default config: tech/ArrayCharacterization/sample_configs/sample_FeFET_32nm.yaml")
        return "tech/ArrayCharacterization/sample_configs/sample_FeFET_32nm.yaml"
    else:
        print(f"Unsupported DesignTarget '{sys_cfg.get('DesignTarget')}'. Only 'cache' is supported.")
        sys.exit(1)


    
def parse_array_char_output(yaml_file_path):
    """
    Parse NVSim YAML output file.
    Returns a list of results (1 or more depending on optimization mode).
    Backwards compatible: if single result, returns list with 1 element.
    """
    with open(yaml_file_path, 'r') as f:
        # Load all YAML documents (separated by ---)
        result = yaml.load(f, Loader=yaml.FullLoader)
    
        data={}

        if "CacheDesign" in result:
            cache = result["CacheDesign"]
            
            data["total_area"] = cache['Area']['Total_mm2']
            data["cache_hit_latency"] = cache['Timing']['CacheHitLatency_ns']
            data["cache_miss_latency"] = cache['Timing']['CacheMissLatency_ns']
            data["cache_write_latency"] = cache['Timing']['CacheWriteLatency_ns']
            data["cache_hit_dynamic_energy"] = cache['Power']['CacheHitDynamicEnergy_nJ']
            data["cache_miss_dynamic_energy"] = cache['Power']['CacheMissDynamicEnergy_nJ']
            data["cache_write_dynamic_energy"] = cache['Power']['CacheWriteDynamicEnergy_nJ']
            data["cache_total_leakage_power"] = cache['Power']['CacheTotalLeakagePower_mW']
            
            if "DataArray" in result and "Results" in result["DataArray"]:
                data_results = result["DataArray"]["Results"]
                data["data_array_read_latency"] = data_results['Timing']['Read']['Latency_ns']
                data["data_array_read_dynamic_energy"] = data_results['Power']['Read']['DynamicEnergy_pJ']
                data["data_array_leakage_power"] = data_results['Power']['Leakage_mW']
                
                if "Write" in data_results["Power"]:
                    data["data_array_write_dynamic_energy"] = data_results['Power']['Write']['DynamicEnergy_pJ']
                elif "Set" in data_results["Power"]:
                    data["data_array_write_dynamic_energy"] = data_results['Power']['Set']['DynamicEnergy_pJ']
            
            if "TagArray" in result and "Results" in result["TagArray"]:
                tag_results = result["TagArray"]["Results"]
                data["tag_array_read_latency"] = tag_results['Timing']['Read']['Latency_ns'] 
                data["tag_array_read_dynamic_energy"] = tag_results['Power']['Read']['DynamicEnergy_pJ']
                data["tag_array_leakage_power"] = tag_results['Power']['Leakage_mW']
                
                if "Write" in tag_results["Power"]:
                    data["tag_array_write_dynamic_energy"] = tag_results['Power']['Write']['DynamicEnergy_pJ']
                elif "Set" in tag_results["Power"]:
                    data["tag_array_write_dynamic_energy"] = tag_results['Power']['Set']['DynamicEnergy_pJ']
        
        else:
            # Non-cache design
            if "Results" in result:
                res = result["Results"]
                data["total_area"] = res['Area']['Total']['Area_mm2']
                data["read_latency"] = res['Timing']['Read']['Latency_ns']
                data["read_dynamic_energy"] = res['Power']['Read']['DynamicEnergy_pJ']
                data["leakage_power"] = res['Power']['Leakage_mW']
                
                if "Write" in res["Timing"]:
                    data["write_latency"] = res['Timing']['Write']['Latency_ns']
                    data["write_dynamic_energy"] = res['Power']['Write']['DynamicEnergy_pJ']
                elif "Set" in res["Timing"]:
                    data["write_latency"] = res['Timing']['Set']['Latency_ns']
                    data["write_dynamic_energy"] = res['Power']['Set']['DynamicEnergy_pJ']
    
    return data

def results_to_csv(apps_cfg, sys_cfg, config_name, tech_result, model_result, csv_filepath):
    file_exists = os.path.exists(csv_filepath)
    with open(csv_filepath, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)

        if not file_exists:
            header = [
                "Config Name",
                "Profiler",
                "Cache Level",
                "Design Target",
                "Capacity (KB)",
                "Word Width (bits)",
                "Optimization Target",
                "Total Reads",
                "Total Writes",
                "Total Hits",
                "Total Misses",
                "Total Read Latency (ms)",
                "Total Write Latency (ms)",
                "Total Hit Latency (ms)",
                "Total Miss Latency (ms)",
                "Total Latency (ms)",
                "Total Read Energy (mJ)",
                "Total Write Energy (mJ)",
                "Total Hit Energy (mJ)",
                "Total Miss Energy (mJ)",
                "Total Energy (mJ)",
                "Cache Hit Latency (ns)",
                "Cache Miss Latency (ns)",
                "Cache Write Latency (ns)",
                "Cache Hit Energy (nJ)",
                "Cache Miss Energy (nJ)",
                "Cache Write Energy (nJ)",
                "Leakage Power (mW)",
                "Total Area (mm^2)"
            ]
            writer.writerow(header)
        
        # Extract tech data properly
        if isinstance(tech_result, list):
            tech_data = tech_result[0]
        else:
            tech_data = tech_result
        
        # Write data row
        row = [
            config_name,
            apps_cfg.get('profiler', 'unknown'),
            apps_cfg.get('level', 'N/A'),
            sys_cfg.get('DesignTarget', 'unknown'),
            sys_cfg.get('Capacity', {}).get('Value', 'N/A'),
            sys_cfg.get('WordWidth', 'N/A'),
            sys_cfg.get('OptimizationTarget', 'N/A'),
            model_result.get('total_reads', 0),
            model_result.get('total_writes', 0),
            model_result.get('total_hits', 0),
            model_result.get('total_misses', 0),
            model_result.get('total_hit_latency (ms)', 0),
            model_result.get('total_write_latency (ms)', 0),
            model_result.get('total_hit_latency (ms)', 0),
            model_result.get('total_miss_latency (ms)', 0),
            model_result.get('total_latency (ms)', 0),
            model_result.get('total_hit_energy (mJ)', 0),
            model_result.get('total_write_energy (mJ)', 0),
            model_result.get('total_hit_energy (mJ)', 0),
            model_result.get('total_miss_energy (mJ)', 0),
            model_result.get('total_energy (mJ)', 0),
            tech_data.get('cache_hit_latency', 0),
            tech_data.get('cache_miss_latency', 0),
            tech_data.get('cache_write_latency', 0),
            tech_data.get('cache_hit_dynamic_energy', 0),
            tech_data.get('cache_miss_dynamic_energy', 0),
            tech_data.get('cache_write_dynamic_energy', 0),
            tech_data.get('cache_total_leakage_power', 0),
            tech_data.get('total_area', 0)
        ]
        writer.writerow(row)