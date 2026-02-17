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

    # Check info for config 
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

    required = set(['DesignTarget', 'Capacity', 'WordWidth'])

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
        if not os.path.exists(tech_cfg['array_characterization_config']):
            print(f"Tech config path {tech_cfg['array_characterization_config']} is not real.")
            sys.exit(1)
        with open(tech_cfg['array_characterization_config'], 'r') as f:
            premade_tech_cfg = yaml.load(f, Loader=yaml.FullLoader)
            premade_tech_cfg.update(tech_cfg)
            tech_cfg = premade_tech_cfg
        print("Loaded tech config from path: ", tech_cfg['array_characterization_config'])
        
        required = set(['Associativity', 'MemoryCellInputFile'])
        if not required.issubset(tech_cfg):
            print(f"Provide required tech inputs for new ArrayCharacterization run: {required}")
            sys.exit(1)

    # logic checks
    if apps_cfg['profiler'] == "dynamorio" and sys_cfg['DesignTarget'] == "cache":
        print("Choose Sniper or Perf as a profiler for cache modeling.")
        sys.exit(1)
    #TODO: add word width vs. read/write size logic checks

    return sys_cfg, apps_cfg, tech_cfg

def main():
    
    # TODO: make it possible to loop over (potentially) multiple configs/inputs

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

    # # Useful var for processes
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
            apps_out = run_drio(apps_cfg['executable'], original_dir)
        elif apps_cfg['profiler'] == "sniper":
            apps_out = run_sniper(apps_cfg['level'], apps_cfg['executable'], apps_cfg['config'], original_dir)
        else: 
            apps_out = run_perf(apps_cfg['level'], apps_cfg['arch'] if apps_cfg['arch'] != None else None, apps_cfg['executable'], original_dir)

        os.chdir(original_dir)

    else: # using existing run    
        apps_patternconfig = apps_cfg['patternconfig_path']
    
    apps_output_dir = os.path.join(results_dir, "apps_output")
    pattern_files = [f for f in os.listdir(apps_output_dir)
            if f.endswith(".json") and "pattern" in f.lower()]

    if not pattern_files:
        raise FileNotFoundError(f"No pattern config JSON found in {apps_output_dir}")

    # If multiple pattern files exist, take the first one (or implement custom logic)
    apps_patternconfig = os.path.join(apps_output_dir, pattern_files[0])
    
    # parse & print apps output
    with open(apps_patternconfig, 'r') as f:
        apps_result = json.load(f)
    print("\nApps output:")
    print(apps_result)

    if tech_cfg['run'] == "new":
        # combine tech and system configs
        arraychar_cfg = tech_cfg
        arraychar_cfg.update(sys_cfg)
        os.chdir(results_dir)
        os.mkdir("tech_output")
        os.chdir(original_dir)
        arraychar_cfg["OutputDirectory"] = os.path.abspath(os.path.join(results_dir, "tech_output")) + "/"
        print("\nUpdated Tech YAML:")
        print(arraychar_cfg)

        # Run Array Characterization
        tech_yaml_str = yaml.dump(arraychar_cfg)
        
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.yaml', delete=False) as tech_yaml:
            tech_yaml.write(tech_yaml_str)
            tech_yaml_path = tech_yaml.name

        tech_result = run_array_characterization(tech_yaml_path, Tech_Dir)
        os.remove(tech_yaml_path)
    else:
        tech_result = parse_array_char_output(tech_cfg['array_characterization_result_path'])
    print("\nTech Output:")
    print(tech_result)

    # ANALYTICAL MODEL - handle single or multiple benchmarks
    os.chdir(results_dir)
    os.mkdir("model_output")
    os.chdir(original_dir)

    csv_filename = f"{config_name}_results.csv"
    csv_filepath = os.path.join(results_dir, "model_output", csv_filename)

    if apps_cfg['profiler'] == "sniper":
        # Sniper outputs a list of benchmarks (one per thread/core)
        if apps_cfg['multithread']:
            print("\nEvaluating multiple benchmarks from Sniper output...")
            for i, benchmark in enumerate(apps_result):
                model_result = evaluate(sys_cfg['DesignTarget'], benchmark, tech_result)
                print(f"\nModel results for benchmark {i}:")
                print(model_result)
                results_to_csv(apps_cfg, sys_cfg, config_name, tech_result, model_result, csv_filepath)
            
        else:
            apps_result_single = apps_result[0]
            model_result = evaluate(sys_cfg['DesignTarget'], apps_result_single, tech_result)
            print("\nModel results:")
            print(model_result)
            results_to_csv(apps_cfg, sys_cfg, config_name, tech_result, model_result, csv_filepath)

    else:
        model_result = evaluate(sys_cfg['DesignTarget'], apps_result, tech_result)
        print("\nModel results:")
        print(model_result)
        results_to_csv(apps_cfg, sys_cfg, config_name, tech_result, model_result, csv_filepath)

        
    
    print(f"\n✓ Model results saved to CSV: {csv_filepath}")

if __name__ == '__main__':
    main()

