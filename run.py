import os
import sys
import tempfile
import argparse
import json
import yaml
import shutil
from run_src.utils import *
from run_src.interfaces import *
from run_src.model import evaluate

def check_inputs(config):

    # Checking if sys, apps and tech configs are present
    required = set(['system', 'apps', 'tech'])
    if not required.issubset(config):
        print(f"Provide required top-level config fields: {required}")
        sys.exit(1)

    # Displying information from config file
    sys_cfg = config['system']
    print("\nSys config:")
    print(sys_cfg)

    apps_cfg = config['apps']
    print("\nApps config:")
    print(apps_cfg)

    tech_cfg = config['tech']
    print("\nTech config:")
    print(tech_cfg)

    # check required arguments for system config
    if sys_cfg is None:
        print("\nSystem config is empty.")
        sys.exit(1)

    if 'sys_config_path' in sys_cfg:
        if not os.path.exists(sys_cfg['sys_config_path']):
            print(f"System config path {sys_cfg['sys_config_path']} is not real.")
            sys.exit(1)
        with open(sys_cfg['sys_config_path'], 'r') as f:
            sys_cfg = yaml.load(f, Loader=yaml.FullLoader)
        print("Loaded system config from path: {sys_cfg}")

    required = set(['DesignTarget', 'Capacity', 'WordWidth', 'OptimizationTarget'])

    if not required.issubset(sys_cfg):
        print(f"Provide required system inputs: {required}")
        sys.exit(1)

    # check required arguments for applications interface
    if apps_cfg is None:
        print("\nApplications config is empty.")
        sys.exit(1)

    if 'run' not in apps_cfg or 'profiler' not in apps_cfg:
        print("\nEvery apps config must specify 'run' and 'profiler' fields.")
        sys.exit(1)
    if apps_cfg['run'] == "new":
        if apps_cfg['profiler'] == "dynamorio":
            required = set(["executable"])
        elif apps_cfg['profiler'] == "sniper":
            required = set(["level", "executable", "config"])
        else:
            required = set(["level", "executable"])
    else:
        required = set(["patternconfig_path"])
        if apps_cfg['profiler'] == "sniper":
            required.add("multithread")
    if not required.issubset(apps_cfg):
        print(f"Provide required apps inputs: {required}")
        sys.exit(1)

    # required arguments for array characterization
    if tech_cfg is None:
        print("\nTech config is empty.")
        sys.exit(1)

    if 'run' not in tech_cfg:
        print("Every tech config must specify 'run' field.")
        sys.exit(1)
    if tech_cfg['run'] == "new":
        required = set(['array_characterization_config'])
    else:
        required = set(['array_characterization_result_path'])
    if not required.issubset(tech_cfg):
        print("Choosing default tech config:")
        tech_cfg['array_characterization_config'] = choosing_tech_yaml(sys_cfg)

    if 'array_characterization_config' in tech_cfg:
        config_path = tech_cfg['array_characterization_config']
        if os.path.isfile(config_path):
            if not os.path.exists(config_path):
                print(f"Tech config path {config_path} is not real.")
                sys.exit(1)
            with open(config_path, 'r') as f:
                premade_tech_cfg = yaml.load(f, Loader=yaml.FullLoader)
                premade_tech_cfg.update(tech_cfg)
                tech_cfg = premade_tech_cfg
            print("Loaded tech config from path: ", config_path)
        elif os.path.isdir(config_path):
            # Validate directory exists, individual files validated during run
            print(f"Using tech config directory: {config_path}")
        else:
            print(f"Tech config path {config_path} is not real.")
            sys.exit(1)

        if os.path.isfile(config_path):
            required = set(['Associativity', 'MemoryCellInputFile'])
            if not required.issubset(tech_cfg):
                print(f"Provide required tech inputs for new ArrayCharacterization run: {required}")
                sys.exit(1)

    # logic checks
    if apps_cfg['profiler'] == "dynamorio" and sys_cfg['DesignTarget'] == "cache":
        print("Choose Sniper or Perf as a profiler for cache modeling.")
        sys.exit(1)

    # Check if data in existing tech results matches sys config requirements
    if tech_cfg['run'] == "existing":
        result_path = tech_cfg['array_characterization_result_path']
        if os.path.isdir(result_path):
            result_files = [
                os.path.join(result_path, f) for f in os.listdir(result_path)
                if f.endswith('.yaml') or f.endswith('.yml')
            ]
        else:
            result_files = [result_path]

        # Build expected sets from sys_cfg
        capacity_list = sys_cfg.get('Capacity', [])
        if not isinstance(capacity_list, list):
            capacity_list = [capacity_list]
        expected_capacities = {f"{cap['Value']}{cap['Unit']}" for cap in capacity_list}

        opt_targets = sys_cfg.get('OptimizationTarget', [])
        if not isinstance(opt_targets, list):
            opt_targets = [opt_targets]
        expected_opt_targets = set(opt_targets)

        for path in result_files:
            with open(path, 'r') as f:
                tech_result = yaml.load(f, Loader=yaml.FullLoader)

            # OptimizationTarget check - works for both cache and RAM
            if 'OptimizationTarget' in sys_cfg:
                if 'CacheDesign' in tech_result:
                    opt_in_result = tech_result['CacheDesign'].get('OptimizationTarget')
                else:
                    opt_in_result = tech_result.get('OptimizationTarget')
                if opt_in_result and opt_in_result not in expected_opt_targets:
                    print(f"Warning: OptimizationTarget mismatch in {path}. "
                          f"Result has {opt_in_result} but sys config expects one of {expected_opt_targets}")
                    sys.exit(1)

            # Capacity check
            if 'Capacity' in tech_result:
                cap = tech_result['Capacity']
                result_cap_label = f"{cap.get('Value', 'N/A')}{cap.get('Unit', '')}"
                if result_cap_label not in expected_capacities:
                    print(f"Warning: Capacity mismatch in {path}. "
                          f"Result has {result_cap_label} but sys config expects one of {expected_capacities}")
                    sys.exit(1)
            else:
                print(f"Warning: No Capacity field found in {path}. "
                      f"Was this result generated with an older version?")

    #TODO: add word width vs. read/write size logic checks

    return sys_cfg, apps_cfg, tech_cfg


