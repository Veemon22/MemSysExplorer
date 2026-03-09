import json
import os
import re
import subprocess
from .utils import *

#Debug Variables
Make_Check_PRINT_ON = True

# run array characterization
def run_array_characterization(tech_yaml_path, Tech_Dir):
     # Checking to see if make has been ran in tech/ArrayCharacterization
    NVSim_File_Path = os.path.join(Tech_Dir, "nvsim")
    if not os.path.exists(NVSim_File_Path):
        if Make_Check_PRINT_ON:
            print("NVSim binary not found. Running make in tech/ArrayCharacterization now")
        subprocess.run(["make"], cwd=Tech_Dir)

    print("\nRunning array characterization interface..")

    try:
        tech_result = subprocess.run(["./nvsim", tech_yaml_path], 
                                     capture_output=True, 
                                     text=True, cwd=Tech_Dir)
    except subprocess.CalledProcessError as e:
        print(e.stderr)
    print(tech_result.stdout)

    match = re.search(r"Results written to ([^\s]+\.yaml)", tech_result.stdout)
    print(match)
    if match:
        result_yaml_path = match.group(1)
        result_yaml_path = os.path.join(Tech_Dir, result_yaml_path)
    
    print("Parsing array characterization results from:", result_yaml_path)
    tech_result = parse_array_char_output(result_yaml_path)
    return tech_result

# run DynamoRIO
def run_drio(executable, original_dir):

    apps_dir = os.path.join(original_dir, "apps")
    built_json_path = os.path.join(apps_dir, "built_profilers.json")
    if not os.path.exists(built_json_path):
        print("Built profilers JSON not found. Running proper processes now")
        subprocess.run(["source", "setup/setup.sh", "dynamorio"], cwd=apps_dir, shell=True)
        subprocess.run(["make", "dynamorio"], cwd=apps_dir)

    with open(built_json_path, 'r') as f:
        built_profilers = json.load(f)
        if built_profilers.get("dynamorio") != True:
            print("DynamoRIO profiler not built. Running proper processes now")
            subprocess.run(["source", "setup/setup.sh", "1"], cwd=apps_dir, shell=True)
            subprocess.run(["make", "dynamorio"], cwd=apps_dir)
    
    print("\nRunning apps profiling interface..")
    try:
        apps_out = subprocess.run(["python3", os.path.join(apps_dir, "main.py"),
                                "--profiler", "dynamorio",
                                "--action", "both",
                                "--config", os.path.join(apps_dir, "config/memcount_config.txt"),
                                "--executable", executable],
                                capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        print(e.stderr)
    print(apps_out.stdout)
    return apps_out

def run_perf(level, arch, executable, original_dir):

    apps_dir = os.path.join(original_dir, "apps")
    built_json_path = os.path.join(apps_dir, "built_profilers.json")
    if not os.path.exists(built_json_path):
        print("Built profilers JSON not found. Running proper processes now")
        subprocess.run(["make", "perf"], cwd=apps_dir)
    
    with open(built_json_path, 'r') as f:
        built_profilers = json.load(f)
        if built_profilers.get("perf") != True:
            print("Perf profiler not built. Running proper processes now")
            subprocess.run(["make", "perf"], cwd=apps_dir)

    print("\nRunning apps profiling interface..")
    try:
        apps_out = subprocess.run(["python3", os.path.join(apps_dir, "main.py"),
                                "--profiler", "perf",
                                "--action", "both",
                                "--arch", arch,
                                "--level", level,
                                "--executable", executable],
                                capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        print(e.stderr)
    print(apps_out.stdout)
    return apps_out
    
# Running Sniper

def run_sniper(level, executable, config, original_dir):

    apps_dir = os.path.join(original_dir, "apps")
    built_json_path = os.path.join(apps_dir, "built_profilers.json")
    if not os.path.exists(built_json_path):
        print("Built profilers JSON not found. Running proper processes now")
        subprocess.run(["source", "setup/setup.sh", "3"], cwd=apps_dir, shell=True)
        subprocess.run(["make", "sniper"], cwd=apps_dir)
    
    with open(built_json_path, 'r') as f:
        built_profilers = json.load(f)
        if built_profilers.get("sniper") != True:
            print("Sniper profiler not built. Running proper processes now")
            subprocess.run(["source", "setup/setup.sh", "3"], cwd=apps_dir, shell=True)
            subprocess.run(["make", "sniper"], cwd=apps_dir)

    print("\nRunning apps profiling interface..")
    try:
        apps_out = subprocess.run(["python3", os.path.join(apps_dir, "main.py"),
                                "-p", "sniper",
                                "-a", "both",
                                "--config", config,
                                "--level", level,
                                "--results_dir", ".",
                                "--executable", executable],
                                capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        print(e.stderr)
    print(apps_out.stdout)
    return apps_out