def main():

    # parse config file input
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', '-c', type=str, required=True)
    args = parser.parse_args()
    with open(args.config, 'r') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    if config is None:
        print("Error loading config file or config is empty.")
        sys.exit(1)

    # input logic checks
    sys_cfg, apps_cfg, tech_cfg = check_inputs(config)

    # Making Directory For Run Outputs
    config_name = os.path.splitext(os.path.basename(args.config))[0]
    i = 1
    results_base = os.path.join("results", config_name)
    results_dir = f"{results_base}_{i}"
    while os.path.isdir(f"{results_base}_{i}"):
        i += 1
        results_dir = f"{results_base}_{i}"
    os.makedirs(results_dir)
    print(f"\nRun outputs will be saved to: {results_dir}")

    # Keeping track of original dir
    original_dir = os.getcwd()

    # Useful var for processes
    Tech_Dir = os.path.join("tech", "ArrayCharacterization")

    # run apps interface or pull existing run
    if apps_cfg['run'] == "new":
        if apps_cfg['profiler'] == "sniper":
            apps_cfg['executable'] = os.path.join(original_dir, apps_cfg['executable'])
            apps_cfg['config'] = os.path.join(original_dir, apps_cfg['config'])
        if apps_cfg['profiler'] == "perf" or apps_cfg['profiler'] == 'dynamorio':
            apps_cfg['executable'] = os.path.join(original_dir, apps_cfg['executable'])

        print(apps_cfg)

        os.chdir(results_dir)
        os.mkdir("apps_output")
        os.chdir("apps_output")

        if apps_cfg['profiler'] == "dynamorio":
            run_drio(apps_cfg['executable'], original_dir)
        elif apps_cfg['profiler'] == "sniper":
            run_sniper(apps_cfg['level'], apps_cfg['executable'], apps_cfg['config'], original_dir)
        else:
            run_perf(apps_cfg['level'], apps_cfg['arch'] if apps_cfg['arch'] != None else None, apps_cfg['executable'], original_dir)

        os.chdir(original_dir)

        apps_output_dir = os.path.join(results_dir, "apps_output")
        pattern_files = [os.path.join(apps_output_dir, f) for f in os.listdir(apps_output_dir)
                if f.endswith(".json") and "pattern" in f.lower()]

        if not pattern_files:
            raise FileNotFoundError(f"No pattern config JSON found in {apps_output_dir}")

        if len(pattern_files) == 1:
            apps_patternconfig = pattern_files[0]
        else:
            apps_patternconfig = pattern_files

    else:  # using existing run
        apps_patternconfig = apps_cfg['patternconfig_path']
        if os.path.isdir(apps_patternconfig):
            pattern_files = [os.path.join(apps_patternconfig, f) for f in os.listdir(apps_patternconfig)
                             if f.endswith(".json") and "pattern" in f.lower()]
            if not pattern_files:
                raise FileNotFoundError(f"No pattern config JSON found in directory {apps_patternconfig}")
            apps_patternconfig = pattern_files

    if isinstance(apps_patternconfig, list):
        print(f"Multiple pattern config files found: {apps_patternconfig}")
        apps_results = []
        for pattern_file in pattern_files:
            print(f"Parsing pattern config file: {pattern_file}")
            with open(pattern_file, 'r') as f:
                apps_result = json.load(f)
            print(f"Apps output from {pattern_file}:")
            print(apps_result)
            apps_results.append(apps_result)
    else:
        with open(apps_patternconfig, 'r') as f:
            apps_result = json.load(f)
        print("\nApps output:")
        print(apps_result)
        apps_results = [apps_result]
        pattern_files = [apps_patternconfig]

    # Array Characterization
    if tech_cfg['run'] == "new":
        arraychar_cfg = tech_cfg.copy()
        arraychar_cfg.update(sys_cfg)
        os.chdir(results_dir)
        os.mkdir("tech_output")
        os.chdir(original_dir)

        tech_output_dir = os.path.abspath(os.path.join(results_dir, "tech_output")) + "/"

        # Get all tech config files
        config_path = tech_cfg['array_characterization_config']
        if os.path.isdir(config_path):
            tech_config_paths = [
                os.path.join(config_path, f) for f in os.listdir(config_path)
                if f.endswith('.yaml') or f.endswith('.yml')
            ]
        else:
            tech_config_paths = [config_path]

        # Get all capacities
        capacity_list = sys_cfg.get('Capacity', [])
        if not isinstance(capacity_list, list):
            capacity_list = [capacity_list]

        # Get all optimization targets
        opt_target_list = sys_cfg.get('OptimizationTarget', [])
        if not isinstance(opt_target_list, list):
            opt_target_list = [opt_target_list]

        tech_results = []

        for tech_config_path in tech_config_paths:
            with open(tech_config_path, 'r') as f:
                single_tech_cfg = yaml.load(f, Loader=yaml.FullLoader)

            for cap in capacity_list:
                for opt_target in opt_target_list:
                    cap_label = f"{cap['Value']}{cap['Unit']}"

                    arraychar_cfg_copy = single_tech_cfg.copy()
                    arraychar_cfg_copy.update(sys_cfg)
                    arraychar_cfg_copy.update({k: v for k, v in tech_cfg.items()
                                            if k not in ('array_characterization_config', 'run')})
                    arraychar_cfg_copy['Capacity'] = cap
                    arraychar_cfg_copy['OptimizationTarget'] = opt_target
                    arraychar_cfg_copy['OutputDirectory'] = tech_output_dir

                    if 'MemoryCellInputFile' in single_tech_cfg:
                        mem_cell_path = arraychar_cfg_copy['MemoryCellInputFile']
                        if not os.path.isabs(mem_cell_path):
                            arraychar_cfg_copy['MemoryCellInputFile'] = os.path.join(original_dir, mem_cell_path)

                    # Use existing prefix if set, otherwise fall back to tech config filename
                    existing_prefix = arraychar_cfg_copy.get('OutputFilePrefix', '').strip()
                    if existing_prefix:
                        arraychar_cfg_copy['OutputFilePrefix'] = f"{existing_prefix}_{cap_label}_{opt_target}"
                    else:
                        tech_label = os.path.splitext(os.path.basename(tech_config_path))[0]
                        arraychar_cfg_copy['OutputFilePrefix'] = f"{tech_label}_{cap_label}_{opt_target}"

                    print(f"\nRunning array characterization: {os.path.basename(tech_config_path)} @ {cap_label} optimized for {opt_target}")

                    tech_yaml_str = yaml.dump(arraychar_cfg_copy)
                    with tempfile.NamedTemporaryFile(mode='w+', suffix='.yaml', delete=False) as tech_yaml:
                        tech_yaml.write(tech_yaml_str)
                        tech_yaml_path = tech_yaml.name

                    result = run_array_characterization(tech_yaml_path, Tech_Dir)
                    tech_results.append(result)
                    os.remove(tech_yaml_path)

    else:
        result_path = tech_cfg['array_characterization_result_path']
        if os.path.isdir(result_path):
            result_files = [
                os.path.join(result_path, f) for f in os.listdir(result_path)
                if f.endswith('.yaml') or f.endswith('.yml')
            ]
        else:
            result_files = [result_path]

        tech_results = []
        for path in result_files:
            result = parse_array_char_output(path)
            tech_results.append(result)

    print("\nTech Results:")
    print(tech_results)

    # ANALYTICAL MODEL
    os.chdir(results_dir)
    os.mkdir("model_output")
    os.chdir(original_dir)

    csv_filename = f"{config_name}_results.csv"
    csv_filepath = os.path.join(results_dir, "model_output", csv_filename)

    for tech_result in tech_results:
        mem_cell = tech_result.get('mem_cell_type', 'unknown')
        capacity = tech_result.get('capacity', 'unknown')
        print(f"\nEvaluating tech config: {mem_cell} @ {capacity}")

        for i, app_result in enumerate(apps_results):
            apps_result_name = os.path.splitext(os.path.basename(pattern_files[i]))[0]

            if apps_cfg['profiler'] == "sniper":
                if apps_cfg['multithread']:
                    print("\nEvaluating multiple benchmarks from Sniper output...")
                    for j, benchmark in enumerate(app_result):
                        model_result = evaluate(sys_cfg['DesignTarget'], benchmark, tech_result)
                        print(f"\nModel results for benchmark {j}:")
                        print(model_result)
                        results_to_csv(apps_cfg, sys_cfg, apps_result_name, tech_result, model_result, csv_filepath)
                else:
                    apps_result_single = app_result[0]
                    model_result = evaluate(sys_cfg['DesignTarget'], apps_result_single, tech_result)
                    print("\nModel results:")
                    print(model_result)
                    results_to_csv(apps_cfg, sys_cfg, apps_result_name, tech_result, model_result, csv_filepath)
            else:
                model_result = evaluate(sys_cfg['DesignTarget'], app_result, tech_result)
                print("\nModel results:")
                print(model_result)
                results_to_csv(apps_cfg, sys_cfg, apps_result_name, tech_result, model_result, csv_filepath)

    print(f"\n✓ Model results saved to CSV: {csv_filepath}")


if __name__ == '__main__':
    main()